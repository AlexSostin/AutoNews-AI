"""
Tests for api_views.py — Batch 3: YouTube, RSS, NewsItem, AutoPublish
Tests for api_views.py — Batch 3: YouTube, RSS, NewsItem
Covers: YouTubeChannelViewSet, RSSFeedViewSet, RSSNewsItemViewSet
"""
import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from django.contrib.auth.models import User

pytestmark = pytest.mark.django_db

API = '/api/v1'
UA = {'HTTP_USER_AGENT': 'TestBrowser/1.0'}


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username='staffyt', email='staffyt@test.com',
        password='Pass123!', is_staff=True,
    )


@pytest.fixture
def staff_client(staff_user):
    client = APIClient(**UA)
    client.force_authenticate(user=staff_user)
    return client


@pytest.fixture
def anon_client():
    return APIClient(**UA)


@pytest.fixture
def youtube_channel(db):
    from news.models import YouTubeChannel
    return YouTubeChannel.objects.create(
        name='Test Channel', channel_url='https://youtube.com/@testchannel',
        is_enabled=True,
    )


@pytest.fixture
def rss_feed(db):
    from news.models import RSSFeed
    return RSSFeed.objects.create(
        name='Test Feed', feed_url='https://example.com/feed.xml',
        is_enabled=True,
    )


@pytest.fixture
def rss_news_item(rss_feed):
    from news.models import RSSNewsItem
    return RSSNewsItem.objects.create(
        rss_feed=rss_feed,
        title='Breaking: New Car',
        source_url='https://example.com/news/1',
        status='new',
    )


# ═══════════════════════════════════════════════════════════════════════════
# YouTubeChannelViewSet Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestYouTubeChannelViewSet:

    def test_list_channels(self, staff_client, youtube_channel):
        resp = staff_client.get(f'{API}/youtube-channels/', **UA)
        assert resp.status_code == 200

    @patch('ai_engine.main.create_pending_article')
    def test_generate_pending_success(self, mock_create, staff_client, youtube_channel):
        mock_create.return_value = {'success': True, 'message': 'Started'}
        resp = staff_client.post(f'{API}/youtube-channels/{youtube_channel.id}/generate_pending/', {
            'video_url': 'https://youtube.com/watch?v=123',
            'video_id': '123',
            'video_title': 'Test Video'
        }, format='json', **UA)
        assert resp.status_code == 200

    def test_generate_pending_no_url(self, staff_client, youtube_channel):
        resp = staff_client.post(f'{API}/youtube-channels/{youtube_channel.id}/generate_pending/', {
            'video_title': 'Missing URL'
        }, format='json', **UA)
        assert resp.status_code == 400

    @patch('ai_engine.main.create_pending_article')
    def test_generate_pending_failure(self, mock_create, staff_client, youtube_channel):
        mock_create.return_value = {'success': False, 'error': 'Failed'}
        resp = staff_client.post(f'{API}/youtube-channels/{youtube_channel.id}/generate_pending/', {
            'video_url': 'https://youtube.com/watch?v=123',
        }, format='json', **UA)
        assert resp.status_code == 400

    @patch('subprocess.Popen')
    def test_scan_all_youtube(self, mock_popen, staff_client, youtube_channel):
        resp = staff_client.post(f'{API}/youtube-channels/scan_all/', **UA)
        assert resp.status_code == 200
        assert mock_popen.called

    def test_scan_all_youtube_unauthorized(self, anon_client):
        resp = anon_client.post(f'{API}/youtube-channels/scan_all/', **UA)
        assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════
# RSSFeedViewSet Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestRSSFeedViewSet:

    def test_with_pending_counts(self, staff_client, rss_feed, rss_news_item):
        from news.models import PendingArticle
        # Create a pending article linked to the feed
        PendingArticle.objects.create(
            title='Test Pending',
            rss_feed=rss_feed,
            status='pending',
            content='content'
        )

        resp = staff_client.get(f'{API}/rss-feeds/with_pending_counts/', **UA)
        assert resp.status_code == 200
        assert len(resp.data) > 0
        assert 'pending_count' in resp.data[0]
        assert resp.data[0]['pending_count'] >= 1

    @patch('subprocess.Popen')
    def test_scan_now(self, mock_popen, staff_client, rss_feed):
        resp = staff_client.post(f'{API}/rss-feeds/{rss_feed.id}/scan_now/', **UA)
        assert resp.status_code == 200
        assert mock_popen.called

    @patch('subprocess.Popen')
    def test_scan_all_rss(self, mock_popen, staff_client, rss_feed):
        resp = staff_client.post(f'{API}/rss-feeds/scan_all/', **UA)
        assert resp.status_code == 200
        assert mock_popen.called

    @patch('subprocess.Popen')
    def test_check_license(self, mock_popen, staff_client, rss_feed):
        resp = staff_client.post(f'{API}/rss-feeds/{rss_feed.id}/check_license/', **UA)
        assert resp.status_code == 200
        assert mock_popen.called

    @patch('subprocess.Popen')
    def test_check_all_licenses(self, mock_popen, staff_client):
        resp = staff_client.post(f'{API}/rss-feeds/check_all_licenses/', {'unchecked_only': True}, format='json', **UA)
        assert resp.status_code == 200
        assert mock_popen.called

