"""
Lightweight background scheduler for periodic tasks.
Runs inside the Django process — no separate services needed.
"""
import threading
import logging
import os

from django.db.models import F

logger = logging.getLogger('news')

# Interval: 6 hours in seconds
GSC_SYNC_INTERVAL = 6 * 60 * 60
# Interval: 7 days in seconds
CURRENCY_UPDATE_INTERVAL = 7 * 24 * 60 * 60
# Auto-publish check interval: 10 minutes
AUTO_PUBLISH_CHECK_INTERVAL = 10 * 60
# Default fallback check interval when module is disabled
DISABLED_CHECK_INTERVAL = 60  # Check again in 60s if disabled

# Track which tasks were already triggered by recovery to prevent double-fire
_recovery_triggered = set()


def _log_scheduler_error(task_name, exception, severity='error'):
    """Log scheduler task failure to BackendErrorLog for dashboard visibility."""
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
            source='scheduler',
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
                source='scheduler',
                severity=severity,
                error_class=error_class,
                message=message,
                traceback=full_tb,
                task_name=task_name,
            )
    except Exception:
        pass  # Never let error logging break the scheduler


def _run_gsc_sync():
    """Sync GSC data and schedule next run."""
    from django.db import close_old_connections
    close_old_connections()  # Release idle DB connections before starting
    try:
        from news.services.gsc_service import GSCService
        service = GSCService()
        if service.service:
            success = service.sync_data(days=7)  # Sync last 7 days
            if success:
                logger.info("✅ Scheduled GSC sync completed successfully")
            else:
                logger.warning("⚠️ Scheduled GSC sync returned failure")
        else:
            logger.warning("⚠️ GSC Service not initialized — missing credentials")
    except Exception as e:
        logger.error(f"❌ Scheduled GSC sync error: {e}")
        _log_scheduler_error('gsc_sync', e)
    finally:
        # Schedule next run
        _schedule_gsc_sync()


def _schedule_gsc_sync():
    """Schedule the next GSC sync run."""
    timer = threading.Timer(GSC_SYNC_INTERVAL, _run_gsc_sync)
    timer.daemon = True
    timer.start()


def _run_currency_update():
    """Update USD price equivalents and schedule next run."""
    from django.db import close_old_connections
    close_old_connections()
    try:
        from news.services.currency_service import update_all_usd_prices
        updated, errors = update_all_usd_prices()
        logger.info(f"💱 Scheduled currency update: {updated} prices updated, {errors} errors")
    except Exception as e:
        logger.error(f"❌ Scheduled currency update error: {e}")
        _log_scheduler_error('currency_update', e)
    finally:
        _schedule_currency_update()


def _schedule_currency_update():
    """Schedule the next currency rate update."""
    timer = threading.Timer(CURRENCY_UPDATE_INTERVAL, _run_currency_update)
    timer.daemon = True
    timer.start()


# =============================================================================
# Automation-controlled tasks (read intervals from AutomationSettings)
# =============================================================================

def _run_rss_scan():
    """Scan RSS feeds if enabled in AutomationSettings."""
    from django.db import close_old_connections
    close_old_connections()
    try:
        from news.models import AutomationSettings, RSSFeed
        from ai_engine.modules.rss_aggregator import RSSAggregator
        from django.utils import timezone
        
        settings = AutomationSettings.load()
        
        if not settings.rss_scan_enabled:
            _schedule_rss_scan(DISABLED_CHECK_INTERVAL)
            return
        
        if not AutomationSettings.acquire_lock('rss'):
            logger.warning("[SCHEDULER/RSS] ⏳ Skipped — another RSS scan is already running")
            _schedule_rss_scan(60)  # retry in 1 minute
            return
        
        settings.reset_daily_counters()
        
        logger.info("[SCHEDULER/RSS] 📡 Auto RSS scan starting...")
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
                logger.error(f"[SCHEDULER/RSS] ❌ Feed error '{feed.name}': {e}")
        
        # Score newly created pending articles
        _score_new_pending_articles()
        
        # Update settings
        AutomationSettings.objects.filter(pk=1).update(
            rss_last_run=timezone.now(),
            rss_last_status=f"✅ {total_created} articles from {feeds.count()} feeds",
            rss_articles_today=F('rss_articles_today') + total_created
        )
        settings.refresh_from_db()
        
        logger.info(f"[SCHEDULER/RSS] ✅ Done: {total_created} articles from {feeds.count()} feeds")
        
        # Schedule next run using configured interval
        _schedule_rss_scan(settings.rss_scan_interval_minutes * 60)
        
    except Exception as e:
        logger.error(f"[SCHEDULER/RSS] ❌ Fatal error: {e}", exc_info=True)
        _log_scheduler_error('rss_scan', e)
        _schedule_rss_scan(5 * 60)  # Retry in 5 min on error


