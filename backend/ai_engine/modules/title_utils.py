"""
Title utilities for article generation.

Provides validation, extraction, and cleaning of article titles
to ensure high-quality, SEO-friendly headlines.
"""
import re
import logging

logger = logging.getLogger(__name__)

# Generic section headers that AI generates as part of article structure.
# These should NEVER be used as article titles.
GENERIC_SECTION_HEADERS = [
    'performance & specs', 'performance and specs',
    'performance & specifications', 'performance and specifications',
    'performance \u0026 specifications', 'performance \u0026amp; specifications',
    'performance \u0026 specs', 'performance \u0026amp; specs',
    'design & interior', 'design and interior',
    'design \u0026 interior', 'design \u0026amp; interior',
    'technology & features', 'technology and features',
    'technology \u0026 features', 'technology \u0026amp; features',
    'driving experience', 'driving impressions',
    'pros & cons', 'pros and cons', 'pros \u0026 cons',
    'conclusion', 'summary', 'overview', 'introduction',
    'us market availability & pricing', 'us market availability',
    'global market & regional availability', 'global market',
    'market availability & pricing', 'pricing & availability',
    'pricing and availability', 'specifications', 'features',
    'details', 'information', 'title:', 'new car review',
    'interior & comfort', 'safety & technology',
    'exterior design', 'interior design',
    'engine & performance', 'powertrain',
    'battery & range', 'charging & range',
]


def _is_generic_header(text: str) -> bool:
    """
    Check if a text is a generic section header that shouldn't be a title.
    Uses fuzzy matching to catch variations.
    """
    clean = text.strip().lower()
    # Remove HTML entities
    clean = clean.replace('&amp;', '&').replace('\u0026amp;', '&').replace('\u0026', '&')
    # Remove leading/trailing punctuation
    clean = re.sub(r'^[\s\-:]+|[\s\-:]+$', '', clean)
    
    # Exact or substring match against known headers
    for header in GENERIC_SECTION_HEADERS:
        if clean == header or (header in clean and len(clean) < 50):
            return True
    
    # Regex patterns for common generic headers
    generic_patterns = [
        r'^(the\s+)?\d{4}\s+(performance|specs|design)',  # "2025 Performance"
        r'^(pros|cons)\s*(\u0026|and|&)',
        r'^(key\s+)?(features|specifications|highlights)$',
        r'^(final\s+)?(verdict|thoughts|conclusion)s?$',
        r'^(driving|ride|road)\s+(experience|test|review)$',
    ]
    for pattern in generic_patterns:
        if re.match(pattern, clean, re.IGNORECASE):
            return True
    
    return False


def _contains_non_latin(text: str) -> bool:
    """Check if text contains non-Latin characters (Cyrillic, Chinese, Arabic, etc.)."""
    # Allow: ASCII, common punctuation, digits, extended Latin (accents)
    # Reject: Cyrillic (0400-04FF), Chinese (4E00-9FFF), Arabic (0600-06FF), etc.
    non_latin = re.findall(r'[\u0400-\u04FF\u4E00-\u9FFF\u0600-\u06FF\u3040-\u309F\u30A0-\u30FF]', text)
    # If more than 2 non-Latin chars, it's likely a non-English title
    return len(non_latin) > 2


# YouTube video title noise patterns to strip
_VIDEO_TITLE_NOISE = re.compile(
    r'\s*\b('
    r'walk\s*around'
    r'|first\s+look'
    r'|first\s+drive'
    r'|test\s+drive'
    r'|full\s+tour'
    r'|full\s+review'
    r'|hands[\s\-]?on'
    r'|in[\s\-]?depth\s+(?:look|review|tour)'
    r'|pov\s+(?:drive|test\s+drive|test|review)'
    r'|exterior\s*(?:and|&|\+)\s*interior'
    r'|interior\s*(?:and|&|\+)\s*exterior'
    r'|detailed\s+look'
    r'|quick\s+look'
    r'|buyer\'?s?\s+guide'
    r'|everything\s+you\s+need\s+to\s+know'
    r'|what\s+you\s+need\s+to\s+know'
    r'|is\s+it\s+worth\s+it\??'
    r'|worth\s+the\s+hype\??'
    r'|should\s+you\s+buy\s+(?:it|one)\??'
    r')\b[!]?\s*',
    re.IGNORECASE
)

# Noise suffixes at end of title (after dash/pipe/colon)
_VIDEO_TITLE_SUFFIX_NOISE = re.compile(
    r'\s*[|–—\-:]\s*('
    r'4[kK]\s*$'
    r'|(?:UHD|HD)\s*$'
    r'|(?:\d{4}p)\s*$'
    r'|POV\s*$'
    r'|Review\s*$'
    r')',
    re.IGNORECASE
)


