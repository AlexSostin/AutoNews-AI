"""
RSS Feed Discovery Module

Discovers automotive news RSS feeds from a curated list of press portals
and media sites. Validates feeds, checks licensing, and returns results.
"""

import logging
import re
import requests
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml,*/*;q=0.8',
}

# ─── Curated list of automotive press portals ───────────────────────────────
# Format: (name, website_url, known_rss_url_or_None, source_type)
CURATED_SOURCES = [
    # ─── Brand Press Portals (press releases = for media) ─────────────
    ("BMW Group PressClub", "https://www.press.bmwgroup.com", None, "brand"),
    ("Mercedes-Benz Media", "https://media.mercedes-benz.com", None, "brand"),
    ("Audi MediaCenter", "https://www.audi-mediacenter.com", None, "brand"),
    ("Volkswagen Newsroom", "https://www.volkswagen-newsroom.com", None, "brand"),
    ("Porsche Newsroom", "https://newsroom.porsche.com", None, "brand"),
    ("Toyota Newsroom", "https://pressroom.toyota.com", None, "brand"),
    ("Honda Newsroom", "https://hondanews.com", None, "brand"),
    ("Ford Media Center", "https://media.ford.com", None, "brand"),
    ("GM Newsroom", "https://news.gm.com", None, "brand"),
    ("Stellantis Media", "https://www.media.stellantis.com", None, "brand"),
    ("Hyundai Newsroom", "https://www.hyundainews.com", None, "brand"),
    ("Kia Newsroom", "https://www.kiamedia.com", None, "brand"),
    ("Nissan Newsroom", "https://usa.nissannews.com", None, "brand"),
    ("Mazda Newsroom", "https://news.mazdausa.com", None, "brand"),
    ("Subaru Media Center", "https://media.subaru.com", None, "brand"),
    ("Volvo Cars Media", "https://www.media.volvocars.com", None, "brand"),
    ("Jaguar Land Rover Media", "https://media.jaguarlandrover.com", None, "brand"),
    ("Rivian Newsroom", "https://rivian.com/newsroom", None, "brand"),
    ("Tesla", "https://www.tesla.com", None, "brand"),
    ("Lucid Motors Media", "https://lucidmotors.com/media-room", None, "brand"),
    ("BYD Global", "https://www.byd.com", None, "brand"),
    ("NIO Newsroom", "https://www.nio.com/newsroom", None, "brand"),
    ("Polestar Press", "https://www.media.polestar.com", None, "brand"),
    ("Genesis Newsroom", "https://www.genesisnewsusa.com", None, "brand"),
    ("Lamborghini Media Center", "https://www.lamborghini.com/en-en/news", None, "brand"),
    ("Ferrari Media", "https://media.ferrari.com", None, "brand"),
    
    # ─── Automotive Media (news sites with RSS) ──────────────────────
    ("Motor1.com", "https://www.motor1.com", "https://www.motor1.com/rss/news/all/", "media"),
    ("Autoblog", "https://www.autoblog.com", "https://www.autoblog.com/rss.xml", "media"),
    ("Car and Driver", "https://www.caranddriver.com", "https://www.caranddriver.com/rss/all.xml/", "media"),
    ("Road & Track", "https://www.roadandtrack.com", None, "media"),
    ("The Drive", "https://www.thedrive.com", "https://www.thedrive.com/feed", "media"),
    ("Jalopnik", "https://jalopnik.com", "https://jalopnik.com/rss", "media"),
    ("Carscoops", "https://www.carscoops.com", "https://www.carscoops.com/feed/", "media"),
    ("InsideEVs", "https://insideevs.com", "https://insideevs.com/rss/news/all/", "media"),
    ("Electrek", "https://electrek.co", "https://electrek.co/feed/", "media"),
    ("CarExpert", "https://www.carexpert.com.au", "https://www.carexpert.com.au/feed", "media"),
    ("TopGear", "https://www.topgear.com", "https://www.topgear.com/rss.xml", "media"),
    ("Autocar", "https://www.autocar.co.uk", "https://www.autocar.co.uk/rss", "media"),
    ("Automotive News", "https://www.autonews.com", None, "media"),
    ("CarNewsChina", "https://carnewschina.com", "https://carnewschina.com/feed/", "media"),
    ("CarsGuide", "https://www.carsguide.com.au", "https://www.carsguide.com.au/rss.xml", "media"),
]


def discover_feeds(check_license: bool = True) -> list:
    """
    Discover automotive RSS feeds from curated sources.
    
    Returns a list of dicts:
    {
        name, website_url, feed_url, source_type,
        feed_valid, license_status, license_details,
        already_added
    }
    """
    from news.models import RSSFeed
    
    # Get existing feed URLs for dedup
    existing_urls = set(
        RSSFeed.objects.values_list('feed_url', flat=True)
    )
    existing_websites = set(
        url.rstrip('/').lower() for url in  
        RSSFeed.objects.values_list('website_url', flat=True) if url
    )
    
    results = []
    
    for name, website_url, known_rss, source_type in CURATED_SOURCES:
        logger.info(f"Discovering: {name} ({website_url})")
        
        result = {
            'name': name,
            'website_url': website_url,
            'feed_url': None,
            'source_type': source_type,
            'feed_valid': False,
            'feed_title': '',
            'entry_count': 0,
            'license_status': 'unchecked',
            'license_details': '',
            'image_policy': 'original' if source_type == 'brand' else 'pexels_only',
            'already_added': False,
        }
        
        # Check if already added
        website_clean = website_url.rstrip('/').lower()
        if website_clean in existing_websites:
            result['already_added'] = True
        
        # Find RSS feed
        feed_url = known_rss
        if not feed_url:
            feed_url = _auto_detect_rss(website_url)
        
        if feed_url:
            result['feed_url'] = feed_url
            if feed_url in existing_urls:
                result['already_added'] = True
            
            # Validate feed
            validation = _validate_feed(feed_url)
            result['feed_valid'] = validation['valid']
            result['feed_title'] = validation.get('title', '')
            result['entry_count'] = validation.get('entry_count', 0)
        
        # Check license (if requested and feed is valid)
        if check_license and (result['feed_valid'] or source_type == 'brand'):
            try:
                from ai_engine.modules.license_checker import check_content_license
                license_result = check_content_license(website_url, source_type=source_type)
                result['license_status'] = license_result['status']
                result['license_details'] = license_result['details']
            except Exception as e:
                logger.error(f"License check failed for {name}: {e}")
                result['license_status'] = 'yellow'
                result['license_details'] = f'Check failed: {str(e)[:200]}'
        
        results.append(result)
    
    # Sort: green first, then yellow, then red; valid feeds first
    status_order = {'green': 0, 'yellow': 1, 'red': 2, 'unchecked': 3}
    results.sort(key=lambda r: (
        status_order.get(r['license_status'], 3),
        not r['feed_valid'],
        r['already_added'],
    ))
    
    return results


def _auto_detect_rss(website_url: str) -> str | None:
    """Auto-detect RSS feed from a website's HTML."""
    try:
        resp = requests.get(website_url, timeout=10, headers=HEADERS, allow_redirects=True)
        if resp.status_code != 200:
            return None
        
        # Look for RSS/Atom link tags
        patterns = [
            re.compile(r'<link[^>]+type=["\']application/rss\+xml["\'][^>]+href=["\']([^"\']+)["\']', re.IGNORECASE),
            re.compile(r'<link[^>]+href=["\']([^"\']+)["\'][^>]+type=["\']application/rss\+xml["\']', re.IGNORECASE),
            re.compile(r'<link[^>]+type=["\']application/atom\+xml["\'][^>]+href=["\']([^"\']+)["\']', re.IGNORECASE),
        ]
        
        for pattern in patterns:
            match = pattern.search(resp.text)
            if match:
                feed_url = match.group(1)
                if feed_url.startswith('/'):
                    feed_url = urljoin(website_url, feed_url)
                return feed_url
        
        # Try common RSS paths
        common_paths = ['/feed/', '/feed', '/rss', '/rss.xml', '/atom.xml', '/feed.xml']
        for path in common_paths:
            try:
                test_url = urljoin(website_url, path)
                test_resp = requests.get(test_url, timeout=5, headers={
                    'User-Agent': HEADERS['User-Agent'],
                    'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                })
                if test_resp.status_code == 200:
                    content = test_resp.text[:200].lower()
                    if '<rss' in content or '<feed' in content or '<?xml' in content:
                        return test_url
            except requests.RequestException:
                continue
        
        return None
        
    except requests.RequestException as e:
        logger.warning(f"Auto-detect RSS failed for {website_url}: {e}")
        return None


def _validate_feed(feed_url: str) -> dict:
    """Validate that a URL is a working RSS/Atom feed."""
    try:
        import feedparser
        
        resp = requests.get(feed_url, timeout=10, headers={
            'User-Agent': 'FreshMotors RSS Reader/1.0',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
        })
        
        if resp.status_code != 200:
            return {'valid': False}
        
        parsed = feedparser.parse(resp.content)
        
        if parsed.entries:
            return {
                'valid': True,
                'title': parsed.feed.get('title', ''),
                'entry_count': len(parsed.entries),
            }
        
        return {'valid': False}
        
    except Exception as e:
        logger.warning(f"Feed validation failed for {feed_url}: {e}")
        return {'valid': False}
