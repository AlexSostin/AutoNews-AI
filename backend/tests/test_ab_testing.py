"""
Tests for the A/B Testing system.
Covers variant serving, impression/click tracking, winner selection, and API endpoints.
"""
import pytest
from unittest.mock import patch
from django.test import RequestFactory
from news.models import Article, Category, ArticleTitleVariant


@pytest.fixture
def category(db):
    return Category.objects.create(name='EVs', slug='evs')


@pytest.fixture
def article(db):
    return Article.objects.create(
        title='Original Title', content='<p>Content</p>', is_published=True
    )


@pytest.fixture
def active_test(article):
    """Create an active A/B test with two variants."""
    v_a = ArticleTitleVariant.objects.create(
        article=article, variant='A', title='Original Title',
        impressions=0, clicks=0, is_active=True, auto_pick_threshold=50,
    )
    v_b = ArticleTitleVariant.objects.create(
        article=article, variant='B', title='Clickbait Title!',
        impressions=0, clicks=0, is_active=True, auto_pick_threshold=50,
    )
    return v_a, v_b


@pytest.mark.django_db
class TestABVariantServing:
    """Tests for deterministic variant assignment."""

    def test_variant_returned_for_active_test(self, active_test):
        """Active tests should return one of the variants."""
        from news.ab_testing_views import get_variant_for_request
        v_a, v_b = active_test
        article = v_a.article

        factory = RequestFactory()
        request = factory.get('/')
        request.COOKIES = {'ab_seed': 'test-user-123'}
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        title, variant_id = get_variant_for_request(article, request)

        assert variant_id in [v_a.id, v_b.id]
        if variant_id == v_a.id:
            assert title == 'Original Title'
        else:
            assert title == 'Clickbait Title!'

    def test_consistent_assignment(self, active_test):
        """Same seed should always get the same variant."""
        from news.ab_testing_views import get_variant_for_request
        v_a, _ = active_test
        article = v_a.article

        factory = RequestFactory()
        request = factory.get('/')
        request.COOKIES = {'ab_seed': 'consistent-seed'}
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        results = set()
        for _ in range(10):
            _, variant_id = get_variant_for_request(article, request)
            results.add(variant_id)

        assert len(results) == 1  # Always same variant

    def test_no_active_test_returns_original(self, article):
        """No active test = original title, no variant_id."""
        from news.ab_testing_views import get_variant_for_request

        factory = RequestFactory()
        request = factory.get('/')
        request.COOKIES = {}
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        title, variant_id = get_variant_for_request(article, request)
        assert title == 'Original Title'
        assert variant_id is None


@pytest.mark.django_db
class TestABTracking:
    """Tests for impression and click tracking."""

    def test_impression_increments(self, active_test, authenticated_client):
        """POST /api/v1/ab/impression/ should increment impressions."""
        v_a, _ = active_test
        response = authenticated_client.post('/api/v1/ab/impression/', {'variant_id': v_a.id})

        assert response.status_code == 200
        v_a.refresh_from_db()
        assert v_a.impressions == 1

    def test_click_increments(self, active_test, authenticated_client):
        """POST /api/v1/ab/click/ should increment clicks."""
        v_a, _ = active_test
        response = authenticated_client.post('/api/v1/ab/click/', {'variant_id': v_a.id})

        assert response.status_code == 200
        v_a.refresh_from_db()
        assert v_a.clicks == 1

    def test_inactive_variant_rejected(self, active_test, authenticated_client):
        """Impressions on inactive variants should be rejected."""
        v_a, _ = active_test
        v_a.is_active = False
        v_a.save()

        response = authenticated_client.post('/api/v1/ab/impression/', {'variant_id': v_a.id})
        assert response.status_code == 404


@pytest.mark.django_db
class TestABWinnerSelection:
    """Tests for automatic and manual winner selection."""

    def test_auto_pick_when_threshold_met(self, article):
        """Winner auto-picked when threshold reached and CTR difference is significant."""
        v_a = ArticleTitleVariant.objects.create(
            article=article, variant='A', title='Title A',
            impressions=100, clicks=5, is_active=True, auto_pick_threshold=100,
        )
        v_b = ArticleTitleVariant.objects.create(
            article=article, variant='B', title='Title B',
            impressions=100, clicks=12, is_active=True, auto_pick_threshold=100,
        )

        winners = ArticleTitleVariant.check_and_pick_winners()

        assert len(winners) == 1
        assert winners[0] == (article.id, 'B')

        v_b.refresh_from_db()
        assert v_b.is_winner is True

        article.refresh_from_db()
        assert article.title == 'Title B'

    def test_no_pick_below_threshold(self, article):
        """No winner picked when impressions below threshold."""
        ArticleTitleVariant.objects.create(
            article=article, variant='A', title='Title A',
            impressions=30, clicks=3, is_active=True, auto_pick_threshold=100,
        )
        ArticleTitleVariant.objects.create(
            article=article, variant='B', title='Title B',
            impressions=30, clicks=6, is_active=True, auto_pick_threshold=100,
        )

        winners = ArticleTitleVariant.check_and_pick_winners()
        assert len(winners) == 0

    def test_manual_pick_winner(self, active_test, authenticated_client):
        """Admin can manually pick a winner."""
        v_a, v_b = active_test
        response = authenticated_client.post('/api/v1/ab/pick-winner/', {'variant_id': v_b.id})

        assert response.status_code == 200
        assert response.data['winning_variant'] == 'B'

        v_b.refresh_from_db()
        assert v_b.is_winner is True

        v_a.refresh_from_db()
        assert v_a.is_active is False

    def test_tests_list(self, active_test, authenticated_client):
        """Admin can list all A/B tests."""
        response = authenticated_client.get('/api/v1/ab/tests/')

        assert response.status_code == 200
        assert response.data['count'] >= 1
        test = response.data['tests'][0]
        assert 'variants' in test
        assert len(test['variants']) == 2
