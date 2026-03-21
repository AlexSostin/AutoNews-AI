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


# ── Hallucination guard for compare cards ──────────────────────────────
def _strip_hallucinated_compare_cards(html: str, allowed_makes: list[str]) -> str:
    """
    Remove compare-card divs whose car brand is NOT in the approved competitor list.

    LLMs sometimes ignore the 'CRITICAL: Do NOT invent' instruction and add cars
    from internal knowledge (e.g. Aito M7/M9 when they weren't in the DB list).
    This function parses the compare-card-name and checks if the make is allowed.

    Args:
        html: generated article HTML
        allowed_makes: list of brand names from competitor_lookup (e.g. ['BYD', 'Denza', 'VOYAH'])
                       If empty, no filtering is applied (safe fallback).
    Returns:
        Cleaned HTML with hallucinated cards removed.
    """
    if not allowed_makes:
        return html  # No allowlist — can't filter, skip

    if 'compare-grid' not in html:
        return html

    # Normalise allowed makes for case-insensitive matching
    allowed_lower = {m.strip().lower() for m in allowed_makes}

    # Pattern for non-featured cards (featured = subject car, never remove)
    card_pattern = re.compile(
        r'(<div\s+class="compare-card">\s*'
        r'<div\s+class="compare-card-name">(.*?)</div>'
        r'.*?'
        r'</div>)',
        re.DOTALL
    )

    removed_cards = []

    def _check_hallucinated(m):
        card_name = re.sub(r'<[^>]+>', '', m.group(2)).strip()  # plain text of card-name
        # Check if any allowed make appears in the card name (word-boundary aware)
        for make in allowed_lower:
            if re.search(r'\b' + re.escape(make) + r'\b', card_name, re.IGNORECASE):
                return m.group(0)  # Allowed — keep
        # Not in allowed list — this is a hallucinated card
        removed_cards.append(card_name)
        return ''

    html = card_pattern.sub(_check_hallucinated, html)

    if removed_cards:
        print(f"  🚫 Hallucination guard: removed {len(removed_cards)} invented competitor card(s): {removed_cards}")
        # Clean up leftover empty compare-grid
        html = re.sub(r'<div\s+class="compare-grid">\s*<div\s+class="compare-card featured">.*?</div>\s*</div>', 
                      lambda m: m.group(0) if 'compare-card">' in m.group(0) else '',
                      html, flags=re.DOTALL)
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
    leaving compare-row / compare-card elements as siblings OUTSIDE their proper parents.

    Strategy using DOM parsing:
    1. Fix orphaned compare-row inside grids (but outside compare-card) by moving them into the preceding compare-card.
    2. Fix orphaned compare-row/compare-card outside grids by pulling them back into the preceding compare-grid.
    """
    if 'compare-grid' not in html:
        return html

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("  ⚠️ BeautifulSoup not found, skipping deep compare-grid repair")
        return html

    soup = BeautifulSoup(html, 'html.parser')
    changed = False

    # 0. Fix bare spans that should have been compare-rows
    for span_k in soup.find_all('span', class_='k'):
        parent = span_k.parent
        # Check if already correctly wrapped in compare-row
        if parent and parent.name == 'div' and 'compare-row' in parent.get('class', []):
            continue
            
        span_v = span_k.find_next_sibling('span', class_='v')
        if span_v:
            new_row = soup.new_tag('div', **{'class': 'compare-row'})
            span_k.insert_before(new_row)
            new_row.append(span_k.extract())
            new_row.append(span_v.extract())
            changed = True

    # 1. Fix orphaned compare-row inside grids (but outside compare-card)
    for grid in soup.find_all('div', class_='compare-grid'):
        last_card = None
        for child in list(grid.children):
            if child.name == 'div' and 'compare-card' in child.get('class', []):
                last_card = child
            elif child.name == 'div' and 'compare-row' in child.get('class', []):
                if last_card:
                    last_card.append(child)
                    changed = True

    # 2. Fix orphaned compare-row and compare-card outside grids
    for grid in soup.find_all('div', class_='compare-grid'):
        sibling = grid.find_next_sibling()
        while sibling and sibling.name == 'div':
            sibling_classes = sibling.get('class', [])
            if 'compare-card' in sibling_classes:
                # Move card into the grid
                grid.append(sibling.extract())
                changed = True
                sibling = grid.find_next_sibling()
            elif 'compare-row' in sibling_classes:
                # Move row into the last card of the grid
                last_card = grid.find_all('div', class_='compare-card')
                if last_card:
                    last_card[-1].append(sibling.extract())
                    changed = True
                    sibling = grid.find_next_sibling()
                else:
                    break
            else:
                break

    if changed:
        print("  🔧 compare-grid repair: fixed malformed grid structure via DOM")
        return str(soup)
        
    return html

def _normalize_compare_rows(html: str) -> str:
    """
    Ensure all compare-cards in a compare-grid have identical row labels.
    
    If the AI used different labels across cards (e.g. 'Torque' in one,
    'Power' in another), this normalizes them to the most common label set.
    Missing rows get 'N/A' values.
    """
    import re
    from collections import Counter
    
    if 'compare-grid' not in html:
        return html
    
    # Find each compare-grid block
    grid_open_re = re.compile(r'<div\s+class="compare-grid">', re.IGNORECASE)
    row_re = re.compile(
        r'<div\s+class="compare-row">\s*<span\s+class="k">(.*?)</span>\s*<span\s+class="v">(.*?)</span>\s*</div>',
        re.DOTALL | re.IGNORECASE
    )
    card_open_re = re.compile(r'<div\s+class="compare-card(\s[^"]*)?">', re.IGNORECASE)
    
    result = html
    for grid_match in list(grid_open_re.finditer(html)):
        grid_start = grid_match.start()
        # Find the end of this grid: count div depth
        depth = 0
        pos = grid_start
        grid_end = None
        while pos < len(html):
            open_m = re.match(r'<div[\s>]', html[pos:], re.IGNORECASE)
            close_m = re.match(r'</div>', html[pos:], re.IGNORECASE)
            if open_m:
                depth += 1
                pos += open_m.end()
            elif close_m:
                depth -= 1
                if depth == 0:
                    grid_end = pos + close_m.end()
                    break
                pos += close_m.end()
            else:
                pos += 1
        
        if grid_end is None:
            continue
        
        grid_html = html[grid_start:grid_end]
        
        # Find all card boundaries
        card_matches = list(card_open_re.finditer(grid_html))
        if len(card_matches) < 2:
            continue
        
        # Extract each card's content by finding boundaries
        cards_data = []
        for ci, cm in enumerate(card_matches):
            card_start = cm.start()
            card_end = card_matches[ci + 1].start() if ci + 1 < len(card_matches) else grid_html.rfind('</div>')
            card_html = grid_html[card_start:card_end]
            
            css_class = (cm.group(1) or '').strip()  # e.g. 'featured' or ''
            rows = row_re.findall(card_html)  # list of (label, value) tuples
            
            # Extract badge and name
            badge_m = re.search(r'<div\s+class="compare-badge">(.*?)</div>', card_html, re.IGNORECASE)
            name_m = re.search(r'<div\s+class="compare-card-name">(.*?)</div>', card_html, re.IGNORECASE)
            
            cards_data.append({
                'css': css_class,
                'badge': badge_m.group(1) if badge_m else None,
                'name': name_m.group(1) if name_m else '',
                'rows': rows,  # [(label, value), ...]
            })
        
        # Get label sets from each card
        label_sets = [tuple(r[0].strip() for r in cd['rows']) for cd in cards_data]
        
        # Already consistent?
        if len(set(label_sets)) <= 1:
            continue
        
        # Find canonical labels (majority wins)
        canonical_labels = list(Counter(label_sets).most_common(1)[0][0])
        print(f"  🔧 compare-grid: normalizing {len(cards_data)} cards to labels {canonical_labels}")
        
        # Rebuild the grid
        new_cards = []
        for cd in cards_data:
            existing = {r[0].strip(): r[1].strip() for r in cd['rows']}
            
            lines = []
            css = f' {cd["css"]}' if cd['css'] else ''
            lines.append(f'<div class="compare-card{css}">')
            if cd['badge']:
                lines.append(f'<div class="compare-badge">{cd["badge"]}</div>')
            lines.append(f'<div class="compare-card-name">{cd["name"]}</div>')
            
            for label in canonical_labels:
                value = existing.get(label, 'N/A')
                lines.append(
                    f'<div class="compare-row"><span class="k">{label}</span>'
                    f'<span class="v">{value}</span></div>'
                )
            lines.append('</div>')
            new_cards.append('\n'.join(lines))
        
        new_grid = '<div class="compare-grid">\n' + '\n'.join(new_cards) + '\n</div>'
        result = result[:grid_start] + new_grid + result[grid_end:]
    
    return result


def post_process_article(html: str, allowed_competitor_makes: list[str] | None = None) -> str:

    """
    Run the full post-processing pipeline on generated HTML.

    Includes: HTML cleanup, banned phrase removal, repetition reduction,
    price validation, duplicate paragraph detection, self-consistency,
    car name shortening, source typo fixes, and empty/hallucinated compare card removal.

    Args:
        html: Raw HTML from LLM.
        allowed_competitor_makes: Optional list of brand names that were passed to the LLM
            as approved competitors (from competitor_lookup). Any compare-card whose make
            is NOT in this list is treated as a hallucination and removed.
            Pass None or [] to skip this check (e.g. when no competitor data was provided).

    This is the single entry-point for callers (RSS generate, merge, publisher, etc.)
    """
    html = _repair_compare_grid(html)   # Fix malformed compare-grid structure first
    html = _normalize_compare_rows(html) # Ensure all cards have identical row labels
    html = ensure_html_only(html)
    html = clean_banned_phrases(html)
    html = _reduce_repetition(html)
    html = _validate_prices(html)
    html = _detect_duplicate_paragraphs(html)
    html = _check_self_consistency(html)
    html = _shorten_car_names(html)
    html = _clean_source_typos(html)
    html = _strip_empty_compare_cards(html)
    if allowed_competitor_makes:
        html = _strip_hallucinated_compare_cards(html, allowed_competitor_makes)
    return html
