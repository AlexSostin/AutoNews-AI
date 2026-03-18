"""
Tests for the next-article endpoint used by InfiniteArticleScroll.

These tests exist to prevent a specific regression: the endpoint MUST return
full article data (content, specs, gallery, attribution) — not lightweight
list data — because ArticleUnit renders the article in-place.

If someone switches back to ArticleListSerializer, these tests will fail.
"""
import pytest
from unittest.mock import patch
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

API = '/api/v1'
UA = {'HTTP_USER_AGENT': 'TestBrowser/1.0'}


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def anon_client():
    return APIClient(**UA)


@pytest.fixture
def category(db):
    from news.models import Category
    return Category.objects.create(name='Electric Vehicles', slug='electric-vehicles')


@pytest.fixture
def tag(db):
    from news.models import Tag
    return Tag.objects.create(name='EV', slug='ev')


@pytest.fixture
def article_a(db, category, tag):
    """First article — the one we're reading."""
    from news.models import Article
    a = Article.objects.create(
        title='Tesla Model 3 Review',
        slug='tesla-model-3-review',
        content='<p>Full review of the Tesla Model 3 Long Range.</p>',
        summary='A detailed review of the Tesla Model 3',
        seo_description='Tesla Model 3 review with specs and pricing',
        youtube_url='https://www.youtube.com/watch?v=test123',
        is_published=True,
    )
    a.categories.add(category)
    a.tags.add(tag)
    return a


@pytest.fixture
def article_b(db, category, tag):
    """Second article — candidate for next-article."""
    from news.models import Article
    a = Article.objects.create(
        title='BMW i4 First Drive',
        slug='bmw-i4-first-drive',
        content='<p>We spent a week with the BMW i4 eDrive40.</p>',
        summary='BMW i4 first impressions and review',
        seo_description='BMW i4 review and specs',
        is_published=True,
    )
    a.categories.add(category)
    a.tags.add(tag)
    return a


@pytest.fixture
def article_c(db):
    """Third article — different category, no tags."""
    from news.models import Article
    return Article.objects.create(
        title='F1 News Roundup',
        slug='f1-news-roundup',
        content='<p>Latest Formula 1 news and updates.</p>',
        summary='F1 weekly roundup',
        is_published=True,
    )


@pytest.fixture
def unpublished_article(db):
    from news.models import Article
    return Article.objects.create(
        title='Draft Article',
        slug='draft-article',
        content='<p>Not yet published</p>',
        summary='Draft',
        is_published=False,
    )


@pytest.fixture
def article_with_specs(db, category):
    """Article with CarSpecification attached."""
    from news.models import Article
    from news.models import CarSpecification
    a = Article.objects.create(
        title='Hyundai Ioniq 5 Review',
        slug='hyundai-ioniq-5-review',
        content='<p>The Ioniq 5 is a game changer.</p>',
        summary='Ioniq 5 review',
        is_published=True,
    )
    a.categories.add(category)
    CarSpecification.objects.create(
        article=a,
        make='Hyundai',
        model='Ioniq 5',
    )
    return a


@pytest.fixture
def article_same_make(db, category):
    """Another Hyundai article for same-make priority test."""
    from news.models import Article
    from news.models import CarSpecification
    a = Article.objects.create(
        title='Hyundai Kona Electric Review',
        slug='hyundai-kona-electric-review',
        content='<p>The Kona Electric is practical and fun.</p>',
        summary='Kona EV review',
        is_published=True,
    )
    a.categories.add(category)
    CarSpecification.objects.create(
        article=a,
        make='Hyundai',
        model='Kona Electric',
    )
    return a


# ═══════════════════════════════════════════════════════════════════════════
# Core: Response must contain full article data (prevents serializer regression)
# ═══════════════════════════════════════════════════════════════════════════

