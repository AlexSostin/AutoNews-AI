"""
Tests for Comparison Article API endpoints.
Tests: comparison_pairs, generate_comparison endpoints on VehicleSpecsViewSet.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User

from news.models import Article, VehicleSpecs, Category, Tag, CarSpecification


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='testadmin', password='testpass123')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def ev_suv_specs(db):
    """Create two EV SUVs from different brands for pairing."""
    spec_a = VehicleSpecs.objects.create(
        make='BYD', model_name='Sealion 07', trim_name='EV AWD',
        body_type='SUV', fuel_type='EV',
        power_hp=530, torque_nm=690, acceleration_0_100=3.8,
        battery_kwh=82.5, range_wltp=570, price_from=280000, price_to=350000,
        currency='CNY', length_mm=4830, weight_kg=2400,
    )
    spec_b = VehicleSpecs.objects.create(
        make='NIO', model_name='ONVO L60', trim_name='Standard',
        body_type='SUV', fuel_type='EV',
        power_hp=340, torque_nm=500, acceleration_0_100=5.9,
        battery_kwh=60, range_wltp=450, price_from=220000, price_to=280000,
        currency='CNY', length_mm=4828, weight_kg=2100,
    )
    return spec_a, spec_b


@pytest.fixture
def same_brand_specs(db):
    """Two specs from the same brand — should not be paired."""
    VehicleSpecs.objects.create(
        make='BYD', model_name='Seal', body_type='sedan', fuel_type='EV',
        power_hp=300, battery_kwh=61, range_wltp=510,
    )
    VehicleSpecs.objects.create(
        make='BYD', model_name='Sealion 05', body_type='sedan', fuel_type='EV',
        power_hp=218, battery_kwh=55, range_wltp=460,
    )


@pytest.fixture
def no_segment_specs(db):
    """Specs without body_type/fuel_type — should be excluded."""
    VehicleSpecs.objects.create(make='Rivian', model_name='R1T', power_hp=835)


class TestComparisonPairsEndpoint:
    """Tests for GET /api/v1/vehicle-specs/comparison-pairs/"""

    def test_pairs_returns_pairs(self, auth_client, ev_suv_specs):
        resp = auth_client.get('/api/v1/vehicle-specs/comparison-pairs/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['total_vehicles'] == 2
        assert data['total_pairs'] == 1
        assert len(data['pairs']) == 1

        pair = data['pairs'][0]
        makes = {pair['spec_a']['make'], pair['spec_b']['make']}
        assert makes == {'BYD', 'NIO'}
        assert pair['score'] > 0
        assert pair['data_health']['a']['filled'] > 0
        assert pair['data_health']['b']['filled'] > 0
        assert pair['segment'] == 'EV SUV'

    def test_pairs_excludes_same_brand(self, auth_client, same_brand_specs):
        resp = auth_client.get('/api/v1/vehicle-specs/comparison-pairs/')
        assert resp.status_code == 200
        assert resp.json()['total_pairs'] == 0

    def test_pairs_excludes_no_segment(self, auth_client, no_segment_specs):
        resp = auth_client.get('/api/v1/vehicle-specs/comparison-pairs/')
        assert resp.status_code == 200
        assert resp.json()['total_vehicles'] == 0

    def test_pairs_segment_filter(self, auth_client, ev_suv_specs):
        resp = auth_client.get('/api/v1/vehicle-specs/comparison-pairs/?segment=SUV&fuel=EV')
        assert resp.status_code == 200
        assert resp.json()['total_pairs'] == 1

        resp2 = auth_client.get('/api/v1/vehicle-specs/comparison-pairs/?segment=sedan')
        assert resp2.status_code == 200
        assert resp2.json()['total_pairs'] == 0

    def test_pairs_excludes_existing_articles(self, auth_client, ev_suv_specs):
        """If a comparison article already exists, mark it in existing_article."""
        Article.objects.create(
            title='BYD Sealion 07 vs NIO ONVO L60',
            slug='byd-sealion-07-vs-nio-onvo-l60-comparison',
            content='<p>Test</p>',
        )
        resp = auth_client.get('/api/v1/vehicle-specs/comparison-pairs/')
        pair = resp.json()['pairs'][0]
        assert pair['existing_article'] is not None
        assert pair['existing_article']['slug'] == 'byd-sealion-07-vs-nio-onvo-l60-comparison'

    def test_pairs_auth_required(self, db):
        client = APIClient()
        resp = client.get('/api/v1/vehicle-specs/comparison-pairs/')
        assert resp.status_code in (401, 403)

    def test_pairs_limit(self, auth_client, ev_suv_specs):
        resp = auth_client.get('/api/v1/vehicle-specs/comparison-pairs/?limit=0')
        assert resp.status_code == 200
        assert len(resp.json()['pairs']) == 0

    def test_pairs_data_health_counts(self, auth_client, ev_suv_specs):
        """Health fields should reflect what's actually filled."""
        resp = auth_client.get('/api/v1/vehicle-specs/comparison-pairs/')
        health_a = resp.json()['pairs'][0]['data_health']['a']
        assert health_a['total'] == 12  # DATA_HEALTH_FIELDS count
        assert health_a['filled'] >= 8  # We filled 10+ fields


