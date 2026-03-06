"""
Tests for features built in the current session:
- A/B test lifecycle (scheduler cleanup)
- Cache busting (pick-winner, resolve-all)
- EmbeddingStatsView
- SystemGraphView enhancements
- Automation triggers (ab-cleanup, index-articles)
- Token verify endpoint
"""
import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.core.cache import cache
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

from news.models import (
    Article, Category, ArticleTitleVariant, AdminNotification,
    FrontendEventLog, BackendErrorLog,
)

UA = {'HTTP_USER_AGENT': 'Mozilla/5.0 TestClient/1.0'}


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def admin_client(db):
    client = APIClient(**UA)
    user = User.objects.create_superuser(username='test_admin', email='a@t.com', password='pw')
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def anon_client():
    return APIClient(**UA)


@pytest.fixture
def sample_article(db):
    return Article.objects.create(
        title='Tesla Model 3 Review',
        content='<p>Great car</p>',
        is_published=True,
    )


@pytest.fixture
def old_ab_test_with_winner(sample_article):
    """A/B test >30 days old with a winner already picked."""
    old = timezone.now() - timedelta(days=35)
    w = ArticleTitleVariant.objects.create(
        article=sample_article, variant='A', title='Winner Title',
        impressions=100, clicks=15, is_active=False, is_winner=True,
    )
    ArticleTitleVariant.objects.filter(pk=w.pk).update(created_at=old)
    l = ArticleTitleVariant.objects.create(
        article=sample_article, variant='B', title='Loser Title',
        impressions=100, clicks=5, is_active=False, is_winner=False,
    )
    ArticleTitleVariant.objects.filter(pk=l.pk).update(created_at=old)
    return w, l


@pytest.fixture
def old_ab_test_no_winner(sample_article):
    """A/B test >30 days old with NO winner."""
    old = timezone.now() - timedelta(days=33)
    a = ArticleTitleVariant.objects.create(
        article=sample_article, variant='A', title='Title A',
        impressions=100, clicks=5, is_active=True, is_winner=False, auto_pick_threshold=50,
    )
    ArticleTitleVariant.objects.filter(pk=a.pk).update(created_at=old)
    b = ArticleTitleVariant.objects.create(
        article=sample_article, variant='B', title='Title B',
        impressions=100, clicks=12, is_active=True, is_winner=False, auto_pick_threshold=50,
    )
    ArticleTitleVariant.objects.filter(pk=b.pk).update(created_at=old)
    return a, b


@pytest.fixture
def very_old_ab_test_no_winner(sample_article):
    """A/B test >37 days old with NO winner — should auto-pick."""
    old = timezone.now() - timedelta(days=40)
    a = ArticleTitleVariant.objects.create(
        article=sample_article, variant='A', title='Old Title A',
        impressions=100, clicks=5, is_active=True, is_winner=False, auto_pick_threshold=50,
    )
    ArticleTitleVariant.objects.filter(pk=a.pk).update(created_at=old)
    b = ArticleTitleVariant.objects.create(
        article=sample_article, variant='B', title='Old Title B',
        impressions=100, clicks=12, is_active=True, is_winner=False, auto_pick_threshold=50,
    )
    ArticleTitleVariant.objects.filter(pk=b.pk).update(created_at=old)
    return a, b


