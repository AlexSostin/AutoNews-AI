"""
Content sanitizer — post-processing filter for AI-generated articles.

Catches data quality issues that slip through the generation pipeline:
1. Non-Latin characters (Bengali, Arabic, Chinese) in car names
2. Duplicate consecutive words/phrases ("6-Seater 6-Seater")
3. Corrupted Unicode tokens in comparison data

Applied at two points:
- competitor_lookup: sanitize DB data BEFORE injecting into prompt
- content_generator: sanitize final article HTML AFTER generation
"""

import re
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# Non-Latin detection — rejects Cyrillic, Bengali, Arabic, CJK, etc.
# Allows: Latin, Latin Extended (accents), digits, punctuation, symbols
# ═══════════════════════════════════════════════════════════════════════════

# Characters that should NOT appear in car names/specs
_NON_LATIN_RE = re.compile(
    r'[\u0400-\u04FF'    # Cyrillic
    r'\u0980-\u09FF'     # Bengali
    r'\u0600-\u06FF'     # Arabic
    r'\u4E00-\u9FFF'     # CJK Unified
    r'\u3040-\u309F'     # Hiragana
    r'\u30A0-\u30FF'     # Katakana
    r'\uAC00-\uD7AF'     # Korean Hangul
    r'\u0900-\u097F'     # Devanagari
    r'\u0A80-\u0AFF'     # Gujarati
    r'\u0B00-\u0B7F'     # Oriya
    r'\u0B80-\u0BFF'     # Tamil
    r'\u0C00-\u0C7F'     # Telugu
    r'\u0C80-\u0CFF'     # Kannada
    r'\u0D00-\u0D7F'     # Malayalam
    r'\u0E00-\u0E7F'     # Thai
    r']+'
)


def strip_non_latin(text: str) -> str:
    """Remove non-Latin script characters from text.
    
    Preserves Latin letters (including accented), digits, punctuation.
    Used to clean car names that may contain corrupted Unicode.
    
    >>> strip_non_latin("Aito M9 EজিৎREV")
    'Aito M9 EREV'
    >>> strip_non_latin("Normal Text 123")
    'Normal Text 123'
    """
    if not text:
        return text
    return _NON_LATIN_RE.sub('', text)


# ═══════════════════════════════════════════════════════════════════════════
# Duplicate word/phrase remover
# ═══════════════════════════════════════════════════════════════════════════

# Matches consecutive duplicate words/hyphenated-phrases: "6-Seater 6-Seater"
_DUPLICATE_WORD_RE = re.compile(
    r'\b([\w]+(?:-[\w]+)*)\s+\1\b',
    re.IGNORECASE
)


def deduplicate_consecutive(text: str) -> str:
    """Remove consecutive duplicate words or hyphenated phrases.
    
    >>> deduplicate_consecutive("6-Seater 6-Seater")
    '6-Seater'
    >>> deduplicate_consecutive("the the quick brown")
    'the quick brown'
    >>> deduplicate_consecutive("Long Range Long Range AWD")
    'Long Range AWD'
    """
    if not text:
        return text
    return _DUPLICATE_WORD_RE.sub(r'\1', text)


# ═══════════════════════════════════════════════════════════════════════════
# Combined sanitizer for car name strings (used in competitor_lookup)
# ═══════════════════════════════════════════════════════════════════════════

def sanitize_car_name(name: str) -> str:
    """Full sanitization for a car name string.
    
    1. Strip non-Latin characters
    2. Remove duplicate consecutive words
    3. Collapse multiple spaces
    
    >>> sanitize_car_name("2026 Aito M9 EজিৎREV 6-Seater 6-Seater")
    '2026 Aito M9 EREV 6-Seater'
    """
    if not name:
        return name
    result = strip_non_latin(name)
    result = deduplicate_consecutive(result)
    # Collapse multiple spaces
    result = re.sub(r'\s{2,}', ' ', result).strip()
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Full article HTML sanitizer (post-processing)
# ═══════════════════════════════════════════════════════════════════════════

def sanitize_article_html(html: str) -> str:
    """Post-process generated article HTML.
    
    Applied AFTER AI generation, BEFORE saving to DB:
    1. Remove non-Latin characters from car name contexts
    2. Remove duplicate consecutive words
    3. Clean up resulting whitespace
    
    Returns cleaned HTML string.
    """
    if not html:
        return html
    
    result = html
    
    # 1. Strip non-Latin from car name patterns (year + brand contexts)
    #    Matches "2026 Brand ModelজিৎVariant" — strips non-Latin chars
    #    within headings and strong tags (where car names typically appear)
    def _clean_non_latin_in_tag(match):
        tag_content = match.group(0)
        if _NON_LATIN_RE.search(tag_content):
            cleaned = _NON_LATIN_RE.sub('', tag_content)
            # Collapse spaces that may result
            cleaned = re.sub(r'\s{2,}', ' ', cleaned)
            logger.warning(
                f"Stripped non-Latin chars from article: "
                f"{tag_content[:80]!r} → {cleaned[:80]!r}"
            )
            return cleaned
        return tag_content
    
    # Clean inside headings and strong tags
    result = re.sub(r'<h[1-6][^>]*>.*?</h[1-6]>', _clean_non_latin_in_tag, result, flags=re.DOTALL)
    result = re.sub(r'<strong>.*?</strong>', _clean_non_latin_in_tag, result, flags=re.DOTALL)
    
    # 2. Clean non-Latin in plain text too (comparison section etc.)
    #    But be more targeted — only in lines that contain both a year and non-Latin
    lines = result.split('\n')
    cleaned_lines = []
    for line in lines:
        if _NON_LATIN_RE.search(line):
            original = line
            line = _NON_LATIN_RE.sub('', line)
            line = re.sub(r'\s{2,}', ' ', line)
            if original != line:
                logger.warning(
                    f"Stripped non-Latin from line: {original[:80]!r}"
                )
        cleaned_lines.append(line)
    result = '\n'.join(cleaned_lines)
    
    # 3. Remove duplicate consecutive words/phrases everywhere
    result = deduplicate_consecutive(result)
    
    # 4. Collapse multiple spaces (but not newlines)
    result = re.sub(r'[ \t]{2,}', ' ', result)
    
    return result
