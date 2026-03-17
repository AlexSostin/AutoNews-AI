"""
Tests for infinite scroll system:
- next-article endpoint (priority chain, caching, exclude, lightweight response)  
- Article list pagination (page_size, next link, last page)
- ArticleListSerializer field validation (no image_2/image_3)
"""
import pytest
from unittest.mock import patch, MagicMock
from django.core.cache import cache
from rest_framework import status
from news.models import Article, Category, CarSpecification


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_article(slug, title=None, is_published=True, views=0, **kwargs):
    """Create a published article with sensible defaults."""
    return Article.objects.create(
        slug=slug,
        title=title or slug.replace('-', ' ').title(),
        content=f'<p>Content for {slug}</p>',
        summary=f'Summary for {slug}',
        is_published=is_published,
        views=views,
        **kwargs,
    )


def _make_spec(article, make='Tesla', model='Model 3'):
    """Attach a CarSpecification to an article."""
    # CarSpecification has a OneToOneField to Article with related_name='specs'
    return CarSpecification.objects.create(
        article=article, make=make, model=model,
        model_name=f'{make} {model}',
    )


# ── next-article endpoint ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestNextArticle:
    """GET /api/v1/articles/{slug}/next-article/"""

    URL_TPL = '/api/v1/articles/{slug}/next-article/'

    def setup_method(self):
        cache.clear()

    # --- Basic functionality ---

    def test_returns_article(self, api_client):
        """Should return a next article for a published article."""
        a1 = _make_article('article-one')
        a2 = _make_article('article-two', views=10)
        resp = api_client.get(self.URL_TPL.format(slug=a1.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['article'] is not None
        assert resp.data['article']['slug'] == a2.slug

    def test_excludes_self(self, api_client):
        """Should never return the same article."""
        a1 = _make_article('only-article')
        resp = api_client.get(self.URL_TPL.format(slug=a1.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['article'] is None
        assert resp.data['source'] == 'none'

    def test_excludes_by_param(self, api_client):
        """?exclude= param should skip specified slugs."""
        a1 = _make_article('base-art')
        a2 = _make_article('skip-this', views=100)
        a3 = _make_article('show-this', views=50)
        url = self.URL_TPL.format(slug=a1.slug) + '?exclude=skip-this'
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['article']['slug'] == a3.slug

    def test_only_published(self, api_client):
        """Should never return draft articles."""
        a1 = _make_article('published-one')
        _make_article('draft-one', is_published=False, views=999)
        resp = api_client.get(self.URL_TPL.format(slug=a1.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['article'] is None

    def test_returns_none_when_empty_db(self, api_client):
        """Should return article=None when no other articles exist."""
        a1 = _make_article('lonely-article')
        resp = api_client.get(self.URL_TPL.format(slug=a1.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['article'] is None
        assert resp.data['source'] == 'none'

    # --- Priority chain ---

    def test_prefers_same_model(self, api_client):
        """Priority 1: same make+model should be chosen over same make or popular."""
        a1 = _make_article('tesla-m3-review')
        _make_spec(a1, make='Tesla', model='Model 3')

        # Same make, different model (should be lower priority)
        a_make = _make_article('tesla-model-y', views=100)
        _make_spec(a_make, make='Tesla', model='Model Y')

        # Same make AND model (should win)
        a_model = _make_article('tesla-m3-perf')
        _make_spec(a_model, make='Tesla', model='Model 3')

        resp = api_client.get(self.URL_TPL.format(slug=a1.slug))
        assert resp.data['article']['slug'] == a_model.slug
        assert resp.data['source'] == 'same_model'

    def test_prefers_same_make(self, api_client):
        """Priority 2: same make (any model) when no same model exists."""
        a1 = _make_article('tesla-m3-rev')
        _make_spec(a1, make='Tesla', model='Model 3')

        # Same make, different model
        a_make = _make_article('tesla-model-s')
        _make_spec(a_make, make='Tesla', model='Model S')

        # Different make
        a_other = _make_article('bmw-i4', views=500)
        _make_spec(a_other, make='BMW', model='i4')

        resp = api_client.get(self.URL_TPL.format(slug=a1.slug))
        assert resp.data['article']['slug'] == a_make.slug
        assert resp.data['source'] == 'same_make'

    def test_falls_back_to_popular(self, api_client):
        """Priority 5: popular fallback when no make/model/category match."""
        a1 = _make_article('random-article')
        a_popular = _make_article('most-popular', views=999)
        a_less = _make_article('less-popular', views=1)
        resp = api_client.get(self.URL_TPL.format(slug=a1.slug))
        assert resp.data['article']['slug'] == a_popular.slug
        assert resp.data['source'] == 'popular'

    def test_category_fallback(self, api_client):
        """Priority 4: same category when no make/model match."""
        cat = Category.objects.create(name='Electric', slug='electric')
        a1 = _make_article('ev-article')
        a1.categories.add(cat)

        a_same_cat = _make_article('another-ev', views=50)
        a_same_cat.categories.add(cat)

        a_other = _make_article('suv-article', views=500)

        resp = api_client.get(self.URL_TPL.format(slug=a1.slug))
        assert resp.data['article']['slug'] == a_same_cat.slug
        assert resp.data['source'] == 'same_category'

    # --- Caching ---

    def test_cached_response_served(self, api_client):
        """Second request within 60s should serve cached response — real cache."""
        cache.clear()  # Isolate from parallel workers

        a1 = _make_article('cache-test')
        a2 = _make_article('cache-target', views=10)

        # First request — populates cache
        resp1 = api_client.get(self.URL_TPL.format(slug=a1.slug))
        assert resp1.data['article'] is not None
        assert resp1.data['article']['slug'] == a2.slug

        # Create a new article with higher views — WITHOUT cache, it would win
        _make_article('cache-interloper', views=999)

        # Second request — should still return cached a2, not the new interloper
        resp2 = api_client.get(self.URL_TPL.format(slug=a1.slug))
        assert resp2.data['article']['slug'] == a2.slug

    # --- Response weight ---

    def test_response_is_lightweight(self, api_client):
        """Response should NOT contain full content, vehicle_specs, or gallery."""
        a1 = _make_article('light-test')
        a2 = _make_article('light-result', views=10)
        resp = api_client.get(self.URL_TPL.format(slug=a1.slug))
        article_data = resp.data['article']
        assert article_data is not None
        # Must NOT have heavy fields
        assert 'content' not in article_data
        assert 'vehicle_specs' not in article_data
        assert 'images' not in article_data
        assert 'car_specification' not in article_data
        # Must HAVE lightweight list fields
        assert 'title' in article_data
        assert 'slug' in article_data
        assert 'thumbnail_url' in article_data
        assert 'categories' in article_data

    def test_response_has_source_field(self, api_client):
        """Response should always include source field."""
        a1 = _make_article('source-test')
        _make_article('source-result', views=5)
        resp = api_client.get(self.URL_TPL.format(slug=a1.slug))
        assert 'source' in resp.data
        assert resp.data['source'] in ('same_model', 'same_make', 'session_brand',
                                        'session_category', 'ml_similar',
                                        'same_category', 'popular', 'none')


# ── Article list pagination ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestArticlePaginationAdvanced:
    """GET /api/v1/articles/ — pagination behavior"""

    URL = '/api/v1/articles/'

    def test_custom_page_size(self, api_client):
        """?page_size=6 should return exactly 6 articles."""
        for i in range(10):
            _make_article(f'pag-art-{i}')
        resp = api_client.get(f'{self.URL}?page_size=6')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data['results']) == 6

    def test_has_next_link(self, api_client):
        """First page should have 'next' link when more pages exist."""
        for i in range(25):
            _make_article(f'next-link-{i}')
        resp = api_client.get(f'{self.URL}?page_size=6')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['next'] is not None

    def test_last_page_no_next(self, api_client):
        """Last page should have next=null."""
        for i in range(3):
            _make_article(f'last-page-{i}')
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['next'] is None  # Only 3 articles, fits in 1 page

    def test_pagination_preserves_filter(self, api_client):
        """Pagination should work with category filter."""
        cat = Category.objects.create(name='Electric', slug='electric')
        for i in range(5):
            a = _make_article(f'ev-pag-{i}')
            a.categories.add(cat)
        for i in range(5):
            _make_article(f'other-pag-{i}')
        resp = api_client.get(f'{self.URL}?category=electric&page_size=3')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data['results']) == 3
        # All should be electric category
        for article in resp.data['results']:
            cat_names = [c['name'] for c in article['categories']]
            assert 'Electric' in cat_names


# ── ArticleListSerializer field validation ───────────────────────────────────

@pytest.mark.django_db
class TestArticleListSerializerFields:
    """Verify list serializer is lightweight."""

    URL = '/api/v1/articles/'

    def test_list_excludes_image_2_3(self, api_client):
        """List serializer should NOT return image_2, image_3 (heavy, unused in cards)."""
        _make_article('field-test')
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data['results']) >= 1
        article_data = resp.data['results'][0]
        assert 'image_2' not in article_data
        assert 'image_3' not in article_data
        assert 'image_2_url' not in article_data
        assert 'image_3_url' not in article_data

    def test_list_includes_essential_fields(self, api_client):
        """List serializer must include all fields needed for article cards."""
        _make_article('essential-test')
        resp = api_client.get(self.URL)
        article_data = resp.data['results'][0]
        essential = ['id', 'title', 'slug', 'summary', 'image', 'thumbnail_url',
                     'categories', 'views', 'created_at', 'image_source']
        for field in essential:
            assert field in article_data, f"Missing essential field: {field}"

    def test_detail_still_has_image_2_3(self, api_client):
        """Detail serializer should STILL return image_2, image_3."""
        a = _make_article('detail-field-test')
        resp = api_client.get(f'/api/v1/articles/{a.slug}/')
        assert resp.status_code == status.HTTP_200_OK
        assert 'image_2' in resp.data
        assert 'image_3' in resp.data
        assert 'content' in resp.data  # Full content in detail
