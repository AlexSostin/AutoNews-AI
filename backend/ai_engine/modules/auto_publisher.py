"""
Auto-publisher engine.

Checks pending articles against quality thresholds and rate limits,
and publishes those that qualify. All behavior controlled by AutomationSettings.
"""
import logging
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger('news')


def auto_publish_pending():
    """
    Check pending articles and auto-publish those meeting criteria.
    
    Returns (published_count, skipped_reasons)
    """
    from news.models import AutomationSettings, PendingArticle, Article
    from ai_engine.modules.publisher import publish_article
    
    settings = AutomationSettings.load()
    
    if not settings.auto_publish_enabled:
        return 0, 'auto-publish disabled'
    
    # Reset daily counters if new day
    settings.reset_daily_counters()
    settings.refresh_from_db()
    
    # Check daily limit
    if settings.auto_publish_today_count >= settings.auto_publish_max_per_day:
        logger.info(f"⏸️ Auto-publish: daily limit reached ({settings.auto_publish_today_count}/{settings.auto_publish_max_per_day})")
        return 0, f'daily limit reached ({settings.auto_publish_today_count}/{settings.auto_publish_max_per_day})'
    
    # Check hourly limit
    one_hour_ago = timezone.now() - timedelta(hours=1)
    articles_this_hour = Article.objects.filter(
        created_at__gte=one_hour_ago,
        is_published=True
    ).count()
    
    if articles_this_hour >= settings.auto_publish_max_per_hour:
        logger.info(f"⏸️ Auto-publish: hourly limit reached ({articles_this_hour}/{settings.auto_publish_max_per_hour})")
        return 0, f'hourly limit reached ({articles_this_hour}/{settings.auto_publish_max_per_hour})'
    
    # How many more can we publish this hour?
    remaining_hourly = settings.auto_publish_max_per_hour - articles_this_hour
    remaining_daily = settings.auto_publish_max_per_day - settings.auto_publish_today_count
    publish_limit = min(remaining_hourly, remaining_daily)
    
    # Find eligible pending articles
    queryset = PendingArticle.objects.filter(
        status='pending',
        quality_score__gte=settings.auto_publish_min_quality,
    ).order_by('created_at')  # FIFO — oldest first
    
    if settings.auto_publish_require_image:
        queryset = queryset.exclude(featured_image='')
    
    candidates = queryset[:publish_limit]
    
    if not candidates:
        return 0, 'no eligible articles'
    
    published_count = 0
    
    for pending in candidates:
        try:
            # Build tag list
            tag_names = pending.tags if isinstance(pending.tags, list) else []
            
            # Determine category
            category_name = pending.suggested_category.name if pending.suggested_category else 'News'
            
            # Get image paths
            image_paths = pending.images if isinstance(pending.images, list) else []
            
            article = publish_article(
                title=pending.title,
                content=pending.content,
                category_name=category_name,
                image_path=pending.featured_image or None,
                image_paths=image_paths if image_paths else None,
                youtube_url=pending.video_url or None,
                summary=pending.excerpt or None,
                tag_names=tag_names if tag_names else None,
                specs=pending.specs if pending.specs else None,
                is_published=True,
            )
            
            if article:
                # Update pending article status
                pending.status = 'published'
                pending.published_article = article
                pending.reviewed_at = timezone.now()
                pending.review_notes = f'Auto-published (quality: {pending.quality_score}/10)'
                pending.save()
                
                # Update counter
                settings.auto_publish_today_count += 1
                settings.save(update_fields=['auto_publish_today_count'])
                
                published_count += 1
                logger.info(f"✅ Auto-published: {article.title[:60]} (quality: {pending.quality_score}/10)")
            else:
                logger.warning(f"⚠️ Auto-publish failed for: {pending.title[:60]}")
                
        except Exception as e:
            logger.error(f"❌ Auto-publish error for '{pending.title[:40]}': {e}")
            continue
    
    if published_count > 0:
        logger.info(f"📝 Auto-publish cycle: {published_count} articles published "
                     f"(today: {settings.auto_publish_today_count}/{settings.auto_publish_max_per_day})")
    
    return published_count, f'{published_count} published'