def _schedule_rss_scan(interval_seconds):
    """Schedule the next RSS scan."""
    timer = threading.Timer(interval_seconds, _run_rss_scan)
    timer.daemon = True
    timer.start()


def _run_youtube_scan():
    """Scan YouTube channels if enabled in AutomationSettings."""
    from django.db import close_old_connections
    close_old_connections()
    try:
        from news.models import AutomationSettings, YouTubeChannel, PendingArticle, Article
        from ai_engine.modules.youtube_client import YouTubeClient
        from ai_engine.main import create_pending_article
        from django.utils import timezone
        
        settings = AutomationSettings.load()
        
        if not settings.youtube_scan_enabled:
            _schedule_youtube_scan(DISABLED_CHECK_INTERVAL)
            return
        
        # Daytime-only check: YouTube scans trigger AI generation (expensive).
        # Skip during night hours to save API costs and avoid generating articles
        # when nobody is awake to review them.
        if settings.youtube_daytime_only:
            try:
                import pytz
                israel_tz = pytz.timezone('Asia/Jerusalem')
                current_hour = timezone.now().astimezone(israel_tz).hour
            except ImportError:
                # Fallback: assume server is in UTC+2 (Israel winter time)
                current_hour = (timezone.now().hour + 2) % 24
            
            start_h = settings.youtube_active_hours_start
            end_h = settings.youtube_active_hours_end
            if not (start_h <= current_hour < end_h):
                logger.info(f"[SCHEDULER/YOUTUBE] 🌙 Night skip — {current_hour}:xx Israel time "
                            f"(active: {start_h}:00-{end_h}:00)")
                settings.youtube_last_status = f"🌙 Night skip ({current_hour}:xx, active {start_h}-{end_h})"
                settings.youtube_last_run = timezone.now()
                settings.save(update_fields=['youtube_last_status', 'youtube_last_run'])
                _schedule_youtube_scan(DISABLED_CHECK_INTERVAL)
                return
        
        # Acquire lock to prevent concurrent scans
        if not AutomationSettings.acquire_lock('youtube'):
            logger.warning("[SCHEDULER/YOUTUBE] ⏳ Skipped — another YouTube scan is already running")
            _schedule_youtube_scan(60)  # retry in 1 minute
            return
        
        settings.reset_daily_counters()
        
        logger.info("[SCHEDULER/YOUTUBE] 🎬 Auto YouTube scan starting...")
        
        try:
            client = YouTubeClient()
        except Exception as e:
            logger.error(f"[SCHEDULER/YOUTUBE] ❌ Client init failed: {e}")
            settings.youtube_last_status = f"❌ Client error: {str(e)[:100]}"
            settings.youtube_last_run = timezone.now()
            settings.save(update_fields=['youtube_last_status', 'youtube_last_run'])
            _schedule_youtube_scan(settings.youtube_scan_interval_minutes * 60)
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
                logger.error(f"[SCHEDULER/YOUTUBE] ❌ Channel error '{channel.name}': {e}")
                _log_scheduler_error('youtube_scan', e, severity='warning')
                continue
            
            for video in videos:
                video_id = video['id']
                video_url = video['url']
                video_title = video['title']
                
                # Skip duplicates — check both Article and PendingArticle tables
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
                    logger.error(f"[SCHEDULER/YOUTUBE] ❌ Article error for '{video_title[:40]}': {e}")
            
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
        settings.refresh_from_db()
        
        logger.info(f"[SCHEDULER/YOUTUBE] ✅ Done: {total_created} articles from {channels.count()} channels")
        
        _schedule_youtube_scan(settings.youtube_scan_interval_minutes * 60)
        
    except Exception as e:
        logger.error(f"[SCHEDULER/YOUTUBE] ❌ Fatal error: {e}", exc_info=True)
        _log_scheduler_error('youtube_scan', e)
        _schedule_youtube_scan(5 * 60)


