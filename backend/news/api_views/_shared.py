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
    Much faster than cache.clear() which deletes EVERYTHING.
    
    Args:
        article_id: Article ID to invalidate specific article cache
        slug: Article slug to invalidate specific article cache
    """
    keys_to_delete = []
    
    # Specific article keys
    if article_id:
        keys_to_delete.append(f'article_{article_id}')
    if slug:
        keys_to_delete.append(f'article_slug_{slug}')
    
    # Pattern-based keys (need to scan Redis)
    patterns_to_delete = [
        'article_list_*',     # Article list pages
        'articles_page_*',    # Paginated lists
        'category_*',         # Category views (article counts changed)
        'homepage_*',         # Homepage caches
        'trending_*',         # Trending articles
        'latest_*',           # Latest articles
        'featured_*',         # Featured articles
        'views.decorators.cache.cache_*',  # Django @cache_page keys
        ':1:views.decorators.cache.cache_page*',  # Django cache_page with prefix
    ]
    
    # Delete simple keys first
    if keys_to_delete:
        cache.delete_many(keys_to_delete)
    
    # Delete pattern-matched keys
    try:
        from django.core.cache.backends.redis import RedisCache
        if isinstance(cache, RedisCache) or hasattr(cache, '_cache'):
            # Use Redis SCAN for pattern matching (safe for large datasets)
            redis_client = cache._cache.get_client() if hasattr(cache._cache, 'get_client') else cache._cache
            
            for pattern in patterns_to_delete:
                cursor = 0
                while True:
                    cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                    if keys:
                        # Decode bytes to strings if needed
                        str_keys = [k.decode('utf-8') if isinstance(k, bytes) else k for k in keys]
                        cache.delete_many(str_keys)
                    if cursor == 0:
                        break
            
            logger.info(f"Selectively invalidated article cache (article_id={article_id}, slug={slug})")
        else:
            # Fallback for non-Redis backends - still better than clearing everything
            logger.warning("Non-Redis cache backend - pattern matching not supported")
            cache.delete_many(keys_to_delete)
    except Exception as e:
        logger.warning(f"Failed to invalidate pattern cache keys: {e}")
        # Still better to continue than fail

    # Trigger Next.js on-demand revalidation (non-blocking)
    trigger_nextjs_revalidation()

def trigger_nextjs_revalidation(paths=None):
    """
    Tell Next.js to revalidate its ISR cache immediately.
    Runs in a background thread so it doesn't slow down the API response.
    """
    def _revalidate():
        import requests as http_requests
        frontend_url = os.environ.get(
            'FRONTEND_URL',
            'http://frontend:3000' if os.environ.get('RUNNING_IN_DOCKER') else 'http://localhost:3000'
        )
        secret = os.environ.get('REVALIDATION_SECRET', 'freshmotors-revalidate-2026')
        try:
            resp = http_requests.post(
                f'{frontend_url}/api/revalidate',
                json={
                    'secret': secret,
                    'paths': paths or ['/', '/articles', '/trending'],
                },
                timeout=5,
            )
            if resp.ok:
                logger.info(f"Next.js revalidation triggered: {resp.json()}")
            else:
                logger.warning(f"Next.js revalidation failed ({resp.status_code}): {resp.text[:200]}")
        except Exception as e:
            logger.debug(f"Next.js revalidation skipped (frontend may not be running): {e}")

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
