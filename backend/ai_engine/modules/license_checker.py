"""
Content License Checker for RSS Feed Sources

Multi-step verification:
1. Check robots.txt
2. Detect if site is a press/media portal (press releases = meant for media)
3. Find Terms of Use page (standard paths + footer link scraping)
4. AI analysis of ToS text via Gemini

Returns a status: green (free to use), yellow (caution), red (restricted).
"""

import logging
import re
import requests
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)

# Common paths where Terms of Use pages are found
TOS_PATHS = [
    '/terms-of-use',
    '/terms-of-service',
    '/terms',
    '/tos',
    '/legal',
    '/legal/terms',
    '/terms-and-conditions',
    '/copyright',
    '/content-policy',
    '/usage-policy',
    '/legal-notice',
    '/imprint',
    '/disclaimer',
]

# Keywords that indicate a press/media portal
PRESS_PORTAL_KEYWORDS = [
    'press release', 'press releases', 'media release', 'media releases',
    'newsroom', 'press room', 'pressroom', 'media center', 'media centre',
    'press office', 'for journalists', 'for media', 'media kit',
    'press kit', 'press contact', 'media contact', 'corporate communications',
    'editorial use', 'media use only', 'press information',
]

# URL patterns that suggest press portals
PRESS_URL_PATTERNS = [
    'press.', 'media.', 'newsroom.', 'news.',
    '/press/', '/media/', '/newsroom/', '/pressroom/',
    '/corporate/', '/press-releases/', '/media-releases/',
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
}

AI_TOS_PROMPT = """You are a legal content analyst specializing in digital media rights.

Analyze the following Terms of Use / Legal page from a website. Determine whether a news aggregator can:
1. Read their RSS feeds
2. Summarize their articles with attribution and link back
3. Use their press releases as source material

KEY LEGAL CONTEXT:
- RSS feeds are PUBLIC by design — publishing an RSS feed is an implicit invitation to syndicate
- Press releases are created FOR media distribution — using them is expected
- "All rights reserved" is standard boilerplate and does NOT prohibit RSS reading or summarization with attribution
- Only EXPLICIT prohibitions matter: "no scraping", "no republishing", "no automated access"
- Fair use / fair dealing allows summarization with attribution in most jurisdictions

Respond ONLY with valid JSON:
{
    "status": "green|yellow|red",
    "summary": "2-3 sentence explanation",
    "allows_rss_syndication": true/false/null,
    "allows_content_reuse_with_attribution": true/false/null,
    "requires_attribution": true/false/null,
    "key_restrictions": ["only list EXPLICIT restrictions found in the text"]
}

Status guide:
- "green" = No explicit prohibition. RSS feeds are public. Standard boilerplate only.
- "yellow" = Some restrictions mentioned but unclear if they apply to RSS/summarization.
- "red" = EXPLICITLY prohibits scraping, republishing, or automated access.

TEXT TO ANALYZE:
{tos_text}"""

AI_HOMEPAGE_PROMPT = """Analyze this website text. Is this a press/media portal designed for journalists and media outlets?

Look for indicators:
- Press releases, media releases, news releases
- "For journalists", "Media center", "Press office"
- Corporate communications content
- Photographer credits suggesting editorial use

Respond ONLY with valid JSON:
{
    "is_press_portal": true/false,
    "confidence": "high|medium|low",
    "evidence": "brief explanation of what you found"
}

WEBSITE TEXT (first 2000 chars):
{homepage_text}"""


