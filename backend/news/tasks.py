"""
Celery tasks for AutoNews background processing.

These tasks replace the threading.Timer-based scheduler.
Each task wraps the existing business logic from scheduler.py.

All tasks:
  1. GSC Sync (every 6h)
  2. Currency Update (daily 3:30 AM)
  3. RSS Scan (every 30 min, checks AutomationSettings)
  4. YouTube Scan (every 30 min, checks AutomationSettings + daytime)
  5. Auto Publish (every 10 min, checks AutomationSettings)
  6. Scheduled Publish (every minute)
  7. Deep Specs Backfill (every 6h)
  8. A/B Lifecycle Cleanup (daily 4 AM)
  9. Stale Error Cleanup (every 6h)
"""
import logging
from celery import shared_task
from django.db import close_old_connections

logger = logging.getLogger('news')


def _log_scheduler_error(task_name, exception, severity='error'):
    """Log task failure to BackendErrorLog for dashboard visibility."""
    try:
        import traceback as tb_module
        from django.utils import timezone
        from datetime import timedelta
        from news.models.system import BackendErrorLog

        error_class = type(exception).__name__
        message = str(exception)[:1000]
        full_tb = tb_module.format_exc()

        one_hour_ago = timezone.now() - timedelta(hours=1)
        existing = BackendErrorLog.objects.filter(
            source='celery',
            task_name=task_name,
            error_class=error_class,
            last_seen__gte=one_hour_ago,
            resolved=False,
        ).first()

        if existing:
            existing.occurrence_count += 1
            existing.message = message
            existing.traceback = full_tb
            existing.save(update_fields=['occurrence_count', 'last_seen', 'message', 'traceback'])
        else:
            BackendErrorLog.objects.create(
                source='celery',
                severity=severity,
                error_class=error_class,
                message=message,
                traceback=full_tb,
                task_name=task_name,
            )
    except Exception:
        pass


# =============================================================================
# 1. GSC Sync
# =============================================================================

@shared_task(name='news.tasks.gsc_sync', ignore_result=True)
def gsc_sync():
    """Sync Google Search Console data (every 6 hours)."""
    close_old_connections()
    try:
        from news.services.gsc_service import GSCService
        service = GSCService()
        if service.service:
            success = service.sync_data(days=7)
            if success:
                logger.info("[CELERY/GSC] Scheduled GSC sync completed successfully")
            else:
                logger.warning("[CELERY/GSC] Scheduled GSC sync returned failure")
        else:
            logger.warning("[CELERY/GSC] GSC Service not initialized — missing credentials")
    except Exception as e:
        logger.error(f"[CELERY/GSC] GSC sync error: {e}")
        _log_scheduler_error('gsc_sync', e)
    finally:
        close_old_connections()


# =============================================================================
# 2. Currency Update
# =============================================================================

@shared_task(name='news.tasks.currency_update', ignore_result=True)
def currency_update():
    """Update USD price equivalents and exchange rates (daily)."""
    close_old_connections()
    try:
        from news.services.currency_service import update_all_usd_prices
        updated, errors = update_all_usd_prices()
        logger.info(f"[CELERY/CURRENCY] Currency update: {updated} prices updated, {errors} errors")
    except Exception as e:
        logger.error(f"[CELERY/CURRENCY] Currency update error: {e}")
        _log_scheduler_error('currency_update', e)

    # Also refresh exchange rates for AI prompt injection
    try:
        from ai_engine.modules.currency_service import fetch_and_cache_rates
        fetch_and_cache_rates()
    except Exception as e:
        logger.warning(f"[CELERY/CURRENCY] Exchange rate fetch failed (non-critical): {e}")
    finally:
        close_old_connections()


# =============================================================================
# 3. RSS Scan
# =============================================================================

