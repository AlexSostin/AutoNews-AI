"""
Quality Gate — structural completeness check for generated articles.

Scores articles on 5 criteria (20 points each = 100 max) using pure
heuristics — no AI call needed, fast and free.

Usage:
    from ai_engine.modules.quality_gate import check_quality_gate
    result = check_quality_gate(article_html)
    # result = {'score': 85, 'passed': True, 'details': {...}, 'issues': [...]}

Threshold: 75/100 to pass (configurable via QUALITY_GATE_THRESHOLD).
"""

import re
import logging

logger = logging.getLogger(__name__)

# Threshold for passing the quality gate
QUALITY_GATE_THRESHOLD = 75

# AI filler phrases (reused from scoring.py for consistency)
_AI_FILLER_PHRASES = [
    'a compelling proposition', 'a compelling package',
    'commanding road presence', 'commanding presence',
    'effectively eliminates range anxiety',
    'in the evolving landscape', 'isn\'t just another',
    'setting a new benchmark', 'making waves',
    'hold on to your hats', 'buckle up',
    'jaw-dropping', 'mind-blowing', 'game-changing', 'game-changer',
    'a testament to', 'dropping bombshells',
    'eye-watering', 'it\'s clear that',
    'remain to be seen', 'only time will tell',
]

_SOURCE_LEAK_PHRASES = [
    'transcript', 'provided text', 'source video',
    'based on the video', 'from the video', 'in the video',
    'the narrator', 'the host mentions', 'the presenter',
    'according to the transcript', 'the footage shows',
]


def check_quality_gate(html: str, has_competitor_data: bool = False) -> dict:
    """
    Run a structural quality gate on generated article HTML.

    Args:
        html: The article HTML content.
        has_competitor_data: Whether competitor data was available during
                            generation (used to adjust competitor scoring).

    Returns:
        {
            'score': int (0-100),
            'passed': bool,
            'details': {criterion: {'score': int, 'max': 20, 'notes': str}, ...},
            'issues': [str, ...],
        }
    """
    if not html:
        return {
            'score': 0,
            'passed': False,
            'details': {},
            'issues': ['Empty article content'],
        }

    details = {}
    issues = []

    # ── 1. Spec Completeness (20 pts) ────────────────────────────────
    spec_score, spec_notes = _score_spec_completeness(html)
    details['spec_completeness'] = {'score': spec_score, 'max': 20, 'notes': spec_notes}
    if spec_score < 12:
        issues.append(f'Spec coverage low ({spec_notes})')

    # ── 2. Competitors (20 pts) ──────────────────────────────────────
    comp_score, comp_notes = _score_competitors(html, has_competitor_data)
    details['competitors'] = {'score': comp_score, 'max': 20, 'notes': comp_notes}
    if comp_score < 10 and has_competitor_data:
        issues.append(f'Competitor section weak ({comp_notes})')

    # ── 3. Structure Completeness (20 pts) ───────────────────────────
    struct_score, struct_notes = _score_structure(html)
    details['structure'] = {'score': struct_score, 'max': 20, 'notes': struct_notes}
    if struct_score < 12:
        issues.append(f'Missing key sections ({struct_notes})')

    # ── 4. Content Depth (20 pts) ────────────────────────────────────
    depth_score, depth_notes = _score_depth(html)
    details['content_depth'] = {'score': depth_score, 'max': 20, 'notes': depth_notes}
    if depth_score < 12:
        issues.append(f'Content too thin ({depth_notes})')

    # ── 5. Tone & Banned Phrases (20 pts) ────────────────────────────
    tone_score, tone_notes = _score_tone(html)
    details['tone'] = {'score': tone_score, 'max': 20, 'notes': tone_notes}
    if tone_score < 14:
        issues.append(f'Tone issues ({tone_notes})')

    total = spec_score + comp_score + struct_score + depth_score + tone_score
    passed = total >= QUALITY_GATE_THRESHOLD

    status = '✅ PASS' if passed else '❌ FAIL'
    logger.info(
        f"🚦 Quality Gate: {total}/100 {status} — "
        f"spec={spec_score} comp={comp_score} struct={struct_score} "
        f"depth={depth_score} tone={tone_score}"
    )
    if issues:
        logger.info(f"   Issues: {'; '.join(issues)}")

    return {
        'score': total,
        'passed': passed,
        'details': details,
        'issues': issues,
    }


# ══════════════════════════════════════════════════════════════════════
#  Criterion Scorers
# ══════════════════════════════════════════════════════════════════════

def _score_spec_completeness(html: str) -> tuple:
    """Score spec-bar completeness (0-20)."""
    score = 0

    # Check for spec-bar div
    has_spec_bar = bool(re.search(r'<div\s+class="spec-bar">', html, re.I))
    if has_spec_bar:
        score += 8  # Has spec bar at all
        # Count spec items
        spec_items = len(re.findall(r'<div\s+class="spec-item">', html, re.I))
        if spec_items >= 5:
            score += 6
        elif spec_items >= 4:
            score += 4
        elif spec_items >= 3:
            score += 2
    else:
        return 0, 'no spec-bar found'

    # Check for powertrain specs grid
    has_powertrain = bool(re.search(r'<div\s+class="powertrain-specs">', html, re.I))
    if has_powertrain:
        score += 4
        ps_items = len(re.findall(r'<div\s+class="ps-item">', html, re.I))
        if ps_items >= 3:
            score += 2

    return min(score, 20), f'{spec_items} spec items, {"has" if has_powertrain else "no"} powertrain grid'


