"""
Integration tests for Analytics API
"""
import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from news.models import Article, Category, Comment, Subscriber


@pytest.mark.django_db
class TestAnalyticsAPI:
    """Tests for Analytics API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create test data"""
        self.category1 = Category.objects.create(
            name='Electric Vehicles',
            slug='electric-vehicles'
        )
        self.category2 = Category.objects.create(
            name='Sports Cars',
            slug='sports-cars'
        )
        
        # Create articles with different dates and views
        now = timezone.now()
        
        self.article1 = Article.objects.create(
            title='Article 1',
            content='<p>Content 1</p>',
            is_published=True,
            views=100,
            created_at=now - timedelta(days=5)
        )
        self.article1.categories.add(self.category1)
        
        self.article2 = Article.objects.create(
            title='Article 2',
            content='<p>Content 2</p>',
            is_published=True,
            views=50,
            created_at=now - timedelta(days=2)
        )
        self.article2.categories.add(self.category1)
        
        self.article3 = Article.objects.create(
            title='Article 3',
            content='<p>Content 3</p>',
            is_published=True,
            views=75,
            created_at=now
        )
        self.article3.categories.add(self.category2)
        
        # Create comments
        Comment.objects.create(
            article=self.article1,
            name='User 1',
            email='user1@test.com',
            content='Great article!',
            is_approved=True
        )
        
        # Create subscribers
        Subscriber.objects.create(
            email='subscriber1@test.com',
            is_active=True
        )
    
    def test_analytics_overview(self, authenticated_client):
        """Test analytics overview endpoint"""
        response = authenticated_client.get('/api/v1/analytics/overview/')
        
        assert response.status_code == 200
        assert 'total_articles' in response.data
        assert 'total_views' in response.data
        assert 'total_comments' in response.data
        assert 'total_subscribers' in response.data
        
        # Check values
        assert response.data['total_articles'] == 3
        assert response.data['total_views'] == 225  # 100 + 50 + 75
        assert response.data['total_comments'] >= 1
        assert response.data['total_subscribers'] >= 1
    
    def test_analytics_requires_auth(self, api_client):
        """Test that analytics requires authentication"""
        response = api_client.get('/api/v1/analytics/overview/')
        
        # Should be 401 or 403
        assert response.status_code in [401, 403]
    
    def test_top_articles(self, authenticated_client):
        """Test top articles endpoint"""
        response = authenticated_client.get('/api/v1/analytics/articles/top/', {
            'limit': 10
        })
        
        assert response.status_code == 200
        assert 'articles' in response.data
        
        articles = response.data['articles']
        assert len(articles) <= 10
        
        # Should be sorted by views descending
        if len(articles) >= 2:
            assert articles[0]['views'] >= articles[1]['views']
        
        # First should be article1 (100 views)
        if len(articles) > 0:
            assert articles[0]['title'] == 'Article 1'
            assert articles[0]['views'] == 100
    
    def test_top_articles_limit(self, authenticated_client):
        """Test top articles with custom limit"""
        response = authenticated_client.get('/api/v1/analytics/articles/top/', {
            'limit': 2
        })
        
        assert response.status_code == 200
        assert len(response.data['articles']) <= 2
    
    def test_views_timeline(self, authenticated_client):
        """Test views timeline endpoint"""
        response = authenticated_client.get('/api/v1/analytics/views/timeline/', {
            'days': 30
        })
        
        assert response.status_code == 200
        assert 'labels' in response.data
        assert 'data' in response.data
        
        # Should have 30 data points
        assert len(response.data['labels']) == 30
        assert len(response.data['data']) == 30
        
        # Data should be integers
        for count in response.data['data']:
            assert isinstance(count, int)
    
    def test_views_timeline_custom_days(self, authenticated_client):
        """Test timeline with custom day range"""
        response = authenticated_client.get('/api/v1/analytics/views/timeline/', {
            'days': 7
        })
        
        assert response.status_code == 200
        assert len(response.data['labels']) == 7
        assert len(response.data['data']) == 7
    
    def test_categories_distribution(self, authenticated_client):
        """Test categories distribution endpoint"""
        response = authenticated_client.get('/api/v1/analytics/categories/')
        
        assert response.status_code == 200
        assert 'labels' in response.data
        assert 'data' in response.data
        
        # Should have 2 categories
        assert len(response.data['labels']) == 2
        assert len(response.data['data']) == 2
        
        # Check distribution
        labels = response.data['labels']
        data = response.data['data']
        
        # Electric Vehicles should have 2 articles
        ev_index = labels.index('Electric Vehicles')
        assert data[ev_index] == 2
        
        # Sports Cars should have 1 article
        sc_index = labels.index('Sports Cars')
        assert data[sc_index] == 1
    
    def test_analytics_growth_percentage(self, authenticated_client):
        """Test articles growth percentage calculation"""
        response = authenticated_client.get('/api/v1/analytics/overview/')
        
        assert response.status_code == 200
        assert 'total_articles' in response.data
        assert 'articles_growth' in response.data
        
        # All 3 articles are within 30 days
        assert response.data['total_articles'] == 3