@shared_task(name='news.tasks.rss_scan', ignore_result=True)
def rss_scan():
    """Scan RSS feeds if enabled in AutomationSettings."""
    close_old_connections()
    try:
        from news.models import AutomationSettings, RSSFeed
        from ai_engine.modules.rss_aggregator import RSSAggregator
        from django.utils import timezone
        from django.db.models import F

        settings = AutomationSettings.load()

        if not settings.rss_scan_enabled:
            return

        if not AutomationSettings.acquire_lock('rss'):
            logger.warning("[CELERY/RSS] Skipped — another RSS scan is already running")
            return

        settings.reset_daily_counters()

        logger.info("[CELERY/RSS] Auto RSS scan starting...")
        aggregator = RSSAggregator()
        feeds = RSSFeed.objects.filter(is_enabled=True)

        total_created = 0
        for feed in feeds:
            try:
                created = aggregator.process_feed(
                    feed,
                    limit=settings.rss_max_articles_per_scan
                )
                total_created += created
            except Exception as e:
                logger.error(f"[CELERY/RSS] Feed error '{feed.name}': {e}")

        # Score newly created pending articles
        _score_new_pending_articles()

        # Update settings
        AutomationSettings.objects.filter(pk=1).update(
            rss_last_run=timezone.now(),
            rss_last_status=f"✅ {total_created} articles from {feeds.count()} feeds",
            rss_articles_today=F('rss_articles_today') + total_created
        )

        logger.info(f"[CELERY/RSS] Done: {total_created} articles from {feeds.count()} feeds")

    except Exception as e:
        logger.error(f"[CELERY/RSS] Fatal error: {e}", exc_info=True)
        _log_scheduler_error('rss_scan', e)
    finally:
        close_old_connections()


# =============================================================================
# 4. YouTube Scan
# =============================================================================

@shared_task(name='news.tasks.youtube_scan', ignore_result=True)
def youtube_scan():
    """Scan YouTube channels if enabled in AutomationSettings."""
    close_old_connections()
    try:
        from news.models import AutomationSettings, YouTubeChannel, PendingArticle, Article
        from ai_engine.modules.youtube_client import YouTubeClient
        from ai_engine.main import create_pending_article
        from django.utils import timezone
        from django.db.models import F

        settings = AutomationSettings.load()

        if not settings.youtube_scan_enabled:
            return

        # Daytime-only check
        if settings.youtube_daytime_only:
            try:
                import pytz
                israel_tz = pytz.timezone('Asia/Jerusalem')
                current_hour = timezone.now().astimezone(israel_tz).hour
            except ImportError:
                current_hour = (timezone.now().hour + 2) % 24

            start_h = settings.youtube_active_hours_start
            end_h = settings.youtube_active_hours_end
            if not (start_h <= current_hour < end_h):
                logger.info(f"[CELERY/YOUTUBE] Night skip — {current_hour}:xx Israel time "
                            f"(active: {start_h}:00-{end_h}:00)")
                settings.youtube_last_status = f"🌙 Night skip ({current_hour}:xx, active {start_h}-{end_h})"
                settings.youtube_last_run = timezone.now()
                settings.save(update_fields=['youtube_last_status', 'youtube_last_run'])
                return

        # Acquire lock
        if not AutomationSettings.acquire_lock('youtube'):
            logger.warning("[CELERY/YOUTUBE] Skipped — another YouTube scan is already running")
            return

        settings.reset_daily_counters()

        logger.info("[CELERY/YOUTUBE] Auto YouTube scan starting...")

        try:
            client = YouTubeClient()
        except Exception as e:
            logger.error(f"[CELERY/YOUTUBE] Client init failed: {e}")
            settings.youtube_last_status = f"❌ Client error: {str(e)[:100]}"
            settings.youtube_last_run = timezone.now()
            settings.save(update_fields=['youtube_last_status', 'youtube_last_run'])
            return

        channels = YouTubeChannel.objects.filter(is_enabled=True)
        total_created = 0

        for channel in channels:
            try:
                videos = client.get_latest_videos(
                    channel.channel_url,
                    max_results=settings.youtube_max_videos_per_scan
                )
                if not videos:
                    channel.last_checked = timezone.now()
                    channel.save(update_fields=['last_checked'])
                    continue
            except Exception as e:
                logger.error(f"[CELERY/YOUTUBE] Channel error '{channel.name}': {e}")
                _log_scheduler_error('youtube_scan', e, severity='warning')
                continue

            for video in videos:
                video_id = video['id']
                video_url = video['url']
                video_title = video['title']

                # Skip duplicates
                if Article.objects.filter(youtube_url=video_url).exists():
                    continue
                if video_id and PendingArticle.objects.filter(video_id=video_id).exists():
                    continue

                try:
                    result = create_pending_article(
                        youtube_url=video_url,
                        channel_id=channel.id,
                        video_title=video_title,
                        video_id=video_id
                    )

                    if result['success']:
                        total_created += 1
                        channel.last_video_id = video_id
                        channel.videos_processed += 1
                        channel.save()
                except Exception as e:
                    logger.error(f"[CELERY/YOUTUBE] Article error for '{video_title[:40]}': {e}")

            channel.last_checked = timezone.now()
            channel.save(update_fields=['last_checked'])

        # Score newly created pending articles
        _score_new_pending_articles()

        # Update settings
        AutomationSettings.objects.filter(pk=1).update(
            youtube_last_run=timezone.now(),
            youtube_last_status=f"✅ {total_created} articles from {channels.count()} channels",
            youtube_articles_today=F('youtube_articles_today') + total_created
        )

        logger.info(f"[CELERY/YOUTUBE] Done: {total_created} articles from {channels.count()} channels")

    except Exception as e:
        logger.error(f"[CELERY/YOUTUBE] Fatal error: {e}", exc_info=True)
        _log_scheduler_error('youtube_scan', e)
    finally:
        close_old_connections()