class TestGenerateComparisonEndpoint:
    """Tests for POST /api/v1/vehicle-specs/generate-comparison/"""

    @patch('ai_engine.modules.comparison_generator.generate_comparison')
    def test_generate_creates_draft(self, mock_gen, auth_client, ev_suv_specs):
        spec_a, spec_b = ev_suv_specs
        mock_gen.return_value = {
            'title': 'BYD Sealion 07 vs NIO ONVO L60: EV SUV Showdown',
            'content': '<h2>Analysis</h2><p>Both are great EVs.</p>',
            'summary': 'A detailed comparison of two popular EV SUVs.',
            'seo_description': 'Compare BYD Sealion 07 and NIO ONVO L60...',
            'slug': 'byd-sealion-07-vs-nio-onvo-l60-comparison',
            'word_count': 850,
        }

        resp = auth_client.post('/api/v1/vehicle-specs/generate-comparison/', {
            'spec_a_id': spec_a.id,
            'spec_b_id': spec_b.id,
            'provider': 'gemini',
        }, format='json')

        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['word_count'] == 850

        # Verify article was created as draft
        article = Article.objects.get(slug='byd-sealion-07-vs-nio-onvo-l60-comparison')
        assert article.is_published is False
        assert article.generation_metadata['source'] == 'comparison_generator'

        # Verify category
        assert article.categories.filter(name='Comparisons').exists()

    def test_generate_missing_ids(self, auth_client, ev_suv_specs):
        resp = auth_client.post('/api/v1/vehicle-specs/generate-comparison/', {
            'spec_a_id': 1,
        }, format='json')
        assert resp.status_code == 400

    def test_generate_invalid_ids(self, auth_client, db):
        resp = auth_client.post('/api/v1/vehicle-specs/generate-comparison/', {
            'spec_a_id': 99999,
            'spec_b_id': 99998,
        }, format='json')
        assert resp.status_code == 404

    def test_generate_auth_required(self, db, ev_suv_specs):
        spec_a, spec_b = ev_suv_specs
        client = APIClient()
        resp = client.post('/api/v1/vehicle-specs/generate-comparison/', {
            'spec_a_id': spec_a.id,
            'spec_b_id': spec_b.id,
        }, format='json')
        assert resp.status_code in (401, 403)

    @patch('ai_engine.modules.comparison_generator.generate_comparison')
    def test_generate_unique_slug(self, mock_gen, auth_client, ev_suv_specs):
        """If slug already exists, should auto-increment."""
        spec_a, spec_b = ev_suv_specs
        Article.objects.create(
            title='Existing', slug='byd-sealion-07-vs-nio-onvo-l60-comparison',
            content='<p>Old</p>',
        )
        mock_gen.return_value = {
            'title': 'New Comparison',
            'content': '<p>New</p>',
            'summary': 'Test',
            'seo_description': 'Test',
            'slug': 'byd-sealion-07-vs-nio-onvo-l60-comparison',
            'word_count': 500,
        }

        resp = auth_client.post('/api/v1/vehicle-specs/generate-comparison/', {
            'spec_a_id': spec_a.id,
            'spec_b_id': spec_b.id,
        }, format='json')

        assert resp.status_code == 200
        # Should have incremented slug
        article = Article.objects.filter(title='New Comparison').first()
        assert article is not None
        assert article.slug == 'byd-sealion-07-vs-nio-onvo-l60-comparison-1'
