
import requests
from bs4 import BeautifulSoup
import time
import logging
import re

logger = logging.getLogger(__name__)

# Try to import search backends
try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False
    logger.warning("duckduckgo_search not installed — web search will be limited")

try:
    from googlesearch import search as google_search
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

# Trusted automotive sources — prioritized in results
TRUSTED_DOMAINS = [
    'caranddriver.com', 'motortrend.com', 'topgear.com',
    'autocar.com', 'edmunds.com', 'kbb.com',
    'autoblog.com', 'carscoops.com', 'insideevs.com',
    'electrek.co', 'carnewschina.com', 'cnevpost.com',
    'byd.com', 'press.byd.com',
    'motor1.com', 'carbuzz.com', 'carexpert.com.au',
    'driving.co.uk', 'whatcar.com', 'parkers.co.uk',
    # EV spec databases — structured data with HP, kW, battery, range
    'ev-database.org', 'evspecifications.com', 'ev-database.uk',
    'zero-emission.org', 'pushevs.com',
]

# Skip these domains entirely — no useful specs data
BLOCKED_DOMAINS = [
    'youtube.com', 'reddit.com', 'pinterest.com',
    'facebook.com', 'twitter.com', 'x.com',
    'instagram.com', 'tiktok.com', 'quora.com',
    'amazon.com', 'ebay.com', 'aliexpress.com',
]

# User-Agent for requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


def _is_blocked(url: str) -> bool:
    """Check if URL is from a blocked domain."""
    return any(domain in url for domain in BLOCKED_DOMAINS)


def _is_trusted(url: str) -> bool:
    """Check if URL is from a trusted automotive source."""
    return any(domain in url for domain in TRUSTED_DOMAINS)