# =============================================================================
# 5. Auto Publish
# =============================================================================

@shared_task(name='news.tasks.auto_publish', ignore_result=True)
def auto_publish():
    """Check for eligible pending articles and auto-publish."""
    close_old_connections()
    try:
        from news.models import AutomationSettings
        from ai_engine.modules.auto_publisher import auto_publish_pending
        from django.utils import timezone

        settings = AutomationSettings.load()

        if not settings.auto_publish_enabled:
            return

        published, reason = auto_publish_pending()

        settings.auto_publish_last_run = timezone.now()
        settings.save(update_fields=['auto_publish_last_run'])

        if published > 0:
            logger.info(f"[CELERY/AUTO-PUBLISH] {published} articles published")

    except Exception as e:
        logger.error(f"[CELERY/AUTO-PUBLISH] Fatal error: {e}", exc_info=True)
        _log_scheduler_error('auto_publish', e)
    finally:
        close_old_connections()


# =============================================================================
# 6. Scheduled Publish (every minute)
# =============================================================================

@shared_task(name='news.tasks.scheduled_publish', ignore_result=True)
def scheduled_publish():
    """Publish articles whose scheduled_publish_at has arrived."""
    close_old_connections()
    try:
        from django.utils import timezone
        from news.models.content import Article

        now = timezone.now()
        due_articles = Article.objects.filter(
            is_published=False,
            is_deleted=False,
            scheduled_publish_at__isnull=False,
            scheduled_publish_at__lte=now,
        )

        published_count = 0
        for article in due_articles:
            try:
                meta = article.generation_metadata or {}
                meta['telegram_post'] = 'scheduled'
                article.generation_metadata = meta
                article.is_published = True
                article.scheduled_publish_at = None
                article.save(update_fields=['is_published', 'scheduled_publish_at', 'generation_metadata'])
                published_count += 1
                logger.info(f"[CELERY/SCHEDULED] Published: {article.title[:60]}")

                # Telegram auto-post
                try:
                    from news.models import AutomationSettings
                    settings = AutomationSettings.load()
                    if settings.telegram_enabled:
                        from ai_engine.modules.telegram_publisher import send_to_channel
                        tg_result = send_to_channel(article, force=True)

                        # Create SocialPost audit record
                        from news.models.system import SocialPost
                        SocialPost.objects.create(
                            article=article,
                            platform='telegram',
                            status='sent' if tg_result.get('ok') else 'failed',
                            message_text='Scheduled auto-post',
                            external_id=str(tg_result.get('result', {}).get('message_id', '')),
                            channel_id=settings.telegram_channel_id,
                            error_message=tg_result.get('description', '') if not tg_result.get('ok') else '',
                            posted_at=now if tg_result.get('ok') else None,
                        )

                        if tg_result.get('ok'):
                            settings.telegram_today_count += 1
                            settings.telegram_last_run = now
                            settings.telegram_last_status = f'Scheduled: {article.title[:60]}'
                            settings.save(update_fields=['telegram_today_count', 'telegram_last_run', 'telegram_last_status'])
                except Exception as tg_err:
                    logger.warning(f"[CELERY/SCHEDULED] Telegram post failed for '{article.title[:40]}': {tg_err}")

                # Invalidate cache
                try:
                    from news.api_views._shared import invalidate_article_cache
                    invalidate_article_cache()
                except Exception:
                    pass

            except Exception as e:
                logger.error(f"[CELERY/SCHEDULED] Failed to publish '{article.title[:40]}': {e}")
                _log_scheduler_error('scheduled_publish', e)

        if published_count > 0:
            logger.info(f"[CELERY/SCHEDULED] Published {published_count} scheduled articles")

    except Exception as e:
        logger.error(f"[CELERY/SCHEDULED] Fatal error: {e}", exc_info=True)
        _log_scheduler_error('scheduled_publish', e)
    finally:
        close_old_connections()


