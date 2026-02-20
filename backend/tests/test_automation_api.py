"""
Tests for Automation API endpoints: settings CRUD, stats, and triggers.
"""
import pytest
from django.utils import timezone
from news.models import (
    AutomationSettings, PendingArticle, Article, Category,
    RSSFeed, AutoPublishLog
)


@pytest.fixture
def category(db):
    return Category.objects.create(name='News', slug='news')


@pytest.fixture
def settings_obj(db):
    s = AutomationSettings.load()
    s.auto_publish_enabled = True
    s.auto_publish_min_quality = 7
    s.auto_publish_require_safe_feed = True
    s.counters_reset_date = timezone.now().date()
    s.save()
    return s


@pytest.fixture
def sample_feeds(db):
    """Create feeds with different safety scores."""
    safe = RSSFeed.objects.create(
        name='Safe Feed', feed_url='https://safe.com/rss', is_enabled=True,
        license_status='green',
        safety_checks={'robots_txt': {'passed': True}, 'tos': {'passed': True}},
        image_policy='original',
    )
    review = RSSFeed.objects.create(
        name='Review Feed', feed_url='https://review.com/rss', is_enabled=True,
        license_status='unchecked', image_policy='pexels_fallback',
    )
    unsafe = RSSFeed.objects.create(
        name='Unsafe Feed', feed_url='https://unsafe.com/rss', is_enabled=True,
        license_status='red', image_policy='pexels_only',
    )
    return safe, review, unsafe


@pytest.mark.django_db
class TestAutomationSettingsAPI:
    """Tests for /api/v1/automation/settings/ endpoint."""

    def test_get_settings(self, authenticated_client, settings_obj):
        """Admin can read automation settings."""
        response = authenticated_client.get('/api/v1/automation/settings/')
        assert response.status_code == 200
        assert 'auto_publish_enabled' in response.data
        assert 'auto_publish_require_safe_feed' in response.data
        assert response.data['auto_publish_enabled'] is True

    def test_update_settings(self, authenticated_client, settings_obj):
        """Admin can update automation settings."""
        response = authenticated_client.put(
            '/api/v1/automation/settings/',
            {'auto_publish_min_quality': 5},
            format='json'
        )
        assert response.status_code == 200
        settings_obj.refresh_from_db()
        assert settings_obj.auto_publish_min_quality == 5

    def test_settings_require_auth(self, api_client, settings_obj):
        """Non-authenticated users get 401/403."""
        response = api_client.get('/api/v1/automation/settings/')
        assert response.status_code in [401, 403]

    def test_toggle_safe_feed_setting(self, authenticated_client, settings_obj):
        """Can toggle the require_safe_feed setting."""
        response = authenticated_client.put(
            '/api/v1/automation/settings/',
            {'auto_publish_require_safe_feed': False},
            format='json'
        )
        assert response.status_code == 200
        assert response.data['auto_publish_require_safe_feed'] is False


@pytest.mark.django_db
class TestAutomationStatsAPI:
    """Tests for /api/v1/automation/stats/ endpoint."""

    def test_stats_overview(self, authenticated_client, settings_obj, category):
        """Stats endpoint returns all expected fields."""
        PendingArticle.objects.create(
            title='Test', content='<p>C</p>',
            suggested_category=category, quality_score=8, status='pending'
        )
        response = authenticated_client.get('/api/v1/automation/stats/')
        assert response.status_code == 200

        data = response.data
        assert 'pending_total' in data
        assert 'pending_high_quality' in data
        assert 'published_today' in data
        assert 'safety_overview' in data
        assert 'eligible' in data
        assert 'recent_decisions' in data
        assert 'decision_breakdown' in data
        assert 'total_decisions' in data

        assert data['pending_total'] >= 1

    def test_stats_safety_overview(self, authenticated_client, settings_obj, sample_feeds):
        """Safety overview counts match enabled feeds."""
        response = authenticated_client.get('/api/v1/automation/stats/')
        assert response.status_code == 200

        safety = response.data['safety_overview']
        assert safety['total_feeds'] == 3
        assert safety['safety_counts']['safe'] == 1
        assert safety['safety_counts']['review'] == 1
        assert safety['safety_counts']['unsafe'] == 1

    def test_stats_decision_log(self, authenticated_client, settings_obj, category):
        """Decision log returns entries after auto-publish."""
        # Create a log entry directly
        AutoPublishLog.objects.create(
            decision='published',
            reason='Quality 8/10 meets threshold',
            quality_score=8,
            article_title='Test Article',
            feed_name='Test Feed',
        )
        response = authenticated_client.get('/api/v1/automation/stats/')
        assert response.status_code == 200
        assert len(response.data['recent_decisions']) >= 1
        assert response.data['total_decisions'] >= 1

    def test_stats_require_auth(self, api_client):
        """Non-authenticated users get 401/403."""
        response = api_client.get('/api/v1/automation/stats/')
        assert response.status_code in [401, 403]
