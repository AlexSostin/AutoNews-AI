from django.apps import AppConfig


class NewsConfig(AppConfig):
    name = 'news'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """Import signals when app is ready"""
        import news.cache_signals
        import news.signals  # Notification signals
        
        # Background tasks are now handled by Celery Beat.
        # Old scheduler (threading.Timer) is kept for reference but not called.
        # To start tasks: celery -A auto_news_site worker -l info
        #                 celery -A auto_news_site beat -l info