# =============================================================================
# 7. Deep Specs Backfill
# =============================================================================

@shared_task(name='news.tasks.deep_specs_backfill', ignore_result=True)
def deep_specs_backfill():
    """Auto-generate VehicleSpecs for published articles without them."""
    close_old_connections()
    try:
        from django.utils import timezone
        from datetime import timedelta
        from news.models import Article, VehicleSpecs, AutomationSettings

        settings = AutomationSettings.objects.first()
        if not settings or not settings.deep_specs_enabled:
            logger.info("[CELERY/DEEP-SPECS] Module disabled, skipping")
            return

        max_per_cycle = settings.deep_specs_max_per_cycle or 3
        cutoff = timezone.now() - timedelta(hours=24)

        articles_with_vehicle_specs = set(
            VehicleSpecs.objects.values_list('article_id', flat=True)
        )

        candidates = list(
            Article.objects
            .filter(
                is_published=True,
                is_deleted=False,
                created_at__lte=cutoff,
                specs__isnull=False,
            )
            .exclude(id__in=articles_with_vehicle_specs)
            .order_by('-views')[:max_per_cycle]
        )

        if not candidates:
            status_msg = "All published articles have VehicleSpecs cards"
            logger.info(f"[CELERY/DEEP-SPECS] {status_msg}")
            settings.deep_specs_last_run = timezone.now()
            settings.deep_specs_last_status = status_msg
            settings.save(update_fields=['deep_specs_last_run', 'deep_specs_last_status'])
            return

        logger.info(f"[CELERY/DEEP-SPECS] Found {len(candidates)} articles without VehicleSpecs")

        filled = 0
        for article in candidates:
            try:
                from ai_engine.modules.deep_specs import generate_deep_vehicle_specs

                specs_dict = {}
                if hasattr(article, 'specs') and article.specs:
                    car_spec = article.specs
                    specs_dict = {
                        'make': car_spec.make or '',
                        'model': car_spec.model or '',
                        'year': car_spec.release_date or '',
                        'trim': car_spec.trim or '',
                        'engine': car_spec.engine or '',
                        'horsepower': car_spec.horsepower or '',
                        'drivetrain': car_spec.drivetrain or '',
                        'price': car_spec.price or '',
                    }

                logger.info(f"[CELERY/DEEP-SPECS] Generating VehicleSpecs for [{article.id}] {article.title[:50]}")
                result = generate_deep_vehicle_specs(article, specs=specs_dict, provider='gemini')

                if result:
                    filled += 1
                    logger.info(f"[CELERY/DEEP-SPECS] Created VehicleSpecs for '{article.title[:40]}'")
                else:
                    logger.warning(f"[CELERY/DEEP-SPECS] No result for '{article.title[:40]}'")

            except Exception as e:
                logger.error(f"[CELERY/DEEP-SPECS] Error for [{article.id}]: {e}")
                continue

        status_msg = f"Filled {filled}/{len(candidates)} VehicleSpecs cards"
        logger.info(f"[CELERY/DEEP-SPECS] {status_msg}")

        settings.deep_specs_last_run = timezone.now()
        settings.deep_specs_last_status = status_msg
        settings.deep_specs_today_count = (settings.deep_specs_today_count or 0) + filled
        settings.save(update_fields=['deep_specs_last_run', 'deep_specs_last_status', 'deep_specs_today_count'])

    except Exception as e:
        logger.error(f"[CELERY/DEEP-SPECS] Fatal error: {e}", exc_info=True)
        _log_scheduler_error('deep_specs', e)
        try:
            settings = AutomationSettings.objects.first()
            if settings:
                settings.deep_specs_last_status = f"Error: {str(e)[:200]}"
                settings.save(update_fields=['deep_specs_last_status'])
        except Exception:
            pass
    finally:
        close_old_connections()