# ═══════════════════════════════════════════════════════════════════════
# 1. A/B Lifecycle (run_ab_test_lifecycle)
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestABLifecycle:

    def test_lifecycle_deletes_losers_when_winner_exists(self, old_ab_test_with_winner):
        """Winner set + 30d old → losers deleted."""
        from news.scheduler import run_ab_test_lifecycle
        winner, loser = old_ab_test_with_winner

        result = run_ab_test_lifecycle()

        assert result['deleted_loser_sets'] >= 1
        assert not ArticleTitleVariant.objects.filter(pk=loser.pk).exists()
        assert ArticleTitleVariant.objects.filter(pk=winner.pk).exists()

    def test_lifecycle_warns_at_30_days(self, old_ab_test_no_winner):
        """30-36d no winner → AdminNotification created."""
        from news.scheduler import run_ab_test_lifecycle

        result = run_ab_test_lifecycle()

        assert result['warned_articles'] >= 1
        notif = AdminNotification.objects.filter(title__contains='A/B Test needs a winner')
        assert notif.exists()

    def test_lifecycle_no_warn_if_recent_warning(self, old_ab_test_no_winner, sample_article):
        """Warning already sent <7d ago → skip."""
        from news.scheduler import run_ab_test_lifecycle
        # Pre-create a recent warning
        AdminNotification.objects.create(
            notification_type='warning',
            title='⚠️ A/B Test needs a winner',
            message='Test',
            link=f'/admin/ab-testing?article={sample_article.id}',
        )

        result = run_ab_test_lifecycle()

        assert result['warned_articles'] == 0

    def test_lifecycle_force_picks_at_37_days(self, very_old_ab_test_no_winner):
        """37d+ no winner → auto-pick by CTR + delete losers."""
        from news.scheduler import run_ab_test_lifecycle

        result = run_ab_test_lifecycle()

        assert result['force_picked'] >= 1

    def test_lifecycle_ignores_young_tests(self, sample_article):
        """<30d → no action at all."""
        from news.scheduler import run_ab_test_lifecycle
        ArticleTitleVariant.objects.create(
            article=sample_article, variant='A', title='Young A',
            impressions=50, clicks=5, is_active=True, is_winner=False,
        )
        ArticleTitleVariant.objects.create(
            article=sample_article, variant='B', title='Young B',
            impressions=50, clicks=8, is_active=True, is_winner=False,
        )

        result = run_ab_test_lifecycle()

        assert result['deleted_loser_sets'] == 0
        assert result['warned_articles'] == 0
        assert result['force_picked'] == 0


# ═══════════════════════════════════════════════════════════════════════
# 2. Cache Busting
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCacheBusting:

    def test_pick_winner_busts_bulk_cache(self, admin_client, sample_article):
        """ab_pick_winner via slug → ab_stats_bulk_v1 cache deleted."""
        client, _ = admin_client
        v = ArticleTitleVariant.objects.create(
            article=sample_article, variant='A', title='Cached Title',
            impressions=50, clicks=10, is_active=True, is_winner=False,
        )
        ArticleTitleVariant.objects.create(
            article=sample_article, variant='B', title='Other',
            impressions=50, clicks=5, is_active=True, is_winner=False,
        )

        # Pre-seed cache
        cache.set('ab_stats_bulk_v1', [{'stale': True}], 60)
        assert cache.get('ab_stats_bulk_v1') is not None

        response = client.post(
            f'/api/v1/articles/{sample_article.slug}/ab-pick-winner/',
            {'variant': 'A'}, format='json',
        )

        assert response.status_code == 200
        assert cache.get('ab_stats_bulk_v1') is None  # Cache busted

    def test_frontend_resolve_all_busts_nav_badges(self, admin_client):
        """Frontend events resolve-all → nav_badges_v1 cache deleted."""
        client, _ = admin_client
        FrontendEventLog.objects.create(
            error_type='js_error', message='test error', url='http://localhost/',
        )
        cache.set('nav_badges_v1', {'stale': True}, 60)

        response = client.post('/api/v1/frontend-events/resolve-all/')

        assert response.status_code == 200
        assert cache.get('nav_badges_v1') is None

    def test_backend_resolve_all_busts_nav_badges(self, admin_client):
        """Backend errors resolve-all → nav_badges_v1 cache deleted."""
        client, _ = admin_client
        BackendErrorLog.objects.create(
            source='api', error_class='TestError', message='fail',
        )
        cache.set('nav_badges_v1', {'stale': True}, 60)

        response = client.post('/api/v1/backend-errors/resolve-all/')

        assert response.status_code == 200
        assert cache.get('nav_badges_v1') is None


