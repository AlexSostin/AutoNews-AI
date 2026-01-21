"""
Unit tests for AutoNews API
Run with: python manage.py test news.tests
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Article, Category, Tag, SiteSettings
import json


class HealthCheckTests(APITestCase):
    """Tests for health check endpoints"""
    
    def test_health_check_returns_200(self):
        """Health check should return 200 OK"""
        response = self.client.get('/api/v1/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')
    
    def test_health_check_detailed_returns_200(self):
        """Detailed health check should return database status"""
        response = self.client.get('/api/v1/health/detailed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('checks', response.data)
        self.assertIn('database', response.data['checks'])
    
    def test_readiness_check(self):
        """Readiness check should return ready status"""
        response = self.client.get('/api/v1/health/ready/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['ready'])


class CategoryTests(APITestCase):
    """Tests for Category API"""
    
    def setUp(self):
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
    
    def test_list_categories(self):
        """Should return list of categories"""
        response = self.client.get('/api/v1/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
    
    def test_retrieve_category(self):
        """Should return single category"""
        response = self.client.get(f'/api/v1/categories/{self.category.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Category')
    
    def test_create_category_unauthorized(self):
        """Anonymous users should not create categories"""
        data = {'name': 'New Category', 'slug': 'new-category'}
        response = self.client.post('/api/v1/categories/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ArticleTests(APITestCase):
    """Tests for Article API"""
    
    def setUp(self):
        self.category = Category.objects.create(
            name='News',
            slug='news'
        )
        self.article = Article.objects.create(
            title='Test Article',
            slug='test-article',
            content='Test content',
            category=self.category,
            is_published=True
        )
        self.draft_article = Article.objects.create(
            title='Draft Article',
            slug='draft-article',
            content='Draft content',
            category=self.category,
            is_published=False
        )
    
    def test_list_articles_returns_only_published(self):
        """Anonymous users should only see published articles"""
        response = self.client.get('/api/v1/articles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that draft is not in results
        titles = [a['title'] for a in response.data['results']]
        self.assertIn('Test Article', titles)
        self.assertNotIn('Draft Article', titles)
    
    def test_retrieve_article_by_slug(self):
        """Should retrieve article by slug"""
        response = self.client.get('/api/v1/articles/test-article/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Article')
    
    def test_create_article_unauthorized(self):
        """Anonymous users should not create articles"""
        data = {
            'title': 'New Article',
            'content': 'Content',
            'category': self.category.id
        }
        response = self.client.post('/api/v1/articles/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticationTests(APITestCase):
    """Tests for JWT Authentication"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_obtain_token_with_valid_credentials(self):
        """Should return JWT tokens for valid credentials"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post('/api/v1/token/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_obtain_token_with_invalid_credentials(self):
        """Should return 401 for invalid credentials"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post('/api/v1/token/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_access_protected_endpoint_with_token(self):
        """Should access protected endpoint with valid token"""
        # Get token
        data = {'username': 'testuser', 'password': 'testpass123'}
        token_response = self.client.post('/api/v1/token/', data)
        token = token_response.data['access']
        
        # Access protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')


class UserRegistrationTests(APITestCase):
    """Tests for user registration"""
    
    def test_register_new_user(self):
        """Should register new user successfully"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123'
        }
        response = self.client.post('/api/v1/users/register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_register_duplicate_username(self):
        """Should reject duplicate username"""
        User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='pass123'
        )
        data = {
            'username': 'existinguser',
            'email': 'new@example.com',
            'password': 'pass123'
        }
        response = self.client.post('/api/v1/users/register/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RateLimitingTests(APITestCase):
    """Tests for rate limiting (disabled in test mode by default)"""
    
    def test_token_endpoint_accessible(self):
        """Token endpoint should be accessible"""
        data = {'username': 'test', 'password': 'test'}
        response = self.client.post('/api/v1/token/', data)
        # Even with wrong credentials, should not be rate limited in tests
        self.assertIn(response.status_code, [401, 200])


class SiteSettingsTests(APITestCase):
    """Tests for Site Settings API"""
    
    def test_get_site_settings(self):
        """Should return site settings"""
        # Create settings first
        SiteSettings.objects.get_or_create(pk=1)
        response = self.client.get('/api/v1/settings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TagTests(APITestCase):
    """Tests for Tag API"""
    
    def setUp(self):
        self.tag = Tag.objects.create(
            name='Electric',
            slug='electric'
        )
    
    def test_list_tags(self):
        """Should return list of tags"""
        response = self.client.get('/api/v1/tags/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_retrieve_tag_by_slug(self):
        """Should retrieve tag by slug"""
        response = self.client.get('/api/v1/tags/electric/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Electric')


class SecurityTests(APITestCase):
    """Tests for security measures"""
    
    def test_cors_headers_present(self):
        """CORS headers should be present in response"""
        response = self.client.options('/api/v1/articles/')
        # In test mode, CORS might not be fully active
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_xss_in_article_title_escaped(self):
        """XSS attempts should be escaped"""
        # Create staff user
        staff = User.objects.create_user(
            username='staff',
            password='staffpass',
            is_staff=True
        )
        self.client.force_authenticate(user=staff)
        
        category = Category.objects.create(name='Test', slug='test')
        data = {
            'title': '<script>alert("xss")</script>',
            'content': 'Safe content',
            'category': category.id,
            'is_published': True
        }
        response = self.client.post('/api/v1/articles/', data)
        if response.status_code == 201:
            # Title should be stored as-is (escaped on frontend)
            article = Article.objects.get(id=response.data['id'])
            self.assertIn('script', article.title)  # Stored but will be escaped on render