def _schedule_youtube_scan(interval_seconds):
    """Schedule the next YouTube scan."""
    timer = threading.Timer(interval_seconds, _run_youtube_scan)
    timer.daemon = True
    timer.start()


def _run_auto_publish():
    """Check for eligible pending articles and auto-publish."""
    from django.db import close_old_connections
    close_old_connections()
    try:
        from news.models import AutomationSettings
        from ai_engine.modules.auto_publisher import auto_publish_pending
        from django.utils import timezone
        
        settings = AutomationSettings.load()
        
        if not settings.auto_publish_enabled:
            _schedule_auto_publish(DISABLED_CHECK_INTERVAL)
            return
        
        published, reason = auto_publish_pending()
        
        settings.auto_publish_last_run = timezone.now()
        settings.save(update_fields=['auto_publish_last_run'])
        
        if published > 0:
            logger.info(f"[SCHEDULER/AUTO-PUBLISH] 📝 {published} articles published")
        
        _schedule_auto_publish(AUTO_PUBLISH_CHECK_INTERVAL)
        
    except Exception as e:
        logger.error(f"[SCHEDULER/AUTO-PUBLISH] ❌ Fatal error: {e}", exc_info=True)
        _log_scheduler_error('auto_publish', e)
        _schedule_auto_publish(AUTO_PUBLISH_CHECK_INTERVAL)


def _schedule_auto_publish(interval_seconds):
    """Schedule the next auto-publish check."""
    timer = threading.Timer(interval_seconds, _run_auto_publish)
    timer.daemon = True
    timer.start()


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
                logger.error(f"[SCHEDULER/SCORING] ❌ Score error for '{pending.title[:40]}': {e}")
                
    except Exception as e:
        logger.error(f"[SCHEDULER/SCORING] ❌ Fatal error: {e}", exc_info=True)
        _log_scheduler_error('scoring', e)


# =============================================================================
# VehicleSpecs auto-backfill (reads settings from AutomationSettings)
# =============================================================================

def _run_deep_specs_backfill():
    """
    Auto-generate VehicleSpecs cards for published articles that:
    1. Are published (not draft)
    2. Have been live for >= 24 hours
    3. Don't have a VehicleSpecs card yet
    4. Have a CarSpecification (so we know make/model)
    """
    from django.db import close_old_connections
    close_old_connections()
    try:
        from django.utils import timezone
        from datetime import timedelta
        from news.models import Article, VehicleSpecs, AutomationSettings

        settings = AutomationSettings.objects.first()
        if not settings or not settings.deep_specs_enabled:
            logger.info("[SCHEDULER/DEEP-SPECS] ⏸️ Module disabled, skipping")
            _schedule_deep_specs_backfill(DISABLED_CHECK_INTERVAL)
            return

        max_per_cycle = settings.deep_specs_max_per_cycle or 3
        interval = (settings.deep_specs_interval_hours or 6) * 3600

        cutoff = timezone.now() - timedelta(hours=24)

        # Articles that are published, older than 24h, have CarSpec but no VehicleSpecs
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
            status_msg = "✅ All published articles have VehicleSpecs cards"
            logger.info(f"[SCHEDULER/DEEP-SPECS] {status_msg}")
            settings.deep_specs_last_run = timezone.now()
            settings.deep_specs_last_status = status_msg
            settings.save(update_fields=['deep_specs_last_run', 'deep_specs_last_status'])
            _schedule_deep_specs_backfill(interval)
            return

        logger.info(f"[SCHEDULER/DEEP-SPECS] 🔍 Found {len(candidates)} articles without VehicleSpecs")
        
        filled = 0
        for article in candidates:
            try:
                from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
                
                # Get existing CarSpecification for context
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
                
                logger.info(f"[SCHEDULER/DEEP-SPECS] ⚙️ Generating VehicleSpecs for [{article.id}] {article.title[:50]}")
                result = generate_deep_vehicle_specs(article, specs=specs_dict, provider='gemini')
                
                if result:
                    filled += 1
                    logger.info(f"[SCHEDULER/DEEP-SPECS] ✅ Created VehicleSpecs for '{article.title[:40]}'")
                else:
                    logger.warning(f"[SCHEDULER/DEEP-SPECS] ⚠️ No result for '{article.title[:40]}'")
                    
            except Exception as e:
                logger.error(f"[SCHEDULER/DEEP-SPECS] ❌ Error for [{article.id}]: {e}")
                continue
        
        status_msg = f"Filled {filled}/{len(candidates)} VehicleSpecs cards"
        logger.info(f"[SCHEDULER/DEEP-SPECS] 📊 {status_msg}")
        
        # Update settings
        settings.deep_specs_last_run = timezone.now()
        settings.deep_specs_last_status = status_msg
        settings.deep_specs_today_count = (settings.deep_specs_today_count or 0) + filled
        settings.save(update_fields=['deep_specs_last_run', 'deep_specs_last_status', 'deep_specs_today_count'])

    except Exception as e:
        logger.error(f"[SCHEDULER/DEEP-SPECS] ❌ Fatal error: {e}", exc_info=True)
        _log_scheduler_error('deep_specs', e)
        try:
            settings = AutomationSettings.objects.first()
            if settings:
                settings.deep_specs_last_status = f"❌ Error: {str(e)[:200]}"
                settings.save(update_fields=['deep_specs_last_status'])
        except Exception:
            pass
    
    # Re-read interval for scheduling
    try:
        settings = AutomationSettings.objects.first()
        interval = (settings.deep_specs_interval_hours or 6) * 3600 if settings else 6 * 3600
    except Exception:
        interval = 6 * 3600
    _schedule_deep_specs_backfill(interval)