# =============================================================================
# 8. A/B Lifecycle Cleanup
# =============================================================================

@shared_task(name='news.tasks.ab_lifecycle', ignore_result=True)
def ab_lifecycle():
    """Daily A/B test lifecycle cleanup."""
    close_old_connections()
    try:
        from news.scheduler import run_ab_test_lifecycle
        result = run_ab_test_lifecycle()
        logger.info(f"[CELERY/AB] A/B lifecycle complete: {result}")
    except Exception as e:
        logger.error(f"[CELERY/AB] A/B lifecycle error: {e}", exc_info=True)
        _log_scheduler_error('ab_lifecycle', e)
    finally:
        close_old_connections()


# =============================================================================
# 9. Stale Error Cleanup
# =============================================================================

@shared_task(name='news.tasks.stale_error_cleanup', ignore_result=True)
def stale_error_cleanup():
    """Auto-resolve errors older than 24h that haven't repeated recently."""
    close_old_connections()
    try:
        from news.models.system import BackendErrorLog, FrontendEventLog
        from django.utils import timezone
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(hours=24)

        stale_backend = BackendErrorLog.objects.filter(
            resolved=False,
            last_seen__lt=cutoff,
        ).update(resolved=True, resolved_at=timezone.now(), resolution_notes='Auto-resolved: no recurrence in 24h')

        try:
            stale_frontend = FrontendEventLog.objects.filter(
                resolved=False,
                last_seen__lt=cutoff,
            ).update(resolved=True, resolved_at=timezone.now(), resolution_notes='Auto-resolved: no recurrence in 24h')
        except Exception:
            stale_frontend = 0

        total = stale_backend + stale_frontend
        if total > 0:
            logger.info(f"[CELERY/STALE-CLEANUP] Auto-resolved {total} stale errors ({stale_backend} backend, {stale_frontend} frontend)")

    except Exception as e:
        logger.warning(f"[CELERY/STALE-CLEANUP] Failed: {e}")
    finally:
        close_old_connections()


# =============================================================================
# Helper (shared with scheduler.py)
# =============================================================================

def _score_new_pending_articles():
    """Score any pending articles that don't have a quality score yet."""
    try:
        from news.models import PendingArticle
        from ai_engine.modules.quality_scorer import score_pending_article

        unscored = PendingArticle.objects.filter(
            status='pending',
            quality_score=0
        )

        for pending in unscored:
            try:
                score_pending_article(pending)
            except Exception as e:
                logger.error(f"[CELERY/SCORING] Score error for '{pending.title[:40]}': {e}")

    except Exception as e:
        logger.error(f"[CELERY/SCORING] Fatal error: {e}", exc_info=True)
        _log_scheduler_error('scoring', e)
