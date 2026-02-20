"""
Tests for brands, RSS feeds, and pending articles:
- Brand CRUD (admin)
- RSS Feed CRUD + filtering
- Pending articles (list, status flow)
"""
import pytest
from django.contrib.auth.models import User
from rest_framework import status
from news.models import Brand, RSSFeed, RSSNewsItem, PendingArticle, Category


@pytest.mark.django_db
class TestBrandsCRUD:
    """Admin brand management /api/v1/admin/brands/"""

    def test_list_brands(self, authenticated_client):
        """Staff can list brands"""
        Brand.objects.create(name='Tesla', slug='tesla')
        Brand.objects.create(name='BMW', slug='bmw')
        resp = authenticated_client.get('/api/v1/admin/brands/')
        assert resp.status_code == status.HTTP_200_OK

    def test_create_brand(self, authenticated_client):
        """Staff can create a brand"""
        resp = authenticated_client.post('/api/v1/admin/brands/', {
            'name': 'Mercedes',
            'slug': 'mercedes',
            'country': 'Germany',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert Brand.objects.filter(name='Mercedes').exists()

    def test_update_brand(self, authenticated_client):
        """Staff can update a brand"""
        brand = Brand.objects.create(name='Teslaa', slug='teslaa')
        resp = authenticated_client.patch(f'/api/v1/admin/brands/{brand.id}/', {
            'name': 'Tesla',
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        brand.refresh_from_db()
        assert brand.name == 'Tesla'

    def test_delete_brand(self, authenticated_client):
        """Staff can delete a brand"""
        brand = Brand.objects.create(name='ToDelete', slug='to-delete')
        resp = authenticated_client.delete(f'/api/v1/admin/brands/{brand.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Brand.objects.filter(id=brand.id).exists()

    def test_brands_anonymous_forbidden(self, api_client):
        """Anonymous users cannot manage brands"""
        resp = api_client.post('/api/v1/admin/brands/', {'name': 'Hack'}, format='json')
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestRSSFeeds:
    """RSS Feed CRUD /api/v1/rss-feeds/"""

    def test_list_feeds(self, authenticated_client):
        """Staff can list RSS feeds"""
        RSSFeed.objects.create(name='BMW Press', feed_url='https://press.bmw.com/rss')
        resp = authenticated_client.get('/api/v1/rss-feeds/')
        assert resp.status_code == status.HTTP_200_OK

    def test_create_feed(self, authenticated_client):
        """Staff can create an RSS feed"""
        resp = authenticated_client.post('/api/v1/rss-feeds/', {
            'name': 'Tesla Blog',
            'feed_url': 'https://www.tesla.com/blog/rss',
            'source_type': 'brand',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert RSSFeed.objects.filter(name='Tesla Blog').exists()

    def test_create_duplicate_feed_rejected(self, authenticated_client):
        """Duplicate feed URLs are rejected"""
        RSSFeed.objects.create(name='Existing', feed_url='https://press.bmw.com/rss')
        resp = authenticated_client.post('/api/v1/rss-feeds/', {
            'name': 'Duplicate',
            'feed_url': 'https://press.bmw.com/rss',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestRSSNewsItems:
    """RSS News Items /api/v1/rss-news-items/"""

    def test_list_news_items(self, authenticated_client):
        """Staff can list RSS news items"""
        feed = RSSFeed.objects.create(name='Test Feed', feed_url='https://feed.com/rss')
        RSSNewsItem.objects.create(rss_feed=feed, title='New Car Release', content='<p>Details</p>')
        resp = authenticated_client.get('/api/v1/rss-news-items/')
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPendingArticles:
    """Pending articles /api/v1/pending-articles/"""

    def test_list_pending(self, authenticated_client):
        """Staff can list pending articles"""
        PendingArticle.objects.create(title='Pending Review', content='<p>Review</p>', status='pending')
        resp = authenticated_client.get('/api/v1/pending-articles/')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data['results']) >= 1

    def test_pending_status_filter(self, authenticated_client):
        """Can filter pending articles by status"""
        PendingArticle.objects.create(title='Pending1', content='<p>P</p>', status='pending')
        PendingArticle.objects.create(title='Approved1', content='<p>A</p>', status='approved')
        resp = authenticated_client.get('/api/v1/pending-articles/?status=pending')
        assert resp.status_code == status.HTTP_200_OK
        for item in resp.data['results']:
            assert item['status'] == 'pending'

    def test_reject_pending(self, authenticated_client):
        """Can reject a pending article"""
        pending = PendingArticle.objects.create(title='Reject Me', content='<p>R</p>', status='pending')
        resp = authenticated_client.patch(f'/api/v1/pending-articles/{pending.id}/', {
            'status': 'rejected',
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        pending.refresh_from_db()
        assert pending.status == 'rejected'

    def test_pending_anonymous_forbidden(self, api_client):
        """Anonymous users cannot access pending articles"""
        resp = api_client.get('/api/v1/pending-articles/')
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_pending_article_detail(self, authenticated_client):
        """Can get pending article detail"""
        pending = PendingArticle.objects.create(title='Detail Test', content='<p>D</p>', status='pending')
        resp = authenticated_client.get(f'/api/v1/pending-articles/{pending.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['title'] == 'Detail Test'


@pytest.mark.django_db
class TestRSSNewsItemExtended:
    """Extended RSS news item tests"""

    def test_news_items_anonymous_forbidden(self, api_client):
        """Anonymous users cannot access RSS news items"""
        resp = api_client.get('/api/v1/rss-news-items/')
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_news_item_detail(self, authenticated_client):
        """Can get news item detail"""
        feed = RSSFeed.objects.create(name='Detail Feed', feed_url='https://detail.com/rss')
        item = RSSNewsItem.objects.create(rss_feed=feed, title='Detail Item', content='<p>D</p>')
        resp = authenticated_client.get(f'/api/v1/rss-news-items/{item.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['title'] == 'Detail Item'

    def test_news_items_list_with_data(self, authenticated_client):
        """Can list news items when multiple feeds exist"""
        feed1 = RSSFeed.objects.create(name='Feed A', feed_url='https://a.com/rss')
        feed2 = RSSFeed.objects.create(name='Feed B', feed_url='https://b.com/rss')
        RSSNewsItem.objects.create(rss_feed=feed1, title='Item A', content='<p>A</p>')
        RSSNewsItem.objects.create(rss_feed=feed2, title='Item B', content='<p>B</p>')
        resp = authenticated_client.get('/api/v1/rss-news-items/')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data['results']) >= 2

    def test_feed_delete(self, authenticated_client):
        """Can delete an RSS feed"""
        feed = RSSFeed.objects.create(name='Del Feed', feed_url='https://del.com/rss')
        resp = authenticated_client.delete(f'/api/v1/rss-feeds/{feed.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_feed_update(self, authenticated_client):
        """Can update an RSS feed"""
        feed = RSSFeed.objects.create(name='Old Name', feed_url='https://update.com/rss')
        resp = authenticated_client.patch(f'/api/v1/rss-feeds/{feed.id}/', {
            'name': 'New Name',
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        feed.refresh_from_db()
        assert feed.name == 'New Name'
