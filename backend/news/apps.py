from django.apps import AppConfig
import sys


class NewsConfig(AppConfig):
    name = 'news'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """Import signals and start background scheduler when app is ready."""
        import news.cache_signals
        import news.signals  # Notification signals
        
        # Start background scheduler (threading.Timer based).
        # Celery Beat is NOT running on Railway (Procfile only has web process),
        # so we need the in-process scheduler for all background tasks:
        # RSS scan, YouTube scan, auto-publish, scheduled publish, etc.
        # Skip during pytest — scheduler threads can't access test DB.
        if 'pytest' not in sys.modules:
            from news.scheduler import start_scheduler
            start_scheduler()
