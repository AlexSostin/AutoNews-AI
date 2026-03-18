"""
Article post-processing pipeline.

Pure HTML cleanup functions (no AI calls). Includes repetition detection,
car name shortening, price validation, duplicate paragraph removal,
self-consistency checks, typo fixes, and empty card stripping.

The `post_process_article` function is the single orchestrator entry-point.
"""
import re
import logging

logger = logging.getLogger(__name__)

from ai_engine.modules.banned_phrases import clean_banned_phrases
from ai_engine.modules.html_normalizer import ensure_html_only


def _reduce_repetition(html: str) -> str:
    """Detect and remove paragraphs/list items that repeat the same spec/phrase excessively."""
    import collections

    # Extract all spec mentions: "1505 km", "530 hp", "82.5 kWh", etc.
    spec_re = re.compile(r'(\d[\d,.]*\s*(?:km|hp|kW|Nm|mm|kWh|mph|kg|seconds?|s)\b)', re.IGNORECASE)

    # Count spec occurrences ONLY in body blocks (p, li) — NOT headings (h2/h3).
    # Specs in the article title heading are expected to appear in the body too,
    # so counting h2/h3 would wrongly flag normal spec mentions as "overused".
    body_blocks = re.findall(r'<(?:p|li)>.*?</(?:p|li)>', html, re.DOTALL)
    if not body_blocks:
        return html

    spec_counts = collections.Counter()
    for block in body_blocks:
        specs_in_block = set(spec_re.findall(block))  # unique per block
        for spec in specs_in_block:
            spec_counts[spec.strip().lower()] += 1

    # Find specs that appear in 3+ different body blocks (lowered from 5 to catch more repetition)
    overused = {spec for spec, count in spec_counts.items() if count >= 3}
    if not overused:
        return html

    print(f"  🔁 Repetition detector: overused specs: {overused}")

    # Only remove from <p> and <li> blocks (not headings)
    spec_seen = collections.Counter()
    removed = 0
    for block in body_blocks:
        block_specs = {s.strip().lower() for s in spec_re.findall(block)}
        dominated = block_specs & overused
        if dominated:
            # Check if ALL overused specs in this block have been seen 3+ times already
            all_seen_enough = all(spec_seen[s] >= 3 for s in dominated)
            for s in dominated:
                spec_seen[s] += 1
            if all_seen_enough:
                # Remove this block — it's redundant
                html = html.replace(block, '', 1)
                removed += 1

    if removed:
        # Clean up empty space and empty <ul> tags
        html = re.sub(r'\n\s*\n\s*\n', '\n\n', html)
        html = re.sub(r'<ul>\s*</ul>', '', html)
        print(f"  🔁 Repetition detector: removed {removed} redundant blocks")

    return html


def _shorten_car_names(html: str) -> str:
    """Replace repeated full car names ('The 2026 BYD TANG 1240') with shorter forms after first 2 mentions."""
    # Match patterns like 'The 2026 BYD TANG 1240' or '2026 HUAWEI M8 REV'
    full_name_re = re.compile(
        r'(?:The\s+)?(20\d{2})\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)\s+([A-Z0-9][A-Za-z0-9]+(?:\s+[A-Z0-9]+)?)',
    )
    
    # Find the most common full car name pattern
    matches = full_name_re.findall(html)
    if len(matches) < 4:
        return html  # Not enough repetition to matter
    
    # Count (year, brand, model) tuples
    from collections import Counter
    name_counts = Counter(matches)
    if not name_counts:
        return html
    
    most_common = name_counts.most_common(1)[0]
    (year, brand, model), count = most_common
    
    if count < 4:
        return html  # Not enough repetition
    
    full_name = f"{year} {brand} {model}"
    the_full_name = f"The {full_name}"
    
    # Keep first 2 occurrences, replace the rest with short form
    short_name = model  # e.g. "TANG 1240" or "M8 REV"
    
    seen = 0
    result = []
    pos = 0
    for m in re.finditer(re.escape(the_full_name), html, re.IGNORECASE):
        result.append(html[pos:m.start()])
        seen += 1
        if seen <= 2:
            result.append(m.group())
        else:
            result.append(f"The {short_name}")
        pos = m.end()
    result.append(html[pos:])
    html = ''.join(result)
    
    # Also handle without 'The' prefix
    seen = 0
    result = []
    pos = 0
    for m in re.finditer(r'(?<!The )' + re.escape(full_name), html):
        result.append(html[pos:m.start()])
        seen += 1
        if seen <= 2:
            result.append(m.group())
        else:
            result.append(short_name)
        pos = m.end()
    result.append(html[pos:])
    html = ''.join(result)
    
    replaced = count - 4  # Roughly how many we replaced
    if replaced > 0:
        print(f"  ✂️ Car name shortener: shortened '{full_name}' → '{short_name}' ({replaced}+ times)")
    
    return html


