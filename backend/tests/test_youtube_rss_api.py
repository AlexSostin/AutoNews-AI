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