def check_content_license(website_url: str, source_type: str = 'media') -> dict:
    """
    Check content licensing status for a website.
    
    Args:
        website_url: The main website URL
        source_type: 'brand', 'media', or 'blog' — affects detection logic
    
    Returns:
        dict with keys: status, details, robots_ok, tos_found, tos_url, safety_checks
    """
    safety_checks = {}
    
    if not website_url:
        return {
            'status': 'yellow',
            'details': 'No website URL provided — cannot check content license.',
            'robots_ok': None,
            'tos_found': False,
            'tos_url': None,
            'safety_checks': {
                'robots_txt': {'passed': False, 'detail': 'No URL provided'},
                'press_portal': {'passed': False, 'detail': 'No URL provided'},
                'tos_analysis': {'passed': False, 'detail': 'No URL provided'},
                'image_rights': {'passed': False, 'detail': 'No URL provided'},
            },
        }
    
    parsed = urlparse(website_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    details_parts = []
    statuses = []
    
    # ─── Step 1: Check robots.txt ─────────────────────────────
    robots_result = _check_robots_txt(base_url)
    statuses.append(robots_result['status'])
    details_parts.append(f"🤖 robots.txt: {robots_result['summary']}")
    safety_checks['robots_txt'] = {
        'passed': robots_result['status'] != 'red',
        'detail': robots_result['summary'],
    }
    
    # ─── Step 2: Detect press portal ─────────────────────────
    press_result = _detect_press_portal(website_url, source_type)
    if press_result['is_press_portal']:
        statuses.append('green')
        details_parts.append(f"📰 Press portal detected: {press_result['evidence']}")
    safety_checks['press_portal'] = {
        'passed': press_result['is_press_portal'],
        'detail': press_result['evidence'] or 'Not a detected press portal',
    }
    
    # ─── Step 3: Find and analyze ToS ────────────────────────
    tos_result = _find_tos_page(base_url)
    tos_text_for_image_check = None
    
    if tos_result['found'] and tos_result['text']:
        details_parts.append(f"📄 ToS: {tos_result['url']}")
        ai_result = _analyze_tos_with_ai(tos_result['text'])
        statuses.append(ai_result.get('status', 'yellow'))
        details_parts.append(f"🔍 Analysis: {ai_result.get('summary', 'N/A')}")
        tos_text_for_image_check = tos_result['text']
        
        if ai_result.get('key_restrictions'):
            restrictions = [r for r in ai_result['key_restrictions'] if r]
            if restrictions:
                details_parts.append(f"⚠️ Restrictions: {', '.join(restrictions)}")
        
        safety_checks['tos_analysis'] = {
            'passed': ai_result.get('status') in ('green', None),
            'detail': ai_result.get('summary', 'Analysis complete'),
        }
    else:
        details_parts.append("📄 ToS: Not found at standard paths")
        if not press_result['is_press_portal']:
            homepage_result = _analyze_homepage(website_url)
            if homepage_result and homepage_result.get('is_press_portal'):
                statuses.append('green')
                details_parts.append(f"🔍 Homepage analysis: Press portal ({homepage_result.get('evidence', '')})")
                safety_checks['tos_analysis'] = {
                    'passed': True,
                    'detail': f"No ToS, but homepage confirms press portal: {homepage_result.get('evidence', '')}",
                }
            else:
                statuses.append('yellow')
                details_parts.append("🔍 No ToS found, not a detected press portal — caution")
                safety_checks['tos_analysis'] = {
                    'passed': False,
                    'detail': 'No Terms of Service found and not a press portal',
                }
        else:
            safety_checks['tos_analysis'] = {
                'passed': True,
                'detail': 'No ToS needed — press portal (content is for media use)',
            }
    
    # ─── Step 4: Image Rights Check ──────────────────────────
    image_rights_result = _check_image_rights(
        tos_text=tos_text_for_image_check,
        is_press_portal=press_result['is_press_portal'],
        source_type=source_type,
    )
    safety_checks['image_rights'] = image_rights_result
    if image_rights_result['passed']:
        details_parts.append(f"📷 Images: {image_rights_result['detail']}")
    else:
        details_parts.append(f"📷 Images: ⚠️ {image_rights_result['detail']}")
    
    # ─── Final Status ────────────────────────────────────────
    if press_result['is_press_portal'] and 'red' not in statuses:
        final_status = 'green'
    else:
        final_status = _combine_statuses(*statuses) if statuses else 'yellow'
    
    return {
        'status': final_status,
        'details': '\n'.join(details_parts),
        'robots_ok': robots_result['status'] != 'red',
        'tos_found': tos_result['found'],
        'tos_url': tos_result.get('url'),
        'safety_checks': safety_checks,
    }


def _check_robots_txt(base_url: str) -> dict:
    """Check robots.txt for scraping restrictions."""
    robots_url = f"{base_url}/robots.txt"
    
    try:
        resp = requests.get(robots_url, timeout=10, headers=HEADERS)
        if resp.status_code != 200:
            return {'status': 'green', 'summary': 'No robots.txt (no restrictions)'}
        
        content = resp.text.lower()
        lines = content.split('\n')
        current_agent = None
        has_blanket_disallow = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('user-agent:'):
                current_agent = line.split(':', 1)[1].strip()
            elif line.startswith('disallow:') and current_agent == '*':
                path = line.split(':', 1)[1].strip()
                if path == '/':
                    has_blanket_disallow = True
        
        if has_blanket_disallow:
            return {'status': 'red', 'summary': 'Blocks all crawlers (Disallow: /)'}
        
        return {'status': 'green', 'summary': 'Allows crawling'}
        
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch robots.txt from {base_url}: {e}")
        return {'status': 'green', 'summary': 'Could not fetch (assuming OK)'}


def _detect_press_portal(url: str, source_type: str) -> dict:
    """Detect if this is a press/media portal based on URL patterns and source type."""
    url_lower = url.lower()
    
    # Check URL patterns
    for pattern in PRESS_URL_PATTERNS:
        if pattern in url_lower:
            return {
                'is_press_portal': True,
                'evidence': f'URL contains "{pattern}" — press/media portal',
            }
    
    # Brand source type = likely press portal
    if source_type == 'brand':
        return {
            'is_press_portal': True,
            'evidence': 'Source type is "brand" — official press releases are meant for media use',
        }
    
    return {'is_press_portal': False, 'evidence': ''}


def _find_tos_page(base_url: str) -> dict:
    """Find ToS page via standard paths AND footer link scraping."""
    
    # Method 1: Try standard paths
    for path in TOS_PATHS:
        url = urljoin(base_url, path)
        try:
            resp = requests.get(url, timeout=8, headers=HEADERS, allow_redirects=True)
            if resp.status_code == 200 and len(resp.text) > 500:
                lower_text = resp.text.lower()
                # Skip soft 404 pages
                if 'not found' not in lower_text[:500] and '404' not in lower_text[:500]:
                    text = _strip_html(resp.text)
                    if len(text) > 200:
                        return {'found': True, 'url': url, 'text': text[:5000]}
        except requests.RequestException:
            continue
    
    # Method 2: Scrape homepage for ToS links in footer
    try:
        resp = requests.get(base_url, timeout=10, headers=HEADERS, allow_redirects=True)
        if resp.status_code == 200:
            # Find links with terms/legal/copyright in href or text
            link_pattern = re.compile(
                r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*(?:terms|legal|copyright|privacy|disclaimer|imprint)[^<]*)</a>',
                re.IGNORECASE
            )
            matches = link_pattern.findall(resp.text)
            
            for href, _text in matches:
                if href.startswith('/'):
                    tos_url = urljoin(base_url, href)
                elif href.startswith('http'):
                    tos_url = href
                else:
                    continue
                
                try:
                    tos_resp = requests.get(tos_url, timeout=8, headers=HEADERS, allow_redirects=True)
                    if tos_resp.status_code == 200:
                        text = _strip_html(tos_resp.text)
                        if len(text) > 200:
                            return {'found': True, 'url': tos_url, 'text': text[:5000]}
                except requests.RequestException:
                    continue
    except requests.RequestException:
        pass
    
    return {'found': False, 'url': None, 'text': None}


