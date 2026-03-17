"""
Tests for System Graph health logic.

Comprehensive tests validating that each System Graph node computes
the correct health status based on real data conditions.
"""
import pytest
from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from news.models import (
    Article, PendingArticle, RSSFeed, ArticleEmbedding,
    FrontendEventLog, BackendErrorLog, SecurityLog, GSCReport,
    AutoPublishLog, AutomationSettings, TOTPDevice, WebAuthnCredential,
    ArticleFeedback,
)
from news.models.sources import YouTubeVideoCandidate, YouTubeChannel


UA = {'HTTP_USER_AGENT': 'Mozilla/5.0 TestClient/1.0'}
GRAPH_URL = '/api/v1/health/graph-data/'


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def admin_client(db):
    user = User.objects.create_superuser(
        username='graph_admin', email='g@test.com', password='pw',
        is_staff=True,
    )
    client = APIClient(**UA)
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def anon_client():
    return APIClient(**UA)


def _find_node(nodes, node_id):
    """Find a node by id in the response."""
    return next((n for n in nodes if n['id'] == node_id), None)


def _find_warning(warnings, substring):
    """Find a warning containing substring."""
    return next((w for w in warnings if substring.lower() in w['message'].lower()), None)


# ═══════════════════════════════════════════════════════════════════
# 1. All Nodes Present
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAllNodesPresent:
    """Verify all expected node IDs exist."""

    EXPECTED_NODE_IDS = [
        'rss_feeds', 'rss_items', 'youtube', 'video_candidates',
        'pending_articles', 'articles', 'article_images',
        'brands', 'brand_aliases', 'car_specs', 'vehicle_specs',
        'categories', 'tag_groups', 'tags',
        'comments', 'ratings', 'favorites', 'feedback',
        'embeddings', 'ab_tests', 'ai_pipeline', 'auto_publish_logs',
        'subscribers', 'errors', 'scheduler',
        'security', 'gsc_sync', 'two_factor_auth',
        'in_app_notifications',
    ]

    def test_all_expected_nodes_exist(self, admin_client):
        client, _ = admin_client
        resp = client.get(GRAPH_URL)
        assert resp.status_code == 200
        node_ids = {n['id'] for n in resp.data['nodes']}
        for expected_id in self.EXPECTED_NODE_IDS:
            assert expected_id in node_ids, f"Missing node: {expected_id}"

    def test_node_count_minimum(self, admin_client):
        """Should have at least 28 nodes (the full graph)."""
        client, _ = admin_client
        resp = client.get(GRAPH_URL)
        assert len(resp.data['nodes']) >= 28


# ═══════════════════════════════════════════════════════════════════
# 2. RSS Feed Health
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestRSSFeedHealth:

    def test_failing_rss_feed_shows_error(self, admin_client):
        client, _ = admin_client
        RSSFeed.objects.create(
            name='Broken Feed', feed_url='https://broken.example.com/rss',
            is_enabled=True, consecutive_failures=5,
        )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'rss_feeds')
        assert node['health'] == 'error'
        assert node['breakdown']['failing'] >= 1

    def test_stale_rss_feed_shows_warning(self, admin_client):
        client, _ = admin_client
        RSSFeed.objects.create(
            name='Stale Feed', feed_url='https://stale.example.com/rss',
            is_enabled=True, consecutive_failures=0,
            last_successful_fetch=timezone.now() - timedelta(hours=72),
        )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'rss_feeds')
        assert node['breakdown']['stale'] >= 1

    def test_healthy_rss_shows_healthy(self, admin_client):
        client, _ = admin_client
        RSSFeed.objects.create(
            name='Good Feed', feed_url='https://good.example.com/rss',
            is_enabled=True, consecutive_failures=0,
            last_successful_fetch=timezone.now() - timedelta(hours=1),
        )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'rss_feeds')
        assert node['breakdown']['healthy'] >= 1


# ═══════════════════════════════════════════════════════════════════
# 3. Scheduler Health
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSchedulerHealth:

    def test_dead_scheduler_shows_error(self, admin_client):
        """No heartbeat → error."""
        client, _ = admin_client
        cache.delete('scheduler:heartbeat')
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'scheduler')
        assert node is not None
        assert node['health'] == 'error'
        warn = _find_warning(resp.data['warnings'], 'scheduler is dead')
        assert warn is not None

    @patch('news.api_views.system_graph.get_scheduler_heartbeat')
    def test_alive_scheduler_shows_healthy(self, mock_hb, admin_client):
        """Fresh heartbeat → healthy."""
        client, _ = admin_client
        mock_hb.return_value = timezone.now().isoformat()
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'scheduler')
        assert node is not None
        assert '✅' in node['breakdown']['heartbeat']

    def test_stuck_articles_show_error(self, admin_client):
        """Articles past their scheduled publish time → error."""
        client, _ = admin_client
        cache.set('scheduler:heartbeat', timezone.now().isoformat(), 300)
        Article.objects.create(
            title='Stuck Article', slug='stuck-art', content='<p>C</p>',
            is_published=False, is_deleted=False,
            scheduled_publish_at=timezone.now() - timedelta(minutes=10),
        )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'scheduler')
        assert '🚨' in node['breakdown']['scheduled_publish']
        warn = _find_warning(resp.data['warnings'], 'stuck')
        assert warn is not None


