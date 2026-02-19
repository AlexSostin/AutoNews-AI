"""
Google Indexing API — submit article URLs for instant indexing.

Usage:
    python manage.py submit_to_google                   # Submit all articles from last 24h
    python manage.py submit_to_google --hours 48        # Submit articles from last 48h
    python manage.py submit_to_google --url https://... # Submit a specific URL
    python manage.py submit_to_google --all             # Submit all published articles

Prerequisites:
    1. Create a Service Account in Google Cloud Console
    2. Enable "Web Search Indexing API" in Google Cloud Console
    3. Add the service account email as Owner in Google Search Console
    4. Set GOOGLE_SERVICE_ACCOUNT_JSON env var with the JSON key content
       OR place the key file at /app/google-service-account.json
"""

import json
import os
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)

SITE_URL = os.environ.get('SITE_URL', 'https://www.freshmotors.net')
INDEXING_API_ENDPOINT = 'https://indexing.googleapis.com/v3/urlNotifications:publish'
BATCH_ENDPOINT = 'https://indexing.googleapis.com/batch'


def get_google_credentials():
    """Get Google service account credentials for Indexing API.
    Reuses the same GSC_SERVICE_ACCOUNT_JSON env var from Search Console integration."""
    try:
        from google.oauth2 import service_account

        SCOPES = ['https://www.googleapis.com/auth/indexing']

        # Try file first (same as gsc_service.py)
        from django.conf import settings as django_settings
        key_file = os.path.join(django_settings.BASE_DIR, 'gsc_key.json')
        if os.path.exists(key_file):
            return service_account.Credentials.from_service_account_file(key_file, scopes=SCOPES)

        # Reuse GSC_SERVICE_ACCOUNT_JSON env var (same service account, different scope)
        json_str = os.environ.get('GSC_SERVICE_ACCOUNT_JSON')
        if not json_str:
            return None

        # Same cleanup as gsc_service.py
        json_str = json_str.strip().strip("'").strip('"')
        info = json.loads(json_str)
        if 'private_key' in info:
            info['private_key'] = info['private_key'].replace('\\n', '\n')

        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

    except Exception as e:
        logger.error(f"Failed to load Google credentials: {e}")
        return None


def submit_url_to_google(url: str, action: str = 'URL_UPDATED') -> dict:
    """
    Submit a single URL to Google Indexing API.
    
    Args:
        url: Full URL to submit (e.g., https://www.freshmotors.net/articles/slug)
        action: 'URL_UPDATED' (new/updated) or 'URL_DELETED' (removed)
    
    Returns:
        dict with 'success' bool and 'response' or 'error'
    """
    credentials = get_google_credentials()
    if not credentials:
        return {'success': False, 'error': 'No Google credentials configured'}

    try:
        import requests
        from google.auth.transport.requests import Request

        # Refresh token
        credentials.refresh(Request())

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {credentials.token}',
        }

        payload = {
            'url': url,
            'type': action,
        }

        response = requests.post(INDEXING_API_ENDPOINT, json=payload, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Submitted to Google: {url} → {data.get('urlNotificationMetadata', {}).get('latestUpdate', {}).get('type', 'OK')}")
            return {'success': True, 'response': data}
        else:
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            logger.warning(f"❌ Failed to submit {url}: {error_msg}")
            return {'success': False, 'error': error_msg}

    except Exception as e:
        logger.error(f"❌ Error submitting {url}: {e}")
        return {'success': False, 'error': str(e)}


class Command(BaseCommand):
    help = 'Submit article URLs to Google Indexing API for instant indexing'

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=int, default=24, help='Submit articles published in last N hours')
        parser.add_argument('--url', type=str, help='Submit a specific URL')
        parser.add_argument('--all', action='store_true', help='Submit ALL published articles')
        parser.add_argument('--dry-run', action='store_true', help='Show URLs without submitting')

    def handle(self, *args, **options):
        from news.models import Article

        if options['url']:
            # Submit single URL
            url = options['url']
            self.stdout.write(f"Submitting: {url}")
            if not options['dry_run']:
                result = submit_url_to_google(url)
                if result['success']:
                    self.stdout.write(self.style.SUCCESS(f"✅ {url} → submitted"))
                else:
                    self.stdout.write(self.style.ERROR(f"❌ {url} → {result['error']}"))
            return

        # Get articles
        if options['all']:
            articles = Article.objects.filter(status='published').order_by('-created_at')
            self.stdout.write(f"Found {articles.count()} published articles")
        else:
            hours = options['hours']
            since = timezone.now() - timedelta(hours=hours)
            articles = Article.objects.filter(
                status='published',
                created_at__gte=since
            ).order_by('-created_at')
            self.stdout.write(f"Found {articles.count()} articles from last {hours}h")

        if not articles.exists():
            self.stdout.write(self.style.WARNING("No articles to submit"))
            return

        # Submit each article
        success_count = 0
        fail_count = 0

        for article in articles:
            url = f"{SITE_URL}/articles/{article.slug}"

            if options['dry_run']:
                self.stdout.write(f"  [DRY RUN] {url}")
                continue

            result = submit_url_to_google(url)
            if result['success']:
                success_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✅ {article.title[:60]}"))
            else:
                fail_count += 1
                self.stdout.write(self.style.ERROR(f"  ❌ {article.title[:60]} → {result['error'][:80]}"))

        if not options['dry_run']:
            self.stdout.write(f"\n{'='*50}")
            self.stdout.write(self.style.SUCCESS(f"✅ Submitted: {success_count}"))
            if fail_count:
                self.stdout.write(self.style.ERROR(f"❌ Failed: {fail_count}"))