class TestNextArticleFullData:
    """
    CRITICAL: These tests ensure next-article returns ArticleDetailSerializer data.
    If someone changes the serializer to ArticleListSerializer, these will fail.
    """

    def test_returns_article_content(self, anon_client, article_a, article_b):
        """Infinite scroll articles must include 'content' for rendering."""
        resp = anon_client.get(f'{API}/articles/{article_a.slug}/next-article/')
        assert resp.status_code == 200
        assert resp.data['article'] is not None
        assert 'content' in resp.data['article'], \
            "next-article must return 'content' — ArticleUnit needs it to render"
        assert len(resp.data['article']['content']) > 0

    def test_returns_seo_description(self, anon_client, article_a, article_b):
        """SEO description is needed for JSON-LD in infinite scroll."""
        resp = anon_client.get(f'{API}/articles/{article_a.slug}/next-article/')
        assert resp.status_code == 200
        assert 'seo_description' in resp.data['article']

    def test_returns_images_gallery(self, anon_client, article_a, article_b):
        """Gallery data must be present (even if empty array)."""
        resp = anon_client.get(f'{API}/articles/{article_a.slug}/next-article/')
        assert resp.status_code == 200
        assert 'images' in resp.data['article']

    def test_returns_tags_as_objects(self, anon_client, article_a, article_b):
        """Detail serializer returns full tag objects, not just tag_names."""
        resp = anon_client.get(f'{API}/articles/{article_a.slug}/next-article/')
        assert resp.status_code == 200
        article_data = resp.data['article']
        assert 'tags' in article_data

    def test_returns_vehicle_specs(self, anon_client, article_with_specs, article_same_make):
        """Vehicle specs must be included for the specs table."""
        resp = anon_client.get(f'{API}/articles/{article_with_specs.slug}/next-article/')
        assert resp.status_code == 200
        article_data = resp.data['article']
        assert 'vehicle_specs' in article_data or 'car_specification' in article_data

    def test_returns_source_attribution_fields(self, anon_client, article_a, article_b):
        """Source attribution fields needed for SourceAttribution component."""
        resp = anon_client.get(f'{API}/articles/{article_a.slug}/next-article/')
        assert resp.status_code == 200
        article_data = resp.data['article']
        # These fields exist on ArticleDetailSerializer but NOT on ArticleListSerializer
        for field in ['youtube_channel_name', 'youtube_channel_url',
                      'youtube_channel_is_partner', 'rss_feed_name',
                      'rss_feed_website_url', 'rss_feed_is_partner']:
            assert field in article_data, \
                f"next-article must return '{field}' for SourceAttribution component"

    def test_returns_essential_common_fields(self, anon_client, article_a, article_b):
        """Verify all essential fields are present."""
        resp = anon_client.get(f'{API}/articles/{article_a.slug}/next-article/')
        assert resp.status_code == 200
        article_data = resp.data['article']
        essential_fields = [
            'id', 'title', 'slug', 'content', 'summary',
            'image', 'created_at', 'updated_at', 'is_published',
            'views', 'average_rating', 'rating_count',
            'categories', 'show_source', 'show_youtube', 'show_price',
            'image_source',
        ]
        for field in essential_fields:
            assert field in article_data, \
                f"next-article missing essential field '{field}'"


# ═══════════════════════════════════════════════════════════════════════════
# Exclude logic — prevents duplicate articles in infinite scroll
# ═══════════════════════════════════════════════════════════════════════════

