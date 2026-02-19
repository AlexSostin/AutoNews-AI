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
        logger.info(f"[AUTO-PUBLISHER] ⏸️ Daily limit reached ({settings.auto_publish_today_count}/{settings.auto_publish_max_per_day})")
        return 0, f'daily limit reached ({settings.auto_publish_today_count}/{settings.auto_publish_max_per_day})'
    
    # Check hourly limit
    one_hour_ago = timezone.now() - timedelta(hours=1)
    articles_this_hour = Article.objects.filter(
        created_at__gte=one_hour_ago,
        is_published=True
    ).count()
    
    if articles_this_hour >= settings.auto_publish_max_per_hour:
        logger.info(f"[AUTO-PUBLISHER] ⏸️ Hourly limit reached ({articles_this_hour}/{settings.auto_publish_max_per_hour})")
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
    
    # If require_image is on AND auto_image is off, filter to only those with images
    if settings.auto_publish_require_image and settings.auto_image_mode == 'off':
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
                # Auto-attach image only for RSS articles (no video = RSS source)
                # YouTube articles already have thumbnails — no AI generation needed
                is_youtube = bool(pending.video_url)
                
                if settings.auto_image_mode != 'off' and not is_youtube:
                    try:
                        from ai_engine.modules.auto_image_finder import find_and_attach_image
                        img_result = find_and_attach_image(article, pending_article=pending)
                        if img_result.get('success'):
                            logger.info(f"[AUTO-PUBLISHER/IMAGE] 📸 Success ({img_result['method']}): {article.title[:50]}")
                        else:
                            logger.info(f"[AUTO-PUBLISHER/IMAGE] 📸 Skipped: {img_result.get('error', '?')}")
                            # If require_image is on and we failed, unpublish
                            if settings.auto_publish_require_image:
                                article.is_published = False
                                article.save(update_fields=['is_published'])
                                logger.warning(f"[AUTO-PUBLISHER] ⚠️ Unpublished (no image): {article.title[:50]}")
                                pending.status = 'pending'
                                pending.review_notes = f'Auto-image failed: {img_result.get("error", "?")}'
                                pending.save()
                                continue
                    except Exception as e:
                        logger.error(f"[AUTO-PUBLISHER/IMAGE] ❌ Error: {e}", exc_info=True)
                elif is_youtube:
                    logger.info(f"[AUTO-PUBLISHER] 🎬 YouTube article — using video thumbnail, skipping AI image")
                
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
                logger.info(f"[AUTO-PUBLISHER] ✅ Published: {article.title[:60]} (quality: {pending.quality_score}/10)")
            else:
                logger.warning(f"[AUTO-PUBLISHER] ⚠️ Publish failed for: {pending.title[:60]}")
                
        except Exception as e:
            logger.error(f"[AUTO-PUBLISHER] ❌ Error for '{pending.title[:40]}': {e}", exc_info=True)
            continue
    
    if published_count > 0:
        logger.info(f"[AUTO-PUBLISHER] 📝 Cycle done: {published_count} published "
                     f"(today: {settings.auto_publish_today_count}/{settings.auto_publish_max_per_day})")
    
    return published_count, f'{published_count} published'
