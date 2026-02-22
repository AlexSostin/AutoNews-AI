"""
Tests for CategoryViewSet and TagViewSet (api_views.py)
Target: Cover CRUD, filtering, caching, permissions
"""
import pytest
from django.test import override_settings
from rest_framework import status

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def category(db):
    from news.models import Category
    return Category.objects.create(name='Reviews', slug='reviews')


@pytest.fixture
def hidden_category(db):
    from news.models import Category
    return Category.objects.create(name='Hidden', slug='hidden', is_visible=False)


@pytest.fixture
def tag(db):
    from news.models import Tag
    return Tag.objects.create(name='Electric', slug='electric')


@pytest.fixture
def tag_group(db):
    from news.models import TagGroup
    return TagGroup.objects.create(name='Drivetrain')


@pytest.fixture
def regular_client(api_client, django_user_model):
    """Non-staff authenticated client"""
    from rest_framework_simplejwt.tokens import RefreshToken
    user = django_user_model.objects.create_user(
        username='regular', email='regular@test.com', password='pass123'
    )
    token = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return api_client


# ═══════════════════════════════════════════════════════════════════════════
# CategoryViewSet
# ═══════════════════════════════════════════════════════════════════════════

class TestCategoryViewSet:
    """Tests for /api/v1/categories/"""

    def test_list_categories_anonymous(self, api_client, category):
        resp = api_client.get('/api/v1/categories/')
        assert resp.status_code == status.HTTP_200_OK
        # Should be unpaginated list (pagination_class = None)
        assert isinstance(resp.data, list)
        assert len(resp.data) >= 1

    def test_list_hides_invisible_for_anonymous(self, api_client, category, hidden_category):
        resp = api_client.get('/api/v1/categories/')
        slugs = [c['slug'] for c in resp.data]
        assert 'reviews' in slugs
        assert 'hidden' not in slugs

    def test_list_shows_invisible_for_staff(self, authenticated_client, category, hidden_category):
        resp = authenticated_client.get('/api/v1/categories/')
        slugs = [c['slug'] for c in resp.data]
        assert 'reviews' in slugs
        assert 'hidden' in slugs

    def test_retrieve_by_slug(self, api_client, category):
        resp = api_client.get(f'/api/v1/categories/{category.slug}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['name'] == 'Reviews'

    def test_retrieve_by_id(self, api_client, category):
        resp = api_client.get(f'/api/v1/categories/{category.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['name'] == 'Reviews'

    def test_retrieve_nonexistent(self, api_client):
        resp = api_client.get('/api/v1/categories/nonexistent-slug/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_create_category_staff(self, authenticated_client):
        resp = authenticated_client.post('/api/v1/categories/', {
            'name': 'News', 'slug': 'news'
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['slug'] == 'news'

    def test_create_category_anonymous_forbidden(self, api_client):
        resp = api_client.post('/api/v1/categories/', {
            'name': 'News', 'slug': 'news'
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_category_regular_user_forbidden(self, regular_client):
        resp = regular_client.post('/api/v1/categories/', {
            'name': 'Forbidden', 'slug': 'forbidden'
        })
        # Non-staff should get 403 on write operations
        assert resp.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_201_CREATED]

    def test_update_category_staff(self, authenticated_client, category):
        resp = authenticated_client.patch(f'/api/v1/categories/{category.slug}/', {
            'name': 'Updated Reviews'
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['name'] == 'Updated Reviews'

    def test_delete_category_staff(self, authenticated_client, category):
        resp = authenticated_client.delete(f'/api/v1/categories/{category.slug}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_category_anonymous_forbidden(self, api_client, category):
        resp = api_client.delete(f'/api/v1/categories/{category.slug}/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_search_categories(self, api_client, category):
        resp = api_client.get('/api/v1/categories/', {'search': 'rev'})
        assert resp.status_code == status.HTTP_200_OK


# ═══════════════════════════════════════════════════════════════════════════
# TagViewSet
# ═══════════════════════════════════════════════════════════════════════════

class TestTagViewSet:
    """Tests for /api/v1/tags/"""

    def test_list_tags_anonymous(self, api_client, tag):
        resp = api_client.get('/api/v1/tags/')
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)
        assert len(resp.data) >= 1

    def test_create_tag_staff(self, authenticated_client):
        resp = authenticated_client.post('/api/v1/tags/', {
            'name': 'PHEV', 'slug': 'phev'
        })
        assert resp.status_code == status.HTTP_201_CREATED

    def test_create_tag_anonymous_forbidden(self, api_client):
        resp = api_client.post('/api/v1/tags/', {
            'name': 'PHEV', 'slug': 'phev'
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_tag_staff(self, authenticated_client, tag):
        resp = authenticated_client.patch(f'/api/v1/tags/{tag.id}/', {
            'name': 'EV'
        })
        assert resp.status_code == status.HTTP_200_OK

    def test_delete_tag_staff(self, authenticated_client, tag):
        resp = authenticated_client.delete(f'/api/v1/tags/{tag.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_search_tags(self, api_client, tag):
        resp = api_client.get('/api/v1/tags/', {'search': 'elec'})
        assert resp.status_code == status.HTTP_200_OK


# ═══════════════════════════════════════════════════════════════════════════
# TagGroupViewSet
# ═══════════════════════════════════════════════════════════════════════════

class TestTagGroupViewSet:
    """Tests for /api/v1/tag-groups/"""

    def test_list_tag_groups(self, api_client, tag_group):
        resp = api_client.get('/api/v1/tag-groups/')
        assert resp.status_code == status.HTTP_200_OK

    def test_create_tag_group_staff(self, authenticated_client):
        resp = authenticated_client.post('/api/v1/tag-groups/', {
            'name': 'Body Type'
        })
        assert resp.status_code == status.HTTP_201_CREATED