def _scrape_page_content(url: str, max_chars: int = 3000) -> str:
    """
    Scrape the main text content from a web page.
    Extracts text from article-like elements, strips navigation/ads.
    Returns clean text limited to max_chars.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        response.raise_for_status()

        # Only process HTML pages
        content_type = response.headers.get('content-type', '')
        if 'text/html' not in content_type:
            return ""

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove noise elements
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header',
                                   'aside', 'form', 'iframe', 'noscript',
                                   'figure', 'figcaption', 'button']):
            tag.decompose()

        # Remove common ad/nav classes
        for el in soup.find_all(class_=re.compile(
            r'(cookie|banner|popup|modal|sidebar|menu|comment|social|share|newsletter|subscribe|ad-|ads-|promo)',
            re.IGNORECASE
        )):
            el.decompose()

        # Try to find main article content first
        article_content = None
        for selector in ['article', '[role="main"]', '.article-body',
                         '.post-content', '.entry-content', '.article-content',
                         '.story-body', 'main']:
            article_content = soup.select_one(selector)
            if article_content:
                break

        # Fall back to body if no article found
        target = article_content or soup.body
        if not target:
            return ""

        # Extract text from paragraphs, headings, and list items
        text_parts = []
        for el in target.find_all(['p', 'h1', 'h2', 'h3', 'li', 'td', 'th', 'span', 'div']):
            text = el.get_text(strip=True)
            # Skip very short fragments (nav links etc.) and very long ones (embedded JSON)
            if 20 < len(text) < 1000:
                text_parts.append(text)

        full_text = '\n'.join(text_parts)

        # Truncate to max_chars
        if len(full_text) > max_chars:
            # Cut at last sentence boundary within limit
            cut = full_text[:max_chars].rfind('.')
            if cut > max_chars // 2:
                full_text = full_text[:cut + 1]
            else:
                full_text = full_text[:max_chars] + '...'

        return full_text

    except requests.exceptions.Timeout:
        logger.debug(f"Timeout scraping {url}")
        return ""
    except requests.exceptions.RequestException as e:
        logger.debug(f"Error scraping {url}: {e}")
        return ""
    except Exception as e:
        logger.debug(f"Unexpected error scraping {url}: {e}")
        return ""


def _search_ddgs(query: str, max_results: int = 8) -> list:
    """
    Search using DuckDuckGo (reliable, no rate limiting, works in Docker).
    Returns list of dicts with 'title', 'url', 'desc'.
    """
    if not HAS_DDGS:
        return []
    
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, region='wt-wt', max_results=max_results))
        
        results = []
        for r in raw_results:
            url = r.get('href', '')
            if _is_blocked(url):
                continue
            results.append({
                'title': r.get('title', ''),
                'desc': r.get('body', ''),
                'url': url,
                'trusted': _is_trusted(url),
            })
        return results
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
        return []


def _search_google(query: str, max_results: int = 8) -> list:
    """
    Search using Google (fallback — often blocked in Docker/cloud).
    Returns list of dicts with 'title', 'url', 'desc'.
    """
    if not HAS_GOOGLE:
        return []
    
    try:
        raw_results = list(google_search(query, num_results=max_results, advanced=True))
        results = []
        for r in raw_results:
            url = r.url
            if _is_blocked(url):
                continue
            results.append({
                'title': r.title,
                'desc': r.description,
                'url': url,
                'trusted': _is_trusted(url),
            })
        return results
    except Exception as e:
        logger.warning(f"Google search failed: {e}")
        return []


# Automotive relevance keywords — at least one must appear in title or description
_AUTO_KEYWORDS = re.compile(
    r'(car|vehicle|suv|sedan|hatchback|electric|ev\b|motor|drive|engine|horsepower|'
    r'hp\b|kw\b|torque|battery|range|mpg|mph|km/h|automotive|auto\b|review|specs|'
    r'specification|price|msrp|dealer|model\s|trim|hybrid|phev|bev\b|charging|'
    r'crossover|pickup|truck|coupe|convertible|wagon|minivan)',
    re.IGNORECASE
)


def _is_automotive_result(entry: dict) -> bool:
    """Check if a search result is actually about cars (not phones, forums, etc.)."""
    # Trusted automotive domains are always relevant
    if entry.get('trusted'):
        return True
    text = f"{entry.get('title', '')} {entry.get('desc', '')}".lower()
    return bool(_AUTO_KEYWORDS.search(text))


# --- Direct site search (no search engine needed) ---
# These sites have predictable search URLs and always return relevant results

DIRECT_SEARCH_SITES = [
    {
        'name': 'CNEVPost',
        'domain': 'cnevpost.com',
        'url_template': 'https://cnevpost.com/?s={query}',
        'article_selectors': ['article h2 a', 'h2.entry-title a', '.post-title a'],
    },
    {
        'name': 'InsideEVs',
        'domain': 'insideevs.com',
        'url_template': 'https://insideevs.com/search/?q={query}',
        'article_selectors': ['h3 a', 'h2 a', '.search-result a'],
    },
    {
        'name': 'Electrek',
        'domain': 'electrek.co',
        'url_template': 'https://electrek.co/?s={query}',
        'article_selectors': ['h2 a', 'h3 a', '.post-title a'],
    },
]


def _search_direct_sites(make: str, model: str, max_per_site: int = 3) -> list:
    """
    Directly search known automotive sites without a search engine.
    Much more reliable than DDG/Google for Chinese EVs.
    Returns list of dicts with 'title', 'url', 'desc', 'trusted'.
    """
    query = f"{make}+{model}".replace(' ', '+')
    results = []
    
    for site in DIRECT_SEARCH_SITES:
        url = site['url_template'].format(query=query)
        try:
            response = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
            if response.status_code != 200:
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try each selector pattern
            found_links = []
            for selector in site['article_selectors']:
                found_links.extend(soup.select(selector))
                if found_links:
                    break
            
            # Fallback: find any h2/h3 with links
            if not found_links:
                for tag in soup.find_all(['h2', 'h3']):
                    a = tag.find('a')
                    if a and a.get('href'):
                        found_links.append(a)
            
            # Filter to relevant links (must mention make or model)
            make_lower = make.lower()
            model_lower = model.lower()
            count = 0
            for a in found_links:
                if count >= max_per_site:
                    break
                title = a.get_text(strip=True)
                href = a.get('href', '')
                # Must mention the car brand or model
                text_lower = f"{title} {href}".lower()
                if (make_lower in text_lower or model_lower in text_lower) and len(title) > 15:
                    results.append({
                        'title': title,
                        'url': href if href.startswith('http') else f"https://{site['domain']}{href}",
                        'desc': f"From {site['name']} — direct site search",
                        'trusted': True,  # These are all trusted automotive sites
                    })
                    count += 1
            
            if count > 0:
                print(f"  🎯 {site['name']}: found {count} articles")
            
        except Exception as e:
            logger.debug(f"Direct search failed for {site['name']}: {e}")
            continue
    
    return results


def search_car_details(make, model, year=None):
    """
    Searches for car details and reviews on the web.
    Returns structured text with key info found, including scraped page content.
    Uses DuckDuckGo as primary (reliable), Google as fallback.
    Runs THREE diverse searches for comprehensive coverage.
    """
    year_str = str(year) if year else ''
    
    # Construct THREE diverse queries for better coverage
    # Query 1: General review with 'car' keyword to avoid brand ambiguity
    #         (e.g., "Xiaomi" alone returns phone results)
    queries = [
        f"{year_str} {make} {model} car review specifications price".strip(),
        f"{make} {model} electric car specs horsepower kW battery range".strip(),
        f"{make} {model} car hp torque 0-60 interior review".strip(),
    ]
    
    print(f"🌐 Searching web for: {make} {model} {year_str}...")
    for i, q in enumerate(queries, 1):
        print(f"  🔍 Query {i}: {q}")

    # --- Search Phase: 3 tiers ---
    all_results = []
    seen_urls = set()
    
    # Tier 1: Direct site search (most reliable, no rate limits)
    print("  🎯 Tier 1: Direct site search (cnevpost, insideevs, electrek)...")
    direct_results = _search_direct_sites(make, model)
    for r in direct_results:
        if r['url'] not in seen_urls:
            all_results.append(r)
            seen_urls.add(r['url'])
    if direct_results:
        print(f"  🎯 Direct search found {len(direct_results)} articles")
    
    # Tier 2: DuckDuckGo (works in Docker, no rate limits)
    if HAS_DDGS:
        print("  🦆 Tier 2: DuckDuckGo...")
        for q in queries:
            ddg_results = _search_ddgs(q, max_results=6)
            for r in ddg_results:
                if r['url'] not in seen_urls:
                    all_results.append(r)
                    seen_urls.add(r['url'])
        
        print(f"  🦆 DuckDuckGo found {len(all_results)} raw results")
    
    # Tier 3: Google (if nothing else returned results)
    if not all_results and HAS_GOOGLE:
        print("  🔍 Tier 3: Google fallback...")
        for q in queries[:2]:  # Only first 2 queries for Google (rate limit risk)
            google_results = _search_google(q, max_results=6)
            for r in google_results:
                if r['url'] not in seen_urls:
                    all_results.append(r)
                    seen_urls.add(r['url'])
        print(f"  🔍 Google found {len(all_results)} results")
    
    if not all_results:
        print("  ⚠️ No search results from any provider!")
        return "No relevant web results found."

    # --- Filter out non-automotive results ---
    automotive_results = [r for r in all_results if _is_automotive_result(r)]
    if automotive_results:
        print(f"  🚗 Filtered to {len(automotive_results)} automotive results (dropped {len(all_results) - len(automotive_results)} irrelevant)")
        all_results = automotive_results
    else:
        print(f"  ⚠️ No results passed automotive filter, using all {len(all_results)} results")

    # --- Prioritize trusted sources ---
    trusted = [r for r in all_results if r['trusted']]
    other = [r for r in all_results if not r['trusted']]
    prioritized = trusted + other
    prioritized = prioritized[:6]  # Take top 6

    print(f"  ✓ {len(trusted)} trusted, {len(other)} other sources (using top {len(prioritized)})")

    # --- Deep scrape top 3 pages for detailed content ---
    for i, entry in enumerate(prioritized[:3]):
        print(f"  📄 Scraping: {entry['url'][:80]}...")
        scraped = _scrape_page_content(entry['url'], max_chars=3000)
        if scraped:
            entry['scraped'] = scraped
            print(f"     ✓ Scraped {len(scraped)} chars")
        else:
            print(f"     ⚠️ No content scraped")
        # Small delay between requests
        if i < 2:
            time.sleep(0.3)

    # --- Format results ---
    search_results = []
    for entry in prioritized:
        trusted_tag = " [TRUSTED SOURCE]" if entry['trusted'] else ""
        result_text = f"Source: {entry['title']} ({entry['url']}){trusted_tag}\n"
        result_text += f"Summary: {entry['desc']}\n"

        if entry.get('scraped'):
            result_text += f"Page Content:\n{entry['scraped']}\n"

        search_results.append(result_text)

    combined = "\n---\n".join(search_results)
    print(f"  ✓ Total web context: {len(combined)} chars from {len(search_results)} sources")
    return combined


def get_web_context(specs_dict):
    """
    Helper to get context string for AI based on specs.
    """
    make = specs_dict.get('make')
    model = specs_dict.get('model')
    year = specs_dict.get('year')

    if make == 'Not specified' or model == 'Not specified':
        return ""

    results = search_car_details(make, model, year)
    return f"\n\n[WEB SEARCH RESULTS FOR CONTEXT]:\n{results}\n"


# --- Image Search for Find Photo feature ---

# Official manufacturer press/media domains (editorial use typically allowed)
_EDITORIAL_DOMAINS = [
    # Official manufacturer media sites
    'newsroom', 'press.', 'media.', 'presseportal',
    'mediaservices', 'news.', 'corporate',
    # Major auto review sites (editorial images, fair use for reviews)
    'cdn.motor1.com', 'hips.hearstapps.com', 'cdn.carbuzz.com',
    'media.autoexpress.co.uk', 'www.autocar.co.uk', 'cdn.mos.cms.futurecdn.net',
    'images.drive.com.au', 'www.topgear.com', 'www.carscoops.com',
    'images.caradisiac.com', 'www.caranddriver.com', 'www.motortrend.com',
    'electrek.co', 'cnevpost.com', 'carnewschina.com',
    # Chinese brand official media
    'byd.com', 'zeekrlife.com', 'nio.com', 'xpeng.com', 'lixiang.com',
    'gac-motor.com', 'geely.com', 'cheryinternational.com',
]

# Creative Commons / freely usable domains
_CC_DOMAINS = [
    'upload.wikimedia.org', 'commons.wikimedia.org',
    'live.staticflickr.com', 'flickr.com',
    'pixabay.com', 'unsplash.com', 'pexels.com',
]

# Domains to block for image search (social media, etc.)
_IMAGE_BLOCKED_DOMAINS = [
    'youtube.com', 'reddit.com', 'pinterest.com', 'facebook.com',
    'twitter.com', 'x.com', 'instagram.com', 'tiktok.com',
    'amazon.com', 'ebay.com', 'aliexpress.com', 'wish.com',
]


def _classify_license(image_url: str, source: str) -> str:
    """
    Classify image license based on source domain.
    Returns: 'editorial', 'cc', or 'unknown'
    """
    url_lower = image_url.lower()
    source_lower = source.lower()
    
    # Check Creative Commons sources first
    if any(d in url_lower or d in source_lower for d in _CC_DOMAINS):
        return 'cc'
    
    # Check editorial/press sources
    if any(d in url_lower or d in source_lower for d in _EDITORIAL_DOMAINS):
        return 'editorial'
    
    return 'unknown'


def _search_bing_images(query: str, max_results: int = 20) -> list:
    """
    Fallback: scrape Bing Image Search results directly.
    More reliable than DuckDuckGo API which often returns 403 in Docker.
    """
    try:
        url = f"https://www.bing.com/images/search"
        params = {
            'q': query,
            'first': 1,
            'count': max_results,
            'qft': '+filterui:imagesize-large+filterui:photo-photo',
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"Bing image search returned status {resp.status_code}")
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = []
        
        import json as _json
        
        # Bing stores image data in 'm' attribute as JSON
        for item in soup.select('a.iusc'):
            try:
                m_data = _json.loads(item.get('m', '{}'))
                image_url = m_data.get('murl', '')
                thumbnail = m_data.get('turl', '')
                title = m_data.get('t', '') or item.get('title', '')
                source = m_data.get('purl', '')
                
                if not image_url:
                    continue
                
                # Skip blocked domains
                if any(d in image_url.lower() for d in _IMAGE_BLOCKED_DOMAINS):
                    continue
                
                # Classify license
                license_type = _classify_license(image_url, source)
                
                results.append({
                    'title': title,
                    'url': image_url,
                    'thumbnail': thumbnail or image_url,
                    'source': source,
                    'width': 0,
                    'height': 0,
                    'is_press': license_type == 'editorial',
                    'license': license_type,
                })
                
                if len(results) >= max_results:
                    break
            except Exception:
                continue
        
        logger.info(f"Bing image search for '{query}': {len(results)} results")
        return results
        
    except Exception as e:
        logger.warning(f"Bing image search failed: {e}")
        return []


def _search_google_images(query: str, max_results: int = 20) -> list:
    """
    Fallback: scrape Google Image Search results.
    Last resort if both DDGS and Bing fail.
    """
    try:
        url = "https://www.google.com/search"
        params = {
            'q': query,
            'tbm': 'isch',
            'tbs': 'isz:l,itp:photo',  # Large photos only
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        
        import json as _json
        
        # Google embeds image data in script tags
        results = []
        # Try to find image URLs in the response using regex
        # Google embeds the image data in various formats
        image_matches = re.findall(r'\["(https?://[^"]+\.(?:jpg|jpeg|png|webp))',  resp.text, re.IGNORECASE)
        
        seen_urls = set()
        for img_url in image_matches:
            if img_url in seen_urls:
                continue
            seen_urls.add(img_url)
            
            # Skip blocked, Google internal, and tiny tracking pixels
            if any(d in img_url.lower() for d in _IMAGE_BLOCKED_DOMAINS):
                continue
            if 'gstatic.com' in img_url or 'google.com' in img_url:
                continue
            
            license_type = _classify_license(img_url, '')
            
            results.append({
                'title': query,
                'url': img_url,
                'thumbnail': img_url,
                'source': '',
                'width': 0,
                'height': 0,
                'is_press': license_type == 'editorial',
                'license': license_type,
            })
            
            if len(results) >= max_results:
                break
        
        logger.info(f"Google image search for '{query}': {len(results)} results")
        return results
        
    except Exception as e:
        logger.warning(f"Google image search failed: {e}")
        return []


def search_car_images(query: str, max_results: int = 20) -> list:
    """
    Search for car press photos using multiple providers with fallback.
    
    Priority:
    1. DuckDuckGo Image API (best metadata, but often 403 in Docker)
    2. Bing Image scraping (reliable, good metadata)
    3. Google Image scraping (last resort, less metadata)
    
    Args:
        query: Search query, e.g. "2025 XPeng G9 press photo"
        max_results: Maximum number of results to return
    
    Returns:
        List of dicts with: title, url, thumbnail, source, width, height,
        is_press, license ('editorial', 'cc', 'unknown')
    """
    results = []
    
    # ── Tier 1: DuckDuckGo API (best results when it works) ──
    if HAS_DDGS:
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.images(
                    query,
                    region='wt-wt',
                    safesearch='moderate',
                    size='Large',
                    type_image='photo',
                    max_results=max_results * 2,
                ))
            
            for r in raw_results:
                image_url = r.get('image', '')
                thumbnail = r.get('thumbnail', '')
                title = r.get('title', '')
                source = r.get('source', '')
                width = r.get('width', 0)
                height = r.get('height', 0)
                
                if any(d in image_url.lower() for d in _IMAGE_BLOCKED_DOMAINS):
                    continue
                if width and height and (width < 400 or height < 300):
                    continue
                
                license_type = _classify_license(image_url, source)
                results.append({
                    'title': title,
                    'url': image_url,
                    'thumbnail': thumbnail or image_url,
                    'source': source,
                    'width': width or 0,
                    'height': height or 0,
                    'is_press': license_type == 'editorial',
                    'license': license_type,
                })
                
                if len(results) >= max_results:
                    break
            
            if results:
                logger.info(f"DDGS image search for '{query}': {len(results)} results")
        except Exception as e:
            logger.warning(f"DDGS image search failed (will try Bing): {e}")
    
    # ── Tier 2: Bing Image scraping (reliable fallback) ──
    if not results:
        logger.info(f"Trying Bing Image Search for '{query}'...")
        results = _search_bing_images(query, max_results=max_results)
    
    # ── Tier 3: Google Image scraping (last resort) ──
    if not results:
        logger.info(f"Trying Google Image Search for '{query}'...")
        results = _search_google_images(query, max_results=max_results)
    
    # ── Sort: editorial first, then CC, then unknown ──
    if results:
        license_order = {'editorial': 0, 'cc': 1, 'unknown': 2}
        results.sort(key=lambda x: (license_order.get(x['license'], 2), -(x.get('width', 0) * x.get('height', 0))))
    
    logger.info(f"Image search total for '{query}': {len(results)} results")
    return results

