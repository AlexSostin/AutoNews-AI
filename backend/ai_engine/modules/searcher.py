
import requests
from googlesearch import search
from bs4 import BeautifulSoup
import time
import random
import logging
import re

logger = logging.getLogger(__name__)

# Trusted automotive sources — prioritized in results
TRUSTED_DOMAINS = [
    'caranddriver.com', 'motortrend.com', 'topgear.com',
    'autocar.com', 'edmunds.com', 'kbb.com',
    'autoblog.com', 'carscoops.com', 'insideevs.com',
    'electrek.co', 'carnewschina.com', 'cnevpost.com',
    'byd.com', 'press.byd.com',
    'motor1.com', 'carbuzz.com', 'carexpert.com.au',
    'driving.co.uk', 'whatcar.com', 'parkers.co.uk',
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


def search_car_details(make, model, year=None):
    """
    Searches for car details and reviews on the web.
    Returns structured text with key info found, including scraped page content.
    """
    # Construct query
    query = f"{year if year else ''} {make} {model} specs review price release date".strip()
    print(f"🌐 Searching web for: {query}...")

    search_results = []
    trusted_results = []
    other_results = []

    try:
        # Search Google (gets top 8 URLs for better coverage)
        urls = list(search(query, num_results=8, advanced=True))

        for result in urls:
            try:
                title = result.title
                desc = result.description
                url = result.url

                # Skip blocked domains
                if _is_blocked(url):
                    continue

                entry = {
                    'title': title,
                    'desc': desc,
                    'url': url,
                    'trusted': _is_trusted(url),
                }

                if entry['trusted']:
                    trusted_results.append(entry)
                else:
                    other_results.append(entry)

            except Exception:
                continue

        # Prioritize trusted sources, then others — take up to 4 total
        prioritized = trusted_results + other_results
        prioritized = prioritized[:4]

        if not prioritized:
            return "No relevant web results found."

        # Deep scrape top 2 pages for detailed content
        for i, entry in enumerate(prioritized[:2]):
            print(f"  📄 Scraping: {entry['url'][:80]}...")
            scraped = _scrape_page_content(entry['url'], max_chars=2500)
            if scraped:
                entry['scraped'] = scraped
            # Small delay between requests
            if i == 0 and len(prioritized) > 1:
                time.sleep(0.5)

        # Format results
        for entry in prioritized:
            trusted_tag = " [TRUSTED SOURCE]" if entry['trusted'] else ""
            result_text = f"Source: {entry['title']} ({entry['url']}){trusted_tag}\n"
            result_text += f"Summary: {entry['desc']}\n"

            if entry.get('scraped'):
                result_text += f"Page Content:\n{entry['scraped']}\n"

            search_results.append(result_text)

        return "\n---\n".join(search_results)

    except Exception as e:
        print(f"⚠️ Search failed: {e}")
        logger.error(f"Web search failed for '{query}': {e}")
        return f"Web search failed: {str(e)}"


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
