"""
Shared utilities and permissions used across article-related API views.
"""
from django.core.cache import cache
from rest_framework.permissions import BasePermission
import logging
import os
import re
import threading

logger = logging.getLogger(__name__)


def invalidate_article_cache(article_id=None, slug=None):
    """
    Selectively invalidate cache keys related to articles.
    Delegates to cache_signals for targeted prefix-based invalidation.
    
    Args:
        article_id: Article ID to invalidate specific article cache
        slug: Article slug to invalidate specific article cache
    """
    from news.cache_signals import invalidate_article_caches, invalidate_category_caches
    
    invalidate_article_caches(article_id=article_id, slug=slug)
    invalidate_category_caches()  # Article counts change
    
    # Trigger Next.js on-demand revalidation (non-blocking)
    trigger_nextjs_revalidation()

def trigger_nextjs_revalidation(paths=None):
    """
    Tell Next.js to revalidate its ISR cache immediately.
    Runs in a background thread so it doesn't slow down the API response.
    Tries FRONTEND_URL first, then falls back to production Vercel URL.
    """
    def _revalidate():
        import requests as http_requests
        frontend_url = os.environ.get(
            'FRONTEND_URL',
            'http://frontend:3000' if os.environ.get('RUNNING_IN_DOCKER') else 'http://localhost:3000'
        )
        # Production Vercel fallback — if FRONTEND_URL is Docker-internal, also try public URL
        vercel_url = os.environ.get('VERCEL_URL', 'https://www.freshmotors.net')
        secret = os.environ.get('REVALIDATION_SECRET', 'freshmotors-revalidate-2026')
        payload = {
            'secret': secret,
            'paths': paths or ['/', '/articles', '/trending'],
        }

        success = False
        for url in [frontend_url, vercel_url]:
            try:
                resp = http_requests.post(
                    f'{url}/api/revalidate',
                    json=payload,
                    timeout=8,
                )
                if resp.ok:
                    logger.info(f"Next.js revalidation triggered via {url}: {resp.json()}")
                    success = True
                    break
                else:
                    logger.warning(f"Next.js revalidation via {url} failed ({resp.status_code}): {resp.text[:200]}")
            except Exception as e:
                logger.debug(f"Next.js revalidation via {url} skipped: {e}")

        if not success:
            logger.warning("Next.js revalidation failed on all URLs")

    threading.Thread(target=_revalidate, daemon=True).start()

class IsStaffOrReadOnly(BasePermission):
    """
    Custom permission to only allow staff users to edit objects.
    Read-only for everyone else. Logs unauthorized access attempts.
    """
    def has_permission(self, request, view):
        # Read permissions are allowed to any request
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        # Write permissions only for staff
        is_allowed = request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)
        
        # Log unauthorized write attempts
        if not is_allowed and request.user and request.user.is_authenticated:
            logger.warning(
                f"Unauthorized write attempt: user={request.user.username}, "
                f"method={request.method}, path={request.path}"
            )
        
        return is_allowed

def is_valid_youtube_url(url):
    """Validate YouTube URL to prevent malicious input"""
    if not url or not isinstance(url, str):
        return False
    youtube_regex = r'^(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([a-zA-Z0-9_-]{11})(&.*)?$'
    return bool(re.match(youtube_regex, url))