def _schedule_deep_specs_backfill(interval_seconds=None):
    """Schedule the next deep specs backfill."""
    if interval_seconds is None:
        interval_seconds = 6 * 3600
    timer = threading.Timer(interval_seconds, _run_deep_specs_backfill)
    timer.daemon = True
    timer.start()



def run_ab_test_lifecycle():
    """
    Daily A/B test lifecycle cleanup.

    Lifecycle:
      day 0-29:   test runs normally
      day 30-36:  no winner yet → AdminNotification warning (once per week)
      day 37+:    still no winner → auto-pick by CTR, delete losers
      any day 30+: winner exists → delete losers
    """
    from django.utils import timezone
    from datetime import timedelta
    from news.models import ArticleTitleVariant, AdminNotification

    now = timezone.now()
    cutoff_30 = now - timedelta(days=30)
    cutoff_37 = now - timedelta(days=37)

    deleted_loser_sets = 0
    warned_articles = 0
    force_picked = 0

    old_article_ids = (
        ArticleTitleVariant.objects
        .filter(created_at__lte=cutoff_30)
        .values_list('article_id', flat=True)
        .distinct()
    )

    for article_id in old_article_ids:
        variants = list(ArticleTitleVariant.objects.filter(article_id=article_id))
        if not variants:
            continue

        winner = next((v for v in variants if v.is_winner), None)
        oldest = min(v.created_at for v in variants)

        if winner:
            # Winner exists — clean up losers
            losers = ArticleTitleVariant.objects.filter(article_id=article_id, is_winner=False)
            if losers.exists():
                losers.delete()
                deleted_loser_sets += 1
        else:
            if oldest <= cutoff_37:
                # 37+ days: force auto-pick then clean up
                ArticleTitleVariant.check_and_pick_winners()
                ArticleTitleVariant.objects.filter(article_id=article_id, is_winner=False).delete()
                force_picked += 1
            elif oldest <= cutoff_30:
                # 30-36 days: send one-per-week warning
                week_ago = now - timedelta(days=7)
                already_warned = AdminNotification.objects.filter(
                    link__contains=f'article={article_id}',
                    created_at__gte=week_ago,
                ).exists()
                if not already_warned:
                    try:
                        from news.models import Article
                        title = Article.objects.get(pk=article_id).title[:60]
                    except Exception:
                        title = f'Article #{article_id}'
                    AdminNotification.create_notification(
                        notification_type='warning',
                        title='⚠️ A/B Test needs a winner',
                        message=(
                            f'"{title}" has an A/B test running 30+ days with no winner. '
                            f'Auto-cleanup in 7 days — pick a winner now or it will be auto-selected by CTR.'
                        ),
                        link=f'/admin/ab-testing?article={article_id}',
                        priority='high',
                    )
                    warned_articles += 1

    logger.info(
        f'[ab-lifecycle] ✅ Cleaned: {deleted_loser_sets}, '
        f'Warned: {warned_articles}, Force-picked: {force_picked}'
    )
    return {'deleted_loser_sets': deleted_loser_sets, 'warned_articles': warned_articles, 'force_picked': force_picked}


