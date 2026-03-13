"""
IndexNow — instant search engine notification on article publish.

Notifies Bing, Yandex, Seznam, and Naver when a new article is published.
Uses a single API key stored in INDEXNOW_KEY env var (or auto-generates one).

Usage:
    from news.indexnow import notify_indexnow
    notify_indexnow('/articles/some-slug')
"""
import os
import logging
import threading
import requests

logger = logging.getLogger(__name__)

# IndexNow API key — get from env or use a static default
# You need to create a text file at /static/{INDEXNOW_KEY}.txt containing the key itself
INDEXNOW_KEY = os.getenv('INDEXNOW_KEY', 'freshmotors_indexnow_2026')
SITE_URL = os.getenv('SITE_URL', 'https://www.freshmotors.net')

# IndexNow endpoints — submit to one, all search engines get notified
INDEXNOW_ENDPOINTS = [
    'https://api.indexnow.org/indexnow',
]


def notify_indexnow(url_path: str):
    """
    Submit a URL to IndexNow for instant indexing.
    Runs in a background thread to avoid blocking the request.
    
    Args:
        url_path: relative path like '/articles/some-slug'
    """
    full_url = f"{SITE_URL.rstrip('/')}{url_path}"
    
    def _submit():
        for endpoint in INDEXNOW_ENDPOINTS:
            try:
                params = {
                    'url': full_url,
                    'key': INDEXNOW_KEY,
                }
                response = requests.get(endpoint, params=params, timeout=10)
                
                if response.status_code in (200, 202):
                    logger.info(f"[INDEXNOW] Submitted: {full_url} -> {response.status_code}")
                elif response.status_code == 422:
                    logger.warning(f"[INDEXNOW] URL not valid or key mismatch: {full_url}")
                elif response.status_code == 429:
                    logger.warning(f"[INDEXNOW] Rate limited, will retry later")
                else:
                    logger.warning(f"[INDEXNOW] Unexpected status {response.status_code}: {full_url}")
                    
            except requests.RequestException as e:
                logger.warning(f"[INDEXNOW] Failed to submit {full_url}: {e}")
    
    # Run in background thread to not block the Django request
    thread = threading.Thread(target=_submit, daemon=True)
    thread.start()


def notify_indexnow_batch(url_paths: list):
    """
    Submit multiple URLs to IndexNow in a single batch request.
    
    Args:
        url_paths: list of relative paths like ['/articles/slug1', '/articles/slug2']
    """
    if not url_paths:
        return
        
    full_urls = [f"{SITE_URL.rstrip('/')}{path}" for path in url_paths]
    
    def _submit_batch():
        try:
            payload = {
                'host': SITE_URL.replace('https://', '').replace('http://', '').rstrip('/'),
                'key': INDEXNOW_KEY,
                'urlList': full_urls,
            }
            response = requests.post(
                'https://api.indexnow.org/indexnow',
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=15,
            )
            
            if response.status_code in (200, 202):
                logger.info(f"[INDEXNOW] Batch submitted {len(full_urls)} URLs")
            else:
                logger.warning(f"[INDEXNOW] Batch status {response.status_code}")
                
        except requests.RequestException as e:
            logger.warning(f"[INDEXNOW] Batch failed: {e}")
    
    thread = threading.Thread(target=_submit_batch, daemon=True)
    thread.start()