def _score_competitors(html: str, has_competitor_data: bool) -> tuple:
    """Score competitor mentions and comparison section (0-20)."""
    score = 0

    # Check for compare-grid
    has_compare_grid = bool(re.search(r'<div\s+class="compare-grid">', html, re.I))
    if has_compare_grid:
        score += 10
        # Count compare cards
        cards = len(re.findall(r'<div\s+class="compare-card', html, re.I))
        if cards >= 3:
            score += 6
        elif cards >= 2:
            score += 4

        # Check cards have actual data (not empty)
        compare_rows = len(re.findall(r'<div\s+class="compare-row">', html, re.I))
        if compare_rows >= 6:
            score += 4
        elif compare_rows >= 3:
            score += 2
    elif not has_competitor_data:
        # No competitor data was available — don't penalise heavily
        score = 14  # Neutral — not the article's fault
        return score, 'no competitor data available'
    else:
        # Had competitor data but didn't use it
        # Check if competitors are at least mentioned in text
        plain = re.sub(r'<[^>]+>', ' ', html).lower()
        comp_keywords = ['compare', 'competitor', 'rival', 'alternative', 'versus', ' vs ']
        mentions = sum(1 for kw in comp_keywords if kw in plain)
        if mentions >= 2:
            score = 8
        return score, f'no compare-grid, {mentions} competitor mentions in text'

    return min(score, 20), f'{cards} compare cards, {compare_rows} data rows'


def _score_structure(html: str) -> tuple:
    """Score required HTML structure elements (0-20)."""
    score = 0
    found = []
    missing = []

    checks = [
        ('spec-bar', r'<div\s+class="spec-bar">', 4),
        ('pros-cons', r'<div\s+class="pros-cons">', 4),
        ('fm-verdict', r'<div\s+class="fm-verdict">', 4),
        ('price-tag', r'<div\s+class="price-tag">', 3),
        ('alt-texts', r'<div\s+class="alt-texts"', 2),
    ]

    for name, pattern, pts in checks:
        if re.search(pattern, html, re.I):
            score += pts
            found.append(name)
        else:
            missing.append(name)

    # Check verdict has real content (≥60 words)
    verdict_match = re.search(
        r'<div\s+class="fm-verdict">.*?</div>\s*</div>',
        html, re.I | re.DOTALL
    )
    if verdict_match:
        verdict_text = re.sub(r'<[^>]+>', ' ', verdict_match.group())
        verdict_words = len(verdict_text.split())
        if verdict_words >= 60:
            score += 3  # Full bonus for proper verdict
        elif verdict_words >= 20:
            score += 1  # Partial — verdict exists but thin
        else:
            # Verdict div exists but is essentially empty (<20 words)
            # Revoke the 4 base points for having the div
            score -= 4
            missing.append(f'verdict-too-thin ({verdict_words} words)')

    notes = f'found: {", ".join(found)}' if found else 'none found'
    if missing:
        notes += f' | missing: {", ".join(missing)}'

    return min(score, 20), notes


def _score_depth(html: str) -> tuple:
    """Score content depth — word count and section count (0-20)."""
    plain = re.sub(r'<[^>]+>', ' ', html)
    words = plain.split()
    word_count = len(words)
    score = 0

    # Word count scoring
    if word_count >= 1200:
        score += 10
    elif word_count >= 1000:
        score += 8
    elif word_count >= 800:
        score += 5
    elif word_count >= 500:
        score += 3

    # Section count (h2 headings)
    h2_count = len(re.findall(r'<h2[^>]*>', html, re.I))
    if 3 <= h2_count <= 7:
        score += 5  # Ideal range
    elif h2_count >= 2:
        score += 3
    elif h2_count >= 1:
        score += 1

    # Paragraph count
    p_count = html.count('</p>')
    if p_count >= 10:
        score += 5
    elif p_count >= 6:
        score += 3
    elif p_count >= 3:
        score += 1

    return min(score, 20), f'{word_count} words, {h2_count} sections, {p_count} paragraphs'


def _score_tone(html: str) -> tuple:
    """Score tone quality — penalise AI filler and source leaks (0-20)."""
    score = 20  # Start perfect, subtract for issues
    content_lower = html.lower()
    penalties = []

    # AI filler phrases
    filler_count = sum(1 for p in _AI_FILLER_PHRASES if p in content_lower)
    if filler_count >= 4:
        score -= 10
        penalties.append(f'{filler_count} AI filler phrases')
    elif filler_count >= 2:
        score -= 5
        penalties.append(f'{filler_count} AI filler phrases')
    elif filler_count == 1:
        score -= 2

    # Source leak phrases
    leak_count = sum(1 for p in _SOURCE_LEAK_PHRASES if p in content_lower)
    if leak_count >= 3:
        score -= 10
        penalties.append(f'{leak_count} source leaks')
    elif leak_count >= 1:
        score -= 5
        penalties.append(f'{leak_count} source leaks')

    notes = 'clean' if not penalties else '; '.join(penalties)
    return max(score, 0), notes
