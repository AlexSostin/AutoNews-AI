"""
Tests for async generate_from_youtube flow:
- POST /articles/generate_from_youtube/ → dispatches Celery task, returns task_id immediately
- GET /articles/generate_status/?task_id=... → polls Celery AsyncResult

All Celery calls are mocked (no real worker needed).
"""
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from rest_framework.test import APIClient


UA = {'HTTP_USER_AGENT': 'Mozilla/5.0 TestClient/1.0'}
DISPATCH_URL = '/api/v1/articles/generate_from_youtube/'
STATUS_URL = '/api/v1/articles/generate_status/'

VALID_YT_URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
INVALID_YT_URL = 'https://example.com/not-a-youtube-url'


@pytest.fixture
def admin_client(db):
    user = User.objects.create_superuser(
        username='gen_admin', email='gen@test.com', password='pw',
    )
    client = APIClient(**UA)
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def anon_client():
    return APIClient(**UA)


# ══════════════════════════════════════════════════════════
# 1. Dispatch endpoint
# ══════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGenerateFromYoutubeDispatch:

    def test_dispatch_returns_task_id_immediately(self, admin_client):
        """POST should return task_id within milliseconds — no blocking."""
        mock_task = MagicMock()
        mock_task.id = 'celery-task-uuid-123'

        with patch('news.tasks.generate_from_youtube_task.delay', return_value=mock_task) as mock_delay:
            resp = admin_client.post(DISPATCH_URL, {'youtube_url': VALID_YT_URL}, format='json')

        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert resp.data['task_id'] == 'celery-task-uuid-123'
        mock_delay.assert_called_once()
        call_kwargs = mock_delay.call_args.kwargs
        assert call_kwargs['youtube_url'] == VALID_YT_URL
        assert call_kwargs['provider'] == 'gemini'

    def test_missing_youtube_url_returns_400(self, admin_client):
        resp = admin_client.post(DISPATCH_URL, {}, format='json')
        assert resp.status_code == 400
        assert 'youtube_url' in str(resp.data).lower()

    def test_invalid_youtube_url_returns_400(self, admin_client):
        resp = admin_client.post(DISPATCH_URL, {'youtube_url': INVALID_YT_URL}, format='json')
        assert resp.status_code == 400

    def test_anon_forbidden(self, anon_client):
        resp = anon_client.post(DISPATCH_URL, {'youtube_url': VALID_YT_URL}, format='json')
        assert resp.status_code in [401, 403]

    def test_celery_dispatch_failure_returns_500(self, admin_client):
        """If Celery broker is unreachable, return 500 — not crash."""
        with patch('news.tasks.generate_from_youtube_task.delay', side_effect=Exception('broker down')):
            resp = admin_client.post(DISPATCH_URL, {'youtube_url': VALID_YT_URL}, format='json')
        assert resp.status_code == 500