def _detect_missing_sections(html: str, word_count: int, has_competitors: bool = False) -> dict:
    """
    Analyze a generated article to detect missing sections and quality issues.
    Returns a dict with 'missing_sections', 'thin_sections', and a ready-to-use 'retry_prompt'.

    Args:
        has_competitors: If True, adds 'How It Compares' to expected sections.
    """
    # Expected sections in a full article
    EXPECTED_SECTIONS = {
        'Performance & Specs': ['performance', 'specs', 'powertrain', 'engine', 'motor'],
        'Design & Interior': ['design', 'interior', 'styling', 'cabin'],
        'Technology & Features': ['technology', 'features', 'tech', 'adas', 'infotainment'],
        'Pricing & Availability': ['pricing', 'price', 'availability', 'cost'],
        'Pros & Cons': ['pros', 'cons', 'advantages', 'disadvantages'],
        'FreshMotors Verdict': ['verdict', 'conclusion', 'final'],
    }

    if has_competitors:
        EXPECTED_SECTIONS['How It Compares'] = ['compares', 'comparison', 'competition', 'competitor', 'versus', 'vs.', 'rivals']

    # Extract all H2 headings from the article
    h2_texts = [h.lower() for h in re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.IGNORECASE)]
    h2_combined = ' '.join(h2_texts)

    missing = []
    for section_name, keywords in EXPECTED_SECTIONS.items():
        if not any(kw in h2_combined for kw in keywords):
            missing.append(section_name)

    # Detect thin sections (H2 followed by very little content)
    thin = []
    h2_positions = [(m.start(), m.end(), m.group(1)) for m in re.finditer(r'<h2[^>]*>(.*?)</h2>', html, re.IGNORECASE)]
    for i, (start, end, title) in enumerate(h2_positions):
        if i == 0:
            continue  # Skip the title H2 — it's the article headline, not a body section
        # Skip sections that are naturally short (bullet-point lists, short verdicts)
        title_lower = title.strip().lower()
        if any(kw in title_lower for kw in ['pros', 'cons', 'verdict', 'conclusion']):
            continue
        # Content between this H2 and the next one (or end of doc)
        next_start = h2_positions[i + 1][0] if i + 1 < len(h2_positions) else len(html)
        section_html = html[end:next_start]
        section_text = re.sub(r'<[^>]+>', ' ', section_html)
        section_words = len(section_text.split())
        if section_words < 40:  # Less than ~2 sentences = practically empty
            thin.append(title.strip())

    # Special check: Verdict heading exists but content is almost empty
    verdict_idx = None
    for i, (start, end, title) in enumerate(h2_positions):
        if any(kw in title.strip().lower() for kw in ['verdict', 'conclusion', 'final']):
            verdict_idx = i
            break
    if verdict_idx is not None:
        _, vend, _ = h2_positions[verdict_idx]
        vnext = h2_positions[verdict_idx + 1][0] if verdict_idx + 1 < len(h2_positions) else len(html)
        verdict_html = html[vend:vnext]
        verdict_text = re.sub(r'<[^>]+>', ' ', verdict_html).strip()
        verdict_words = len(verdict_text.split())
        if verdict_words < 15:  # Heading exists but essentially empty
            if 'FreshMotors Verdict' not in missing:
                missing.append('FreshMotors Verdict')
    elif 'FreshMotors Verdict' not in missing:
        # Verdict heading not found at all
        missing.append('FreshMotors Verdict')

    # Build a targeted retry prompt
    retry_parts = []

    if missing:
        retry_parts.append(
            f"Your article is MISSING these sections: {', '.join(missing)}. "
            f"Add detailed, data-driven content for each."
        )

    if thin:
        retry_parts.append(
            f"These sections are TOO THIN (under 40 words): {', '.join(thin)}. "
            f"Expand them with specific facts, numbers, and real-world context."
        )

    if word_count < 1000 and not missing:
        retry_parts.append(
            f"The article is only {word_count} words — MINIMUM is 1000 words. "
            "Write LONGER, more detailed sections. Deepen your analysis: add competitor comparisons with real data, "
            "explain what the specs mean for the driver, include real-world driving context, "
            "and expand the Pricing & Availability section with regional details. "
            "Also ensure FreshMotors Verdict has 2-3 meaningful sentences."
        )

    retry_prompt = ""
    if retry_parts:
        retry_prompt = (
            "⚠️ SMART RETRY — Your previous article needs improvement:\n"
            + "\n".join(f"  • {p}" for p in retry_parts)
            + "\n\nFix ONLY the issues above. Keep everything else intact. "
            "Do NOT add filler — only REAL information.\n\n"
        )

    return {
        'missing_sections': missing,
        'thin_sections': thin,
        'needs_retry': bool(retry_parts),
        'retry_prompt': retry_prompt,
    }