@pytest.mark.django_db
class TestAIGenerationAnalytics:
    """Tests for AI generation analytics endpoint"""

    def test_ai_generation_stats(self, authenticated_client):
        """AI generation stats endpoint returns correct structure"""
        response = authenticated_client.get('/api/v1/analytics/ai-generation/')
        assert response.status_code == 200
        assert 'spec_coverage' in response.data
        assert 'generation_time' in response.data
        assert 'edit_rates' in response.data

    def test_ai_generation_requires_auth(self, api_client):
        """AI generation stats requires authentication"""
        response = api_client.get('/api/v1/analytics/ai-generation/')
        assert response.status_code in [401, 403]

    def test_ai_generation_spec_coverage_format(self, authenticated_client):
        """Spec coverage should have per-field fill rates"""
        response = authenticated_client.get('/api/v1/analytics/ai-generation/')
        assert response.status_code == 200
        spec_coverage = response.data.get('spec_coverage', {})
        assert isinstance(spec_coverage, (dict, list))


@pytest.mark.django_db
class TestPopularModelsAnalytics:
    """Tests for popular models analytics endpoint"""

    def test_popular_models(self, authenticated_client):
        """Popular models endpoint returns correct structure"""
        Article.objects.create(title='Model Test', slug='model-test',
                              content='<p>Test</p>', is_published=True, views=50)
        response = authenticated_client.get('/api/v1/analytics/popular-models/')
        assert response.status_code == 200
        assert 'models' in response.data

    def test_popular_models_requires_auth(self, api_client):
        """Popular models requires authentication"""
        response = api_client.get('/api/v1/analytics/popular-models/')
        assert response.status_code in [401, 403]


@pytest.mark.django_db
class TestProviderStatsAnalytics:
    """Tests for provider stats analytics endpoint"""

    def test_provider_stats(self, authenticated_client):
        """Provider stats endpoint returns correct structure"""
        response = authenticated_client.get('/api/v1/analytics/provider-stats/')
        assert response.status_code == 200
        assert 'providers' in response.data
        assert 'total_records' in response.data

    def test_provider_stats_requires_auth(self, api_client):
        """Provider stats requires authentication"""
        response = api_client.get('/api/v1/analytics/provider-stats/')
        assert response.status_code in [401, 403]


@pytest.mark.django_db
class TestAIStatsAnalytics:
    """Tests for AI stats analytics endpoint"""

    def test_ai_stats(self, authenticated_client):
        """AI stats endpoint returns data"""
        response = authenticated_client.get('/api/v1/analytics/ai-stats/')
        assert response.status_code == 200

    def test_ai_stats_requires_auth(self, api_client):
        """AI stats requires authentication"""
        response = api_client.get('/api/v1/analytics/ai-stats/')
        assert response.status_code in [401, 403]


@pytest.mark.django_db
class TestGSCAnalytics:
    """Tests for GSC analytics endpoint"""

    def test_gsc_analytics(self, authenticated_client):
        """GSC endpoint returns data or empty"""
        response = authenticated_client.get('/api/v1/analytics/gsc/?days=7')
        assert response.status_code == 200
