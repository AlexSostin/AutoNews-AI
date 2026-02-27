"""
Error Capture Middleware — automatically logs unhandled exceptions to BackendErrorLog.

Catches ALL API 500 errors with full traceback, request context, and deduplication.
Works alongside Sentry (if configured) — this middleware never swallows exceptions.
"""
import logging
import traceback as tb

logger = logging.getLogger(__name__)


class ErrorCaptureMiddleware:
    """
    Django middleware that captures unhandled exceptions and logs them
    to BackendErrorLog for the System Health Dashboard.
    
    Uses Django's process_exception hook — only fires on actual 500s.
    Deduplicates: same error_class + message + path within 1 hour
    increments occurrence_count instead of creating duplicates.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        """Called by Django when a view raises an unhandled exception."""
        try:
            self._log_error(request, exception)
        except Exception as log_err:
            # Never let error logging break the request
            logger.warning(f"ErrorCaptureMiddleware failed to log: {log_err}")

        # Return None so Django continues normal exception handling
        # (DRF returns JSON 500, Sentry captures it, etc.)
        return None

    def _log_error(self, request, exception):
        from news.models.system import BackendErrorLog
        from django.utils import timezone
        from datetime import timedelta

        error_class = type(exception).__name__
        message = str(exception)[:1000]
        request_path = getattr(request, 'path', '')[:500]
        request_method = getattr(request, 'method', '')
        full_traceback = tb.format_exc()

        # Extract user info
        request_user = ''
        if hasattr(request, 'user') and hasattr(request.user, 'username'):
            if request.user.is_authenticated:
                request_user = request.user.username

        # Extract IP
        request_ip = None
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            request_ip = x_forwarded.split(',')[0].strip()
        else:
            raw_ip = request.META.get('REMOTE_ADDR')
            if raw_ip:
                request_ip = raw_ip

        # Determine severity
        severity = 'error'
        critical_exceptions = ('DatabaseError', 'OperationalError', 'ConnectionError', 'TimeoutError')
        if error_class in critical_exceptions:
            severity = 'critical'

        # Deduplication: check for same error in last hour
        one_hour_ago = timezone.now() - timedelta(hours=1)
        existing = BackendErrorLog.objects.filter(
            source='api',
            error_class=error_class,
            request_path=request_path,
            last_seen__gte=one_hour_ago,
            resolved=False,
        ).first()

        if existing:
            existing.occurrence_count += 1
            existing.message = message
            existing.traceback = full_traceback
            existing.severity = severity
            existing.save(update_fields=[
                'occurrence_count', 'last_seen', 'message', 'traceback', 'severity'
            ])
            logger.info(f"[ErrorCapture] Deduplicated: {error_class} at {request_path} (#{existing.occurrence_count})")
        else:
            BackendErrorLog.objects.create(
                source='api',
                severity=severity,
                error_class=error_class,
                message=message,
                traceback=full_traceback,
                request_method=request_method,
                request_path=request_path,
                request_user=request_user,
                request_ip=request_ip,
            )
            logger.info(f"[ErrorCapture] Logged: {error_class} at {request_method} {request_path}")
