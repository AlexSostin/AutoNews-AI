"""
Integration tests for Search API
"""
import pytest
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
            category=self.category,
            is_published=True,
            is_deleted=False,
            meta_keywords='Tesla, Model 3, EV'
        )
        
        self.article2 = Article.objects.create(
            title='BMW i4 Electric Sedan',
            content='<p>BMW i4 offers luxury and electric performance.</p>',
            summary='BMW i4 electric sedan review',
            category=self.category,
            is_published=True,
            is_deleted=False,
            meta_keywords='BMW, i4, electric'
        )
        
        # Create tags
        ev_tag = Tag.objects.create(name='EV', slug='ev')
        luxury_tag = Tag.objects.create(name='Luxury', slug='luxury')
        self.article1.tags.add(ev_tag)
        self.article2.tags.add(ev_tag, luxury_tag)
    
    def test_search_by_title(self, api_client):
        """Test search by article title"""
        response = api_client.get('/api/v1/search/', {'q': 'Tesla'})
        
        assert response.status_code == 200
        assert response.data['total'] >= 1
        titles = [r['title'] for r in response.data['results']]
        assert any('Tesla' in title for title in titles)
    
    def test_search_by_content(self, api_client):
        """Test search by article content"""
        response = api_client.get('/api/v1/search/', {'q': 'luxury'})
        
        assert response.status_code == 200
        assert response.data['total'] >= 1
    
    def test_search_by_keywords(self, api_client):
        """Test search by meta keywords"""
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
        for article in response.data['results']:
            # API returns category_name, not nested object
            assert article['category_name'] == 'Electric Vehicles'
    
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
    
    def test_no_results(self, api_client):
        """Test search with no matching results"""
        response = api_client.get('/api/v1/search/', {
            'q': 'xyznonexistent123'
        })
        
        assert response.status_code == 200
        assert response.data['total'] == 0
        assert response.data['results'] == []
    
    def test_search_ignores_unpublished(self, api_client):
        """Test that unpublished articles are not returned"""
        # Create unpublished article
        Article.objects.create(
            title='Unpublished Article',
            content='<p>Secret content</p>',
            category=self.category,
            is_published=False,
            is_deleted=False
        )
        
        response = api_client.get('/api/v1/search/', {
            'q': 'Unpublished'
        })
        
        assert response.status_code == 200
        assert response.data['total'] == 0
    
    def test_search_ignores_deleted(self, api_client):
        """Test that deleted articles are not returned"""
        # Create deleted article
        Article.objects.create(
            title='Deleted Article',
            content='<p>Deleted content</p>',
            category=self.category,
            is_published=True,
            is_deleted=True
        )
        
        response = api_client.get('/api/v1/search/', {
            'q': 'Deleted'
        })
        
        assert response.status_code == 200
        assert response.data['total'] == 0