# ═══════════════════════════════════════════════════════════════════
# 4. Security Monitoring
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSecurityHealth:

    def test_brute_force_shows_error(self, admin_client):
        """21+ failed logins in 24h → error."""
        client, _ = admin_client
        for i in range(21):
            SecurityLog.objects.create(
                action='login_failed',
                ip_address='192.168.1.100',
            )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'security')
        assert node is not None
        assert node['health'] == 'error'
        assert node['breakdown']['failed_logins_24h'] >= 21
        warn = _find_warning(resp.data['warnings'], 'brute force')
        assert warn is not None

    def test_suspicious_activity_shows_warning(self, admin_client):
        """6-20 failed logins → warning."""
        client, _ = admin_client
        for i in range(6):
            SecurityLog.objects.create(
                action='login_failed',
                ip_address='10.0.0.1',
            )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'security')
        assert node['health'] == 'warning'

    def test_account_locked_shows_error(self, admin_client):
        """Account locked → error."""
        client, user = admin_client
        SecurityLog.objects.create(
            action='account_locked', user=user,
            ip_address='10.0.0.1',
        )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'security')
        assert node['health'] == 'error'
        assert node['breakdown']['accounts_locked_24h'] >= 1

    def test_clean_security_shows_healthy(self, admin_client):
        """No failed logins → healthy."""
        client, user = admin_client
        SecurityLog.objects.create(
            action='login_success', user=user,
        )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'security')
        assert node['health'] == 'healthy'


# ═══════════════════════════════════════════════════════════════════
# 5. GSC Sync Freshness
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGSCHealth:

    def test_stale_gsc_shows_warning(self, admin_client):
        """GSC data >7 days old → warning."""
        client, _ = admin_client
        GSCReport.objects.create(
            date=timezone.now().date() - timedelta(days=10),
            clicks=50, impressions=1000,
        )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'gsc_sync')
        assert node is not None
        assert node['health'] == 'warning'

    def test_very_stale_gsc_shows_error(self, admin_client):
        """GSC data >14 days old → error."""
        client, _ = admin_client
        GSCReport.objects.create(
            date=timezone.now().date() - timedelta(days=20),
            clicks=50, impressions=1000,
        )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'gsc_sync')
        assert node['health'] == 'error'

    def test_fresh_gsc_shows_healthy(self, admin_client):
        """GSC data <7 days old → healthy."""
        client, _ = admin_client
        GSCReport.objects.create(
            date=timezone.now().date() - timedelta(days=2),
            clicks=100, impressions=2000,
        )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'gsc_sync')
        assert node['health'] == 'healthy'

    def test_no_gsc_data_shows_warning(self, admin_client):
        """No GSC reports → warning."""
        client, _ = admin_client
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'gsc_sync')
        assert node['health'] == 'warning'
        assert 'never' in node['breakdown']['last_sync'].lower()


# ═══════════════════════════════════════════════════════════════════
# 6. YouTube Video Candidates
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestVideoCandidatesHealth:

    def test_many_pending_shows_warning(self, admin_client):
        """11+ new videos → warning."""
        client, _ = admin_client
        channel = YouTubeChannel.objects.create(
            name='Test Channel', channel_url='https://youtube.com/@test',
        )
        for i in range(12):
            YouTubeVideoCandidate.objects.create(
                channel=channel, video_id=f'vid_{i}', title=f'Video {i}',
                status='new',
            )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'video_candidates')
        assert node is not None
        assert node['health'] == 'warning'
        assert node['breakdown']['new'] == 12

    def test_few_pending_shows_healthy(self, admin_client):
        """≤10 new videos → healthy."""
        client, _ = admin_client
        channel = YouTubeChannel.objects.create(
            name='Test Channel 2', channel_url='https://youtube.com/@test2',
        )
        for i in range(3):
            YouTubeVideoCandidate.objects.create(
                channel=channel, video_id=f'vid2_{i}', title=f'Video {i}',
                status='new',
            )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'video_candidates')
        assert node['health'] == 'healthy'


