"""
Tests for article generation timeouts:
  1. generate_from_youtube → signal.alarm → HTTP 408 on timeout
  2. generate_from_youtube → normal success path (alarm cancelled)
  3. generate_from_youtube → AI engine error (HTTP 500)
  4. generate_from_youtube → missing youtube_url (HTTP 400)
  5. regenerate_article_task → SoftTimeLimitExceeded → structured error
  6. regenerate_article_task → success path
  7. regenerate_article_task → generic exception → structured error
  8. regenerate_status → pending / done / error states
"""
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from news.models import Article

pytestmark = pytest.mark.django_db

UA = {'HTTP_USER_AGENT': 'TestBrowser/1.0'}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def admin_user():
    return User.objects.create_superuser('genAdmin', 'gen@admin.com', 'adminpass')


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def anon_client():
    return APIClient()


@pytest.fixture
def article():
    return Article.objects.create(
        title='2026 BYD Seal AWD Review',
        slug='byd-seal-awd-review',
        content='<p>BYD Seal content</p>',
        is_published=False,
        youtube_url='https://youtube.com/watch?v=abc123',
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. generate_from_youtube — timeout returns HTTP 408
# ═══════════════════════════════════════════════════════════════════════════

class TestGenerateFromYoutubeTimeout:
    """Tests for async generate_from_youtube dispatch.
    Timeout/error handling happens inside the Celery task — tested in TestRegenerateArticleTask
    and test_generate_from_youtube_async.py. These tests verify the view layer."""

    @patch('news.tasks.generate_from_youtube_task.delay')
    def test_dispatch_returns_task_id(self, mock_delay, admin_client):
        """View dispatches Celery task and returns task_id immediately."""
        mock_task = MagicMock()
        mock_task.id = 'timeout-task-001'
        mock_delay.return_value = mock_task

        resp = admin_client.post('/api/v1/articles/generate_from_youtube/', {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        }, format='json', **UA)

        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert resp.data['task_id'] == 'timeout-task-001'

    def test_missing_url_returns_400(self, admin_client):
        """Missing youtube_url → 400 before any task dispatch."""
        resp = admin_client.post('/api/v1/articles/generate_from_youtube/', {}, format='json', **UA)
        assert resp.status_code == 400
        assert 'youtube_url' in str(resp.data).lower() or 'required' in str(resp.data).lower()

    @patch('news.api_views.mixins.article_generation.is_valid_youtube_url', return_value=False)
    def test_invalid_url_returns_400(self, mock_valid, admin_client):
        """Invalid YouTube URL format → 400."""
        resp = admin_client.post('/api/v1/articles/generate_from_youtube/', {
            'youtube_url': 'https://notyoutube.com/video',
        }, format='json', **UA)
        assert resp.status_code == 400

    @patch('news.tasks.generate_from_youtube_task.delay')
    def test_celery_dispatch_failure_returns_500(self, mock_delay, admin_client):
        """If Celery broker is unreachable, return 500."""
        mock_delay.side_effect = Exception('Broker connection refused')
        resp = admin_client.post('/api/v1/articles/generate_from_youtube/', {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        }, format='json', **UA)
        assert resp.status_code == 500

    @patch('news.tasks.generate_from_youtube_task.delay')
    def test_successful_dispatch_with_task_id(self, mock_delay, admin_client):
        """Successful dispatch → 200 with task_id for status polling."""
        mock_task = MagicMock()
        mock_task.id = 'success-task-002'
        mock_delay.return_value = mock_task
        resp = admin_client.post('/api/v1/articles/generate_from_youtube/', {
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        }, format='json', **UA)
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert 'task_id' in resp.data

    def test_anon_forbidden(self, anon_client):
        """Unauthenticated users → 401 or 403."""
        resp = anon_client.post('/api/v1/articles/generate_from_youtube/', {
            'youtube_url': 'https://youtube.com/watch?v=abc123',
        }, format='json', **UA)
        assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════
# 2. regenerate_article_task — Celery task unit tests
# ═══════════════════════════════════════════════════════════════════════════

class TestRegenerateArticleTask:
    """
    Unit tests for the Celery task itself (called directly, no broker needed).
    The task uses a lazy `from ai_engine.modules.regenerator import ...` inside its body,
    so we inject a mock module into sys.modules to intercept it.
    """

    def _make_mock_regenerator(self, side_effect=None, return_value=None):
        """Create a mock for ai_engine.modules.regenerator."""
        import sys
        import types
        mock_module = types.ModuleType('ai_engine.modules.regenerator')
        mock_fn = MagicMock()
        if side_effect is not None:
            mock_fn.side_effect = side_effect
        if return_value is not None:
            mock_fn.return_value = return_value
        mock_module.regenerate_existing_article = mock_fn
        return mock_module, mock_fn

    def test_soft_time_limit_returns_structured_error(self, article):
        """SoftTimeLimitExceeded → returns dict with success=False, timeout=True."""
        import sys
        from celery.exceptions import SoftTimeLimitExceeded
        from news.tasks import regenerate_article_task

        mock_mod, mock_fn = self._make_mock_regenerator(side_effect=SoftTimeLimitExceeded())
        sys.modules['ai_engine.modules.regenerator'] = mock_mod
        try:
            result = regenerate_article_task.apply(
                args=[article.id, article.slug, 'gemini'],
                kwargs={'user_id': None},
            ).get()
        finally:
            sys.modules.pop('ai_engine.modules.regenerator', None)

        assert result['success'] is False
        assert result.get('timeout') is True
        assert '14 minutes' in result['message']

    def test_generic_exception_returns_structured_error(self, article):
        """Any other exception → returns dict with success=False."""
        import sys
        from news.tasks import regenerate_article_task

        mock_mod, mock_fn = self._make_mock_regenerator(side_effect=ValueError("DB connection failed"))
        sys.modules['ai_engine.modules.regenerator'] = mock_mod
        try:
            result = regenerate_article_task.apply(
                args=[article.id, article.slug, 'gemini'],
                kwargs={'user_id': None},
            ).get()
        finally:
            sys.modules.pop('ai_engine.modules.regenerator', None)

        assert result['success'] is False
        assert 'DB connection failed' in result['message']
        assert result.get('timeout') is not True

    def test_success_path(self, article):
        """Successful regeneration → returns the regenerator's result dict."""
        import sys
        from news.tasks import regenerate_article_task

        expected = {'success': True, 'article_id': article.id, 'word_count': 1200}
        mock_mod, mock_fn = self._make_mock_regenerator(return_value=expected)
        sys.modules['ai_engine.modules.regenerator'] = mock_mod
        try:
            result = regenerate_article_task.apply(
                args=[article.id, article.slug, 'gemini'],
                kwargs={'user_id': None},
            ).get()
        finally:
            sys.modules.pop('ai_engine.modules.regenerator', None)

        assert result == expected
        from unittest.mock import ANY
        mock_fn.assert_called_once_with(article.id, provider='gemini', user_id=None, instruction=None, celery_task=ANY)

    def test_task_has_time_limits_configured(self):
        """Ensure the task decorator has soft_time_limit and time_limit set."""
        from news.tasks import regenerate_article_task
        # Celery stores these on the task instance
        assert regenerate_article_task.soft_time_limit == 14 * 60, \
            f"Expected soft_time_limit=840, got {regenerate_article_task.soft_time_limit}"
        assert regenerate_article_task.time_limit == 15 * 60, \
            f"Expected time_limit=900, got {regenerate_article_task.time_limit}"


# ═══════════════════════════════════════════════════════════════════════════
# 3. regenerate endpoint + regenerate_status polling
# ═══════════════════════════════════════════════════════════════════════════

class TestRegenerateEndpoint:

    @patch('news.tasks.regenerate_article_task.delay')
    def test_regenerate_dispatches_task(self, mock_delay, admin_client, article):
        """POST /regenerate/ → dispatches Celery task and returns task_id."""
        mock_task = MagicMock()
        mock_task.id = 'test-task-uuid-1234'
        mock_delay.return_value = mock_task

        resp = admin_client.post(f'/api/v1/articles/{article.slug}/regenerate/', {
            'provider': 'gemini',
        }, format='json', **UA)

        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert resp.data['task_id'] == 'test-task-uuid-1234'
        mock_delay.assert_called_once()

    def test_regenerate_article_not_found(self, admin_client):
        """Regenerate with non-existent slug → 400 with message."""
        resp = admin_client.post('/api/v1/articles/does-not-exist-xyz/regenerate/', {
            'provider': 'gemini',
        }, format='json', **UA)
        assert resp.status_code == 400
        assert 'not found' in str(resp.data).lower() or 'message' in resp.data

    @patch('celery.result.AsyncResult')
    def test_regenerate_status_pending(self, mock_async_result, admin_client):
        """GET regenerate_status/?task_id=... → pending."""
        mock_result = MagicMock()
        mock_result.state = 'PENDING'
        mock_async_result.return_value = mock_result

        resp = admin_client.get('/api/v1/articles/regenerate_status/?task_id=abc123', **UA)
        assert resp.status_code == 200
        assert resp.data['status'] == 'pending'

    @patch('celery.result.AsyncResult')
    def test_regenerate_status_done_success(self, mock_async_result, admin_client, article):
        """GET regenerate_status/ → done with article data."""
        mock_result = MagicMock()
        mock_result.state = 'SUCCESS'
        mock_result.result = {'success': True, 'article_id': article.id}
        mock_async_result.return_value = mock_result

        resp = admin_client.get('/api/v1/articles/regenerate_status/?task_id=abc123', **UA)
        assert resp.status_code == 200
        assert resp.data['status'] == 'done'
        assert 'article' in resp.data

    @patch('celery.result.AsyncResult')
    def test_regenerate_status_done_timeout(self, mock_async_result, admin_client):
        """GET regenerate_status/ → done but result is a timeout error."""
        mock_result = MagicMock()
        mock_result.state = 'SUCCESS'
        mock_result.result = {
            'success': False,
            'message': 'Generation timed out after 14 minutes',
            'timeout': True,
        }
        mock_async_result.return_value = mock_result

        resp = admin_client.get('/api/v1/articles/regenerate_status/?task_id=abc123', **UA)
        assert resp.status_code == 200
        assert resp.data['status'] == 'error'
        assert 'timed out' in resp.data['error'].lower() or 'Generation' in resp.data['error']

    @patch('celery.result.AsyncResult')
    def test_regenerate_status_failure(self, mock_async_result, admin_client):
        """GET regenerate_status/ → FAILURE state."""
        mock_result = MagicMock()
        mock_result.state = 'FAILURE'
        mock_result.info = Exception("Worker died")
        mock_async_result.return_value = mock_result

        resp = admin_client.get('/api/v1/articles/regenerate_status/?task_id=abc123', **UA)
        assert resp.status_code == 200
        assert resp.data['status'] == 'error'

    def test_regenerate_status_missing_task_id(self, admin_client):
        """GET regenerate_status/ without task_id → 400."""
        resp = admin_client.get('/api/v1/articles/regenerate_status/', **UA)
        assert resp.status_code == 400

    def test_regenerate_anon_forbidden(self, anon_client, article):
        """Unauthenticated → 401/403."""
        resp = anon_client.post(f'/api/v1/articles/{article.slug}/regenerate/', {
            'provider': 'gemini',
        }, format='json', **UA)
        assert resp.status_code in (401, 403)
