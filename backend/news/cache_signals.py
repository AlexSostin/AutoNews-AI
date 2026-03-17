"""
Cache invalidation signals for automatic cache clearing when data changes.

Strategy:
- Each @cache_page uses a key_prefix so we can invalidate it by name
- On model save/delete, we clear specific cache groups instead of nuking everything
- SiteSettings uses manual cache.set/delete (no cache_page decorator)
"""
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import cache
from .models import Article, Category, Tag, Rating, Comment


# ──────────────────────────────────────────────────────────────
# Cache key prefixes — must match the key_prefix in @cache_page()
# ──────────────────────────────────────────────────────────────
CACHE_PREFIXES = {
    'articles':     'articles_list',       # ArticleViewSet._cached_list
    'categories':   'categories_list',     # CategoryViewSet._cached_list
    'tags':         'tags_list',           # TagViewSet._cached_list
    'trending':     'trending',            # ArticleEngagementMixin.trending
    'popular':      'popular',             # ArticleEngagementMixin.popular
    'cars_picker':  'cars_picker',         # CarPickerListView
    'currency':     'currency_rates',      # CurrencyRatesView
    'robots':       'robots_txt',          # robots.txt view
    'settings':     'site_settings_api_v1', # SiteSettingsViewSet (manual cache)
}


def _delete_cache_page_prefix(prefix):
    """Delete all cache_page keys with the given prefix.
    
    Django's cache_page with key_prefix stores keys like:
    views.decorators.cache.cache_page.<prefix>.<method>.<url_hash>.<content_hash>
    With Redis key version prefix: :1:views.decorators.cache.cache_page.<prefix>.*
    """
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(f'views.decorators.cache.cache_page.{prefix}*')
        cache.delete_pattern(f':1:views.decorators.cache.cache_page.{prefix}*')
    else:
        # Fallback: try Redis SCAN
        try:
            redis_client = cache._cache.get_client() if hasattr(cache._cache, 'get_client') else cache._cache
            pattern = f'*cache_page.{prefix}*'
            cursor = 0
            while True:
                cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                if keys:
                    str_keys = [k.decode('utf-8') if isinstance(k, bytes) else k for k in keys]
                    cache.delete_many(str_keys)
                if cursor == 0:
                    break
        except Exception:
            pass


def invalidate_article_caches(article_id=None, slug=None):
    """Clear article-related caches. Called on Article save/delete."""
    # Specific article keys
    keys = ['trending_articles']
    if article_id:
        keys.append(f'article_{article_id}')
    if slug:
        keys.append(f'article_{slug}')
    cache.delete_many(keys)
    
    # Clear cache_page responses for article lists, trending, popular
    for prefix in ['articles_list', 'trending', 'popular']:
        _delete_cache_page_prefix(prefix)


def invalidate_category_caches():
    """Clear category-related caches."""
    _delete_cache_page_prefix('categories_list')


def invalidate_tag_caches():
    """Clear tag-related caches."""
    _delete_cache_page_prefix('tags_list')


def invalidate_cars_caches():
    """Clear car picker/compare caches."""
    _delete_cache_page_prefix('cars_picker')


def invalidate_settings_cache():
    """Clear the manual settings cache."""
    cache.delete(CACHE_PREFIXES['settings'])


# ──────────────────────────────────────────────────────────────
# Django signals → targeted invalidation
# ──────────────────────────────────────────────────────────────

@receiver([post_save, post_delete], sender=Article)
def on_article_change(sender, instance, **kwargs):
    """Article saved/deleted → clear article + category caches + Vercel ISR."""
    invalidate_article_caches(article_id=instance.id, slug=instance.slug)
    # Categories are affected because article counts change
    invalidate_category_caches()

    # Trigger Next.js ISR revalidation when publish-relevant fields change.
    # We check update_fields to avoid triggering on every save (e.g. view count).
    # post_delete always triggers (deleted articles must disappear from homepage).
    is_delete = not kwargs.get('created', False) and kwargs.get('signal') == post_delete
    update_fields = kwargs.get('update_fields')
    publish_fields = {'is_published', 'is_deleted', 'is_hero', 'title', 'slug', 'summary', 'image'}

    should_revalidate = (
        is_delete
        or update_fields is None  # full save (admin form, list_editable, etc.)
        or bool(publish_fields & set(update_fields))  # targeted save with relevant field
    )

    if should_revalidate:
        try:
            from news.api_views._shared import trigger_nextjs_revalidation
            paths = ['/', '/articles', '/trending']
            if instance.slug:
                paths.append(f'/articles/{instance.slug}')
            trigger_nextjs_revalidation(paths=paths)
        except Exception:
            pass


@receiver([post_save, post_delete], sender=Category)
def on_category_change(sender, instance, **kwargs):
    """Category saved/deleted → clear category caches."""
    invalidate_category_caches()


@receiver([post_save, post_delete], sender=Tag)
def on_tag_change(sender, instance, **kwargs):
    """Tag saved/deleted → clear tag caches."""
    invalidate_tag_caches()


@receiver(m2m_changed, sender=Article.tags.through)
def on_article_tags_change(sender, instance, **kwargs):
    """Article tags changed → clear article + tag caches."""
    if isinstance(instance, Article):
        invalidate_article_caches(article_id=instance.id, slug=instance.slug)
        invalidate_tag_caches()


@receiver(m2m_changed, sender=Article.categories.through)
def on_article_categories_change(sender, instance, **kwargs):
    """Article categories changed → clear article + category caches."""
    if isinstance(instance, Article):
        invalidate_article_caches(article_id=instance.id, slug=instance.slug)
        invalidate_category_caches()


@receiver([post_save, post_delete], sender=Rating)
def on_rating_change(sender, instance, **kwargs):
    """Rating changed → clear that article's cache."""
    invalidate_article_caches(
        article_id=instance.article_id,
        slug=instance.article.slug
    )


@receiver([post_save, post_delete], sender=Comment)
def on_comment_change(sender, instance, **kwargs):
    """Comment changed → clear that article's cache."""
    invalidate_article_caches(
        article_id=instance.article_id,
        slug=instance.article.slug
    )
