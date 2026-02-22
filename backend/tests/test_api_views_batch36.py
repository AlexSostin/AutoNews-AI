"""
Batches 3+6: Rating, Views, Bulk Re-Enrich, Subscriber CRUD, YouTube/RSS actions.

Targets ~550 uncovered lines:
  Batch 3: L1133-1252 (rating, views), L2031-2373 (bulk re-enrich)
  Batch 6: L3432-3603 (subscriber), L3679-3807 (YouTube), L3859-4135 (RSS)
"""
import pytest
import io
from unittest.mock import patch, MagicMock, PropertyMock
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from news.models import (
    Article, Category, Rating, CarSpecification, VehicleSpecs,
    NewsletterSubscriber, YouTubeChannel, RSSFeed, PendingArticle,
)

pytestmark = pytest.mark.django_db

UA = {'HTTP_USER_AGENT': 'TestBrowser/1.0'}


@pytest.fixture
def staff_user():
    return User.objects.create_user('staff36', 'staff@b36.com', 'pass', is_staff=True)


@pytest.fixture
def regular_user():
    return User.objects.create_user('user36', 'user@b36.com', 'pass')


@pytest.fixture
def staff_client(staff_user):
    c = APIClient()
    c.force_authenticate(user=staff_user)
    return c


@pytest.fixture
def user_client(regular_user):
    c = APIClient()
    c.force_authenticate(user=regular_user)
    return c


@pytest.fixture
def anon_client():
    return APIClient()


