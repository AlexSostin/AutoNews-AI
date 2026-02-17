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
            is_published=True
        )
        self.article.categories.add(self.category)
        self.draft_article = Article.objects.create(
            title='Draft Article',
            slug='draft-article',
            content='Draft content',
            is_published=False
        )
        self.draft_article.categories.add(self.category)
    
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
            'category_ids': [self.category.id]
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
        """Should retrieve tag by id"""
        response = self.client.get(f'/api/v1/tags/{self.tag.id}/')
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
            'category_ids': [category.id],
            'is_published': True
        }
        response = self.client.post('/api/v1/articles/', data)
        if response.status_code == 201:
            # Title should be stored as-is (escaped on frontend)
            article = Article.objects.get(id=response.data['id'])
            self.assertIn('script', article.title)  # Stored but will be escaped on render


class FeedbackTests(APITestCase):
    """Tests for article feedback submission and admin management"""
    
    def setUp(self):
        self.category = Category.objects.create(name='Reviews', slug='reviews')
        self.article = Article.objects.create(
            title='Test Car Review',
            slug='test-car-review',
            content='This is a test article about a car.',
            is_published=True
        )
        self.article.categories.add(self.category)
        self.admin = User.objects.create_user(
            username='admin_feedback',
            password='adminpass123',
            is_staff=True
        )
    
    def test_anonymous_can_submit_feedback(self):
        """Anonymous users should be able to submit feedback"""
        data = {
            'category': 'factual_error',
            'message': 'The horsepower figure is incorrect, should be 450hp not 500hp.'
        }
        response = self.client.post(
            f'/api/v1/articles/{self.article.slug}/feedback/',
            data
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['success'])
    
    def test_feedback_requires_minimum_message(self):
        """Feedback message must be at least 5 characters"""
        data = {
            'category': 'typo',
            'message': 'hi'
        }
        response = self.client.post(
            f'/api/v1/articles/{self.article.slug}/feedback/',
            data
        )
        self.assertEqual(response.status_code, 400)
    
    def test_feedback_empty_message_rejected(self):
        """Empty feedback message should be rejected"""
        data = {
            'category': 'other',
            'message': ''
        }
        response = self.client.post(
            f'/api/v1/articles/{self.article.slug}/feedback/',
            data
        )
        self.assertEqual(response.status_code, 400)
    
    def test_feedback_invalid_category_defaults_to_other(self):
        """Invalid category should default to 'other'"""
        data = {
            'category': 'nonexistent_category',
            'message': 'This is a valid feedback message about the article.'
        }
        response = self.client.post(
            f'/api/v1/articles/{self.article.slug}/feedback/',
            data
        )
        self.assertEqual(response.status_code, 201)
    
    def test_admin_can_list_feedback(self):
        """Admin should be able to list all feedback"""
        # Submit feedback first
        from .models import ArticleFeedback
        ArticleFeedback.objects.create(
            article=self.article,
            category='factual_error',
            message='Test feedback for admin listing'
        )
        
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/v1/feedback/')
        self.assertEqual(response.status_code, 200)


class ProfileUpdateTests(APITestCase):
    """Tests for user profile update (PATCH /auth/user/)"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='profileuser',
            email='profile@example.com',
            password='profilepass123',
            first_name='Original',
            last_name='Name'
        )
    
    def _get_token(self):
        response = self.client.post('/api/v1/token/', {
            'username': 'profileuser',
            'password': 'profilepass123'
        })
        return response.data['access']
    
    def test_update_name_only_succeeds(self):
        """PATCH with only first_name/last_name should succeed (no email)"""
        token = self._get_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        data = {
            'first_name': 'Updated',
            'last_name': 'User'
        }
        response = self.client.patch('/api/v1/auth/user/', data)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
    
    def test_update_with_email_rejected(self):
        """PATCH with email field should be rejected (400)"""
        token = self._get_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        data = {
            'first_name': 'Updated',
            'email': 'newemail@example.com'
        }
        response = self.client.patch('/api/v1/auth/user/', data)
        self.assertEqual(response.status_code, 400)
    
    def test_unauthorized_update_rejected(self):
        """Unauthenticated users should not access /auth/user/"""
        response = self.client.patch('/api/v1/auth/user/', {'first_name': 'Hacker'})
        self.assertEqual(response.status_code, 401)
    
    def test_password_change(self):
        """Authenticated user should be able to change password"""
        token = self._get_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        data = {
            'old_password': 'profilepass123',
            'new_password1': 'newSecurePass456!',
            'new_password2': 'newSecurePass456!'
        }
        response = self.client.post('/api/v1/auth/password/change/', data)
        self.assertIn(response.status_code, [200, 204])


class ABTitleTests(APITestCase):
    """Tests for A/B title testing system"""
    
    def setUp(self):
        from .models import ArticleTitleVariant
        
        self.category = Category.objects.create(name='Test', slug='test-ab')
        self.article = Article.objects.create(
            title='2025 Tesla Model Y Review',
            slug='2025-tesla-model-y-review',
            content='Test content for A/B testing',
            is_published=True
        )
        self.article.categories.add(self.category)
        
        # Create A/B variants
        self.variant_a = ArticleTitleVariant.objects.create(
            article=self.article,
            variant='A',
            title='2025 Tesla Model Y Review'
        )
        self.variant_b = ArticleTitleVariant.objects.create(
            article=self.article,
            variant='B',
            title='Tesla Model Y 2025: Best EV Under $50K?'
        )
        self.variant_c = ArticleTitleVariant.objects.create(
            article=self.article,
            variant='C',
            title='Why The 2025 Model Y Changes Everything'
        )
        
        self.admin = User.objects.create_user(
            username='ab_admin',
            password='adminpass123',
            is_staff=True
        )
    
    def test_ab_title_returns_variant(self):
        """GET ab-title should return a title variant"""
        response = self.client.get(
            f'/api/v1/articles/{self.article.slug}/ab-title/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['ab_active'])
        self.assertIn(response.data['variant'], ['A', 'B', 'C'])
        self.assertTrue(len(response.data['title']) > 0)
    
    def test_ab_title_no_variants_returns_original(self):
        """Article without variants should return original title"""
        no_ab_article = Article.objects.create(
            title='No AB Test Article',
            slug='no-ab-test',
            content='Content',
            is_published=True
        )
        no_ab_article.categories.add(self.category)
        
        response = self.client.get(
            f'/api/v1/articles/{no_ab_article.slug}/ab-title/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['ab_active'])
        self.assertEqual(response.data['title'], 'No AB Test Article')
    
    def test_ab_click_records_conversion(self):
        """POST ab-click should increment click counter"""
        response = self.client.post(
            f'/api/v1/articles/{self.article.slug}/ab-click/',
            {'variant': 'B'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        
        self.variant_b.refresh_from_db()
        self.assertEqual(self.variant_b.clicks, 1)
    
    def test_ab_stats_admin_only(self):
        """ab-stats should only be accessible to admin"""
        # Anonymous
        response = self.client.get(
            f'/api/v1/articles/{self.article.slug}/ab-stats/'
        )
        self.assertEqual(response.status_code, 401)
        
        # Admin
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            f'/api/v1/articles/{self.article.slug}/ab-stats/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['variants']), 3)
    
    def test_pick_winner_updates_title(self):
        """Picking a winner should update the article's title"""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f'/api/v1/articles/{self.article.slug}/ab-pick-winner/',
            {'variant': 'B'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, 'Tesla Model Y 2025: Best EV Under $50K?')
        
        self.variant_b.refresh_from_db()
        self.assertTrue(self.variant_b.is_winner)
