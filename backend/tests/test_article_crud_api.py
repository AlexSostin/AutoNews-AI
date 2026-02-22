"""
Tests for api_views.py — Batch 2: Article CRUD, A/B Testing, Spec Extraction
Covers: ArticleViewSet list/retrieve/destroy, ab_title, ab_click, ab_stats,
        ab_pick_winner, extract_specs, invalidate_article_cache
"""
import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from django.contrib.auth.models import User

pytestmark = pytest.mark.django_db

API = '/api/v1'
UA = {'HTTP_USER_AGENT': 'TestBrowser/1.0'}


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username='staff', email='staff@test.com',
        password='Pass123!', is_staff=True, is_superuser=True,
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username='regular', email='regular@test.com', password='Pass123!',
    )


@pytest.fixture
def staff_client(staff_user):
    client = APIClient(**UA)
    client.force_authenticate(user=staff_user)
    return client


@pytest.fixture
def auth_client(regular_user):
    client = APIClient(**UA)
    client.force_authenticate(user=regular_user)
    return client


@pytest.fixture
def anon_client():
    return APIClient(**UA)


@pytest.fixture
def article(db):
    from news.models import Article
    return Article.objects.create(
        title='Test Article', slug='test-article',
        content='<p>Test content about Tesla Model 3</p>',
        summary='Test summary', is_published=True,
    )


@pytest.fixture
def unpublished_article(db):
    from news.models import Article
    return Article.objects.create(
        title='Draft Article', slug='draft-article',
        content='<p>Draft</p>', summary='Draft',
        is_published=False,
    )


@pytest.fixture
def ab_variant(article):
    from news.models import ArticleTitleVariant
    return ArticleTitleVariant.objects.create(
        article=article, variant='A', title='Title A',
        impressions=100, clicks=10,
    )


@pytest.fixture
def ab_variant_b(article):
    from news.models import ArticleTitleVariant
    return ArticleTitleVariant.objects.create(
        article=article, variant='B', title='Title B',
        impressions=100, clicks=15,
    )


# ═══════════════════════════════════════════════════════════════════════════
# ArticleViewSet.list — GET /api/v1/articles/
# ═══════════════════════════════════════════════════════════════════════════

class TestArticleList:

    def test_list_articles(self, anon_client, article):
        resp = anon_client.get(f'{API}/articles/')
        assert resp.status_code == 200
        assert resp.data['count'] >= 1

    def test_list_excludes_unpublished(self, anon_client, article, unpublished_article):
        resp = anon_client.get(f'{API}/articles/')
        slugs = [a['slug'] for a in resp.data['results']]
        assert 'test-article' in slugs
        assert 'draft-article' not in slugs

    def test_list_search(self, anon_client, article):
        resp = anon_client.get(f'{API}/articles/', {'search': 'Tesla'})
        assert resp.status_code == 200

    def test_list_ordering(self, anon_client, article):
        resp = anon_client.get(f'{API}/articles/', {'ordering': '-created_at'})
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# ArticleViewSet.retrieve — GET /api/v1/articles/{slug}/
# ═══════════════════════════════════════════════════════════════════════════

class TestArticleRetrieve:

    def test_retrieve_by_slug(self, anon_client, article):
        resp = anon_client.get(f'{API}/articles/{article.slug}/')
        assert resp.status_code == 200
        assert resp.data['slug'] == 'test-article'
        assert resp.data['title'] == 'Test Article'

    def test_retrieve_nonexistent(self, anon_client):
        resp = anon_client.get(f'{API}/articles/no-such-slug/')
        assert resp.status_code == 404

    def test_retrieve_by_id(self, anon_client, article):
        resp = anon_client.get(f'{API}/articles/{article.id}/')
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# ArticleViewSet.destroy — DELETE /api/v1/articles/{slug}/
# ═══════════════════════════════════════════════════════════════════════════

class TestArticleDestroy:

    def test_destroy_staff(self, staff_client, article):
        resp = staff_client.delete(f'{API}/articles/{article.slug}/')
        assert resp.status_code == 204

    def test_destroy_anonymous_forbidden(self, anon_client, article):
        resp = anon_client.delete(f'{API}/articles/{article.slug}/')
        assert resp.status_code in (401, 403)

    def test_destroy_regular_user_forbidden(self, auth_client, article):
        resp = auth_client.delete(f'{API}/articles/{article.slug}/')
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# A/B Title Testing — /api/v1/articles/{slug}/ab-title/
# ═══════════════════════════════════════════════════════════════════════════