def _run_ab_lifecycle_daily():
    """Scheduler wrapper — runs A/B lifecycle daily."""
    try:
        run_ab_test_lifecycle()
    except Exception as e:
        _log_scheduler_error('ab_lifecycle', e)
    timer = threading.Timer(24 * 3600, _run_ab_lifecycle_daily)
    timer.daemon = True
    timer.start()


def _check_overdue_tasks():
    """
    Startup recovery: check if tasks are overdue and run them immediately.
    Called once shortly after server start to handle tasks that were missed
    during downtime/deploys.
    """
    global _recovery_triggered
    try:
        from news.models import AutomationSettings
        from django.utils import timezone
        from datetime import timedelta
        
        settings = AutomationSettings.load()
        now = timezone.now()
        
        # Clear any stale locks from a previous crash
        AutomationSettings.objects.filter(pk=1).update(
            rss_lock=False, rss_lock_at=None,
            youtube_lock=False, youtube_lock_at=None,
            auto_publish_lock=False, auto_publish_lock_at=None,
            score_lock=False, score_lock_at=None,
        )
        logger.info("[SCHEDULER] 🔓 Cleared stale locks from previous session")
        
        overdue = []
        
        # Check RSS
        if settings.rss_scan_enabled and settings.rss_last_run:
            rss_interval = timedelta(minutes=settings.rss_scan_interval_minutes)
            if now - settings.rss_last_run > rss_interval:
                overdue.append('rss')
                _recovery_triggered.add('rss')
                threading.Thread(target=_run_rss_scan, daemon=True).start()
        
        # Check YouTube  
        if settings.youtube_scan_enabled and settings.youtube_last_run:
            yt_interval = timedelta(minutes=settings.youtube_scan_interval_minutes)
            if now - settings.youtube_last_run > yt_interval:
                overdue.append('youtube')
                _recovery_triggered.add('youtube')
                threading.Thread(target=_run_youtube_scan, daemon=True).start()
        
        # Check Auto-publish (every 10 mins, so likely always overdue after restart)
        if settings.auto_publish_enabled:
            overdue.append('auto-publish')
            _recovery_triggered.add('auto-publish')
            threading.Thread(target=_run_auto_publish, daemon=True).start()
        
        if overdue:
            logger.info(f"[SCHEDULER] 🔄 Startup recovery: triggered overdue tasks: {', '.join(overdue)}")
        else:
            logger.info("[SCHEDULER] ✅ Startup recovery: no overdue tasks found")
            
    except Exception as e:
        logger.error(f"[SCHEDULER] ❌ Startup recovery error: {e}", exc_info=True)


