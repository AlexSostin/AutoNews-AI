"""
Group 4: Signal tests — notification creation on model events.
Tests that admin notifications are created by Django signals.
"""
import pytest
from news.models import (
    Article, Comment, Subscriber,
    PendingArticle, AdminNotification, CarSpecification, Tag
)


@pytest.fixture
def article(db):
    return Article.objects.create(
        title='Signal Article', slug='signal-article',
        content='<p>Content</p>', is_published=True
    )


@pytest.mark.django_db
class TestNotificationSignals:
    """Tests for auto notification creation signals"""

    def test_new_comment_creates_notification(self, article):
        """New comment should create admin notification"""
        initial = AdminNotification.objects.count()
        Comment.objects.create(
            article=article, name='Tester',
            email='test@test.com', content='Great article!'
        )
        assert AdminNotification.objects.count() > initial

    def test_new_subscriber_creates_notification(self):
        """New subscriber should create admin notification"""
        initial = AdminNotification.objects.count()
        Subscriber.objects.create(email='newsub@test.com')
        assert AdminNotification.objects.count() > initial

    def test_new_article_creates_notification(self):
        """New published article should create admin notification"""
        initial = AdminNotification.objects.count()
        Article.objects.create(
            title='New Signal Art', slug='new-signal-art',
            content='<p>X</p>', is_published=True
        )
        assert AdminNotification.objects.count() > initial

    def test_pending_article_creates_notification(self):
        """New pending article should create admin notification"""
        initial = AdminNotification.objects.count()
        PendingArticle.objects.create(
            title='Pending Signal', content='<p>P</p>', status='pending'
        )
        assert AdminNotification.objects.count() > initial

    def test_update_does_not_duplicate_notification(self, article):
        """Updating an article should NOT create a new notification"""
        count_before = AdminNotification.objects.count()
        article.title = 'Updated Title'
        article.save()
        assert AdminNotification.objects.count() == count_before


@pytest.mark.django_db
class TestCarSpecTagSync:
    """Tests for sync_car_spec_tags signal — auto-tags from CarSpecification"""

    def test_car_spec_signal_runs_without_error(self, article):
        """CarSpec creation should not crash even without Drivetrain tag group"""
        # This should not raise an error
        CarSpecification.objects.create(
            article=article, make='ZEEKR', model='007GT', drivetrain='AWD'
        )
        # Signal runs but doesn't find a matching tag group — no crash

    def test_no_tag_created_when_missing(self, article):
        """Should not create new tags — only add existing ones"""
        initial_tags = Tag.objects.count()
        CarSpecification.objects.create(
            article=article, make='BYD', model='Seal', drivetrain='FWD'
        )
        # FWD tag doesn't exist, so no new tags should be created
        assert Tag.objects.count() == initial_tags