# ═══════════════════════════════════════════════════════════════════
# 7. Auto-Publish Logs
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAutoPublishLogsHealth:

    def test_high_fail_rate_shows_warning(self, admin_client):
        """>20% failure rate → warning."""
        client, _ = admin_client
        for i in range(7):
            AutoPublishLog.objects.create(
                decision='published', reason='Good', article_title=f'Art {i}',
            )
        for i in range(3):
            AutoPublishLog.objects.create(
                decision='failed', reason='Error', article_title=f'Fail {i}',
            )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'auto_publish_logs')
        assert node is not None
        assert node['health'] == 'warning'

    def test_very_high_fail_rate_shows_error(self, admin_client):
        """>50% failure rate → error."""
        client, _ = admin_client
        for i in range(3):
            AutoPublishLog.objects.create(
                decision='published', reason='Good', article_title=f'Art {i}',
            )
        for i in range(7):
            AutoPublishLog.objects.create(
                decision='failed', reason='Error', article_title=f'Fail {i}',
            )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'auto_publish_logs')
        assert node['health'] == 'error'

    def test_healthy_publish_rate(self, admin_client):
        """0% failure → healthy."""
        client, _ = admin_client
        for i in range(5):
            AutoPublishLog.objects.create(
                decision='published', reason='Good', article_title=f'Art {i}',
            )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'auto_publish_logs')
        assert node['health'] == 'healthy'


# ═══════════════════════════════════════════════════════════════════
# 8. 2FA Coverage
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTwoFactorHealth:

    def test_no_2fa_shows_error(self, admin_client):
        """No admins have 2FA → error."""
        client, _ = admin_client
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'two_factor_auth')
        assert node is not None
        assert node['health'] == 'error'
        warn = _find_warning(resp.data['warnings'], '2FA')
        assert warn is not None

    def test_partial_2fa_shows_warning(self, admin_client):
        """< 50% coverage → warning."""
        client, user = admin_client
        # Create 3 more admins without 2FA
        for i in range(3):
            User.objects.create_user(
                f'admin_{i}', f'a{i}@test.com', 'pw', is_staff=True,
            )
        # Only our admin has TOTP
        TOTPDevice.objects.create(user=user, secret='JBSWY3DPEHPK3PXP', is_confirmed=True)
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'two_factor_auth')
        assert node['health'] == 'warning'  # 1/4 = 25% < 50%

    def test_full_2fa_shows_healthy(self, admin_client):
        """100% coverage → healthy."""
        client, user = admin_client
        TOTPDevice.objects.create(user=user, secret='JBSWY3DPEHPK3PXP', is_confirmed=True)
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'two_factor_auth')
        assert node['health'] == 'healthy'  # 1/1 = 100%


# ═══════════════════════════════════════════════════════════════════
# 9. Embedding Coverage
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestEmbeddingHealth:

    def test_low_coverage_shows_warning(self, admin_client):
        """<80% embedding coverage → warning."""
        client, _ = admin_client
        # Create 10 published articles, only 5 with embeddings
        for i in range(10):
            art = Article.objects.create(
                title=f'Emb Art {i}', slug=f'emb-art-{i}',
                content='<p>C</p>', is_published=True,
            )
            if i < 5:
                ArticleEmbedding.objects.create(
                    article=art,
                    embedding_vector=[0.1] * 768,
                )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'embeddings')
        assert node['health'] == 'warning'


# ═══════════════════════════════════════════════════════════════════
# 10. Errors Node
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestErrorsHealth:

    def test_many_errors_shows_error(self, admin_client):
        """>10 unresolved → error."""
        client, _ = admin_client
        for i in range(12):
            BackendErrorLog.objects.create(
                source='api', error_class='TestError', message=f'fail {i}',
            )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'errors')
        assert node['health'] == 'error'

    def test_few_errors_shows_warning(self, admin_client):
        """1-10 unresolved → warning."""
        client, _ = admin_client
        BackendErrorLog.objects.create(
            source='api', error_class='TestError', message='fail',
        )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'errors')
        assert node['health'] == 'warning'

    def test_zero_errors_shows_healthy(self, admin_client):
        """0 unresolved → healthy."""
        client, _ = admin_client
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'errors')
        assert node['health'] == 'healthy'


# ═══════════════════════════════════════════════════════════════════
# 11. Pending Articles
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPendingArticlesHealth:

    def test_overflow_shows_warning(self, admin_client):
        """>20 pending → warning."""
        client, _ = admin_client
        for i in range(25):
            PendingArticle.objects.create(
                title=f'Pending {i}', status='pending',
                content='<p>C</p>', excerpt='E',
            )
        resp = client.get(GRAPH_URL)
        node = _find_node(resp.data['nodes'], 'pending_articles')
        assert node['health'] == 'warning'


# ═══════════════════════════════════════════════════════════════════
# 12. Auth / Access Control
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGraphAuth:

    def test_anonymous_forbidden(self, anon_client):
        resp = anon_client.get(GRAPH_URL)
        assert resp.status_code in [401, 403]

    def test_admin_allowed(self, admin_client):
        client, _ = admin_client
        resp = client.get(GRAPH_URL)
        assert resp.status_code == 200
