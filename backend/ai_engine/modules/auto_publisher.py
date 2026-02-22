"""
Auto-publisher engine.

Checks pending articles against quality thresholds, safety scores,
and rate limits, then publishes those that qualify.
All decisions are logged to AutoPublishLog for transparency and ML training.

Circuit breaker: articles that fail 3 times are marked 'auto_failed'
and excluded from future attempts. Exponential backoff between retries.
"""
import logging
import traceback
from datetime import timedelta
from django.db.models import F, Q
from django.utils import timezone

logger = logging.getLogger('news')

# Circuit breaker settings
MAX_RETRIES = 3                # After 3 failures, mark as auto_failed
BACKOFF_MINUTES = [30, 120]    # Wait 30min after 1st fail, 2h after 2nd, then permanent
CIRCUIT_BREAKER_THRESHOLD = 5  # Pause auto-publish if 5 consecutive failures


def _log_decision(pending, decision, reason, article=None):
    """Record an auto-publish decision for transparency and ML."""
    from news.models import AutoPublishLog
    
    feed = pending.rss_feed
    is_youtube = bool(pending.video_url)
    
    AutoPublishLog.objects.create(
        pending_article=pending,
        published_article=article,
        decision=decision,
        reason=reason,
        quality_score=pending.quality_score or 0,
        safety_score=getattr(feed, 'safety_score', '') if feed else '',
        image_policy=getattr(feed, 'image_policy', '') if feed else '',
        feed_name=feed.name if feed else ('YouTube' if is_youtube else 'Unknown'),
        source_type=feed.source_type if feed else ('youtube' if is_youtube else ''),
        article_title=pending.title[:500],
        content_length=len(pending.content or ''),
        has_image=bool(pending.featured_image),
        has_specs=bool(pending.specs),
        tag_count=len(pending.tags) if isinstance(pending.tags, list) else 0,
        category_name=pending.suggested_category.name if pending.suggested_category else '',
        source_is_youtube=is_youtube,
    )


