"""
Cache invalidation signals for automatic cache clearing when data changes
"""
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import cache
from .models import Article, Category, Tag


@receiver([post_save, post_delete], sender=Article)
def invalidate_article_cache(sender, instance, **kwargs):
    """Clear article-related caches when article is saved or deleted"""
    cache.delete_many([
        f'article_list',
        f'article_{instance.id}',
        f'article_{instance.slug}',
        f'category_{instance.category.slug}_articles',
        f'trending_articles',
    ])
    # Clear article list cache patterns
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
    cache.delete_pattern('category*')


@receiver([post_save, post_delete], sender=Tag)
def invalidate_tag_cache(sender, instance, **kwargs):
    """Clear tag-related caches when tag is saved or deleted"""
    cache.delete_many([
        f'tag_list',
        f'tag_{instance.id}',
        f'tag_{instance.slug}',
    ])
    cache.delete_pattern('tag*')


@receiver(m2m_changed, sender=Article.tags.through)
def invalidate_article_tags_cache(sender, instance, **kwargs):
    """Clear caches when article tags are changed"""
    if isinstance(instance, Article):
        cache.delete_many([
            f'article_{instance.id}',
            f'article_{instance.slug}',
        ])
        cache.delete_pattern('article_list*')