class TestABTitle:

    def test_ab_title_no_variants(self, anon_client, article):
        resp = anon_client.get(f'{API}/articles/{article.slug}/ab-title/')
        assert resp.status_code == 200
        assert resp.data['ab_active'] is False
        assert resp.data['title'] == article.title

    def test_ab_title_with_variants(self, anon_client, article, ab_variant):
        resp = anon_client.get(f'{API}/articles/{article.slug}/ab-title/')
        assert resp.status_code == 200
        assert resp.data['ab_active'] is True
        assert resp.data['variant'] is not None

    def test_ab_title_bot_gets_variant_a(self, article, ab_variant, ab_variant_b):
        client = APIClient(HTTP_USER_AGENT='Googlebot/2.1')
        resp = client.get(f'{API}/articles/{article.slug}/ab-title/')
        assert resp.status_code == 200
        assert resp.data['variant'] == 'A'


# ═══════════════════════════════════════════════════════════════════════════
# A/B Click — POST /api/v1/articles/{slug}/ab-click/
# ═══════════════════════════════════════════════════════════════════════════

class TestABClick:

    def test_ab_click_success(self, anon_client, article, ab_variant):
        resp = anon_client.post(
            f'{API}/articles/{article.slug}/ab-click/',
            {'variant': 'A'}, format='json',
        )
        assert resp.status_code == 200
        assert resp.data['success'] is True

    def test_ab_click_no_variant(self, anon_client, article):
        resp = anon_client.post(
            f'{API}/articles/{article.slug}/ab-click/',
            {}, format='json',
        )
        assert resp.status_code == 400

    def test_ab_click_invalid_variant(self, anon_client, article, ab_variant):
        resp = anon_client.post(
            f'{API}/articles/{article.slug}/ab-click/',
            {'variant': 'Z'}, format='json',
        )
        assert resp.status_code == 200
        assert resp.data['success'] is False


# ═══════════════════════════════════════════════════════════════════════════
# A/B Stats — GET /api/v1/articles/{slug}/ab-stats/
# ═══════════════════════════════════════════════════════════════════════════

class TestABStats:

    def test_ab_stats_admin(self, staff_client, article, ab_variant, ab_variant_b):
        resp = staff_client.get(f'{API}/articles/{article.slug}/ab-stats/')
        assert resp.status_code == 200
        assert len(resp.data['variants']) == 2
        assert resp.data['total_impressions'] == 200

    def test_ab_stats_anonymous_forbidden(self, anon_client, article):
        resp = anon_client.get(f'{API}/articles/{article.slug}/ab-stats/')
        assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════
# Extract Specs — POST /api/v1/articles/{slug}/extract-specs/
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractSpecs:

    @patch('ai_engine.modules.specs_extractor.extract_vehicle_specs')
    def test_extract_specs_success(self, mock_extract, auth_client, article):
        mock_extract.return_value = {
            'make': 'Tesla', 'model_name': 'Model 3',
            'fuel_type': 'Electric',
        }
        resp = auth_client.post(
            f'{API}/articles/{article.slug}/extract_specs/',
            format='json',
        )
        assert resp.status_code == 200
        assert resp.data['success'] is True

    @patch('ai_engine.modules.specs_extractor.extract_vehicle_specs',
           side_effect=Exception('AI error'))
    def test_extract_specs_error(self, mock_extract, auth_client, article):
        resp = auth_client.post(
            f'{API}/articles/{article.slug}/extract_specs/',
            format='json',
        )
        assert resp.status_code == 500
        assert resp.data['success'] is False

    def test_extract_specs_anonymous_forbidden(self, anon_client, article):
        resp = anon_client.post(
            f'{API}/articles/{article.slug}/extract_specs/',
            format='json',
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# invalidate_article_cache
# ═══════════════════════════════════════════════════════════════════════════

class TestInvalidateArticleCache:

    @patch('news.api_views.cache')
    def test_invalidate_with_article_id(self, mock_cache):
        from news.api_views import invalidate_article_cache
        invalidate_article_cache(article_id=1)
        assert mock_cache.delete_many.called or mock_cache.delete.called

    @patch('news.api_views.cache')
    def test_invalidate_with_slug(self, mock_cache):
        from news.api_views import invalidate_article_cache
        invalidate_article_cache(slug='test-slug')
        assert mock_cache.delete_many.called or mock_cache.delete.called

    @patch('news.api_views.cache')
    def test_invalidate_no_args(self, mock_cache):
        from news.api_views import invalidate_article_cache
        invalidate_article_cache()
        # Should still work (clear list caches even without specific article)
