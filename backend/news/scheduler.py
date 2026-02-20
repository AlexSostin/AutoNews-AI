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


def _run_gsc_sync():
    """Sync GSC data and schedule next run."""
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
    try:
        from news.services.currency_service import update_all_usd_prices
        updated, errors = update_all_usd_prices()
        logger.info(f"💱 Scheduled currency update: {updated} prices updated, {errors} errors")
    except Exception as e:
        logger.error(f"❌ Scheduled currency update error: {e}")
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
        _schedule_rss_scan(5 * 60)  # Retry in 5 min on error


def _schedule_rss_scan(interval_seconds):
    """Schedule the next RSS scan."""
    timer = threading.Timer(interval_seconds, _run_rss_scan)
    timer.daemon = True
    timer.start()


def _run_youtube_scan():
    """Scan YouTube channels if enabled in AutomationSettings."""
    try:
        from news.models import AutomationSettings, YouTubeChannel, PendingArticle, Article
        from ai_engine.modules.youtube_client import YouTubeClient
        from ai_engine.main import create_pending_article
        from django.utils import timezone
        
        settings = AutomationSettings.load()
        
        if not settings.youtube_scan_enabled:
            _schedule_youtube_scan(DISABLED_CHECK_INTERVAL)
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
            videos = client.get_latest_videos(
                channel.channel_url, 
                max_results=settings.youtube_max_videos_per_scan
            )
            if not videos:
                continue
            
            for video in videos:
                video_id = video['id']
                video_url = video['url']
                video_title = video['title']
                
                # Skip duplicates
                if Article.objects.filter(youtube_url=video_url).exists():
                    continue
                if PendingArticle.objects.filter(video_id=video_id).exists():
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
        _schedule_youtube_scan(5 * 60)


def _schedule_youtube_scan(interval_seconds):
    """Schedule the next YouTube scan."""
    timer = threading.Timer(interval_seconds, _run_youtube_scan)
    timer.daemon = True
    timer.start()


def _run_auto_publish():
    """Check for eligible pending articles and auto-publish."""
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


def _check_overdue_tasks():
    """
    Startup recovery: check if tasks are overdue and run them immediately.
    Called once shortly after server start to handle tasks that were missed
    during downtime/deploys.
    """
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
                threading.Thread(target=_run_rss_scan, daemon=True).start()
        
        # Check YouTube  
        if settings.youtube_scan_enabled and settings.youtube_last_run:
            yt_interval = timedelta(minutes=settings.youtube_scan_interval_minutes)
            if now - settings.youtube_last_run > yt_interval:
                overdue.append('youtube')
                threading.Thread(target=_run_youtube_scan, daemon=True).start()
        
        # Check Auto-publish (every 10 mins, so likely always overdue after restart)
        if settings.auto_publish_enabled:
            overdue.append('auto-publish')
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

    # Prevent double-start in dev server (autoreload spawns 2 processes)
    if os.environ.get('RUN_MAIN') == 'true' or not os.environ.get('RUN_MAIN'):
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
        
        # --- New automation tasks (only start if NOT triggered by recovery) ---
        
        # RSS scan — start after 180 seconds
        rss_timer = threading.Timer(180, _run_rss_scan)
        rss_timer.daemon = True
        rss_timer.start()
        
        # YouTube scan — start after 240 seconds
        yt_timer = threading.Timer(240, _run_youtube_scan)
        yt_timer.daemon = True
        yt_timer.start()
        
        # Auto-publish — start after 300 seconds
        ap_timer = threading.Timer(300, _run_auto_publish)
        ap_timer.daemon = True
        ap_timer.start()