# ── Price format validator ─────────────────────────────────────────────
def _validate_prices(html: str) -> str:
    """Fix broken price formatting that LLMs sometimes produce."""
    original = html

    # 1. Fix doubled approximate conversions:
    #    "CNY 359,800 (approx. $5,000)0 (approximately $49,800 USD)"
    #    → "CNY 359,800 (approximately $49,800)"
    html = re.sub(
        r'\(approx\.?\s*\$[\d,]+\)\d*\s*\(approximately\s*(\$[\d,]+(?:\s*USD)?)\)',
        r'(approximately \1)',
        html, flags=re.IGNORECASE,
    )
    # Catch the reverse order too
    html = re.sub(
        r'\(approximately\s*\$[\d,]+(?:\s*USD)?\)\s*\(approx\.?\s*(\$[\d,]+)\)',
        r'(approximately \1)',
        html, flags=re.IGNORECASE,
    )

    # 2. Fix CNY prices with too few digits (broken comma placement):
    #    "CNY 359,80" → "CNY 359,800"  (probable dropped trailing zero)
    #    Only triggers for values that look like broken thousands (X,XX pattern)
    def _fix_cny_comma(m):
        prefix = m.group(1)  # "CNY " or "RMB "
        before_comma = m.group(2)
        after_comma = m.group(3)
        # If after-comma part is exactly 2 digits and before-comma is 1-3 digits,
        # it's likely a dropped trailing zero (359,80 → 359,800)
        if len(after_comma) == 2 and 1 <= len(before_comma) <= 3:
            fixed = f"{prefix}{before_comma},{after_comma}0"
            print(f"  💰 Price fix: {m.group(0)} → {fixed}")
            return fixed
        return m.group(0)

    html = re.sub(
        r'(CNY\s+|RMB\s+)(\d{1,3}),(\d{2})\b(?!\d)',
        _fix_cny_comma, html,
    )

    # 3. Fix stray digits after closing parenthesis in price conversions:
    #    "(approx. $49,800)0" → "(approx. $49,800)"
    html = re.sub(
        r'(\(approx(?:imately)?\.?\s*\$[\d,]+(?:\s*USD)?\))(\d{1,2})(?=\s|[.,;)]|$)',
        r'\1', html,
    )

    # 4. Remove duplicate USD annotations on the same price:
    #    "CNY 359,800 (approximately $49,800) (approx. $49,800)"
    html = re.sub(
        r'(\(approx(?:imately)?\.?\s*\$[\d,]+(?:\s*USD)?\))\s*\(approx(?:imately)?\.?\s*\$[\d,]+(?:\s*USD)?\)',
        r'\1', html, flags=re.IGNORECASE,
    )

    if html != original:
        print(f"  💰 Price validator: fixed formatting issues")

    return html


