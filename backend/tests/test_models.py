"""
Tests for core Django models: AutomationSettings singleton, counters,
AutoPublishLog, RSSFeed safety_score, PendingArticle status flow.
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from news.models import (
    AutomationSettings, AutoPublishLog, PendingArticle,
    Article, Category, RSSFeed
)


@pytest.fixture
def category(db):
    return Category.objects.create(name='Test', slug='test')


@pytest.mark.django_db
class TestAutomationSettingsSingleton:
    """AutomationSettings must always be a singleton (pk=1)."""

    def test_singleton_load(self):
        """load() always returns same instance."""
        s1 = AutomationSettings.load()
        s2 = AutomationSettings.load()
        assert s1.pk == s2.pk == 1

    def test_singleton_save(self):
        """Multiple saves don't create duplicates."""
        s = AutomationSettings.load()
        s.auto_publish_enabled = True
        s.save()
        s.auto_publish_enabled = False
        s.save()
        assert AutomationSettings.objects.count() == 1

    def test_daily_counter_reset(self):
        """Counters reset when date changes."""
        s = AutomationSettings.load()
        s.auto_publish_today_count = 5
        s.rss_articles_today = 10
        s.counters_reset_date = (timezone.now() - timedelta(days=1)).date()
        s.save()

        s.reset_daily_counters()
        s.refresh_from_db()

        assert s.auto_publish_today_count == 0
        assert s.rss_articles_today == 0
        assert s.counters_reset_date == timezone.now().date()

    def test_counters_no_reset_same_day(self):
        """Counters don't reset when called same day."""
        s = AutomationSettings.load()
        s.auto_publish_today_count = 5
        s.counters_reset_date = timezone.now().date()
        s.save()

        s.reset_daily_counters()
        s.refresh_from_db()
        assert s.auto_publish_today_count == 5


@pytest.mark.django_db
class TestAutoPublishLog:
    """Tests for AutoPublishLog model."""

    def test_create_log(self, category):
        """Log entries are created correctly."""
        log = AutoPublishLog.objects.create(
            decision='published',
            reason='Quality 9/10 meets threshold 7/10',
            quality_score=9,
            safety_score='safe',
            image_policy='original',
            feed_name='BMW Press',
            article_title='BMW X5 2026 Review',
            content_length=5000,
            has_image=True,
            has_specs=True,
            tag_count=3,
            category_name='News',
        )
        assert log.pk is not None
        assert log.decision == 'published'
        assert 'BMW X5' in str(log)

    def test_ordering(self, category):
        """Logs are ordered by -created_at (newest first)."""
        AutoPublishLog.objects.create(decision='published', reason='First', article_title='A')
        AutoPublishLog.objects.create(decision='skipped_quality', reason='Second', article_title='B')

        logs = AutoPublishLog.objects.all()
        assert logs[0].article_title == 'B'  # Most recent first


@pytest.mark.django_db
class TestRSSFeedSafetyScore:
    """Tests for RSSFeed.safety_score computed property."""

    def test_safe_feed(self):
        """Green license + all checks passed = safe."""
        feed = RSSFeed.objects.create(
            name='Safe', feed_url='https://safe.com/rss', is_enabled=True,
            license_status='green',
            safety_checks={'robots': {'passed': True}, 'tos': {'passed': True}},
        )
        assert feed.safety_score == 'safe'

    def test_unsafe_feed(self):
        """Red license = unsafe."""
        feed = RSSFeed.objects.create(
            name='Unsafe', feed_url='https://unsafe.com/rss', is_enabled=True,
            license_status='red',
        )
        assert feed.safety_score == 'unsafe'

    def test_review_feed_no_checks(self):
        """No safety_checks = review."""
        feed = RSSFeed.objects.create(
            name='Review', feed_url='https://review.com/rss', is_enabled=True,
            license_status='unchecked',
        )
        assert feed.safety_score == 'review'

    def test_review_feed_partial_checks(self):
        """Some checks failed = review."""
        feed = RSSFeed.objects.create(
            name='Partial', feed_url='https://partial.com/rss', is_enabled=True,
            license_status='green',
            safety_checks={'robots': {'passed': True}, 'tos': {'passed': False}},
        )
        assert feed.safety_score == 'review'


@pytest.mark.django_db
class TestPendingArticleStatusFlow:
    """Tests for PendingArticle status transitions."""

    def test_pending_to_published(self, category):
        """PendingArticle can transition from pending to published."""
        p = PendingArticle.objects.create(
            title='Test', content='<p>C</p>',
            suggested_category=category,
            quality_score=8, status='pending',
        )
        assert p.status == 'pending'

        p.status = 'published'
        p.is_auto_published = True
        p.reviewed_at = timezone.now()
        p.save()
        p.refresh_from_db()

        assert p.status == 'published'
        assert p.is_auto_published is True

    def test_pending_to_rejected(self, category):
        """PendingArticle can be rejected."""
        p = PendingArticle.objects.create(
            title='Bad Article', content='<p>C</p>',
            suggested_category=category,
            quality_score=3, status='pending',
        )
        p.status = 'rejected'
        p.review_notes = 'Low quality'
        p.save()
        p.refresh_from_db()

        assert p.status == 'rejected'
        assert p.review_notes == 'Low quality'
