import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from news.models.system import BackendErrorLog

UA = {'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) TestClient/1.0'}


@pytest.fixture
def admin_client():
    client = APIClient(**UA)
    admin = User.objects.create_superuser(username='health_admin', email='admin@test.com', password='pass')
    client.force_authenticate(user=admin)
    return client, admin


@pytest.fixture
def anon_client():
    return APIClient(**UA)


@pytest.fixture
def sample_errors():
    """Create a set of sample errors for testing."""
    errors = []
    errors.append(BackendErrorLog.objects.create(
        source='api', severity='error',
        error_class='ValueError', message='Invalid input data',
        traceback='Traceback...', request_method='POST',
        request_path='/api/v1/articles/', request_user='admin',
    ))
    errors.append(BackendErrorLog.objects.create(
        source='scheduler', severity='critical',
        error_class='ConnectionError', message='Database connection refused',
        traceback='Traceback...', task_name='rss_scan',
    ))
    errors.append(BackendErrorLog.objects.create(
        source='api', severity='warning',
        error_class='TimeoutError', message='Request timeout',
        traceback='Traceback...', request_method='GET',
        request_path='/api/v1/health/', resolved=True,
        resolved_at=timezone.now(),
    ))
    return errors


# ── Model Tests ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBackendErrorLogModel:
    def test_create_api_error(self):
        err = BackendErrorLog.objects.create(
            source='api', severity='error',
            error_class='ValueError', message='test error',
            request_method='GET', request_path='/api/v1/test/',
        )
        assert err.id is not None
        assert err.occurrence_count == 1
        assert err.resolved is False
        assert err.source == 'api'

    def test_create_scheduler_error(self):
        err = BackendErrorLog.objects.create(
            source='scheduler', severity='critical',
            error_class='ConnectionError', message='DB down',
            task_name='rss_scan',
        )
        assert err.task_name == 'rss_scan'
        assert err.severity == 'critical'

    def test_deduplication_via_update(self):
        """Test that dedup works by updating occurrence_count."""
        err1 = BackendErrorLog.objects.create(
            source='api', severity='error',
            error_class='ValueError', message='duplicate test',
            request_path='/api/test/',
        )
        # Simulate dedup: find existing and increment
        updated = BackendErrorLog.objects.filter(
            source='api', error_class='ValueError',
            message='duplicate test', request_path='/api/test/',
        ).update(occurrence_count=err1.occurrence_count + 1)
        assert updated == 1

        err1.refresh_from_db()
        assert err1.occurrence_count == 2

    def test_resolution(self):
        err = BackendErrorLog.objects.create(
            source='api', severity='error',
            error_class='RuntimeError', message='test',
        )
        err.resolved = True
        err.resolved_at = timezone.now()
        err.resolution_notes = 'Fixed in deploy v2.1'
        err.save()

        err.refresh_from_db()
        assert err.resolved is True
        assert err.resolved_at is not None
        assert 'v2.1' in err.resolution_notes

    def test_str_representation(self):
        err = BackendErrorLog.objects.create(
            source='api', severity='error',
            error_class='ValueError', message='test msg',
        )
        s = str(err)
        assert 'ValueError' in s or 'api' in s or str(err.id) in s


# ── Middleware Tests ────────────────────────────────────────────────

@pytest.mark.django_db
class TestErrorCaptureMiddleware:
    def test_middleware_captures_500(self):
        """Verify that the middleware creates a BackendErrorLog on unhandled exception."""
        from news.error_capture import ErrorCaptureMiddleware

        # Create a mock request
        request = MagicMock()
        request.method = 'GET'
        request.path = '/api/v1/test/'
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        request.user = MagicMock()
        request.user.is_authenticated = True
        request.user.username = 'testuser'

        # Create middleware with a dummy get_response
        middleware = ErrorCaptureMiddleware(get_response=lambda r: None)

        # Call process_exception
        exc = ValueError("Test middleware capture")
        result = middleware.process_exception(request, exc)

        # Should return None (not swallow exception)
        assert result is None

        # Should have created a BackendErrorLog
        assert BackendErrorLog.objects.filter(
            source='api',
            error_class='ValueError',
            message='Test middleware capture',
            request_method='GET',
            request_path='/api/v1/test/',
        ).exists()

    def test_middleware_deduplicates(self):
        """Same error within dedup window should increment count, not create new."""
        from news.error_capture import ErrorCaptureMiddleware

        request = MagicMock()
        request.method = 'GET'
        request.path = '/api/v1/dup-test/'
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        request.user = MagicMock()
        request.user.is_authenticated = False

        middleware = ErrorCaptureMiddleware(get_response=lambda r: None)
        exc = RuntimeError("Dedup test error")

        middleware.process_exception(request, exc)
        middleware.process_exception(request, exc)

        entries = BackendErrorLog.objects.filter(
            error_class='RuntimeError',
            request_path='/api/v1/dup-test/',
        )
        assert entries.count() == 1
        assert entries.first().occurrence_count >= 2

    def test_middleware_never_swallows(self):
        """Middleware must return None so Django continues normal exception handling."""
        from news.error_capture import ErrorCaptureMiddleware

        request = MagicMock()
        request.method = 'POST'
        request.path = '/api/v1/broken/'
        request.META = {'REMOTE_ADDR': '10.0.0.1'}
        request.user = MagicMock()
        request.user.is_authenticated = False

        middleware = ErrorCaptureMiddleware(get_response=lambda r: None)
        result = middleware.process_exception(request, Exception("crash"))
        assert result is None