# ── Duplicate paragraph detector ───────────────────────────────────────
def _detect_duplicate_paragraphs(html: str) -> str:
    """Remove near-duplicate paragraphs (>70% text similarity)."""
    from difflib import SequenceMatcher

    # Extract all <p> blocks with their positions
    para_pattern = re.compile(r'<p>.*?</p>', re.DOTALL)
    matches = list(para_pattern.finditer(html))

    if len(matches) < 3:
        return html  # Not enough paragraphs to compare

    # Convert to plain text for comparison
    def _plain(html_block):
        return re.sub(r'<[^>]+>', ' ', html_block).strip().lower()

    texts = [_plain(m.group()) for m in matches]

    # Find duplicate pairs (compare each para with all later ones)
    to_remove = set()
    for i in range(len(texts)):
        if i in to_remove:
            continue
        if len(texts[i]) < 80:  # Skip very short paragraphs
            continue
        for j in range(i + 1, len(texts)):
            if j in to_remove:
                continue
            if len(texts[j]) < 80:
                continue
            ratio = SequenceMatcher(None, texts[i], texts[j]).ratio()
            if ratio > 0.70:
                # Remove the later (duplicate) paragraph
                to_remove.add(j)
                print(f"  🔁 Duplicate para detected: {ratio:.0%} similar, removing para #{j+1}")

    if not to_remove:
        return html

    # Remove duplicates from end to start (to preserve indices)
    for idx in sorted(to_remove, reverse=True):
        m = matches[idx]
        html = html[:m.start()] + html[m.end():]

    # Clean up leftover whitespace
    html = re.sub(r'\n\s*\n\s*\n', '\n\n', html)
    print(f"  🔁 Duplicate detector: removed {len(to_remove)} duplicate paragraph(s)")

    return html


# ── Self-consistency checker ───────────────────────────────────────────
def _check_self_consistency(html: str) -> str:
    """
    Detect and fix contradictory numeric specs within the same article.
    Example: "63.3 kWh" in one place and "63 kWh" in another → keep 63.3 kWh.
    """
    import collections

    # Extract all numeric claims with units (skip inside headings)
    body_text = re.sub(r'<h[1-6][^>]*>.*?</h[1-6]>', '', html, flags=re.DOTALL | re.IGNORECASE)
    spec_re = re.compile(
        r'(\d[\d,.]*)\s*(kWh|km|hp|HP|kW|Nm|mm|kg|mph|liters?|litres?|seconds?)\b',
        re.IGNORECASE
    )

    # Group by unit type
    unit_groups = collections.defaultdict(list)
    for value_str, unit in spec_re.findall(body_text):
        # Normalize unit
        unit_lower = unit.lower().rstrip('s')
        if unit_lower in ('liter', 'litre'):
            unit_lower = 'liter'
        if unit_lower == 'second':
            unit_lower = 'second'
        try:
            value = float(value_str.replace(',', ''))
        except ValueError:
            continue
        unit_groups[unit_lower].append((value, value_str))

    # For each unit, check for near-duplicates (within ±3%)
    fixes = {}
    for unit, values in unit_groups.items():
        if len(values) < 2:
            continue
        unique_values = list(set(v[0] for v in values))
        if len(unique_values) < 2:
            continue

        # Check each pair of unique values
        for i in range(len(unique_values)):
            for j in range(i + 1, len(unique_values)):
                v1, v2 = unique_values[i], unique_values[j]
                if v1 == 0 or v2 == 0:
                    continue
                diff_pct = abs(v1 - v2) / max(v1, v2) * 100
                if diff_pct <= 3:  # Within 3% — likely a rounding inconsistency
                    # Keep the more precise value (more decimal places)
                    str1 = next(s for v, s in values if v == v1)
                    str2 = next(s for v, s in values if v == v2)
                    # More decimal places = more precise
                    prec1 = len(str1.split('.')[-1]) if '.' in str1 else 0
                    prec2 = len(str2.split('.')[-1]) if '.' in str2 else 0
                    if prec1 >= prec2:
                        keep, replace = str1, str2
                    else:
                        keep, replace = str2, str1

                    if keep != replace:
                        fixes[replace] = (keep, unit)

    if not fixes:
        return html

    for old_val, (new_val, unit) in fixes.items():
        # Only replace the bare number followed by the unit, not inside larger numbers
        pattern = re.compile(
            r'\b' + re.escape(old_val) + r'(\s*' + unit + r')',
            re.IGNORECASE
        )
        new_html = pattern.sub(new_val + r'\1', html)
        if new_html != html:
            print(f"  🔧 Consistency fix: {old_val} {unit} → {new_val} {unit}")
            html = new_html

    return html


# ── Source typo propagation guard ──────────────────────────────────────

