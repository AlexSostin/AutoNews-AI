
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

    # --- Search Phase: DuckDuckGo primary, Google fallback ---
    all_results = []
    seen_urls = set()
    
    # Primary: DuckDuckGo (works in Docker, no rate limits)
    if HAS_DDGS:
        print("  🦆 Using DuckDuckGo...")
        for q in queries:
            ddg_results = _search_ddgs(q, max_results=6)
            for r in ddg_results:
                if r['url'] not in seen_urls:
                    all_results.append(r)
                    seen_urls.add(r['url'])
        
        print(f"  🦆 DuckDuckGo found {len(all_results)} raw results")
    
    # Fallback: Google (if DuckDuckGo returned nothing)
    if not all_results and HAS_GOOGLE:
        print("  🔍 DuckDuckGo empty, trying Google fallback...")
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