# ── Scheduler Error Logging Tests ──────────────────────────────────

@pytest.mark.django_db
class TestSchedulerErrorLogging:
    def test_log_scheduler_error(self):
        from news.scheduler import _log_scheduler_error

        exc = ConnectionError("Redis connection lost")
        _log_scheduler_error('rss_scan', exc)

        err = BackendErrorLog.objects.get(
            source='scheduler',
            task_name='rss_scan',
        )
        assert err.error_class == 'ConnectionError'
        assert 'Redis' in err.message

    def test_log_scheduler_error_dedup(self):
        from news.scheduler import _log_scheduler_error

        exc = TimeoutError("Task timed out")
        _log_scheduler_error('youtube_scan', exc)
        _log_scheduler_error('youtube_scan', exc)

        entries = BackendErrorLog.objects.filter(
            source='scheduler', task_name='youtube_scan',
        )
        assert entries.count() == 1
        assert entries.first().occurrence_count >= 2


# ── API Tests ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBackendErrorLogAPI:
    def test_list_requires_admin(self, anon_client):
        response = anon_client.get('/api/v1/backend-errors/')
        assert response.status_code in [401, 403]

    def test_list_as_admin(self, admin_client, sample_errors):
        client, _ = admin_client
        response = client.get('/api/v1/backend-errors/')
        assert response.status_code == 200
        data = response.json()
        results = data.get('results', data)
        assert len(results) >= 3

    def test_filter_by_source(self, admin_client, sample_errors):
        client, _ = admin_client
        response = client.get('/api/v1/backend-errors/?source=scheduler')
        assert response.status_code == 200
        data = response.json()
        results = data.get('results', data)
        assert all(r['source'] == 'scheduler' for r in results)

    def test_filter_by_resolved(self, admin_client, sample_errors):
        client, _ = admin_client
        response = client.get('/api/v1/backend-errors/?resolved=false')
        assert response.status_code == 200
        data = response.json()
        results = data.get('results', data)
        assert all(r['resolved'] is False for r in results)

    def test_patch_resolve(self, admin_client, sample_errors):
        client, _ = admin_client
        err = sample_errors[0]
        response = client.patch(f'/api/v1/backend-errors/{err.id}/', {'resolved': True}, format='json')
        assert response.status_code == 200
        err.refresh_from_db()
        assert err.resolved is True

    def test_delete_error(self, admin_client, sample_errors):
        client, _ = admin_client
        err = sample_errors[0]
        response = client.delete(f'/api/v1/backend-errors/{err.id}/')
        assert response.status_code == 204
        assert not BackendErrorLog.objects.filter(id=err.id).exists()


@pytest.mark.django_db
class TestResolveAllAction:
    def test_resolve_all(self, admin_client, sample_errors):
        client, _ = admin_client
        unresolved_before = BackendErrorLog.objects.filter(resolved=False).count()
        assert unresolved_before >= 2

        response = client.post('/api/v1/backend-errors/resolve-all/')
        assert response.status_code == 200
        data = response.json()
        assert data['resolved'] >= 2

        assert BackendErrorLog.objects.filter(resolved=False).count() == 0

    def test_resolve_all_requires_admin(self, anon_client):
        response = anon_client.post('/api/v1/backend-errors/resolve-all/')
        assert response.status_code in [401, 403]


# ── Health Summary Tests ───────────────────────────────────────────

@pytest.mark.django_db
class TestHealthSummaryAPI:
    def test_summary_requires_admin(self, anon_client):
        response = anon_client.get('/api/v1/health/errors-summary/')
        assert response.status_code in [401, 403]

    def test_summary_returns_counts(self, admin_client, sample_errors):
        client, _ = admin_client
        response = client.get('/api/v1/health/errors-summary/')
        assert response.status_code == 200
        data = response.json()

        assert 'backend_errors' in data
        assert 'api_errors' in data
        assert 'scheduler_errors' in data
        assert 'frontend_errors' in data
        assert 'overall_status' in data
        assert 'total_unresolved' in data
        assert 'trend' in data

        assert data['backend_errors']['total'] >= 3
        assert data['backend_errors']['unresolved'] >= 2
        assert data['api_errors']['unresolved'] >= 1
        assert data['scheduler_errors']['unresolved'] >= 1

    def test_summary_trend_has_7_days(self, admin_client, sample_errors):
        client, _ = admin_client
        response = client.get('/api/v1/health/errors-summary/')
        data = response.json()

        assert len(data['trend']) == 7
        for day in data['trend']:
            assert 'date' in day
            assert 'api' in day
            assert 'scheduler' in day
            assert 'frontend' in day

    def test_overall_status_healthy(self, admin_client):
        """No errors → healthy."""
        client, _ = admin_client
        BackendErrorLog.objects.all().delete()
        response = client.get('/api/v1/health/errors-summary/')
        data = response.json()
        assert data['overall_status'] == 'healthy'
        assert data['total_unresolved'] == 0
