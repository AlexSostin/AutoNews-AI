from django.apps import AppConfig


class NewsConfig(AppConfig):
    name = 'news'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """Import signals when app is ready"""
        import news.cache_signals
        import news.signals  # Notification signals
        
        # Start background scheduler (GSC sync, etc.)
        from news.scheduler import start_scheduler
        start_scheduler()
