"""
Tests for api_views.py — Batch 6: AI Pipelines Deep (mocked)
Covers: ArticleViewSet.update (FormData), generate_from_youtube (full),
        translate_enhance, regenerate (YouTube+RSS), re_enrich, bulk_re_enrich,
        submit_feedback, ab_pick_winner, similar_articles, debug_vehicle_specs,
        increment_views, rate, get_user_rating
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
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
        username='staffdeep', email='staffdeep@test.com',
        password='Pass123!', is_staff=True, is_superuser=True,
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username='regulardeep', email='regulardeep@test.com', password='Pass123!',
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
        title='2025 Tesla Model 3 Review', slug='test-article-deep',
        content='<p>' + 'Test content about Tesla Model 3. ' * 20 + '</p>',
        summary='Tesla Model 3 review summary', is_published=True,
    )


@pytest.fixture
def article_youtube(db):
    from news.models import Article
    return Article.objects.create(
        title='2025 BMW M3 Review', slug='youtube-article',
        content='<p>Content</p>', summary='Summary', is_published=True,
        youtube_url='https://youtube.com/watch?v=abc123',
    )


@pytest.fixture
def article_rss(db):
    from news.models import Article
    return Article.objects.create(
        title='2025 Audi e-tron Launch', slug='rss-article',
        content='<p>Content</p>', summary='Summary', is_published=True,
        author_channel_url='https://audi.com/press/1',
    )


@pytest.fixture
def ab_variant_a(article):
    from news.models import ArticleTitleVariant
    return ArticleTitleVariant.objects.create(
        article=article, variant='A', title='Title A',
        impressions=200, clicks=20,
    )


@pytest.fixture
def ab_variant_b(article):
    from news.models import ArticleTitleVariant
    return ArticleTitleVariant.objects.create(
        article=article, variant='B', title='Title B',
        impressions=200, clicks=30,
    )


# ═══════════════════════════════════════════════════════════════════════════
# ArticleViewSet.update — PATCH /api/v1/articles/{slug}/
# ═══════════════════════════════════════════════════════════════════════════

class TestArticleUpdate:

    def test_update_title(self, staff_client, article):
        resp = staff_client.patch(f'{API}/articles/{article.slug}/', {
            'title': 'Updated Title',
        }, format='json')
        assert resp.status_code == 200
        article.refresh_from_db()
        assert article.title == 'Updated Title'

    def test_update_anonymous_forbidden(self, anon_client, article):
        resp = anon_client.patch(f'{API}/articles/{article.slug}/', {
            'title': 'Hack',
        }, format='json')
        assert resp.status_code in (401, 403)

    def test_update_regular_user_forbidden(self, auth_client, article):
        resp = auth_client.patch(f'{API}/articles/{article.slug}/', {
            'title': 'Hack',
        }, format='json')
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# ArticleViewSet.generate_from_youtube — full flow (mocked AI)
# ═══════════════════════════════════════════════════════════════════════════

class TestGenerateFromYouTubeFullFlow:
    """Tests for async generate_from_youtube — dispatches Celery task, returns task_id."""

    @patch('news.tasks.generate_from_youtube_task.delay')
    def test_generate_success(self, mock_delay, staff_client):
        mock_task = MagicMock()
        mock_task.id = 'full-flow-001'
        mock_delay.return_value = mock_task
        resp = staff_client.post(f'{API}/articles/generate_from_youtube/', {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'provider': 'gemini',
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert resp.data['task_id'] == 'full-flow-001'

    @patch('news.tasks.generate_from_youtube_task.delay')
    def test_generate_ai_failure(self, mock_delay, staff_client):
        """AI failures now happen in Celery task. View always returns 200+task_id."""
        mock_task = MagicMock()
        mock_task.id = 'full-flow-002'
        mock_delay.return_value = mock_task
        resp = staff_client.post(f'{API}/articles/generate_from_youtube/', {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['task_id'] == 'full-flow-002'

    @patch('news.tasks.generate_from_youtube_task.delay')
    def test_generate_invalid_provider_normalized(self, mock_delay, staff_client):
        """Invalid provider gets silently normalized to 'gemini' (not rejected)."""
        mock_task = MagicMock()
        mock_task.id = 'full-flow-003'
        mock_delay.return_value = mock_task
        resp = staff_client.post(f'{API}/articles/generate_from_youtube/', {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'provider': 'chatgpt',
        }, format='json')
        assert resp.status_code == 200

    @patch('news.tasks.generate_from_youtube_task.delay')
    def test_generate_exception(self, mock_delay, staff_client):
        """Celery broker failure → 500."""
        mock_delay.side_effect = Exception('API down')
        resp = staff_client.post(f'{API}/articles/generate_from_youtube/', {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        }, format='json')
        assert resp.status_code == 500


# ═══════════════════════════════════════════════════════════════════════════
# ArticleViewSet.translate_enhance — POST /api/v1/articles/translate-enhance/
# ═══════════════════════════════════════════════════════════════════════════

class TestTranslateEnhance:

    @patch('ai_engine.modules.translator.translate_and_enhance')
    def test_translate_success(self, mock_translate, staff_client):
        mock_translate.return_value = {
            'title': 'Test Translation',
            'content': '<p>' + 'Translated content. ' * 20 + '</p>',
            'summary': 'A translated article',
            'seo_keywords': ['EV', 'Tesla'],
            'meta_description': 'Test meta',
            'suggested_slug': 'test-translation',
        }
        resp = staff_client.post(f'{API}/articles/translate-enhance/', {
            'russian_text': 'Длинный русский текст о новом автомобиле Tesla Model 3 с описанием.',
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert resp.data['title'] == 'Test Translation'

    def test_translate_empty_text(self, staff_client):
        resp = staff_client.post(f'{API}/articles/translate-enhance/', {
            'russian_text': '',
        }, format='json')
        assert resp.status_code == 400

    def test_translate_too_short(self, staff_client):
        resp = staff_client.post(f'{API}/articles/translate-enhance/', {
            'russian_text': 'Коротко.',
        }, format='json')
        assert resp.status_code == 400

    @patch('ai_engine.modules.translator.translate_and_enhance',
           side_effect=Exception('AI error'))
    def test_translate_ai_error(self, mock_translate, staff_client):
        resp = staff_client.post(f'{API}/articles/translate-enhance/', {
            'russian_text': 'Длинный русский текст о новом автомобиле Tesla Model 3 с описанием.',
        }, format='json')
        assert resp.status_code == 500

    @patch('ai_engine.modules.translator.translate_and_enhance')
    def test_translate_save_as_draft(self, mock_translate, staff_client):
        mock_translate.return_value = {
            'title': '2026 BYD Seal Review',
            'content': '<h2>BYD Seal</h2><p>' + 'Content. ' * 20 + '</p>',
            'summary': 'Summary',
            'seo_keywords': ['BYD', 'Seal'],
            'meta_description': 'Meta',
            'suggested_slug': 'byd-seal-review',
            'suggested_categories': [],
        }
        resp = staff_client.post(f'{API}/articles/translate-enhance/', {
            'russian_text': 'Длинный русский текст о новом автомобиле BYD Seal с описанием деталей.',
            'save_as_draft': True,
        }, format='json')
        assert resp.status_code == 200
        assert resp.data.get('saved') is True
        assert resp.data.get('published') is False

    @patch('ai_engine.modules.translator.translate_and_enhance')
    def test_translate_invalid_params_default(self, mock_translate, staff_client):
        """Invalid target_length, tone, provider should default to valid values"""
        mock_translate.return_value = {
            'title': 'Title',
            'content': '<p>' + 'Content. ' * 20 + '</p>',
            'summary': 'Summary',
            'seo_keywords': [],
        }
        resp = staff_client.post(f'{API}/articles/translate-enhance/', {
            'russian_text': 'Длинный русский текст о новом автомобиле с подробным описанием.',
            'target_length': 'invalid',
            'tone': 'invalid',
            'provider': 'invalid',
        }, format='json')
        assert resp.status_code == 200  # Defaults applied, no error


# ═══════════════════════════════════════════════════════════════════════════
# ArticleViewSet.regenerate — YouTube and RSS branches
# ═══════════════════════════════════════════════════════════════════════════

class TestRegenerate:

    @patch('news.tasks.regenerate_article_task.delay')
    def test_regenerate_youtube_success(self, mock_delay,
                                        staff_client, article_youtube):
        """Regenerate dispatches a Celery task and returns task_id."""
        mock_task = MagicMock()
        mock_task.id = 'test-task-123'
        mock_delay.return_value = mock_task

        resp = staff_client.post(
            f'{API}/articles/{article_youtube.slug}/regenerate/',
            {'provider': 'gemini'}, format='json',
        )
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert resp.data['task_id'] == 'test-task-123'
        mock_delay.assert_called_once()

    @patch('news.tasks.regenerate_article_task.delay')
    def test_regenerate_returns_task_id(self, mock_delay, staff_client,
                                        article_youtube):
        """Response includes task_id for status polling."""
        mock_task = MagicMock()
        mock_task.id = 'abc-456'
        mock_delay.return_value = mock_task

        resp = staff_client.post(
            f'{API}/articles/{article_youtube.slug}/regenerate/',
            {'provider': 'gemini'}, format='json',
        )
        assert resp.status_code == 200
        assert 'task_id' in resp.data

    @patch('news.tasks.regenerate_article_task.delay')
    def test_regenerate_normalizes_provider_to_gemini(self, mock_delay,
                                                       staff_client, article):
        """Invalid provider gets normalized to gemini (not rejected)."""
        mock_task = MagicMock()
        mock_task.id = 'norm-task'
        mock_delay.return_value = mock_task

        resp = staff_client.post(
            f'{API}/articles/{article.slug}/regenerate/',
            {'provider': 'openai'}, format='json',
        )
        # The endpoint normalizes provider to 'gemini' and dispatches the task
        assert resp.status_code == 200
        assert resp.data['success'] is True
        # Verify the task was called with gemini
        call_kwargs = mock_delay.call_args[1]
        assert call_kwargs['provider'] == 'gemini'

    @patch('news.tasks.regenerate_article_task.delay')
    def test_regenerate_rss_dispatches_task(self, mock_delay,
                                             staff_client, article_rss):
        """RSS article also dispatches a regeneration task."""
        mock_task = MagicMock()
        mock_task.id = 'rss-task'
        mock_delay.return_value = mock_task

        resp = staff_client.post(
            f'{API}/articles/{article_rss.slug}/regenerate/',
            {'provider': 'gemini'}, format='json',
        )
        assert resp.status_code == 200
        assert resp.data['success'] is True

    def test_regenerate_anonymous_forbidden(self, anon_client, article):
        resp = anon_client.post(
            f'{API}/articles/{article.slug}/regenerate/',
            {}, format='json',
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# ArticleViewSet.re_enrich — POST /api/v1/articles/{slug}/re-enrich/
# ═══════════════════════════════════════════════════════════════════════════

class TestReEnrich:

    def test_re_enrich_anonymous_forbidden(self, anon_client, article):
        resp = anon_client.post(
            f'{API}/articles/{article.slug}/re-enrich/',
            format='json',
        )
        assert resp.status_code == 401

    def test_re_enrich_regular_user_forbidden(self, auth_client, article):
        resp = auth_client.post(
            f'{API}/articles/{article.slug}/re-enrich/',
            format='json',
        )
        # Regular users should be blocked — admin-only endpoint
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# ArticleViewSet.bulk_re_enrich — POST /api/v1/articles/bulk-re-enrich/
# ═══════════════════════════════════════════════════════════════════════════

class TestBulkReEnrich:

    def test_bulk_re_enrich_status_missing_task_id(self, staff_client):
        resp = staff_client.get(f'{API}/articles/bulk-re-enrich-status/')
        assert resp.status_code == 400

    def test_bulk_re_enrich_status_nonexistent(self, staff_client):
        resp = staff_client.get(f'{API}/articles/bulk-re-enrich-status/', {
            'task_id': 'nonexistent',
        })
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# ArticleViewSet.submit_feedback — POST /api/v1/articles/{slug}/feedback/
# ═══════════════════════════════════════════════════════════════════════════

class TestSubmitFeedback:

    def test_submit_feedback_success(self, anon_client, article):
        resp = anon_client.post(f'{API}/articles/{article.slug}/feedback/', {
            'category': 'factual_error',
            'message': 'The horsepower number is wrong in this article',
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['success'] is True

    def test_submit_feedback_too_short(self, anon_client, article):
        resp = anon_client.post(f'{API}/articles/{article.slug}/feedback/', {
            'message': 'Bad',
        }, format='json')
        assert resp.status_code == 400

    def test_submit_feedback_too_long(self, anon_client, article):
        resp = anon_client.post(f'{API}/articles/{article.slug}/feedback/', {
            'message': 'x' * 1001,
        }, format='json')
        assert resp.status_code == 400

    def test_submit_feedback_invalid_category_defaults_other(self, anon_client, article):
        resp = anon_client.post(f'{API}/articles/{article.slug}/feedback/', {
            'category': 'invalid_category',
            'message': 'This is a valid feedback message for testing',
        }, format='json')
        assert resp.status_code == 201  # Invalid category defaults to 'other'

    def test_submit_feedback_rate_limited(self, anon_client, article):
        # First feedback
        anon_client.post(f'{API}/articles/{article.slug}/feedback/', {
            'message': 'First feedback message for testing',
        }, format='json')
        # Second feedback same IP same article same day → rate limited
        resp = anon_client.post(f'{API}/articles/{article.slug}/feedback/', {
            'message': 'Second feedback message for testing',
        }, format='json')
        assert resp.status_code == 429


# ═══════════════════════════════════════════════════════════════════════════
# ArticleViewSet.ab_pick_winner — POST /api/v1/articles/{slug}/ab-pick-winner/
# ═══════════════════════════════════════════════════════════════════════════

class TestABPickWinner:

    def test_pick_winner_success(self, staff_client, article, ab_variant_a, ab_variant_b):
        resp = staff_client.post(
            f'{API}/articles/{article.slug}/ab-pick-winner/',
            {'variant': 'B'}, format='json',
        )
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert resp.data['new_title'] == 'Title B'
        article.refresh_from_db()
        assert article.title == 'Title B'

    def test_pick_winner_no_variant(self, staff_client, article):
        resp = staff_client.post(
            f'{API}/articles/{article.slug}/ab-pick-winner/',
            {}, format='json',
        )
        assert resp.status_code == 400

    def test_pick_winner_invalid_variant(self, staff_client, article, ab_variant_a):
        resp = staff_client.post(
            f'{API}/articles/{article.slug}/ab-pick-winner/',
            {'variant': 'Z'}, format='json',
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# ArticleViewSet.similar_articles — GET /api/v1/articles/{slug}/similar-articles/
# ═══════════════════════════════════════════════════════════════════════════

class TestSimilarArticles:

    @patch('ai_engine.modules.vector_search.get_vector_engine')
    def test_similar_articles_success(self, mock_engine, staff_client, article):
        mock_ve = MagicMock()
        mock_ve.find_similar_articles.return_value = [
            {'article_id': article.id, 'score': 0.9},
        ]
        mock_engine.return_value = mock_ve

        resp = staff_client.get(
            f'{API}/articles/{article.slug}/similar_articles/',
        )
        assert resp.status_code == 200
        assert resp.data['success'] is True

    @patch('ai_engine.modules.vector_search.get_vector_engine',
           side_effect=Exception('FAISS not loaded'))
    def test_similar_articles_fallback(self, mock_engine, staff_client, article):
        resp = staff_client.get(
            f'{API}/articles/{article.slug}/similar_articles/',
        )
        assert resp.status_code == 200
        assert resp.data['similar_articles'] == []


# ═══════════════════════════════════════════════════════════════════════════
# ArticleViewSet.debug_vehicle_specs — GET /api/v1/articles/debug-vehicle-specs/
# ═══════════════════════════════════════════════════════════════════════════

class TestDebugVehicleSpecs:

    def test_debug_specs(self, staff_client, article):
        resp = staff_client.get(f'{API}/articles/debug-vehicle-specs/')
        assert resp.status_code == 200

    def test_debug_specs_filtered(self, staff_client, article):
        resp = staff_client.get(f'{API}/articles/debug-vehicle-specs/', {
            'make': 'Tesla',
        })
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# ArticleViewSet.increment_views — POST /api/v1/articles/{slug}/increment-views/
# ═══════════════════════════════════════════════════════════════════════════

class TestIncrementViews:

    def test_increment_views(self, anon_client, article):
        resp = anon_client.post(
            f'{API}/articles/{article.slug}/increment_views/',
        )
        assert resp.status_code == 200
