import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from unittest.mock import patch, MagicMock
from news.models import RSSFeed, RSSNewsItem

@pytest.fixture
def rss_feed(db):
    return RSSFeed.objects.create(
        name='Test Feed',
        feed_url='https://test.com/rss',
        website_url='https://test.com',
        is_enabled=True,
    )

@pytest.mark.django_db
class TestRSSFeedAPIViewSetExtensions:

    def test_export_opml_endpoint(self, authenticated_client, rss_feed):
        # Create a disabled feed to ensure it is excluded
        RSSFeed.objects.create(
            name='Disabled Feed',
            feed_url='https://disabled.com/rss',
            is_enabled=False
        )

        resp = authenticated_client.get('/api/v1/rss-feeds/export_opml/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp['Content-Type'] == 'application/xml'
        
        # Verify content contains OPML structure and enabled feed
        content = resp.content.decode('utf-8')
        assert '<opml version="2.0">' in content
        assert 'Test Feed' in content
        assert 'https://test.com/rss' in content
        assert 'https://test.com' in content
        
        # Verify disabled feed is NOT included
        assert 'Disabled Feed' not in content

    def test_recent_entries_endpoint(self, authenticated_client, rss_feed):
        # Create DB entries
        for i in range(3):
            RSSNewsItem.objects.create(
                rss_feed=rss_feed,
                title=f'DB Article {i}',
                source_url=f'https://test.com/db{i}',
                content_hash=f'hash{i}',
                published_at=timezone.now() - timedelta(minutes=i)
            )

        resp = authenticated_client.get(f'/api/v1/rss-feeds/{rss_feed.id}/recent_entries/')
        assert resp.status_code == status.HTTP_200_OK
        
        data = resp.json()
        assert 'entries' in data
        # Should have the 3 DB entries
        assert len(data['entries']) == 3
        assert 'DB Article 0' in [e['title'] for e in data['entries']]