class TestNextArticleExclude:

    def test_excludes_self(self, anon_client, article_a, article_b):
        """The current article must never appear as 'next'."""
        resp = anon_client.get(f'{API}/articles/{article_a.slug}/next-article/')
        assert resp.status_code == 200
        assert resp.data['article']['slug'] != article_a.slug

    def test_excludes_specified_slugs(self, anon_client, article_a, article_b, article_c):
        """Exclude parameter prevents repeats in the feed."""
        resp = anon_client.get(
            f'{API}/articles/{article_a.slug}/next-article/',
            {'exclude': [article_a.slug, article_b.slug]}
        )
        assert resp.status_code == 200
        if resp.data['article'] is not None:
            assert resp.data['article']['slug'] not in [article_a.slug, article_b.slug]

    def test_returns_null_when_all_excluded(self, anon_client, article_a, article_b):
        """When all articles are excluded, returns null gracefully."""
        from news.models import Article
        all_slugs = list(Article.objects.filter(
            is_published=True
        ).values_list('slug', flat=True))
        resp = anon_client.get(
            f'{API}/articles/{article_a.slug}/next-article/',
            {'exclude': all_slugs}
        )
        assert resp.status_code == 200
        assert resp.data['article'] is None
        assert resp.data['source'] == 'none'

    def test_never_returns_unpublished(self, anon_client, article_a, unpublished_article):
        """Unpublished articles must never appear in infinite scroll."""
        resp = anon_client.get(f'{API}/articles/{article_a.slug}/next-article/')
        assert resp.status_code == 200
        if resp.data['article'] is not None:
            assert resp.data['article']['is_published'] is True


# ═══════════════════════════════════════════════════════════════════════════
# Priority: same make/model → category → popular
# ═══════════════════════════════════════════════════════════════════════════

class TestNextArticlePriority:

    def test_same_make_priority(self, anon_client, article_with_specs, article_same_make, article_c):
        """Articles with same car make should be prioritized."""
        resp = anon_client.get(f'{API}/articles/{article_with_specs.slug}/next-article/')
        assert resp.status_code == 200
        assert resp.data['article'] is not None
        # Should prefer same make (Hyundai) over unrelated article
        assert resp.data['source'] in ('same_model', 'same_make'), \
            f"Expected same_make/model priority, got '{resp.data['source']}'"
        assert resp.data['article']['slug'] == article_same_make.slug

    def test_source_field_present(self, anon_client, article_a, article_b):
        """Response must include 'source' field for debugging."""
        resp = anon_client.get(f'{API}/articles/{article_a.slug}/next-article/')
        assert resp.status_code == 200
        assert 'source' in resp.data
        valid_sources = [
            'same_model', 'same_make', 'session_brand', 'session_category',
            'ml_similar', 'same_category', 'popular', 'none',
        ]
        assert resp.data['source'] in valid_sources


# ═══════════════════════════════════════════════════════════════════════════
# Edge cases and access control
# ═══════════════════════════════════════════════════════════════════════════

class TestNextArticleEdgeCases:

    def test_nonexistent_article_404(self, anon_client):
        """Requesting next for non-existent slug returns 404."""
        resp = anon_client.get(f'{API}/articles/no-such-article/next-article/')
        assert resp.status_code == 404

    def test_accessible_anonymously(self, anon_client, article_a, article_b):
        """Endpoint must be accessible without auth (public feed)."""
        resp = anon_client.get(f'{API}/articles/{article_a.slug}/next-article/')
        assert resp.status_code == 200

    def test_no_candidates_returns_null(self, anon_client, article_a):
        """When all other articles are excluded, next-article returns null.
        
        Note: can't test truly single article due to xdist shared DB,
        so we simulate it by excluding everything via the exclude param.
        """
        from news.models import Article
        all_slugs = list(Article.objects.filter(
            is_published=True
        ).values_list('slug', flat=True))
        resp = anon_client.get(
            f'{API}/articles/{article_a.slug}/next-article/',
            {'exclude': all_slugs}
        )
        assert resp.status_code == 200
        assert resp.data['article'] is None
        assert resp.data['source'] == 'none'

    def test_response_is_cacheable(self, anon_client, article_a, article_b):
        """Calling twice with same params should return identical data."""
        resp1 = anon_client.get(f'{API}/articles/{article_a.slug}/next-article/')
        resp2 = anon_client.get(f'{API}/articles/{article_a.slug}/next-article/')
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        # Same result both times (whether from cache or fresh)
        assert resp1.data['article']['slug'] == resp2.data['article']['slug']
