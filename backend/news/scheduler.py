"""
Lightweight background scheduler for periodic tasks.
Runs inside the Django process — no separate services needed.
"""
import threading
import logging
import os

logger = logging.getLogger('news')

# Interval: 6 hours in seconds
GSC_SYNC_INTERVAL = 6 * 60 * 60


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
        logger.info("🕐 Starting background scheduler (GSC sync every 6 hours)")
        
        # Run first sync after 60 seconds (let app finish starting)
        initial_timer = threading.Timer(60, _run_gsc_sync)
        initial_timer.daemon = True
        initial_timer.start()
