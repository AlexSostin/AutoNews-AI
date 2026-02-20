"""
Tests for Car Brands API.
"""
import pytest
from rest_framework import status
from news.models import Article, CarSpecification


@pytest.mark.django_db
class TestCarBrandsAPI:
    """Tests for /api/v1/cars/brands/ endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self):
        # CarBrandDetailView queries CarSpecification, not Brand model
        self.article1 = Article.objects.create(
            title='BMW X5 Review', slug='bmw-x5-review',
            content='<p>BMW review</p>', is_published=True
        )
        CarSpecification.objects.create(
            article=self.article1, make='BMW', model='X5',
            engine='3.0L', horsepower='335'
        )
        self.article2 = Article.objects.create(
            title='Toyota Camry Review', slug='toyota-camry-review',
            content='<p>Toyota review</p>', is_published=True
        )
        CarSpecification.objects.create(
            article=self.article2, make='Toyota', model='Camry',
            engine='2.5L', horsepower='203'
        )

    def test_list_brands(self, api_client):
        """Should list brands with articles"""
        resp = api_client.get('/api/v1/cars/brands/')
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)
        assert len(resp.data) >= 2

    def test_brand_detail(self, api_client):
        """Should return brand detail by slug"""
        resp = api_client.get('/api/v1/cars/brands/bmw/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['brand'] == 'BMW'
        assert len(resp.data['models']) >= 1

    def test_brand_not_found(self, api_client):
        """Non-existent brand returns 404"""
        resp = api_client.get('/api/v1/cars/brands/nonexistent/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_brand_models_have_specs(self, api_client):
        """Brand detail should include model specs"""
        resp = api_client.get('/api/v1/cars/brands/bmw/')
        assert resp.status_code == status.HTTP_200_OK
        models = resp.data['models']
        assert len(models) >= 1
        assert models[0]['model'] == 'X5'

    def test_brands_have_counts(self, api_client):
        """Brand list should include article and model counts"""
        resp = api_client.get('/api/v1/cars/brands/')
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)
        # Each brand should have article_count and model_count
        for brand in resp.data:
            assert 'article_count' in brand
            assert 'model_count' in brand