# ══════════════════════════════════════════════════════════
# 2. Status polling endpoint
# ══════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGenerateStatus:

    def _mock_async_result(self, state, result=None):
        ar = MagicMock()
        ar.state = state
        ar.result = result
        ar.info = result  # FAILURE state uses .info
        return ar

    def test_status_missing_task_id_returns_400(self, admin_client):
        resp = admin_client.get(STATUS_URL)
        assert resp.status_code == 400

    def test_status_pending(self, admin_client):
        with patch('celery.result.AsyncResult', return_value=self._mock_async_result('PENDING')):
            resp = admin_client.get(STATUS_URL, {'task_id': 'abc123'})
        assert resp.status_code == 200
        assert resp.data['status'] == 'pending'

    def test_status_running(self, admin_client):
        with patch('celery.result.AsyncResult', return_value=self._mock_async_result('STARTED')):
            resp = admin_client.get(STATUS_URL, {'task_id': 'abc123'})
        assert resp.status_code == 200
        assert resp.data['status'] == 'running'

    def test_status_done_with_article(self, admin_client, db):
        """When task succeeds, generate_status fetches article and returns it."""
        from news.models import Article, Category
        cat = Category.objects.create(name='Test')
        article = Article.objects.create(
            title='Test Article', slug='test-article-yt',
            content='<p>Test</p>', summary='Summary',
        )
        result = {'success': True, 'article_id': article.id}

        with patch('celery.result.AsyncResult', return_value=self._mock_async_result('SUCCESS', result)):
            resp = admin_client.get(STATUS_URL, {'task_id': 'abc123'})

        assert resp.status_code == 200
        assert resp.data['status'] == 'done'
        assert resp.data['article_id'] == article.id
        assert resp.data['article'] is not None

    def test_status_done_task_reported_failure(self, admin_client):
        """Task returned success=False → status=error."""
        result = {'success': False, 'message': 'Gemini API quota exceeded'}

        with patch('celery.result.AsyncResult', return_value=self._mock_async_result('SUCCESS', result)):
            resp = admin_client.get(STATUS_URL, {'task_id': 'abc123'})

        assert resp.status_code == 200
        assert resp.data['status'] == 'error'
        assert 'Gemini' in resp.data['error']

    def test_status_timeout(self, admin_client):
        """Task returned timeout=True → status=error with timeout flag."""
        result = {'success': False, 'message': 'Generation timed out after 9 minutes.', 'timeout': True}

        with patch('celery.result.AsyncResult', return_value=self._mock_async_result('SUCCESS', result)):
            resp = admin_client.get(STATUS_URL, {'task_id': 'abc123'})

        assert resp.status_code == 200
        assert resp.data['status'] == 'error'
        assert resp.data.get('timeout') is True

    def test_status_celery_failure(self, admin_client):
        """Celery raised an unhandled exception → FAILURE state."""
        with patch('celery.result.AsyncResult',
                   return_value=self._mock_async_result('FAILURE', Exception('Worker crashed'))):
            resp = admin_client.get(STATUS_URL, {'task_id': 'abc123'})
        assert resp.status_code == 200
        assert resp.data['status'] == 'error'

    def test_status_anon_forbidden(self, anon_client):
        resp = anon_client.get(STATUS_URL, {'task_id': 'abc123'})
        assert resp.status_code in [401, 403]


# ══════════════════════════════════════════════════════════
# 3. Celery task unit test
# ══════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGenerateFromYoutubeTask:

    def test_task_success(self):
        """Task calls generate_article_from_youtube and returns its result."""
        expected = {'success': True, 'article_id': 42}

        import sys
        mock_main = MagicMock()
        mock_main.generate_article_from_youtube = MagicMock(return_value=expected)
        sys.modules['ai_engine.main'] = mock_main

        try:
            from news.tasks import generate_from_youtube_task
            result = generate_from_youtube_task.apply(
                kwargs={'youtube_url': VALID_YT_URL, 'provider': 'gemini'}
            ).get()
            assert result == expected
        finally:
            sys.modules.pop('ai_engine.main', None)

    def test_task_timeout_returns_structured_error(self):
        """SoftTimeLimitExceeded → structured {success: False, timeout: True}."""
        from celery.exceptions import SoftTimeLimitExceeded

        import sys
        mock_main = MagicMock()
        mock_main.generate_article_from_youtube = MagicMock(
            side_effect=SoftTimeLimitExceeded()
        )
        sys.modules['ai_engine.main'] = mock_main

        try:
            from news.tasks import generate_from_youtube_task
            result = generate_from_youtube_task.apply(
                kwargs={'youtube_url': VALID_YT_URL, 'provider': 'gemini'}
            ).get()
            assert result['success'] is False
            assert result.get('timeout') is True
        finally:
            sys.modules.pop('ai_engine.main', None)

    def test_task_general_exception_returns_error(self):
        """Any other exception → {success: False, message}."""
        import sys
        mock_main = MagicMock()
        mock_main.generate_article_from_youtube = MagicMock(
            side_effect=RuntimeError('AI engine crashed')
        )
        sys.modules['ai_engine.main'] = mock_main

        try:
            from news.tasks import generate_from_youtube_task
            result = generate_from_youtube_task.apply(
                kwargs={'youtube_url': VALID_YT_URL, 'provider': 'gemini'}
            ).get()
            assert result['success'] is False
            assert 'AI engine crashed' in result['message']
        finally:
            sys.modules.pop('ai_engine.main', None)
