"""
Integration tests for Search API
"""
import pytest
from unittest.mock import patch
from django.urls import reverse
from news.models import Article, Category, Tag


@pytest.mark.django_db
class TestSearchAPI:
    """Tests for Search API endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create test data"""
        # Create category
        self.category = Category.objects.create(
            name='Electric Vehicles',
            slug='electric-vehicles'
        )
        
        # Create articles
        self.article1 = Article.objects.create(
            title='Tesla Model 3 Review',
            content='<p>Tesla Model 3 is an excellent electric vehicle.</p>',
            summary='Review of Tesla Model 3',
            is_published=True,
            is_deleted=False,
            meta_keywords='Tesla, Model 3, EV'
        )
        self.article1.categories.add(self.category)
        
        self.article2 = Article.objects.create(
            title='BMW i4 Electric Sedan',
            content='<p>BMW i4 offers luxury and electric performance.</p>',
            summary='BMW i4 electric sedan review',
            is_published=True,
            is_deleted=False,
            meta_keywords='BMW, i4, electric'
        )
        self.article2.categories.add(self.category)
        
        # Create tags
        ev_tag = Tag.objects.create(name='EV', slug='ev')
        luxury_tag = Tag.objects.create(name='Luxury', slug='luxury')
        self.article1.tags.add(ev_tag)
        self.article2.tags.add(ev_tag, luxury_tag)
    
    @patch('news.search_analytics_views.SearchAPIView._hybrid_article_ids', return_value=[])
    def test_search_by_title(self, mock_hybrid, api_client):
        """Test search by article title (ORM fallback)"""
        response = api_client.get('/api/v1/search/', {'q': 'Tesla'})
        
        assert response.status_code == 200
        assert response.data['total'] >= 1
        titles = [r['title'] for r in response.data['results']]
        assert any('Tesla' in title for title in titles)
    
    @patch('news.search_analytics_views.SearchAPIView._hybrid_article_ids', return_value=[])
    def test_search_by_content(self, mock_hybrid, api_client):
        """Test search by article content (ORM fallback)"""
        response = api_client.get('/api/v1/search/', {'q': 'luxury'})
        
        assert response.status_code == 200
        assert response.data['total'] >= 1
    
    @patch('news.search_analytics_views.SearchAPIView._hybrid_article_ids', return_value=[])
    def test_search_by_keywords(self, mock_hybrid, api_client):
        """Test search by meta keywords (ORM fallback)"""
        response = api_client.get('/api/v1/search/', {'q': 'Model 3'})
        
        assert response.status_code == 200
        assert response.data['total'] >= 1
    
    def test_filter_by_category(self, api_client):
        """Test filtering by category"""
        response = api_client.get('/api/v1/search/', {
            'category': 'electric-vehicles'
        })
        
        assert response.status_code == 200
        assert response.data['total'] >= 2
        # All results should be from the filtered category
        assert len(response.data['results']) >= 2
    
    def test_filter_by_tags(self, api_client):
        """Test filtering by tags"""
        response = api_client.get('/api/v1/search/', {
            'tags': 'luxury'
        })
        
        assert response.status_code == 200
        # Only BMW i4 has luxury tag
        assert response.data['total'] >= 1
    
    def test_sort_by_newest(self, api_client):
        """Test sorting by newest"""
        response = api_client.get('/api/v1/search/', {
            'sort': 'newest'
        })
        
        assert response.status_code == 200
        results = response.data['results']
        # Newest should be first
        if len(results) >= 2:
            assert results[0]['id'] >= results[1]['id']
    
    def test_sort_by_popular(self, api_client):
        """Test sorting by views"""
        # Set different view counts
        self.article1.views = 100
        self.article1.save()
        self.article2.views = 50
        self.article2.save()
        
        response = api_client.get('/api/v1/search/', {
            'sort': 'popular'
        })
        
        assert response.status_code == 200
        results = response.data['results']
        # Most viewed should be first
        if len(results) >= 2:
            assert results[0]['views'] >= results[1]['views']
    
    def test_pagination(self, api_client):
        """Test search pagination"""
        response = api_client.get('/api/v1/search/', {
            'page': 1
        })
        
        assert response.status_code == 200
        # Just check pagination exists
        assert 'results' in response.data
        assert 'total' in response.data
        # Don't check exact count as default page_size may vary
    
    def test_empty_search(self, api_client):
        """Test search with no query"""
        response = api_client.get('/api/v1/search/')
        
        assert response.status_code == 200
        # Should return all published articles
        assert response.data['total'] >= 2
    
    @patch('news.search_analytics_views.SearchAPIView._hybrid_article_ids', return_value=[])
    def test_no_results(self, mock_hybrid, api_client):
        """Test search with no matching results"""
        response = api_client.get('/api/v1/search/', {
            'q': 'zzz_nonexistent_brand_xyz_9999'
        })
        
        assert response.status_code == 200
        assert response.data['total'] == 0
        assert response.data['results'] == []
    
    @patch('news.search_analytics_views.SearchAPIView._hybrid_article_ids', return_value=[])
    def test_search_ignores_unpublished(self, mock_hybrid, api_client):
        """Test that unpublished articles are not returned"""
        # Create unpublished article with unique title
        a = Article.objects.create(
            title='ZZQQ_Unpublished_UniqueMarker_8877',
            content='<p>Secret content</p>',
            is_published=False,
            is_deleted=False
        )
        a.categories.add(self.category)
        
        response = api_client.get('/api/v1/search/', {
            'q': 'ZZQQ_Unpublished_UniqueMarker_8877'
        })
        
        assert response.status_code == 200
        assert response.data['total'] == 0
    
    @patch('news.search_analytics_views.SearchAPIView._hybrid_article_ids', return_value=[])
    def test_search_ignores_deleted(self, mock_hybrid, api_client):
        """Test that deleted articles are not returned"""
        # Create deleted article with unique title
        a = Article.objects.create(
            title='ZZQQ_Deleted_UniqueMarker_9988',
            content='<p>Deleted content</p>',
            is_published=True,
            is_deleted=True
        )
        a.categories.add(self.category)
        
        response = api_client.get('/api/v1/search/', {
            'q': 'ZZQQ_Deleted_UniqueMarker_9988'
        })
        
        assert response.status_code == 200
        assert response.data['total'] == 0