def start_scheduler():
    """
    Start background scheduler. Called once from AppConfig.ready().
    Only runs in the main process (not in management commands or migrations).
    """
    # Don't run in management commands (migrate, collectstatic, etc.)
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in ('migrate', 'makemigrations', 'collectstatic', 'createsuperuser', 'shell', 'test'):
        return

    # Prevent double-start in dev server (autoreload spawns parent + child processes)
    # In runserver: parent has RUN_MAIN=None, child has RUN_MAIN='true'
    # In production (gunicorn/uwsgi): RUN_MAIN is never set, no autoreload
    is_runserver = any('runserver' in arg for arg in sys.argv)
    if is_runserver and os.environ.get('RUN_MAIN') != 'true':
        # Parent process of autoreload — skip, child will handle it
        return

    logger.info("🕐 Starting background scheduler (GSC 6h, currency 7d, RSS/YouTube/auto-publish from settings)")
    
    # --- Startup recovery: check for overdue tasks ---
    recovery_timer = threading.Timer(30, _check_overdue_tasks)
    recovery_timer.daemon = True
    recovery_timer.start()
    
    # --- Existing tasks ---
    
    # Run first GSC sync after 60 seconds (let app finish starting)
    initial_timer = threading.Timer(60, _run_gsc_sync)
    initial_timer.daemon = True
    initial_timer.start()
    
    # Run first currency update after 120 seconds
    currency_timer = threading.Timer(120, _run_currency_update)
    currency_timer.daemon = True
    currency_timer.start()
    
    # --- Automation tasks: only start if NOT already triggered by recovery ---
    # Recovery runs at +30s. These timers fire at +180/240/300s.
    # If recovery already triggered a task, the scheduled timer skips it
    # and lets the recovery-triggered task handle rescheduling.
    
    def _start_rss_if_not_recovered():
        if 'rss' not in _recovery_triggered:
            _run_rss_scan()
        else:
            logger.info("[SCHEDULER] ⏭️ Skipping scheduled RSS — already triggered by recovery")
    
    def _start_youtube_if_not_recovered():
        if 'youtube' not in _recovery_triggered:
            _run_youtube_scan()
        else:
            logger.info("[SCHEDULER] ⏭️ Skipping scheduled YouTube — already triggered by recovery")
    
    def _start_auto_publish_if_not_recovered():
        if 'auto-publish' not in _recovery_triggered:
            _run_auto_publish()
        else:
            logger.info("[SCHEDULER] ⏭️ Skipping scheduled auto-publish — already triggered by recovery")
    
    # RSS scan — start after 180 seconds (if not already recovered)
    rss_timer = threading.Timer(180, _start_rss_if_not_recovered)
    rss_timer.daemon = True
    rss_timer.start()
    
    # YouTube scan — start after 240 seconds (if not already recovered)
    yt_timer = threading.Timer(240, _start_youtube_if_not_recovered)
    yt_timer.daemon = True
    yt_timer.start()
    
    # Auto-publish — start after 300 seconds (if not already recovered)
    ap_timer = threading.Timer(300, _start_auto_publish_if_not_recovered)
    ap_timer.daemon = True
    ap_timer.start()
    
    # VehicleSpecs auto-backfill — start after 360 seconds
    deep_specs_timer = threading.Timer(360, _run_deep_specs_backfill)
    deep_specs_timer.daemon = True
    deep_specs_timer.start()

    # Auto-resolve stale errors — start after 600 seconds, then every 6 hours
    stale_timer = threading.Timer(600, _auto_resolve_stale_errors)
    stale_timer.daemon = True
    stale_timer.start()

    # A/B test lifecycle cleanup — runs once daily, first fire after 5 minutes
    ab_lifecycle_timer = threading.Timer(5 * 60, _run_ab_lifecycle_daily)
    ab_lifecycle_timer.daemon = True
    ab_lifecycle_timer.start()
    logger.info("[SCHEDULER] 🧹 A/B lifecycle cleanup scheduled (daily)")


def _auto_resolve_stale_errors():
    """Auto-resolve errors older than 24h that haven't repeated recently."""
    try:
        from news.models.system import BackendErrorLog, FrontendEventLog
        from django.utils import timezone
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(hours=24)

        # Resolve stale backend errors
        stale_backend = BackendErrorLog.objects.filter(
            resolved=False,
            last_seen__lt=cutoff,
        ).update(resolved=True, resolved_at=timezone.now(), resolution_notes='Auto-resolved: no recurrence in 24h')

        # Resolve stale frontend errors
        try:
            stale_frontend = FrontendEventLog.objects.filter(
                resolved=False,
                last_seen__lt=cutoff,
            ).update(resolved=True, resolved_at=timezone.now(), resolution_notes='Auto-resolved: no recurrence in 24h')
        except Exception:
            stale_frontend = 0

        total = stale_backend + stale_frontend
        if total > 0:
            logger.info(f"[SCHEDULER/STALE-CLEANUP] ✅ Auto-resolved {total} stale errors ({stale_backend} backend, {stale_frontend} frontend)")

    except Exception as e:
        logger.warning(f"[SCHEDULER/STALE-CLEANUP] ⚠️ Failed: {e}")
    finally:
        # Reschedule every 6 hours
        next_timer = threading.Timer(6 * 3600, _auto_resolve_stale_errors)
        next_timer.daemon = True
        next_timer.start()
