"""
Editorial Memory — Few-shot learning from editor corrections.

Extracts style patterns from published articles where the editor modified
the AI-generated content. These patterns are injected into the generation
prompt so the AI learns from past corrections.

Storage: Redis cache for fast access, DB as source of truth.
"""
import re
import logging
import hashlib
from difflib import SequenceMatcher
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY = 'editorial_memory:patterns'
CACHE_TTL = 60 * 60 * 24  # 24 hours


def _strip_html(html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = re.sub(r'<[^>]+>', ' ', html)
    return ' '.join(text.split())


def _extract_meaningful_diffs(original: str, edited: str, min_change_len: int = 20) -> list[dict]:
    """
    Compare original AI content with editor-modified content.
    Returns list of meaningful changes (not just formatting fixes).
    """
    orig_text = _strip_html(original)
    edit_text = _strip_html(edited)

    # Split into sentences for granular comparison
    orig_sents = re.split(r'(?<=[.!?])\s+', orig_text)
    edit_sents = re.split(r'(?<=[.!?])\s+', edit_text)

    matcher = SequenceMatcher(None, orig_sents, edit_sents)
    diffs = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue

        original_chunk = ' '.join(orig_sents[i1:i2]).strip()
        edited_chunk = ' '.join(edit_sents[j1:j2]).strip()

        # Skip very small changes (typos, formatting)
        if len(original_chunk) < min_change_len and len(edited_chunk) < min_change_len:
            continue

        # Skip if both are empty
        if not original_chunk and not edited_chunk:
            continue

        diff_entry = {
            'type': tag,  # 'replace', 'insert', 'delete'
            'original': original_chunk[:300],  # Cap length
            'edited': edited_chunk[:300],
        }

        # Classify the change type
        if tag == 'replace':
            # Check if it's a tone/style fix
            orig_lower = original_chunk.lower()
            edit_lower = edited_chunk.lower()
            if any(w in orig_lower for w in ['unprecedented', 'revolutionary', 'game-changing',
                                              'stunning', 'incredible', 'amazing']):
                diff_entry['category'] = 'tone_fix'
            elif len(edited_chunk) > len(original_chunk) * 1.5:
                diff_entry['category'] = 'expansion'
            elif len(edited_chunk) < len(original_chunk) * 0.7:
                diff_entry['category'] = 'condensation'
            else:
                diff_entry['category'] = 'rewrite'
        elif tag == 'insert':
            diff_entry['category'] = 'addition'
        elif tag == 'delete':
            diff_entry['category'] = 'removal'

        diffs.append(diff_entry)

    return diffs


def extract_edit_patterns(max_articles: int = 20) -> list[dict]:
    """
    Scan published articles for editorial corrections.
    Compares content_original (AI output) with content (editor-reviewed).
    
    Returns list of pattern dicts with category, original, and edited text.
    """
    try:
        from news.models import Article

        # Find published articles with both original and edited content
        articles = Article.objects.filter(
            is_published=True,
            content_original__isnull=False,
        ).exclude(
            content_original=''
        ).order_by('-created_at')[:max_articles]

        all_patterns = []

        for article in articles:
            # Skip if content hasn't been modified
            if not article.content or not article.content_original:
                continue

            # Quick similarity check — skip if nearly identical
            orig_hash = hashlib.md5(article.content_original.encode()).hexdigest()
            edit_hash = hashlib.md5(article.content.encode()).hexdigest()
            if orig_hash == edit_hash:
                continue

            diffs = _extract_meaningful_diffs(article.content_original, article.content)
            for diff in diffs:
                diff['article_id'] = article.id
                diff['article_title'] = article.title[:60]
            all_patterns.extend(diffs)

        logger.info(f"[EDITORIAL-MEMORY] Extracted {len(all_patterns)} patterns from {articles.count()} articles")
        return all_patterns

    except Exception as e:
        logger.warning(f"[EDITORIAL-MEMORY] Failed to extract patterns: {e}")
        return []


def get_style_examples(n: int = 3, category: str = None) -> str:
    """
    Get formatted editorial correction examples for prompt injection.
    
    Args:
        n: Number of examples to return
        category: Optional filter (tone_fix, rewrite, expansion, etc.)
    
    Returns:
        Formatted string block for injection into generation prompt.
        Empty string if no patterns available.
    """
    # Try cache first
    cached = cache.get(CACHE_KEY)
    if cached is None:
        cached = extract_edit_patterns()
        if cached:
            cache.set(CACHE_KEY, cached, CACHE_TTL)

    if not cached:
        return ''

    # Filter by category if specified
    patterns = cached
    if category:
        patterns = [p for p in patterns if p.get('category') == category]

    if not patterns:
        return ''

    # Prioritize tone fixes and rewrites (most useful for AI)
    priority_order = ['tone_fix', 'rewrite', 'condensation', 'expansion', 'addition', 'removal']
    patterns.sort(key=lambda p: (
        priority_order.index(p.get('category', 'rewrite')) if p.get('category') in priority_order else 99
    ))

    selected = patterns[:n]

    # Format for prompt
    lines = [
        "═══ EDITORIAL STYLE GUIDE (learn from past corrections) ═══",
        "Our editors have corrected these patterns in past articles.",
        "Apply the same corrections proactively in your writing:\n",
    ]

    for i, p in enumerate(selected, 1):
        cat = p.get('category', 'unknown')
        if p['original'] and p['edited']:
            lines.append(f"Example {i} ({cat}):")
            lines.append(f"  ❌ AI wrote: \"{p['original'][:150]}\"")
            lines.append(f"  ✅ Editor fixed: \"{p['edited'][:150]}\"")
            lines.append("")
        elif p['original'] and not p['edited']:
            lines.append(f"Example {i} (removed):")
            lines.append(f"  ❌ AI wrote: \"{p['original'][:150]}\"")
            lines.append(f"  ✅ Editor removed this entirely")
            lines.append("")

    lines.append("═══════════════════════════════════════════════════\n")
    return '\n'.join(lines)


def invalidate_cache():
    """Clear cached patterns — call after articles are published/edited."""
    cache.delete(CACHE_KEY)
    logger.info("[EDITORIAL-MEMORY] Cache invalidated")
