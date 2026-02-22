"""
Batch 2: ArticleViewSet AI Actions — generate_from_youtube, translate_enhance,
regenerate, re_enrich.

Targets ~360 uncovered lines (L779-838, L910-1095, L1672-1838, L1868-2009).
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from news.models import (
    Article, Category, Tag, TagGroup, CarSpecification, VehicleSpecs,
    PendingArticle, RSSNewsItem, RSSFeed,
)

pytestmark = pytest.mark.django_db

UA = {'HTTP_USER_AGENT': 'TestBrowser/1.0'}


@pytest.fixture
def staff_user():
    return User.objects.create_user('staffb2', 'staff@b2.com', 'pass', is_staff=True)


@pytest.fixture
def regular_user():
    return User.objects.create_user('userb2', 'user@b2.com', 'pass')


@pytest.fixture
def staff_client(staff_user):
    c = APIClient()
    c.force_authenticate(user=staff_user)
    return c


@pytest.fixture
def user_client(regular_user):
    c = APIClient()
    c.force_authenticate(user=regular_user)
    return c


@pytest.fixture
def article():
    return Article.objects.create(
        title='2026 Tesla Model Y Review',
        slug='test-tesla-model-y',
        content='<h2>Test</h2><p>Original content about Tesla Model Y</p>',
        is_published=True,
    )


@pytest.fixture
def article_with_youtube():
    return Article.objects.create(
        title='2026 BYD Seal First Drive',
        slug='test-byd-seal',
        content='<h2>BYD Seal</h2><p>Content</p>',
        youtube_url='https://www.youtube.com/watch?v=testBYD12345',
        is_published=True,
    )


@pytest.fixture
def article_with_rss():
    feed = RSSFeed.objects.create(name='Test Feed', feed_url='http://test.com/feed.xml')
    art = Article.objects.create(
        title='2026 ZEEKR 007 Launched',
        slug='test-zeekr-007',
        content='<h2>ZEEKR</h2><p>ZEEKR 007 content</p>',
        author_channel_url='http://test.com/zeekr-007',
        is_published=True,
    )
    pending = PendingArticle.objects.create(
        title='ZEEKR 007',
        source_url='http://test.com/zeekr-007',
        rss_feed=feed,
        published_article=art,
    )
    RSSNewsItem.objects.create(
        rss_feed=feed,
        title='ZEEKR 007 press release',
        source_url='http://test.com/zeekr-007',
        content='<p>ZEEKR has launched the all-new 007 electric sedan with 800V architecture</p>',
        excerpt='ZEEKR 007 launched',
        pending_article=pending,
    )
    return art


@pytest.fixture
def category():
    return Category.objects.create(name='News', slug='news')


# ═══════════════════════════════════════════════════════════════════════════
# generate_from_youtube (L749-847)
# ═══════════════════════════════════════════════════════════════════════════

class TestGenerateFromYouTubeDeep:
    """Covers L779-838 — the AI processing and article creation paths."""

    @patch('ai_engine.main.generate_article_from_youtube')
    def test_success_creates_article(self, mock_gen, staff_client):
        result_article = Article.objects.create(
            title='AI Generated', slug='ai-gen', content='<p>AI</p>',
        )
        mock_gen.return_value = {
            'success': True,
            'article_id': result_article.id,
        }
        resp = staff_client.post('/api/v1/articles/generate_from_youtube/', {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'provider': 'gemini',
        }, format='json', **UA)
        assert resp.status_code == 200
        assert resp.data['success'] is True

    @patch('ai_engine.main.generate_article_from_youtube')
    def test_ai_failure_returns_error(self, mock_gen, staff_client):
        mock_gen.return_value = {
            'success': False,
            'error': 'Transcript not available',
        }
        resp = staff_client.post('/api/v1/articles/generate_from_youtube/', {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        }, format='json', **UA)
        assert resp.status_code == 400
        assert 'Transcript' in resp.data.get('error', '')

    @patch('ai_engine.main.generate_article_from_youtube')
    def test_ai_exception_returns_500(self, mock_gen, staff_client):
        mock_gen.side_effect = RuntimeError('Gemini quota exceeded')
        resp = staff_client.post('/api/v1/articles/generate_from_youtube/', {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        }, format='json', **UA)
        assert resp.status_code == 500

    def test_invalid_provider_rejected(self, staff_client):
        resp = staff_client.post('/api/v1/articles/generate_from_youtube/', {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'provider': 'openai',
        }, format='json', **UA)
        assert resp.status_code == 400

    @patch('ai_engine.main.generate_article_from_youtube')
    def test_provider_groq(self, mock_gen, staff_client):
        result_article = Article.objects.create(
            title='Groq Generated', slug='groq-gen', content='<p>Groq</p>',
        )
        mock_gen.return_value = {'success': True, 'article_id': result_article.id}
        resp = staff_client.post('/api/v1/articles/generate_from_youtube/', {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'provider': 'groq',
        }, format='json', **UA)
        assert resp.status_code == 200
        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args
        assert call_kwargs[1].get('provider') == 'groq' or call_kwargs[0][0] == 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'


# ═══════════════════════════════════════════════════════════════════════════
# translate_enhance (L849-1100)
# ═══════════════════════════════════════════════════════════════════════════

class TestTranslateEnhanceDeep:
    """Covers L910-1095 — article save, categories, tags, deep specs, A/B titles."""

    def test_missing_russian_text(self, staff_client):
        resp = staff_client.post('/api/v1/articles/translate-enhance/', {}, format='json', **UA)
        assert resp.status_code == 400
        assert 'russian_text' in resp.data.get('error', '').lower()

    def test_text_too_short(self, staff_client):
        resp = staff_client.post('/api/v1/articles/translate-enhance/', {
            'russian_text': 'Короткий текст',
        }, format='json', **UA)
        assert resp.status_code == 400
        assert 'short' in resp.data.get('error', '').lower()

    @patch('ai_engine.modules.translator.translate_and_enhance')
    def test_translate_preview_only(self, mock_trans, staff_client):
        """No save_as_draft or save_and_publish → preview only."""
        mock_trans.return_value = {
            'title': 'Translated Title About BYD Seal',
            'content': '<h2>BYD Seal</h2><p>Comprehensive content about BYD Seal</p>',
            'summary': 'A great EV',
            'meta_description': 'BYD Seal review',
            'suggested_slug': 'byd-seal-review',
            'suggested_categories': ['News'],
            'seo_keywords': ['BYD', 'Seal', 'EV'],
            'reading_time': 5,
        }
        resp = staff_client.post('/api/v1/articles/translate-enhance/', {
            'russian_text': 'Обзор нового BYD Seal электрического седана с батареей Blade',
        }, format='json', **UA)
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert 'Translated Title' in resp.data.get('title', '')
        assert Article.objects.filter(slug='byd-seal-review').count() == 0  # Not saved

    @patch('ai_engine.modules.deep_specs.generate_deep_vehicle_specs')
    @patch('ai_engine.main.generate_title_variants')
    @patch('ai_engine.modules.translator.translate_and_enhance')
    def test_translate_save_as_draft(self, mock_trans, mock_ab, mock_deep, staff_client, category):
        """save_as_draft=True creates Draft article with categories/tags."""
        mock_trans.return_value = {
            'title': '2026 BYD Seal Review',
            'content': '<h2>2026 BYD Seal</h2><p>Long translated content about BYD Seal electric sedan</p>',
            'summary': 'BYD Seal is impressive',
            'meta_description': 'BYD Seal review',
            'suggested_slug': 'byd-seal-review-draft',
            'suggested_categories': ['News'],
            'seo_keywords': ['BYD', 'Seal', 'Electric'],
            'reading_time': 5,
        }
        mock_deep.return_value = None
        mock_ab.return_value = None
        resp = staff_client.post('/api/v1/articles/translate-enhance/', {
            'russian_text': 'Обзор нового BYD Seal электрического седана с батареей Blade Battery',
            'save_as_draft': True,
        }, format='json', **UA)
        assert resp.status_code == 200
        assert resp.data.get('saved') is True
        assert resp.data.get('published') is False
        art = Article.objects.filter(slug__startswith='byd-seal-review').first()
        assert art is not None
        assert art.is_published is False

    @patch('ai_engine.modules.deep_specs.generate_deep_vehicle_specs')
    @patch('ai_engine.main.generate_title_variants')
    @patch('ai_engine.modules.translator.translate_and_enhance')
    def test_translate_save_and_publish(self, mock_trans, mock_ab, mock_deep, staff_client, category):
        """save_and_publish=True creates Published article."""
        mock_trans.return_value = {
            'title': '2026 ZEEKR X Overview',
            'content': '<h2>ZEEKR X</h2><p>Content about ZEEKR X electric crossover with good range</p>',
            'summary': 'ZEEKR X is good',
            'meta_description': 'ZEEKR X overview',
            'suggested_slug': 'zeekr-x-published',
            'suggested_categories': ['News'],
            'seo_keywords': ['ZEEKR', 'Electric'],
            'reading_time': 4,
        }
        mock_deep.return_value = None
        mock_ab.return_value = None
        resp = staff_client.post('/api/v1/articles/translate-enhance/', {
            'russian_text': 'Обзор нового ZEEKR X электрического кроссовера с большим запасом хода',
            'save_and_publish': True,
        }, format='json', **UA)
        assert resp.status_code == 200
        assert resp.data.get('published') is True

    @patch('ai_engine.modules.translator.translate_and_enhance')
    def test_translate_ai_error(self, mock_trans, staff_client):
        mock_trans.side_effect = Exception('Gemini API timeout')
        resp = staff_client.post('/api/v1/articles/translate-enhance/', {
            'russian_text': 'Обзор нового электрического автомобиля с очень большим запасом хода',
        }, format='json', **UA)
        assert resp.status_code == 500
        assert 'Translation failed' in resp.data.get('error', '')

    def test_translate_invalid_params_fallback(self, staff_client):
        """Invalid target_length/tone/provider fall back to defaults."""
        with patch('ai_engine.modules.translator.translate_and_enhance') as mock_trans:
            mock_trans.return_value = {
                'title': 'Test Fallback',
                'content': '<p>Content</p>',
            }
            resp = staff_client.post('/api/v1/articles/translate-enhance/', {
                'russian_text': 'Обзор нового электрического автомобиля с очень большим запасом хода',
                'target_length': 'invalid',
                'tone': 'invalid',
                'provider': 'invalid',
            }, format='json', **UA)
            assert resp.status_code == 200
            call_kwargs = mock_trans.call_args[1]
            assert call_kwargs['target_length'] == 'medium'
            assert call_kwargs['tone'] == 'professional'
            assert call_kwargs['provider'] == 'gemini'


# ═══════════════════════════════════════════════════════════════════════════
# regenerate (L1616-1841)
# ═══════════════════════════════════════════════════════════════════════════

class TestRegenerateDeep:
    """Covers L1672-1838 — YouTube + RSS source detection, backup, post-processing."""

    @patch('ai_engine.main.generate_title_variants')
    @patch('ai_engine.main._generate_article_content')
    def test_regenerate_youtube_source(self, mock_gen, mock_ab, staff_client, article_with_youtube):
        mock_gen.return_value = {
            'success': True,
            'title': 'BYD Seal Regenerated',
            'content': '<h2>BYD Seal</h2><p>Regenerated YouTube content with more detail</p>',
            'summary': 'Updated summary',
            'generation_metadata': {'provider': 'gemini', 'source_type': 'youtube'},
            'specs': {},
            'tag_names': [],
        }
        mock_ab.return_value = None
        resp = staff_client.post(
            f'/api/v1/articles/{article_with_youtube.slug}/regenerate/',
            {'provider': 'gemini'}, format='json', **UA
        )
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert 'youtube' in resp.data.get('message', '').lower()
        # Verify backup
        article_with_youtube.refresh_from_db()
        assert article_with_youtube.content_original is not None

    @pytest.mark.slow
    @patch('ai_engine.main.generate_title_variants')
    @patch('ai_engine.modules.article_generator.expand_press_release')
    def test_regenerate_rss_source(self, mock_expand, mock_ab, staff_client, article_with_rss):
        mock_expand.return_value = '<h2>ZEEKR 007 Full Review</h2><p>Expanded content about the ZEEKR 007 electric sedan featuring 800V architecture and impressive range figures for the global market</p>'
        mock_ab.return_value = None
        resp = staff_client.post(
            f'/api/v1/articles/{article_with_rss.slug}/regenerate/',
            {'provider': 'gemini'}, format='json', **UA
        )
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert 'rss' in resp.data.get('message', '').lower()
        article_with_rss.refresh_from_db()
        assert 'ZEEKR' in article_with_rss.content

    def test_regenerate_invalid_provider(self, staff_client, article):
        resp = staff_client.post(
            f'/api/v1/articles/{article.slug}/regenerate/',
            {'provider': 'openai'}, format='json', **UA
        )
        assert resp.status_code == 400

    def test_regenerate_no_source_content(self, staff_client, article):
        """Article with no youtube_url and no RSSNewsItem → 400."""
        resp = staff_client.post(
            f'/api/v1/articles/{article.slug}/regenerate/',
            {'provider': 'gemini'}, format='json', **UA
        )
        assert resp.status_code in (400, 500)

    @patch('ai_engine.main.generate_title_variants')
    @patch('ai_engine.main._generate_article_content')
    def test_regenerate_youtube_with_specs(self, mock_gen, mock_ab, staff_client, article_with_youtube):
        mock_gen.return_value = {
            'success': True,
            'title': '2026 BYD Seal Review',
            'content': '<h2>BYD Seal</h2><p>Content</p>',
            'summary': 'Summary',
            'specs': {'make': 'BYD', 'model': 'Seal', 'year': 2026, 'price': '$35,000'},
            'tag_names': ['BYD', 'EV'],
            'generation_metadata': {'provider': 'gemini'},
        }
        mock_ab.return_value = None
        resp = staff_client.post(
            f'/api/v1/articles/{article_with_youtube.slug}/regenerate/',
            {'provider': 'gemini'}, format='json', **UA
        )
        assert resp.status_code == 200
        # CarSpecification should be created/updated
        specs = CarSpecification.objects.filter(article=article_with_youtube)
        assert specs.exists()


# ═══════════════════════════════════════════════════════════════════════════
# re_enrich (L1843-2020)
# ═══════════════════════════════════════════════════════════════════════════

class TestReEnrichDeep:
    """Covers L1868-2009 — web search, deep specs, A/B titles, smart tags."""

    @patch('news.auto_tags.auto_tag_article')
    @patch('ai_engine.main.generate_title_variants')
    @patch('ai_engine.modules.deep_specs.generate_deep_vehicle_specs')
    @patch('ai_engine.modules.searcher.get_web_context')
    def test_re_enrich_full_pipeline(
        self, mock_web, mock_deep, mock_ab, mock_tags, staff_client, article
    ):
        CarSpecification.objects.create(article=article, make='Tesla', model='Model Y')
        mock_web.return_value = 'Web context about Tesla Model Y specs and pricing'
        vs = VehicleSpecs(article=article, make='Tesla', model_name='Model Y')
        vs.save()
        mock_deep.return_value = vs
        mock_ab.return_value = None
        mock_tags.return_value = {'created': 1, 'matched': 2, 'total': 3, 'ai_used': True}

        resp = staff_client.post(
            f'/api/v1/articles/{article.slug}/re-enrich/',
            format='json', **UA
        )
        assert resp.status_code == 200
        assert resp.data['success'] is True
        results = resp.data.get('results', {})
        assert results.get('deep_specs', {}).get('success') is True
        assert results.get('web_search', {}).get('success') is True

    @patch('news.auto_tags.auto_tag_article')
    @patch('ai_engine.main.generate_title_variants')
    @patch('ai_engine.modules.deep_specs.generate_deep_vehicle_specs')
    def test_re_enrich_no_car_spec_title_parsing(
        self, mock_deep, mock_ab, mock_tags, staff_client, article
    ):
        """No CarSpecification → parses make/model from title."""
        mock_deep.return_value = None
        mock_ab.return_value = None
        mock_tags.return_value = {'created': 0, 'matched': 0, 'total': 0, 'ai_used': False}

        resp = staff_client.post(
            f'/api/v1/articles/{article.slug}/re-enrich/',
            format='json', **UA
        )
        assert resp.status_code == 200
        # Should have attempted title parsing for "2026 Tesla Model Y Review"

    @patch('news.auto_tags.auto_tag_article')
    @patch('ai_engine.main.generate_title_variants')
    @patch('ai_engine.modules.deep_specs.generate_deep_vehicle_specs')
    def test_re_enrich_with_existing_ab_titles(
        self, mock_deep, mock_ab, mock_tags, staff_client, article
    ):
        """Existing A/B variants → skipped."""
        from news.models import ArticleTitleVariant
        ArticleTitleVariant.objects.create(
            article=article, title='Alt Title', variant='B',
        )
        mock_deep.return_value = None
        mock_tags.return_value = {'created': 0, 'matched': 0, 'total': 0, 'ai_used': False}

        resp = staff_client.post(
            f'/api/v1/articles/{article.slug}/re-enrich/',
            format='json', **UA
        )
        assert resp.status_code == 200
        ab = resp.data['results'].get('ab_titles', {})
        assert ab.get('skipped') is True
        mock_ab.assert_not_called()

    @patch('news.auto_tags.auto_tag_article')
    @patch('ai_engine.main.generate_title_variants')
    @patch('ai_engine.modules.deep_specs.generate_deep_vehicle_specs')
    def test_re_enrich_partial_failure(
        self, mock_deep, mock_ab, mock_tags, staff_client, article
    ):
        """Some steps fail → still returns success if at least 1 succeeds."""
        mock_deep.side_effect = Exception('Gemini quota')
        mock_ab.side_effect = Exception('API error')
        mock_tags.return_value = {'created': 1, 'matched': 0, 'total': 1, 'ai_used': True}

        resp = staff_client.post(
            f'/api/v1/articles/{article.slug}/re-enrich/',
            format='json', **UA
        )
        assert resp.status_code == 200
        # At least smart_tags succeeded
        assert resp.data['success'] is True
        errors = resp.data.get('errors', [])
        assert len(errors) >= 2
