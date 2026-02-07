"""
Cache invalidation signals for automatic cache clearing when data changes
"""
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import cache
from .models import Article, Category, Tag, Rating, Comment


@receiver([post_save, post_delete], sender=Article)
def invalidate_article_cache(sender, instance, **kwargs):
    """Clear article-related caches when article is saved or deleted"""
    cache_keys = [
        f'article_list',
        f'article_{instance.id}',
        f'article_{instance.slug}',
        f'trending_articles',
    ]
    
    # Add cache keys for all categories (ManyToMany)
    if kwargs.get('signal') == post_delete:
        # For delete, we can't access categories anymore, so clear all category caches
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern('category_*_articles')
    else:
        # For save, clear cache for each category
        for category in instance.categories.all():
            cache_keys.append(f'category_{category.slug}_articles')
    
    cache.delete_many(cache_keys)
    
    # Clear article list cache patterns (only if cache supports pattern deletion)
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern('article_list*')
        cache.delete_pattern('articles*')


@receiver([post_save, post_delete], sender=Category)
def invalidate_category_cache(sender, instance, **kwargs):
    """Clear category-related caches when category is saved or deleted"""
    cache.delete_many([
        f'category_list',
        f'category_{instance.id}',
        f'category_{instance.slug}',
    ])
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern('category*')


@receiver([post_save, post_delete], sender=Tag)
def invalidate_tag_cache(sender, instance, **kwargs):
    """Clear tag-related caches when tag is saved or deleted"""
    cache.delete_many([
        f'tag_list',
        f'tag_{instance.id}',
        f'tag_{instance.slug}',
    ])
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern('tag*')


@receiver(m2m_changed, sender=Article.tags.through)
def invalidate_article_tags_cache(sender, instance, **kwargs):
    """Clear caches when article tags are changed"""
    if isinstance(instance, Article):
        cache.delete_many([
            f'article_{instance.id}',
            f'article_{instance.slug}',
        ])
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern('article_list*')


@receiver(m2m_changed, sender=Article.categories.through)
def invalidate_article_categories_cache(sender, instance, **kwargs):
    """Clear caches when article categories are changed"""
    if isinstance(instance, Article):
        cache_keys = [
            f'article_{instance.id}',
            f'article_{instance.slug}',
        ]
        
        # Clear cache for affected categories
        for category in instance.categories.all():
            cache_keys.append(f'category_{category.slug}_articles')
        
        cache.delete_many(cache_keys)
        
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern('article_list*')



@receiver([post_save, post_delete], sender=Rating)
def invalidate_article_on_rating(sender, instance, **kwargs):
    """Clear article-related caches when a rating is added or changed"""
    cache.delete_many([
        f'article_{instance.article.id}',
        f'article_{instance.article.slug}',
        'trending_articles',
    ])
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern('article_list*')


@receiver([post_save, post_delete], sender=Comment)
def invalidate_article_on_comment(sender, instance, **kwargs):
    """Clear article-related caches when a comment is added or changed"""
    cache.delete_many([
        f'article_{instance.article.id}',
        f'article_{instance.article.slug}',
    ])
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern('article_list*')


@receiver(m2m_changed, sender=Article.categories.through)
def invalidate_cache_on_category_change(sender, instance, action, **kwargs):
    """Clear category caches when article categories are changed"""
    if action in ['post_add', 'post_remove', 'post_clear']:
        # Clear cache for all affected categories
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern('category*')
        
        # Clear article list caches
        cache.delete_many([
            f'article_{instance.id}',
            f'article_{instance.slug}',
        ])
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern('article_list*')

