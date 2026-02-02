import os
import json
import logging
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from django.conf import settings
from news.models import GSCReport, ArticleGSCStats, Article

logger = logging.getLogger('news')

class GSCService:
    def __init__(self):
        self.site_url = 'sc-domain:freshmotors.net'
        self.credentials = self._get_credentials()
        self.service = build('searchconsole', 'v1', credentials=self.credentials) if self.credentials else None

    def _get_credentials(self):
        """Load credentials from a local file or environment variable."""
        # 1. Try loading from a local file first (more stable for Docker/PEM)
        key_file_path = os.path.join(settings.BASE_DIR, 'gsc_key.json')
        if os.path.exists(key_file_path):
            try:
                return service_account.Credentials.from_service_account_file(
                    key_file_path,
                    scopes=['https://www.googleapis.com/auth/webmasters.readonly']
                )
            except Exception as e:
                logger.error(f"Failed to load GSC credentials from file {key_file_path}: {e}")

        # 2. Fallback to environment variable
        gsc_json = os.environ.get('GSC_SERVICE_ACCOUNT_JSON')
        if not gsc_json:
            logger.error("GSC_SERVICE_ACCOUNT_JSON not found in environment")
            return None
        
        try:
            # Clean up potential quote wrapping and handle escaped newlines
            gsc_json = gsc_json.strip().strip("'").strip('"')
            info = json.loads(gsc_json)
            
            if 'private_key' in info:
                # Essential for PEM loading from env vars
                info['private_key'] = info['private_key'].replace('\\n', '\n')
                
            return service_account.Credentials.from_service_account_info(
                info,
                scopes=['https://www.googleapis.com/auth/webmasters.readonly']
            )
        except Exception as e:
            logger.error(f"Failed to load GSC credentials from environment: {e}")
            return None

    def fetch_site_overview(self, start_date, end_date):
        """Fetch overall site performance"""
        if not self.service:
            return None

        request = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'dimensions': ['date']
        }

        try:
            response = self.service.searchanalytics().query(
                siteUrl=self.site_url, body=request).execute()
            return response.get('rows', [])
        except Exception as e:
            logger.error(f"Error fetching GSC site overview: {e}")
            return []

    def fetch_article_performance(self, start_date, end_date):
        """Fetch performance for all URLs"""
        if not self.service:
            return None

        request = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'dimensions': ['page', 'date'],
            'rowLimit': 5000
        }

        try:
            response = self.service.searchanalytics().query(
                siteUrl=self.site_url, body=request).execute()
            return response.get('rows', [])
        except Exception as e:
            logger.error(f"Error fetching GSC article performance: {e}")
            return []

    def sync_data(self, days=3):
        """Sync data for the last N days (GSC data is usually 2-3 days delayed)"""
        if not self.service:
            logger.error("GSC Service not initialized. Check credentials.")
            return False

        end_date = datetime.now() - timedelta(days=2)  # Most recent data
        start_date = end_date - timedelta(days=days)

        logger.info(f"Starting GSC sync from {start_date} to {end_date}")

        # 1. Sync Overall Reports
        site_data = self.fetch_site_overview(start_date, end_date)
        for row in site_data:
            date_str = row['keys'][0]
            GSCReport.objects.update_or_create(
                date=date_str,
                defaults={
                    'clicks': int(row.get('clicks', 0)),
                    'impressions': int(row.get('impressions', 0)),
                    'ctr': float(row.get('ctr', 0.0)),
                    'position': float(row.get('position', 0.0))
                }
            )

        # 2. Sync Article Stats
        article_data = self.fetch_article_performance(start_date, end_date)
        
        # Build URL to Article map for efficiency
        # Base URL: https://freshmotors.net/articles/
        site_url_base = "https://freshmotors.net/articles/"
        
        for row in article_data:
            page_url = row['keys'][0]
            date_str = row['keys'][1]
            
            if site_url_base in page_url:
                slug = page_url.replace(site_url_base, '').strip('/')
                try:
                    article = Article.objects.get(slug=slug, is_deleted=False)
                    ArticleGSCStats.objects.update_or_create(
                        article=article,
                        date=date_str,
                        defaults={
                            'clicks': int(row.get('clicks', 0)),
                            'impressions': int(row.get('impressions', 0)),
                            'ctr': float(row.get('ctr', 0.0)),
                            'position': float(row.get('position', 0.0))
                        }
                    )
                except Article.DoesNotExist:
                    continue

        return True
