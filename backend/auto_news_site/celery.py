"""
Celery application for AutoNews.

This module initializes the Celery app with Django settings,
using Redis as both broker and result backend.

Usage:
    celery -A auto_news_site worker -l info
    celery -A auto_news_site beat -l info
"""
import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')

app = Celery('auto_news_site')

# Load settings from Django settings, using CELERY_ namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks.py in all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery connectivity."""
    print(f'Request: {self.request!r}')