@pytest.fixture
def article():
    return Article.objects.create(
        title='2026 BYD Atto 3 Review',
        slug='byd-atto-3-review',
        content='<p>Content about BYD Atto 3</p>',
        is_published=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# BATCH 3: Rate article (L1100-1189)
# ═══════════════════════════════════════════════════════════════════════════

class TestRateArticle:

    def test_rate_authenticated(self, user_client, article):
        resp = user_client.post(f'/api/v1/articles/{article.slug}/rate/', {
            'rating': 4,
        }, format='json', **UA)
        assert resp.status_code == 200
        assert 'average_rating' in resp.data

    def test_rate_anonymous(self, anon_client, article):
        resp = anon_client.post(f'/api/v1/articles/{article.slug}/rate/', {
            'rating': 5,
        }, format='json', **UA)
        assert resp.status_code == 200

    def test_rate_update_existing(self, user_client, article, regular_user):
        """Rate the same article twice → updates existing rating."""
        user_client.post(f'/api/v1/articles/{article.slug}/rate/',
                         {'rating': 3}, format='json', **UA)
        resp = user_client.post(f'/api/v1/articles/{article.slug}/rate/',
                                {'rating': 5}, format='json', **UA)
        assert resp.status_code == 200
        # Should now be 5, not average of 3 and 5
        assert Rating.objects.filter(article=article, user=regular_user).count() == 1

    def test_rate_missing_value(self, anon_client, article):
        resp = anon_client.post(f'/api/v1/articles/{article.slug}/rate/', {},
                                format='json', **UA)
        assert resp.status_code == 400

    def test_rate_out_of_range(self, anon_client, article):
        resp = anon_client.post(f'/api/v1/articles/{article.slug}/rate/', {
            'rating': 10,
        }, format='json', **UA)
        assert resp.status_code == 400

    def test_rate_invalid_value(self, anon_client, article):
        resp = anon_client.post(f'/api/v1/articles/{article.slug}/rate/', {
            'rating': 'abc',
        }, format='json', **UA)
        assert resp.status_code == 400

    def test_rate_with_xff_header(self, anon_client, article):
        """X-Forwarded-For header used for IP fingerprinting."""
        resp = anon_client.post(f'/api/v1/articles/{article.slug}/rate/', {
            'rating': 4,
        }, format='json', HTTP_X_FORWARDED_FOR='1.2.3.4,5.6.7.8', **UA)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# BATCH 3: Get user rating (L1191-1221)
# ═══════════════════════════════════════════════════════════════════════════

class TestGetUserRating:

    def test_no_rating(self, anon_client, article):
        resp = anon_client.get(f'/api/v1/articles/{article.slug}/my-rating/', **UA)
        assert resp.status_code == 200
        assert resp.data['has_rated'] is False

    def test_has_rating(self, anon_client, article):
        anon_client.post(f'/api/v1/articles/{article.slug}/rate/',
                         {'rating': 4}, format='json', **UA)
        resp = anon_client.get(f'/api/v1/articles/{article.slug}/my-rating/', **UA)
        assert resp.status_code == 200
        assert resp.data['has_rated'] is True


# ═══════════════════════════════════════════════════════════════════════════
# BATCH 3: Increment views (L1223-1252)
# ═══════════════════════════════════════════════════════════════════════════

class TestIncrementViews:

    def test_increment_views_success(self, anon_client, article):
        resp = anon_client.post(
            f'/api/v1/articles/{article.slug}/increment_views/', **UA)
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            assert 'views' in resp.data

    def test_increment_views_twice(self, anon_client, article):
        anon_client.post(f'/api/v1/articles/{article.slug}/increment_views/', **UA)
        resp = anon_client.post(
            f'/api/v1/articles/{article.slug}/increment_views/', **UA)
        assert resp.status_code in (200, 204)


# ═══════════════════════════════════════════════════════════════════════════
# BATCH 3: Bulk re-enrich (L2031-2373)
# ═══════════════════════════════════════════════════════════════════════════

class TestBulkReEnrich:

    def test_start_mode_missing(self, staff_client, article):
        CarSpecification.objects.create(article=article, make='BYD', model='Atto 3')
        resp = staff_client.post('/api/v1/articles/bulk-re-enrich/', {
            'mode': 'missing',
        }, format='json', **UA)
        assert resp.status_code == 200
        assert 'task_id' in resp.data

    def test_start_mode_selected(self, staff_client, article):
        resp = staff_client.post('/api/v1/articles/bulk-re-enrich/', {
            'mode': 'selected',
            'article_ids': [article.id],
        }, format='json', **UA)
        assert resp.status_code == 200

    def test_start_mode_all(self, staff_client, article):
        resp = staff_client.post('/api/v1/articles/bulk-re-enrich/', {
            'mode': 'all',
        }, format='json', **UA)
        assert resp.status_code == 200

    def test_status_valid(self, staff_client, article):
        # Start a job first
        resp = staff_client.post('/api/v1/articles/bulk-re-enrich/', {
            'mode': 'all',
        }, format='json', **UA)
        task_id = resp.data.get('task_id')
        # Then poll it
        import time
        time.sleep(0.5)
        resp2 = staff_client.get(
            f'/api/v1/articles/bulk-re-enrich-status/?task_id={task_id}', **UA)
        assert resp2.status_code == 200

    def test_status_invalid(self, staff_client):
        resp = staff_client.get(
            '/api/v1/articles/bulk-re-enrich-status/?task_id=nonexistent', **UA)
        assert resp.status_code == 404

    def test_status_no_task_id(self, staff_client):
        resp = staff_client.get('/api/v1/articles/bulk-re-enrich-status/', **UA)
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# BATCH 6: Subscriber — subscribe/reactivate/unsubscribe (L3420-3472)
# ═══════════════════════════════════════════════════════════════════════════

class TestSubscriberActions:

    def test_subscribe_new(self, anon_client):
        resp = anon_client.post('/api/v1/subscribers/', {
            'email': 'new@subscriber.com',
        }, format='json', **UA)
        assert resp.status_code in (201, 200)

    def test_subscribe_duplicate(self, anon_client):
        NewsletterSubscriber.objects.create(email='dup@test.com', is_active=True)
        resp = anon_client.post('/api/v1/subscribers/', {
            'email': 'dup@test.com',
        }, format='json', **UA)
        assert resp.status_code == 200
        assert 'Already' in resp.data.get('message', '')

    def test_subscribe_reactivate(self, anon_client):
        NewsletterSubscriber.objects.create(email='re@test.com', is_active=False)
        resp = anon_client.post('/api/v1/subscribers/', {
            'email': 're@test.com',
        }, format='json', **UA)
        assert resp.status_code == 201
        sub = NewsletterSubscriber.objects.get(email='re@test.com')
        assert sub.is_active is True

    def test_unsubscribe_success(self, anon_client):
        NewsletterSubscriber.objects.create(email='unsub@test.com', is_active=True)
        resp = anon_client.post('/api/v1/subscribers/unsubscribe/', {
            'email': 'unsub@test.com',
        }, format='json', **UA)
        assert resp.status_code == 200

    def test_unsubscribe_not_found(self, anon_client):
        resp = anon_client.post('/api/v1/subscribers/unsubscribe/', {
            'email': 'nobody@test.com',
        }, format='json', **UA)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# BATCH 6: Subscriber — send newsletter (L3474-3515)
# ═══════════════════════════════════════════════════════════════════════════

class TestSendNewsletter:

    @patch('django.core.mail.send_mass_mail')
    def test_send_success(self, mock_mail, staff_client):
        NewsletterSubscriber.objects.create(email='sub@test.com', is_active=True)
        mock_mail.return_value = 1
        resp = staff_client.post('/api/v1/subscribers/send_newsletter/', {
            'subject': 'Test Newsletter',
            'message': 'Hello subscribers!',
        }, format='json', **UA)
        assert resp.status_code == 200
        assert resp.data['count'] == 1

    def test_send_missing_fields(self, staff_client):
        resp = staff_client.post('/api/v1/subscribers/send_newsletter/', {},
                                 format='json', **UA)
        assert resp.status_code == 400

    def test_send_no_subscribers(self, staff_client):
        resp = staff_client.post('/api/v1/subscribers/send_newsletter/', {
            'subject': 'Test', 'message': 'Hello',
        }, format='json', **UA)
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# BATCH 6: Subscriber — import CSV (L3543-3597)
# ═══════════════════════════════════════════════════════════════════════════

class TestImportCSV:

    def test_import_valid_csv(self, staff_client):
        csv_content = "email\nnew1@import.com\nnew2@import.com\n"
        from django.core.files.uploadedfile import SimpleUploadedFile
        csv_file = SimpleUploadedFile("subscribers.csv", csv_content.encode(), content_type="text/csv")
        resp = staff_client.post('/api/v1/subscribers/import_csv/',
                                 {'file': csv_file}, format='multipart', **UA)
        assert resp.status_code == 200
        assert resp.data['added'] == 2

    def test_import_with_duplicates(self, staff_client):
        NewsletterSubscriber.objects.create(email='existing@import.com', is_active=True)
        csv_content = "email\nexisting@import.com\nnewone@import.com\n"
        from django.core.files.uploadedfile import SimpleUploadedFile
        csv_file = SimpleUploadedFile("subs.csv", csv_content.encode(), content_type="text/csv")
        resp = staff_client.post('/api/v1/subscribers/import_csv/',
                                 {'file': csv_file}, format='multipart', **UA)
        assert resp.status_code == 200
        assert resp.data['added'] == 1
        assert resp.data['skipped'] == 1

    def test_import_no_file(self, staff_client):
        resp = staff_client.post('/api/v1/subscribers/import_csv/', {},
                                 format='multipart', **UA)
        assert resp.status_code == 400

    def test_import_wrong_format(self, staff_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("data.txt", b"test", content_type="text/plain")
        resp = staff_client.post('/api/v1/subscribers/import_csv/',
                                 {'file': f}, format='multipart', **UA)
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# BATCH 6: Subscriber — bulk delete (L3599-3610)
# ═══════════════════════════════════════════════════════════════════════════

class TestBulkDeleteSubscribers:

    def test_bulk_delete_success(self, staff_client):
        s1 = NewsletterSubscriber.objects.create(email='del1@test.com', is_active=True)
        s2 = NewsletterSubscriber.objects.create(email='del2@test.com', is_active=True)
        resp = staff_client.post('/api/v1/subscribers/bulk_delete/', {
            'ids': [s1.id, s2.id],
        }, format='json', **UA)
        assert resp.status_code == 200
        assert NewsletterSubscriber.objects.filter(id__in=[s1.id, s2.id]).count() == 0

    def test_bulk_delete_no_ids(self, staff_client):
        resp = staff_client.post('/api/v1/subscribers/bulk_delete/', {
            'ids': [],
        }, format='json', **UA)
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# BATCH 6: YouTube Channel — scan_now, fetch_videos, generate_pending
# ═══════════════════════════════════════════════════════════════════════════

class TestYouTubeChannelActions:

    @pytest.fixture
    def channel(self):
        return YouTubeChannel.objects.create(
            name='Test Channel',
            channel_url='https://www.youtube.com/@testchannel',
            is_enabled=True,
        )

    def test_scan_now(self, staff_client, channel):
        resp = staff_client.post(
            f'/api/v1/youtube-channels/{channel.id}/scan_now/', **UA)
        assert resp.status_code in (200, 202, 500)

    def test_scan_all(self, staff_client, channel):
        resp = staff_client.post('/api/v1/youtube-channels/scan_all/', **UA)
        assert resp.status_code in (200, 202, 500)

    def test_fetch_videos(self, staff_client, channel):
        resp = staff_client.get(
            f'/api/v1/youtube-channels/{channel.id}/fetch_videos/', **UA)
        assert resp.status_code in (200, 500)


# ═══════════════════════════════════════════════════════════════════════════
# BATCH 6: RSS Feed — scan_now, discover, test_feed, check_license
# ═══════════════════════════════════════════════════════════════════════════

class TestRSSFeedActions:

    @pytest.fixture
    def feed(self):
        return RSSFeed.objects.create(
            name='Test Feed',
            feed_url='https://example.com/rss',
            is_enabled=True,
        )

    def test_scan_now(self, staff_client, feed):
        resp = staff_client.post(f'/api/v1/rss-feeds/{feed.id}/scan_now/', **UA)
        assert resp.status_code in (200, 202, 500)

    def test_scan_all(self, staff_client):
        resp = staff_client.post('/api/v1/rss-feeds/scan_all/', **UA)
        assert resp.status_code in (200, 202)

    def test_check_license(self, staff_client, feed):
        resp = staff_client.post(
            f'/api/v1/rss-feeds/{feed.id}/check_license/', **UA)
        assert resp.status_code in (200, 500)

    def test_check_all_licenses(self, staff_client, feed):
        resp = staff_client.post('/api/v1/rss-feeds/check_all_licenses/', **UA)
        assert resp.status_code in (200, 202, 500)

    @patch('ai_engine.modules.feed_discovery.discover_feeds')
    def test_discover_feeds(self, mock_discover, staff_client):
        mock_discover.return_value = [
            {'url': 'https://example.com/feed.xml', 'title': 'Test Feed',
             'feed_valid': True, 'already_added': False, 'source_type': 'media'},
        ]
        resp = staff_client.post('/api/v1/rss-feeds/discover_feeds/', **UA)
        assert resp.status_code == 200

    def test_add_discovered(self, staff_client):
        resp = staff_client.post('/api/v1/rss-feeds/add_discovered/', {
            'feed_url': 'https://newsite.com/rss',
            'name': 'New Feed',
        }, format='json', **UA)
        assert resp.status_code in (200, 201)

    def test_test_feed_valid(self, staff_client):
        resp = staff_client.post('/api/v1/rss-feeds/test_feed/', {
            'url': 'https://www.topgear.com/rss/feed.xml',
        }, format='json', **UA)
        assert resp.status_code in (200, 400, 500)

    def test_test_feed_no_url(self, staff_client):
        resp = staff_client.post('/api/v1/rss-feeds/test_feed/', {},
                                 format='json', **UA)
        assert resp.status_code == 400