# ═══════════════════════════════════════════════════════════════════════
# 3. EmbeddingStatsView
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestEmbeddingStats:

    def test_embedding_stats_returns_correct_data(self, admin_client, sample_article):
        """Returns {indexed, total, not_indexed, pct}."""
        client, _ = admin_client
        response = client.get('/api/v1/health/embedding-stats/')

        assert response.status_code == 200
        data = response.data
        assert 'indexed' in data
        assert 'total' in data
        assert 'not_indexed' in data
        assert 'pct' in data
        assert isinstance(data['indexed'], int)
        assert isinstance(data['total'], int)
        assert isinstance(data['pct'], (int, float))

    def test_embedding_stats_requires_admin(self, anon_client):
        """Anon user → 401/403."""
        response = anon_client.get('/api/v1/health/embedding-stats/')
        assert response.status_code in [401, 403]


# ═══════════════════════════════════════════════════════════════════════
# 4. SystemGraphView enhancements
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSystemGraph:

    def test_graph_data_returns_nodes_and_edges(self, admin_client):
        """Response has nodes, edges, warnings."""
        client, _ = admin_client
        response = client.get('/api/v1/health/graph-data/')

        assert response.status_code == 200
        data = response.data
        assert 'nodes' in data
        assert 'edges' in data
        assert isinstance(data['nodes'], list)
        assert len(data['nodes']) > 0

    def test_graph_embeddings_node_has_numeric_breakdown(self, admin_client, sample_article):
        """Embeddings node breakdown has indexed/total as numbers, not strings."""
        client, _ = admin_client
        response = client.get('/api/v1/health/graph-data/')

        assert response.status_code == 200
        emb_node = next(
            (n for n in response.data['nodes'] if n['id'] == 'embeddings'),
            None,
        )
        assert emb_node is not None
        breakdown = emb_node.get('breakdown', {})
        assert 'indexed' in breakdown
        assert 'total' in breakdown
        assert isinstance(breakdown['indexed'], int)
        assert isinstance(breakdown['total'], int)

    def test_graph_data_requires_admin(self, anon_client):
        """Anon → 401/403."""
        response = anon_client.get('/api/v1/health/graph-data/')
        assert response.status_code in [401, 403]


# ═══════════════════════════════════════════════════════════════════════
# 5. Automation Triggers
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAutomationTriggers:

    @patch('news.scheduler.run_ab_test_lifecycle')
    def test_trigger_ab_cleanup(self, mock_lifecycle, admin_client):
        """POST ab-cleanup → calls run_ab_test_lifecycle in background."""
        mock_lifecycle.return_value = {'deleted_loser_sets': 0, 'warned_articles': 0, 'force_picked': 0}
        client, _ = admin_client

        response = client.post('/api/v1/automation/trigger/ab-cleanup/')

        assert response.status_code == 200
        assert 'cleanup' in response.data.get('message', '').lower() or 'lifecycle' in response.data.get('message', '').lower()

    @patch('subprocess.run')
    def test_trigger_index_articles(self, mock_subprocess, admin_client):
        """POST index-articles → starts background subprocess."""
        client, _ = admin_client

        response = client.post('/api/v1/automation/trigger/index-articles/')

        assert response.status_code == 200
        assert 'index' in response.data.get('message', '').lower()


# ═══════════════════════════════════════════════════════════════════════
# 6. Token Verify Endpoint
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTokenVerify:

    def test_token_verify_valid(self):
        """Valid JWT → 200."""
        user = User.objects.create_user(
            username='verify_user', email='v@t.com', password='pw',
        )
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        client = APIClient(**UA)
        response = client.post(
            '/api/v1/token/verify/',
            {'token': access}, format='json',
        )
        assert response.status_code == 200

    def test_token_verify_invalid(self):
        """Garbage token → 401."""
        client = APIClient(**UA)
        response = client.post(
            '/api/v1/token/verify/',
            {'token': 'garbage.invalid.token'}, format='json',
        )
        assert response.status_code == 401
