"""
Tests for user management, favorites, newsletter, and health checks:
- Admin user list/update
- Favorites (add/remove)
- Newsletter subscription
- Health check endpoints
"""
import pytest
from django.contrib.auth.models import User
from rest_framework import status
from news.models import Article, Favorite, NewsletterSubscriber


@pytest.mark.django_db
class TestAdminUserManagement:
    """Admin user endpoints /api/v1/admin/users/"""

    def test_list_users(self, authenticated_client):
        """Superuser can list all users"""
        resp = authenticated_client.get('/api/v1/admin/users/')
        assert resp.status_code == status.HTTP_200_OK

    def test_list_users_anonymous_forbidden(self, api_client):
        """Anonymous users cannot list users"""
        resp = api_client.get('/api/v1/admin/users/')
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_update_user(self, authenticated_client):
        """Superuser can update user details"""
        user = User.objects.create_user(username='editme', password='pass123', email='edit@test.com')
        resp = authenticated_client.patch(f'/api/v1/admin/users/{user.id}/', {
            'first_name': 'Edited',
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestFavorites:
    """Favorites CRUD /api/v1/favorites/"""

    def test_add_favorite(self, authenticated_client):
        """Authenticated user can favorite an article"""
        article = Article.objects.create(
            title='Fav Article', slug='fav-article',
            content='<p>Love it</p>', is_published=True
        )
        resp = authenticated_client.post('/api/v1/favorites/', {
            'article': article.id,
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED

    def test_list_favorites(self, authenticated_client):
        """Authenticated user can list their favorites"""
        resp = authenticated_client.get('/api/v1/favorites/')
        assert resp.status_code == status.HTTP_200_OK

    def test_favorites_anonymous_forbidden(self, api_client):
        """Anonymous users cannot manage favorites"""
        resp = api_client.get('/api/v1/favorites/')
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestNewsletterSubscription:
    """POST /api/v1/newsletter/subscribe/"""

    def test_subscribe(self, api_client):
        """Anyone can subscribe to newsletter"""
        resp = api_client.post('/api/v1/newsletter/subscribe/', {
            'email': 'subscriber@test.com',
        }, format='json')
        assert resp.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_subscribe_invalid_email(self, api_client):
        """Invalid email is rejected"""
        resp = api_client.post('/api/v1/newsletter/subscribe/', {
            'email': 'not-an-email',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestHealthChecks:
    """Health check endpoints"""

    def test_health_check(self, api_client):
        """Basic health check returns 200"""
        resp = api_client.get('/api/v1/health/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['status'] == 'healthy'

    def test_health_detailed(self, api_client):
        """Detailed health check returns component statuses"""
        resp = api_client.get('/api/v1/health/detailed/')
        assert resp.status_code == status.HTTP_200_OK
        assert 'checks' in resp.data

    def test_readiness_check(self, api_client):
        """Readiness check returns 200"""
        resp = api_client.get('/api/v1/health/ready/')
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestFavoritesExtended:
    """Extended favorites tests"""

    def test_remove_favorite(self, authenticated_client):
        """Can remove a favorite"""
        article = Article.objects.create(
            title='UnFav', slug='unfav', content='<p>Remove</p>', is_published=True
        )
        # Add first
        resp = authenticated_client.post('/api/v1/favorites/', {
            'article': article.id,
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        fav_id = resp.data['id']
        # Remove
        resp = authenticated_client.delete(f'/api/v1/favorites/{fav_id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_duplicate_favorite_rejected(self, authenticated_client):
        """Cannot favorite the same article twice"""
        article = Article.objects.create(
            title='DupFav', slug='dupfav', content='<p>Dup</p>', is_published=True
        )
        authenticated_client.post('/api/v1/favorites/', {'article': article.id}, format='json')
        resp = authenticated_client.post('/api/v1/favorites/', {'article': article.id}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestNewsletterExtended:
    """Extended newsletter tests"""

    def test_duplicate_subscription(self, api_client):
        """Subscribing same email twice should be handled gracefully"""
        api_client.post('/api/v1/newsletter/subscribe/', {'email': 'dup@test.com'}, format='json')
        resp = api_client.post('/api/v1/newsletter/subscribe/', {'email': 'dup@test.com'}, format='json')
        # Should either succeed (idempotent) or return 400
        assert resp.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]

    def test_subscribe_with_name(self, api_client):
        """Can subscribe with optional name"""
        resp = api_client.post('/api/v1/newsletter/subscribe/', {
            'email': 'named@test.com',
            'name': 'John Doe',
        }, format='json')
        assert resp.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]


@pytest.mark.django_db
class TestAdminUserExtended:
    """Extended admin user management tests"""

    def test_admin_user_detail(self, authenticated_client):
        """Superuser can view user details"""
        user = User.objects.create_user(username='detailuser', password='pass123', email='detail@test.com')
        resp = authenticated_client.get(f'/api/v1/admin/users/{user.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['username'] == 'detailuser'

    def test_admin_toggle_staff(self, authenticated_client):
        """Can toggle staff status"""
        user = User.objects.create_user(username='stafftest', password='pass123', email='staff@test.com')
        resp = authenticated_client.patch(f'/api/v1/admin/users/{user.id}/', {
            'is_staff': True,
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
