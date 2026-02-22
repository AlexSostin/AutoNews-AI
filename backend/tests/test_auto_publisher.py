"""
Tests for the auto-publisher engine.
Verifies safety gating, quality thresholds, rate limits, ordering, and decision logging.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import timedelta
from django.utils import timezone
from news.models import (
    AutomationSettings, PendingArticle, Article, Category,
    RSSFeed, AutoPublishLog
)


@pytest.fixture
def category(db):
    return Category.objects.create(name='News', slug='news')


@pytest.fixture
def safe_feed(db):
    """An RSS feed that is considered 'safe'."""
    return RSSFeed.objects.create(
        name='BMW Press',
        feed_url='https://press.bmw.com/rss',
        is_enabled=True,
        license_status='green',
        safety_checks={'robots_txt': {'passed': True}, 'terms_of_service': {'passed': True}},
        image_policy='original',
    )


@pytest.fixture
def unsafe_feed(db):
    """An RSS feed that is considered 'unsafe'."""
    return RSSFeed.objects.create(
        name='Spam Blog',
        feed_url='https://spam-blog.com/rss',
        is_enabled=True,
        license_status='red',
        image_policy='pexels_only',
    )


@pytest.fixture
def settings(db):
    """Pre-configured automation settings."""
    s = AutomationSettings.load()
    s.auto_publish_enabled = True
    s.auto_publish_min_quality = 7
    s.auto_publish_max_per_hour = 5
    s.auto_publish_max_per_day = 20
    s.auto_publish_require_image = False
    s.auto_publish_require_safe_feed = True
    s.auto_image_mode = 'off'
    s.auto_publish_today_count = 0
    s.counters_reset_date = timezone.now().date()
    s.save()
    return s


def _make_pending(category, feed=None, quality=8, title='Test Article', has_image=False):
    """Helper to create a PendingArticle."""
    return PendingArticle.objects.create(
        title=title,
        content='<p>Test content for the article.</p>',
        suggested_category=category,
        rss_feed=feed,
        quality_score=quality,
        featured_image='https://example.com/img.jpg' if has_image else '',
        status='pending',
    )


def _make_article(title='Test Article'):
    """Helper to create an Article (uses M2M categories, not FK)."""
    return Article.objects.create(
        title=title, content='<p>Content</p>', is_published=True
    )


@pytest.mark.django_db
class TestAutoPublisher:
    """Tests for auto_publish_pending function."""

    def test_disabled_returns_zero(self, settings, category):
        """When auto_publish is disabled, nothing is published."""
        settings.auto_publish_enabled = False
        settings.save()

        _make_pending(category, quality=10)

        from ai_engine.modules.auto_publisher import auto_publish_pending
        count, reason = auto_publish_pending()

        assert count == 0
        assert 'disabled' in reason

    @patch('ai_engine.modules.publisher.publish_article')
    def test_quality_threshold(self, mock_publish, settings, category, safe_feed):
        """Only articles meeting quality threshold get published."""
        mock_publish.return_value = _make_article('Published')

        _make_pending(category, safe_feed, quality=4, title='Low Quality')
        _make_pending(category, safe_feed, quality=9, title='High Quality')

        from ai_engine.modules.auto_publisher import auto_publish_pending
        count, _ = auto_publish_pending()

        # Only the high quality one should have been attempted
        assert mock_publish.call_count == 1
        call_kwargs = mock_publish.call_args[1]
        assert call_kwargs['title'] == 'High Quality'

    @patch('ai_engine.modules.publisher.publish_article')
    def test_safety_gating_blocks_unsafe(self, mock_publish, settings, category, unsafe_feed):
        """Articles from unsafe feeds are skipped when require_safe_feed=True."""
        _make_pending(category, unsafe_feed, quality=9, title='Unsafe Feed Article')

        from ai_engine.modules.auto_publisher import auto_publish_pending
        count, _ = auto_publish_pending()

        assert count == 0
        mock_publish.assert_not_called()

        # Check decision log
        log = AutoPublishLog.objects.filter(decision='skipped_safety').first()
        assert log is not None
        assert 'unsafe' in log.reason.lower()

    @patch('ai_engine.modules.publisher.publish_article')
    def test_safety_off_allows_unsafe(self, mock_publish, settings, category, unsafe_feed):
        """When require_safe_feed=False, unsafe feeds are allowed."""
        settings.auto_publish_require_safe_feed = False
        settings.save()

        mock_publish.return_value = _make_article('From Unsafe')
        _make_pending(category, unsafe_feed, quality=9)

        from ai_engine.modules.auto_publisher import auto_publish_pending
        count, _ = auto_publish_pending()

        assert count == 1

    @patch('ai_engine.modules.publisher.publish_article')
    def test_daily_limit(self, mock_publish, settings, category, safe_feed):
        """Publishing stops at daily limit."""
        settings.auto_publish_max_per_day = 2
        settings.auto_publish_today_count = 2
        settings.save()

        _make_pending(category, safe_feed, quality=9)

        from ai_engine.modules.auto_publisher import auto_publish_pending
        count, reason = auto_publish_pending()

        assert count == 0
        assert 'daily limit' in reason

    @patch('ai_engine.modules.publisher.publish_article')
    def test_score_ordering(self, mock_publish, settings, category, safe_feed):
        """Higher quality articles should be published first."""
        articles_published = []

        def track_publish(**kwargs):
            articles_published.append(kwargs['title'])
            return _make_article(kwargs['title'])

        mock_publish.side_effect = track_publish

        # Create in reverse quality order
        _make_pending(category, safe_feed, quality=7, title='Score 7')
        _make_pending(category, safe_feed, quality=10, title='Score 10')
        _make_pending(category, safe_feed, quality=8, title='Score 8')

        from ai_engine.modules.auto_publisher import auto_publish_pending
        count, _ = auto_publish_pending()

        assert count == 3
        # Should be published in descending quality order
        assert articles_published[0] == 'Score 10'
        assert articles_published[1] == 'Score 8'
        assert articles_published[2] == 'Score 7'

    @patch('ai_engine.modules.publisher.publish_article')
    def test_decision_logging(self, mock_publish, settings, category, safe_feed, unsafe_feed):
        """All decisions should be logged to AutoPublishLog."""
        mock_publish.return_value = _make_article('Published')

        _make_pending(category, safe_feed, quality=9, title='Good Article')
        _make_pending(category, unsafe_feed, quality=9, title='Unsafe Article')

        from ai_engine.modules.auto_publisher import auto_publish_pending
        auto_publish_pending()

        logs = AutoPublishLog.objects.all()
        assert logs.count() >= 2

        decisions = set(logs.values_list('decision', flat=True))
        assert 'drafted' in decisions or 'published' in decisions
        assert 'skipped_safety' in decisions

    @patch('ai_engine.modules.publisher.publish_article')
    def test_require_image_skips_no_image(self, mock_publish, settings, category, safe_feed):
        """Articles without images are skipped when require_image=True and auto_image=off."""
        settings.auto_publish_require_image = True
        settings.save()

        _make_pending(category, safe_feed, quality=9, title='No Image', has_image=False)
        _make_pending(category, safe_feed, quality=9, title='Has Image', has_image=True)

        mock_publish.return_value = _make_article('Has Image')

        from ai_engine.modules.auto_publisher import auto_publish_pending
        count, _ = auto_publish_pending()

        # Only the one with image should be published
        assert count == 1