def _clean_video_title_noise(title: str) -> str:
    """Remove YouTube-specific noise from a video title to make it article-ready."""
    if not title:
        return title
    
    # Strip channel name suffixes (after | or — or –)
    cleaned = re.sub(r'\s*[|–—]\s*[^|–—]+$', '', title).strip()
    
    # Strip video format noise
    cleaned = _VIDEO_TITLE_NOISE.sub(' ', cleaned).strip()
    cleaned = _VIDEO_TITLE_SUFFIX_NOISE.sub('', cleaned).strip()
    
    # Remove orphaned connectors ("and Review", "or Test", etc.)
    cleaned = re.sub(r'\s+(?:and|or|&|\+)\s+(?:Review|Test|Drive|Tour)\b', '', cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'\s+(?:and|&|\+)\s*$', '', cleaned).strip()
    cleaned = re.sub(r'^\s*(?:NEW|All New|All-New)\s+', '', cleaned, flags=re.IGNORECASE).strip()
    
    # Clean up trailing/leading punctuation left behind (dashes, colons, question marks, exclamation)
    cleaned = re.sub(r'[\s:,\-–—!?]+$', '', cleaned).strip()
    cleaned = re.sub(r'^[\s:,\-–—!?]+', '', cleaned).strip()
    
    # Clean stray colon-space in middle ("BYD Song DM i : The Range" → "BYD Song DM i: The Range")
    cleaned = re.sub(r'\s+:\s+', ': ', cleaned)
    
    # Clean double spaces
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    
    if cleaned != title.strip():
        logger.info(f"[TITLE] Cleaned video noise: '{title}' → '{cleaned}'")
    
    return cleaned if len(cleaned) > 10 else title.strip()


def validate_title(title: str, video_title: str = None, specs: dict = None) -> str:
    """
    Validates and fixes article title. Returns a good title or constructs one from available data.
    
    Priority:
    1. Use provided title if it's valid (not generic, long enough, in English)
    2. Use video_title if available (cleaned of YouTube noise)
    3. Construct from specs (Year Make Model Review)
    4. Last resort: generic but unique-ish fallback
    """
    # Clean video noise from AI-generated title too (AI sometimes copies video title verbatim)
    if title:
        title = _clean_video_title_noise(title)
    
    # Check if title is valid
    if title and len(title) > 15 and not _is_generic_header(title):
        # Reject non-English titles (Cyrillic, Chinese, etc.)
        if _contains_non_latin(title):
            logger.warning(f"[TITLE] Rejected non-English title: {title[:60]}")
            # Fall through to fallbacks below
        else:
            return title.strip()
    
    # Fallback 1: Use video title (cleaned up)
    if video_title and len(video_title) > 10:
        clean_vt = _clean_video_title_noise(video_title)
        if clean_vt and len(clean_vt) > 10 and not _contains_non_latin(clean_vt):
            return clean_vt
        if not _contains_non_latin(video_title):
            return video_title.strip()
    
    # Fallback 2: Construct from specs
    if specs:
        make = specs.get('make', '')
        model = specs.get('model', '')
        year = specs.get('year', '')
        trim = specs.get('trim', '')
        
        if make and make != 'Not specified' and model and model != 'Not specified':
            year_str = f"{year} " if year else ""
            trim_str = f" {trim}" if trim and trim != 'Not specified' else ""
            return f"{year_str}{make} {model}{trim_str} Review"
    
    # Last resort
    if title and len(title) > 5 and not _contains_non_latin(title):
        return title
    return "New Car Review"


def extract_title(html_content):
    """
    Extracts the main article title from generated HTML.
    Ignores generic section headers like 'Performance & Specifications'.
    """
    # Find all h2 tags (handle attributes in tags)
    h2_matches = re.findall(r'<h2[^>]*>(.*?)</h2>', html_content, re.IGNORECASE | re.DOTALL)
    
    for title in h2_matches:
        # Strip HTML tags inside the h2 (e.g., <strong>, <em>)
        clean_t = re.sub(r'<[^>]+>', '', title).strip()
        clean_t = clean_t.replace('Title:', '').strip()
        
        # Skip empty or very short
        if len(clean_t) < 10:
            continue
        
        # Skip generic section headers
        if _is_generic_header(clean_t):
            continue
        
        return clean_t
    
    return None  # Return None instead of fallback — let validate_title handle it