def _strip_html(html: str) -> str:
    """Strip HTML tags for text extraction."""
    text = re.sub(r'<(script|style|nav|header|footer)[^>]*>[\s\S]*?</\1>', '', html, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _analyze_tos_with_ai(tos_text: str) -> dict:
    """Use Gemini to analyze Terms of Use text."""
    import json
    
    try:
        from ai_engine.modules.ai_provider import get_ai_provider
        provider = get_ai_provider('gemini')
        
        prompt = AI_TOS_PROMPT.replace('{tos_text}', tos_text)
        response = provider.generate_completion(prompt, temperature=0.2, max_tokens=1000)
        
        return _parse_json_response(response)
        
    except Exception as e:
        logger.error(f"AI ToS analysis failed: {e}")
        return {
            'status': 'yellow',
            'summary': f'AI analysis error: {str(e)[:100]}',
            'key_restrictions': [],
        }


def _check_image_rights(tos_text: str = None, is_press_portal: bool = False, source_type: str = 'media') -> dict:
    """
    Check if images from the source can be used.
    
    - Official press portals: images are for media → pass
    - Other sites: analyze ToS for image-specific restrictions
    """
    # Official press portals: images are created for media distribution
    if is_press_portal and source_type == 'brand':
        return {
            'passed': True,
            'detail': 'Official press portal — images are for media distribution',
        }
    
    # If press portal detected but not a brand (e.g. media aggregator with /press/ URL)
    if is_press_portal and source_type != 'brand':
        return {
            'passed': False,
            'detail': 'Press-style URL but not an official brand — image rights unclear',
        }
    
    # No ToS text available → assume images are NOT safe to use
    if not tos_text:
        return {
            'passed': False,
            'detail': 'No Terms of Service found — cannot verify image rights, defaulting to Pexels',
        }
    
    # Use AI to specifically analyze image rights from ToS text
    try:
        import json
        from ai_engine.modules.ai_provider import get_ai_provider
        provider = get_ai_provider('gemini')
        
        prompt = f"""Analyze this Terms of Use text SPECIFICALLY for IMAGE/PHOTO usage rights.

I need to know if a news aggregator can use images/photos from this website.

Look for:
- "images may not be reproduced/copied/downloaded"
- "photographs are copyrighted"
- "no unauthorized use of images/photos"
- "images are for editorial/press use only"
- "images may be used with attribution/credit"
- "all content including images is protected"

Respond ONLY with valid JSON:
{{
    "images_allowed": true/false,
    "confidence": "high|medium|low",
    "evidence": "quote or describe the relevant clause"
}}

Rules:
- If ToS EXPLICITLY says images cannot be used → images_allowed = false
- If ToS says images require attribution/credit → images_allowed = true (we will credit)
- If ToS only protects TEXT but doesn't mention images → images_allowed = false (be cautious)
- If site is clearly an editorial/blog with copyrighted photos → images_allowed = false

TERMS OF USE TEXT:
{tos_text[:3000]}"""
        
        response = provider.generate_completion(prompt, temperature=0.1, max_tokens=500)
        result = _parse_json_response(response)
        
        if result.get('images_allowed'):
            return {
                'passed': True,
                'detail': f"Images allowed: {result.get('evidence', 'ToS permits image use')}",
            }
        else:
            return {
                'passed': False,
                'detail': f"Images restricted: {result.get('evidence', 'ToS restricts image use')}",
            }
    except Exception as e:
        logger.error(f"Image rights check failed: {e}")
        return {
            'passed': False,
            'detail': f'Image rights check error — defaulting to Pexels: {str(e)[:80]}',
        }


def _analyze_homepage(website_url: str) -> dict:
    """Analyze homepage to detect if site is a press portal."""
    import json
    
    try:
        resp = requests.get(website_url, timeout=10, headers=HEADERS, allow_redirects=True)
        if resp.status_code != 200:
            return None
        
        text = _strip_html(resp.text)[:2000]
        if len(text) < 100:
            return None
        
        from ai_engine.modules.ai_provider import get_ai_provider
        provider = get_ai_provider('gemini')
        
        prompt = AI_HOMEPAGE_PROMPT.replace('{homepage_text}', text)
        response = provider.generate_completion(prompt, temperature=0.1, max_tokens=500)
        
        return _parse_json_response(response)
        
    except Exception as e:
        logger.error(f"Homepage analysis failed: {e}")
        return None


def _parse_json_response(response_text: str) -> dict:
    """Parse JSON from AI response, handling markdown code blocks."""
    import json
    
    text = response_text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group())
        return {'status': 'yellow', 'summary': 'Could not parse AI response'}


def _combine_statuses(*statuses: str) -> str:
    """Combine statuses — worst wins, but green votes can override a single yellow."""
    priority = {'red': 3, 'yellow': 2, 'green': 1}
    
    # If any red → red
    if 'red' in statuses:
        return 'red'
    
    # If mostly green with one yellow → green (benefit of the doubt)
    green_count = statuses.count('green')
    yellow_count = statuses.count('yellow')
    
    if green_count >= 2 and yellow_count <= 1:
        return 'green'
    
    if yellow_count > green_count:
        return 'yellow'
    
    return 'green' if green_count > 0 else 'yellow'