# Common AI-propagated automotive typos: (wrong → correct)
_COMMON_TYPOS = [
    # "staring price" → "starting price" (very common in AI output)
    (re.compile(r'\bstaring\s+price\b', re.IGNORECASE), 'starting price'),
    (re.compile(r'\bstaring\s+at\b', re.IGNORECASE), 'starting at'),
    (re.compile(r'\bstaring\s+from\b', re.IGNORECASE), 'starting from'),
    (re.compile(r'\bstaring\s+EREV\b'), 'starting EREV'),
    (re.compile(r'\bstaring\s+model\b', re.IGNORECASE), 'starting model'),
    # Model-name "staring" used as trim name (e.g., "X9 staring") — flag in title too
    (re.compile(r'(\b[A-Z][A-Za-z0-9]+)\s+staring\b'), r'\1 Starting'),
    # Other common AI typos
    (re.compile(r'\bbraking\s+news\b', re.IGNORECASE), 'breaking news'),
    (re.compile(r'\bluxary\b', re.IGNORECASE), 'luxury'),
    (re.compile(r'\bvehcile\b', re.IGNORECASE), 'vehicle'),
    (re.compile(r'\bsedan\s+sedan\b', re.IGNORECASE), 'sedan'),
    (re.compile(r'\bSUV\s+SUV\b'), 'SUV'),
    (re.compile(r'\belectirc\b', re.IGNORECASE), 'electric'),
    (re.compile(r'\bkilowat\b', re.IGNORECASE), 'kilowatt'),
    (re.compile(r'\baccelration\b', re.IGNORECASE), 'acceleration'),
    (re.compile(r'\bpowertarin\b', re.IGNORECASE), 'powertrain'),
    (re.compile(r'\binfotainement\b', re.IGNORECASE), 'infotainment'),
    (re.compile(r'\bautonomus\b', re.IGNORECASE), 'autonomous'),
    (re.compile(r'\bwheelbaes\b', re.IGNORECASE), 'wheelbase'),
    (re.compile(r'\bchasis\b', re.IGNORECASE), 'chassis'),
    (re.compile(r'\bmanuever\b', re.IGNORECASE), 'maneuver'),
    (re.compile(r'\baerodynaminc\b', re.IGNORECASE), 'aerodynamic'),
]


def _clean_source_typos(html: str) -> str:
    """Fix common typos that AI copies from source data and repeats throughout."""
    original = html
    fixed_count = 0

    for pattern, replacement in _COMMON_TYPOS:
        new_html = pattern.sub(replacement, html)
        if new_html != html:
            count = len(pattern.findall(html))
            fixed_count += count
            html = new_html

    if fixed_count > 0:
        print(f"  🔤 Typo guard: fixed {fixed_count} propagated typo(s)")

    return html


# ── Empty compare card stripper ────────────────────────────────────────
def _strip_empty_compare_cards(html: str) -> str:
    """Remove compare-card divs that have no compare-row children (empty cards)."""
    # Match individual compare-card blocks (non-featured)
    card_pattern = re.compile(
        r'<div\s+class="compare-card">\s*'
        r'<div\s+class="compare-card-name">.*?</div>\s*'
        r'((?:<div\s+class="compare-row">.*?</div>\s*)*)'
        r'</div>',
        re.DOTALL
    )
    
    removed = 0
    def _check_card(m):
        nonlocal removed
        rows = m.group(1).strip()
        if not rows:
            removed += 1
            return ''  # Remove completely
        return m.group(0)
    
    html = card_pattern.sub(_check_card, html)
    
    if removed:
        print(f"  🗑️ Compare cards: removed {removed} empty competitor card(s)")
        # Clean up whitespace
        html = re.sub(r'\n\s*\n\s*\n', '\n\n', html)
    
    return html


# ── Dedup guard (shared helper) ────────────────────────────────────────
def _dedup_guard(html: str) -> str:
    """If the article's first H2 appears twice, trim at second occurrence."""
    first_h2 = re.search(r'<h2[^>]*>.*?</h2>', html, re.DOTALL)
    if first_h2:
        second_pos = html.find(first_h2.group(0), first_h2.end())
        if second_pos > 0:
            html = html[:second_pos].rstrip()
            print(f"  🔁 Dedup guard: trimmed duplicate content at position {second_pos}")
    return html


