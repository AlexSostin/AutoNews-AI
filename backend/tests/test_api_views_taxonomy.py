import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from unittest.mock import patch
from news.models import Category, Tag, TagGroup

UA = {'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) TestClient/1.0'}

@pytest.fixture
def auth_client():
    client = APIClient(**UA)
    user = User.objects.create_user(username='normal_user', password='password123', email='user@test.com')
    client.force_authenticate(user=user)
    return client

@pytest.fixture
def test_client():
    return APIClient(**UA)

@pytest.mark.django_db
class TestCategoryViewSet:
    def test_list_categories_public(self, test_client):
        Category.objects.create(name='Visible Category', slug='visible', is_visible=True)
        Category.objects.create(name='Hidden Category', slug='hidden', is_visible=False)
        
        response = test_client.get('/api/v1/categories/')
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]['slug'] == 'visible'

    def test_list_categories_authenticated(self, auth_client):
        Category.objects.create(name='Visible Category', slug='visible', is_visible=True)
        Category.objects.create(name='Hidden Category', slug='hidden', is_visible=False)
        
        response = auth_client.get('/api/v1/categories/')
        assert response.status_code == 200
        assert len(response.data) == 2

    @patch('news.api_views.categories_tags.invalidate_article_cache')
    def test_create_category_admin(self, mock_invalidate, test_client):
        admin = User.objects.create_superuser(username='super_admin', email='admin@test.com', password='pass')
        client = APIClient(**UA)
        client.force_authenticate(user=admin)
        
        response = client.post('/api/v1/categories/', {'name': 'New Category', 'slug': 'new-category'}, format='json')
        assert response.status_code == 201
        mock_invalidate.assert_called_once()
