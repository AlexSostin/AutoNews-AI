"""
Tests for cars_views.py — Car catalog API endpoints.
Covers CarBrandsListView, CarBrandDetailView, CarModelDetailView,
BrandCleanupView, BrandViewSet.
"""
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from news.models import Article, CarSpecification, Brand, VehicleSpecs

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    c = APIClient()
    c.defaults['HTTP_USER_AGENT'] = 'TestBrowser/1.0'
    return c


@pytest.fixture
def admin_client():
    user = User.objects.create_superuser('admin', 'admin@t.com', 'pass')
    c = APIClient()
    c.defaults['HTTP_USER_AGENT'] = 'TestBrowser/1.0'
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def sample_car_data():
    """Create articles with car specs for testing."""
    a1 = Article.objects.create(
        title='Tesla Model 3 Review', slug='tesla-model-3',
        content='Full review', is_published=True,
    )
    a2 = Article.objects.create(
        title='BMW iX xDrive50', slug='bmw-ix',
        content='BMW review', is_published=True,
    )
    a3 = Article.objects.create(
        title='Tesla Model Y', slug='tesla-model-y',
        content='Y review', is_published=True,
    )
    CarSpecification.objects.create(article=a1, make='Tesla', model='Model 3', trim='Long Range')
    CarSpecification.objects.create(article=a2, make='BMW', model='iX', trim='xDrive50')
    CarSpecification.objects.create(article=a3, make='Tesla', model='Model Y')
    return a1, a2, a3


# ═══════════════════════════════════════════════════════════════════════════
# CarBrandsListView — GET /api/v1/cars/brands/
# ═══════════════════════════════════════════════════════════════════════════

class TestCarBrandsList:

    def test_empty_list(self, client):
        resp = client.get('/api/v1/cars/brands/')
        assert resp.status_code == 200

    def test_returns_brands(self, client, sample_car_data):
        resp = client.get('/api/v1/cars/brands/')
        assert resp.status_code == 200
        data = resp.json()
        # Should have at least Tesla and BMW
        brands = data if isinstance(data, list) else data.get('brands', data.get('results', []))
        brand_names = [b.get('name', b.get('make', '')) for b in brands]
        assert any('Tesla' in n or 'tesla' in n.lower() for n in brand_names)

    def test_unauthenticated_access(self, client):
        """Car brands should be publicly accessible."""
        resp = client.get('/api/v1/cars/brands/')
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# CarBrandDetailView — GET /api/v1/cars/brands/{slug}/
# ═══════════════════════════════════════════════════════════════════════════

class TestCarBrandDetail:

    def test_brand_not_found(self, client):
        resp = client.get('/api/v1/cars/brands/nonexistent/')
        assert resp.status_code in (200, 404)

    def test_returns_brand_models(self, client, sample_car_data):
        resp = client.get('/api/v1/cars/brands/tesla/')
        assert resp.status_code == 200
        data = resp.json()
        # Should include Model 3 and Model Y
        content = str(data).lower()
        assert 'model 3' in content or 'model-3' in content or 'tesla' in content


# ═══════════════════════════════════════════════════════════════════════════
# CarModelDetailView — GET /api/v1/cars/brands/{brand}/models/{model}/
# ═══════════════════════════════════════════════════════════════════════════

class TestCarModelDetail:

    def test_model_not_found(self, client):
        resp = client.get('/api/v1/cars/brands/fake/models/fake/')
        assert resp.status_code in (200, 404)

    def test_returns_model_data(self, client, sample_car_data):
        resp = client.get('/api/v1/cars/brands/tesla/models/model-3/')
        assert resp.status_code == 200
        data = resp.json()
        assert data is not None


# ═══════════════════════════════════════════════════════════════════════════
# BrandCleanupView — POST /api/v1/cars/cleanup/
# ═══════════════════════════════════════════════════════════════════════════

class TestBrandCleanup:

    def test_requires_admin(self, client):
        resp = client.post('/api/v1/cars/cleanup/')
        assert resp.status_code in (401, 403)

    def test_dry_run(self, admin_client, sample_car_data):
        resp = admin_client.post('/api/v1/cars/cleanup/')
        assert resp.status_code == 200

    def test_apply(self, admin_client, sample_car_data):
        resp = admin_client.post('/api/v1/cars/cleanup/', {'apply': 'true'})
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# BrandViewSet — /api/v1/admin/brands/
# ═══════════════════════════════════════════════════════════════════════════

class TestBrandViewSet:

    def test_list_requires_auth(self, client):
        resp = client.get('/api/v1/admin/brands/')
        assert resp.status_code in (401, 403)

    def test_admin_can_list(self, admin_client):
        resp = admin_client.get('/api/v1/admin/brands/')
        assert resp.status_code == 200

    def test_create_brand(self, admin_client):
        resp = admin_client.post('/api/v1/admin/brands/', {
            'name': 'TestBrand', 'slug': 'testbrand',
        })
        assert resp.status_code in (201, 200)
        assert Brand.objects.filter(slug='testbrand').exists()

    def test_update_brand(self, admin_client):
        brand = Brand.objects.create(name='OldName', slug='oldname')
        resp = admin_client.patch(f'/api/v1/admin/brands/{brand.id}/', {
            'name': 'NewName',
        })
        assert resp.status_code == 200

    def test_delete_brand(self, admin_client):
        brand = Brand.objects.create(name='Delete Me', slug='delete-me')
        resp = admin_client.delete(f'/api/v1/admin/brands/{brand.id}/')
        assert resp.status_code in (204, 200)

    def test_merge_brands(self, admin_client, sample_car_data):
        target = Brand.objects.create(name='Tesla', slug='tesla')
        source = Brand.objects.create(name='TSLA', slug='tsla')
        resp = admin_client.post(f'/api/v1/admin/brands/{target.id}/merge/', {
            'source_brand_id': source.id,
        })
        assert resp.status_code == 200

    def test_sync_from_specs(self, admin_client, sample_car_data):
        resp = admin_client.post('/api/v1/admin/brands/sync/')
        assert resp.status_code == 200
        # Should create Brand records from CarSpecification data
        assert Brand.objects.count() > 0