# ── Compare-grid structure repair ──────────────────────────────────────
def _repair_compare_grid(html: str) -> str:
    """
    Repair malformed compare-grid HTML where the AI closes divs too early,
    leaving compare-row / compare-card elements as siblings OUTSIDE the grid.

    Pattern to fix (raw string level — BS4 auto-repairs on parse so we can't use DOM):
        <div class="compare-grid">...<div class="compare-card featured">
          <div class="compare-row">Power...</div>
        </div></div>             ← compare-grid closed too early!
        <div class="compare-row">EV Range...</div>    ← orphaned
        <div class="compare-card">BMW...</div>         ← orphaned

    Strategy:
    1. Find </div> that closes a compare-grid (by tracking depth)
    2. Check if the content immediately following is compare-row or compare-card divs
    3. If yes, extract them and inject before the closing </div> of the grid
    """
    # Pattern: closing </div> followed by whitespace+newlines then compare-row/compare-card
    # We use a loop to handle multiple grids and multiple orphan runs
    ORPHAN_PATTERN = re.compile(
        r'(</div>)'                               # closing tag (candidate grid close)
        r'(\s*)'                                  # whitespace
        r'((?:'                                   # one or more orphaned blocks:
        r'<div\s+class="compare-(?:row|card)[^"]*">'  # compare-row or compare-card open
        r'.*?</div>'                              # content + close
        r'\s*'                                    # optional whitespace
        r')+)',                                   # end repeat
        re.DOTALL
    )

    def _is_grid_close(html, closing_pos):
        """Check if the </div> at closing_pos actually closes a compare-grid."""
        # Walk backward to find the matching opening tag
        depth = 0
        pos = closing_pos - 1
        while pos >= 0:
            # Find nearest opening or closing div tag going backward
            open_tag = html.rfind('<div', 0, pos + 1)
            close_tag = html.rfind('</div>', 0, pos + 1)
            if open_tag < 0:
                break
            if close_tag > open_tag:
                depth += 1
                pos = close_tag - 1
            else:
                if depth == 0:
                    # This open tag matches our closing — check if it's a compare-grid
                    tag_end = html.find('>', open_tag)
                    tag_text = html[open_tag:tag_end + 1]
                    return 'compare-grid' in tag_text
                depth -= 1
                pos = open_tag - 1
        return False

    if 'compare-grid' not in html:
        return html

    # Find all </div> followed by orphaned compare-* elements
    changed = False
    result = html

    # Use a single-pass regex scan with manual verification
    offset = 0
    max_iterations = 20  # Safety limit
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        m = ORPHAN_PATTERN.search(result, offset)
        if not m:
            break

        closing_div_pos = m.start(1)

        # Verify this </div> closes a compare-grid
        if not _is_grid_close(result, closing_div_pos):
            offset = m.end(1)
            continue

        # Extract the orphaned block
        orphaned_content = m.group(3)
        whitespace = m.group(2)

        # Rebuild: move orphaned content inside the grid before its closing </div>
        # i.e.: </div>[orphans] → [orphans]</div>
        replacement = orphaned_content.rstrip() + '\n' + m.group(1)
        result = result[:closing_div_pos] + replacement + result[m.end():]

        orphan_count = orphaned_content.count('<div class="compare-')
        print(f"  🔧 compare-grid repair: moved {orphan_count} orphaned element(s) inside grid")
        changed = True
        # Don't advance offset — re-check from same position (might be more to fix)

    return result if changed else html



def post_process_article(html: str) -> str:
    """
    Run the full post-processing pipeline on generated HTML.

    Includes: HTML cleanup, banned phrase removal, repetition reduction,
    price validation, duplicate paragraph detection, self-consistency,
    car name shortening, source typo fixes, and empty compare card removal.

    This is the single entry-point for callers (RSS generate, merge, publisher, etc.)
    """
    html = _repair_compare_grid(html)   # Fix malformed compare-grid structure first
    html = ensure_html_only(html)
    html = clean_banned_phrases(html)
    html = _reduce_repetition(html)
    html = _validate_prices(html)
    html = _detect_duplicate_paragraphs(html)
    html = _check_self_consistency(html)
    html = _shorten_car_names(html)
    html = _clean_source_typos(html)
    html = _strip_empty_compare_cards(html)
    return html