def _is_backed_off(pending):
    """Check if an article is in backoff cooldown after a failure."""
    if pending.auto_publish_attempts == 0:
        return False
    if pending.auto_publish_attempts >= MAX_RETRIES:
        return True  # Permanently failed
    if not pending.auto_publish_last_attempt:
        return False
    
    # Exponential backoff
    backoff_idx = min(pending.auto_publish_attempts - 1, len(BACKOFF_MINUTES) - 1)
    backoff_until = pending.auto_publish_last_attempt + timedelta(minutes=BACKOFF_MINUTES[backoff_idx])
    return timezone.now() < backoff_until


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
    
    # Find ALL pending articles with minimum quality (exclude circuit-broken ones)
    all_candidates = PendingArticle.objects.filter(
        status='pending',
        quality_score__gte=settings.auto_publish_min_quality,
        auto_publish_attempts__lt=MAX_RETRIES,  # Circuit breaker: skip after MAX_RETRIES failures
    ).select_related('rss_feed', 'suggested_category').order_by(
        'auto_publish_attempts',  # Try fresh articles first
        '-quality_score', 'created_at'
    )
    
    # If require_image is on AND auto_image is off, filter to only those with images
    if settings.auto_publish_require_image and settings.auto_image_mode == 'off':
        all_candidates = all_candidates.exclude(featured_image='')
    
    # Apply safety gating and collect decisions
    eligible = []
    
    for pending in all_candidates:
        feed = pending.rss_feed
        
        # Circuit breaker: skip if in backoff cooldown
        if _is_backed_off(pending):
            logger.debug(f"[AUTO-PUBLISHER] ⏳ Backoff: {pending.title[:50]} (attempt {pending.auto_publish_attempts})")
            continue
        
        # Safety check: skip unsafe feeds if setting is on
        if settings.auto_publish_require_safe_feed and feed:
            feed_safety = getattr(feed, 'safety_score', 'review')
            if feed_safety == 'unsafe':
                _log_decision(pending, 'skipped_safety',
                    f"Feed '{feed.name}' has safety_score='unsafe' — blocked by 'Only safe feeds' setting")
                logger.info(f"[AUTO-PUBLISHER] 🛡️ Skipped (unsafe feed): {pending.title[:50]} (feed: {feed.name})")
                continue
        
        # Image check for no-image articles when auto_image is off
        if settings.auto_publish_require_image and settings.auto_image_mode == 'off':
            if not pending.featured_image:
                _log_decision(pending, 'skipped_no_image',
                    f"No featured image and auto-image is off")
                continue
        
        eligible.append(pending)
        
        if len(eligible) >= publish_limit:
            break
    
    if not eligible:
        return 0, 'no eligible articles'
    
    published_count = 0
    
    for pending in eligible:
        try:
            # Build tag list
            tag_names = pending.tags if isinstance(pending.tags, list) else []
            
            # Determine category
            category_name = pending.suggested_category.name if pending.suggested_category else 'News'
            
            # Get image paths
            image_paths = pending.images if isinstance(pending.images, list) else []
            
            # Draft mode: create as draft for manual review, or publish directly
            as_draft = settings.auto_publish_as_draft
            
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
                is_published=not as_draft,
            )
            
            if article:
                # Auto-attach image only for RSS articles (no video = RSS source)
                # YouTube articles already have thumbnails — no AI generation needed
                is_youtube = bool(pending.video_url)
                
                if settings.auto_image_mode != 'off' and not is_youtube:
                    try:
                        from ai_engine.modules.auto_image_finder import find_and_attach_image
                        img_result = find_and_attach_image(article, pending_article=pending)
                        
                        # Track auto-image stats
                        AutomationSettings.objects.filter(pk=1).update(
                            auto_image_last_run=timezone.now(),
                            auto_image_last_status=f"{'✅' if img_result.get('success') else '❌'} {article.title[:60]}",
                        )
                        if img_result.get('success'):
                            AutomationSettings.objects.filter(pk=1).update(
                                auto_image_today_count=F('auto_image_today_count') + 1
                            )
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
                                _log_decision(pending, 'skipped_no_image',
                                    f"Auto-image generation failed: {img_result.get('error', '?')}")
                                continue
                    except Exception as e:
                        logger.error(f"[AUTO-PUBLISHER/IMAGE] ❌ Error: {e}", exc_info=True)
                elif is_youtube:
                    logger.info(f"[AUTO-PUBLISHER] 🎬 YouTube article — using video thumbnail, skipping AI image")
                
                # Update pending article status
                pending.status = 'published'
                pending.published_article = article
                pending.is_auto_published = True
                pending.reviewed_at = timezone.now()
                mode_label = 'as draft' if as_draft else 'published'
                pending.review_notes = f'Auto-{mode_label} (quality: {pending.quality_score}/10)'
                pending.save()
                
                # Log the decision
                decision = 'drafted' if as_draft else 'published'
                _log_decision(pending, decision,
                    f"Quality {pending.quality_score}/10 meets threshold {settings.auto_publish_min_quality}/10 → {mode_label}",
                    article=article)
                
                # Update counter atomically
                AutomationSettings.objects.filter(pk=1).update(
                    auto_publish_today_count=F('auto_publish_today_count') + 1
                )
                settings.refresh_from_db()
                
                published_count += 1
                logger.info(f"[AUTO-PUBLISHER] ✅ Published: {article.title[:60]} (quality: {pending.quality_score}/10)")
            else:
                # publish_article() returned None — count as failure
                pending.auto_publish_attempts += 1
                pending.auto_publish_last_error = 'publish_article() returned None'
                pending.auto_publish_last_attempt = timezone.now()
                if pending.auto_publish_attempts >= MAX_RETRIES:
                    pending.status = 'auto_failed'
                    pending.review_notes = f'Auto-publish failed {MAX_RETRIES} times: publish_article() returned None'
                    logger.warning(f"[AUTO-PUBLISHER] 🚫 CIRCUIT BREAK: {pending.title[:50]} — {MAX_RETRIES} failures, marking auto_failed")
                pending.save()
                _log_decision(pending, 'failed', f'publish_article() returned None (attempt {pending.auto_publish_attempts}/{MAX_RETRIES})')
                logger.warning(f"[AUTO-PUBLISHER] ⚠️ Publish failed for: {pending.title[:60]} (attempt {pending.auto_publish_attempts}/{MAX_RETRIES})")
                
        except Exception as e:
            # Capture FULL error details for debugging
            error_detail = f'{type(e).__name__}: {str(e) or "(empty)"}'
            tb = traceback.format_exc()
            
            pending.auto_publish_attempts += 1
            pending.auto_publish_last_error = f'{error_detail}\n{tb[-500:]}'  # Last 500 chars of traceback
            pending.auto_publish_last_attempt = timezone.now()
            if pending.auto_publish_attempts >= MAX_RETRIES:
                pending.status = 'auto_failed'
                pending.review_notes = f'Auto-publish failed {MAX_RETRIES} times: {error_detail[:200]}'
                logger.warning(f"[AUTO-PUBLISHER] 🚫 CIRCUIT BREAK: {pending.title[:50]} — {MAX_RETRIES} failures, marking auto_failed")
            pending.save()
            _log_decision(pending, 'failed', f'{error_detail[:200]} (attempt {pending.auto_publish_attempts}/{MAX_RETRIES})')
            logger.error(f"[AUTO-PUBLISHER] ❌ Error for '{pending.title[:40]}' (attempt {pending.auto_publish_attempts}/{MAX_RETRIES}): {error_detail}", exc_info=True)
            continue
    
    if published_count > 0:
        logger.info(f"[AUTO-PUBLISHER] 📝 Cycle done: {published_count} published "
                     f"(today: {settings.auto_publish_today_count}/{settings.auto_publish_max_per_day})")
    
    return published_count, f'{published_count} published'
