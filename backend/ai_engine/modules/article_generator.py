from groq import Groq
import sys
import os
import logging
from datetime import datetime
try:
    import markdown
except ImportError:
    markdown = None
import re

logger = logging.getLogger(__name__)

# Import config - try multiple paths, fallback to env
try:
    from ai_engine.config import GROQ_API_KEY, GROQ_MODEL
except ImportError:
    try:
        from config import GROQ_API_KEY, GROQ_MODEL
    except ImportError:
        GROQ_API_KEY = os.getenv('GROQ_API_KEY')
        GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')

# Import utils
try:
    from ai_engine.modules.utils import clean_title, calculate_reading_time, validate_article_quality, clean_html_markup
    from ai_engine.modules.ai_provider import get_ai_provider
    from ai_engine.modules.prompt_sanitizer import wrap_untrusted, sanitize_for_prompt, ANTI_INJECTION_NOTICE
except ImportError:
    from modules.utils import clean_title, calculate_reading_time, validate_article_quality, clean_html_markup
    from modules.ai_provider import get_ai_provider
    from modules.prompt_sanitizer import wrap_untrusted, sanitize_for_prompt, ANTI_INJECTION_NOTICE

# Legacy Groq client for backwards compatibility
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# ── Banned phrase post-processing ──────────────────────────────────────────
# Gemini sometimes ignores prompt bans.  This is the safety net.

_BANNED_SENTENCE_PATTERNS = re.compile(
    r'<(?:p|li)>[^<]*?('
    r'While a comprehensive driving review is pending'
    r'|While I haven\'t personally driven'
    r'|some assumptions can be made'
    r'|specific .{3,30} figures are still emerging'
    r'|specific .{3,30} figures are not available'
    r'|specific .{3,30} figures .{3,30} not .{3,30} released'
    r'|horsepower and torque figures are not specified'
    r'|exact battery capacity is not specified'
    r'|further details .{3,30} will be released'
    r'|pricing details .{3,30} have not been officially announced'
    r'|details .{3,30} are .{0,20}under wraps'
    r'|details .{3,30} are .{0,20}currently confidential'
    r'|details .{3,30} are yet to be .{3,30} detailed'
    r'|I wish I could dive'
    r'|the truth is, .{3,50} not .{3,30} released'
    r'|without official confirmation'
    r'|without concrete information'
    r'|we cannot .{3,30} any specific'
    r'|we can\'t speak to the'
    r'|information .{3,30} currently unavailable'
    r'|have not yet been officially released'
    r'|are currently confidential'
    r'|we\'d anticipate'
    r'|it\'s reasonable to expect'
    # Filler openers
    r'|isn\'t just another'
    r'|isn\'t just dipping'
    r'|isn\'t merely another'
    r'|this isn\'t your typical'
    r'|this isn\'t your average'
    # AI filler
    r'|a compelling proposition'
    r'|a compelling package'
    r'|for the discerning'
    r'|effectively eliminat(?:ing|es?) range anxiety'
    r'|in the evolving landscape'
    r'|prioritizing .{3,30} and .{3,30} comfort'
    r'|central to .{3,40} identity'
    # Lazy Cons
    r'|While specific cons .{3,60} aren\'t detailed'
    r'|While specific cons .{3,60} not .{3,30} detailed'
    # Cons about missing specs (NOT real cons)
    r'|[Ss]pecific .{3,60} (?:is |are )not (?:yet )?(?:detailed|public|available|confirmed|released)'
    r'|[Dd]etailed .{3,60} (?:is |are |have )not (?:been )?(?:publicly )?(?:available|released|detailed|confirmed)'
    r'|[Ee]xact .{3,40} (?:is |are )not (?:yet )?confirmed'
    r'|has not yet been officially announced'
    r'|details remain .{3,20} to be .{3,20} confirmed'
    r'|specifics have yet to be .{3,20} disclosed'
    r'|the complexity inherent in'
    r'|might be a consideration for some buyers'
    # Empty "still emerging" paragraphs
    r'|are still emerging'
    r'|remain to be seen'
    r'|only time will tell'
    r'|it remains to be seen'
    # Conversational filler paragraphs
    r'|this is where .{3,40} truly shines'
    r'|this is where .{3,40} really shines'
    r'|this is where things get .{3,20} interesting'
    ')[^<]*?</(?:p|li)>',
    re.IGNORECASE
)

_BANNED_INLINE_REPLACEMENTS = [
    # (pattern, replacement)
    (re.compile(r'is making waves (?:as |in )', re.I), 'is positioned as '),
    (re.compile(r'making waves in the .{3,30} segment', re.I), 'competing in this segment'),
    (re.compile(r'setting a new benchmark', re.I), 'raising the bar'),
    (re.compile(r'a hefty amount of torque', re.I), 'strong torque'),
    (re.compile(r'expected to be equipped', re.I), 'equipped'),
    (re.compile(r'anticipated to be a key component', re.I), 'a key component'),
    (re.compile(r'potentially with', re.I), 'with'),
    (re.compile(r'likely running', re.I), 'running'),
    (re.compile(r'is expected to feature', re.I), 'features'),
    (re.compile(r'it\'s reasonable to expect', re.I), 'we expect'),
    (re.compile(r'we can expect', re.I), 'expect'),
    (re.compile(r'we\'d anticipate', re.I), 'we expect'),
    (re.compile(r'As a journalist, I wish I could[^.]*\.\s*', re.I), ''),
    (re.compile(r'However, the truth is,?\s*', re.I), ''),
    (re.compile(r'details .{3,30} under wraps', re.I), 'details pending'),
    # Filler clichés
    (re.compile(r'isn\'t just dipping (?:its|their) toes[^.]*[.;]\s*', re.I), ''),
    (re.compile(r'they\'re cannonballing in[^.]*[.;]\s*', re.I), ''),
    (re.compile(r'nothing short of phenomenal[^.]*[.;]?', re.I), 'strong'),
    (re.compile(r'has been nothing short of', re.I), 'has been'),
    (re.compile(r'a prime example of .{3,40} strategy', re.I), 'a clear strategic move'),
    (re.compile(r'Not content to rest on (?:its|their) laurels,?\s*', re.I), ''),
    # AI-typical filler
    (re.compile(r'commanding (?:road |on-road )?presence', re.I), 'strong visual impact'),
    (re.compile(r'prioritiz(?:ing|es?) (?:both )?comfort and', re.I), 'balancing comfort and'),
    (re.compile(r'generous dimensions', re.I), 'large dimensions'),
    (re.compile(r'the market response has been .{3,30}phenomenal:?\s*', re.I), 'Market response: '),
    (re.compile(r'it\'s clear (?:that )?', re.I), ''),
    # Round 3: AITO M9 article filler
    (re.compile(r',? which is quite brisk(?:\s+for .{3,30})?', re.I), ''),
    (re.compile(r',? which sounds absolutely \w+', re.I), ''),
    (re.compile(r'\bWell, ', re.I), ''),
    (re.compile(r'for a touch of futuristic flair,?\s*', re.I), ''),
    (re.compile(r'for those wanting to stand out,?\s*', re.I), ''),
    (re.compile(r'for those (?:who|looking)\s+(?:want|prefer)\s+(?:to )?stand out,?\s*', re.I), ''),
    (re.compile(r'\bplus, for a touch of\b', re.I), 'Additionally, for'),
    (re.compile(r'(?:the )?real party trick (?:here )?is', re.I), 'The key figure is'),
    (re.compile(r'doing its thing,?\s*', re.I), 'working, '),
    (re.compile(r'a testament to its appeal', re.I), 'a sign of strong demand'),
    (re.compile(r'(?:Its|The) rapid ascent to a top.selling position[^.]*\.\s*', re.I), ''),
    # Clickbait / hype tone
    (re.compile(r'Hold on to your hats,?\s*(?:folks,?\s*)?(?:because\s*)?', re.I), ''),
    (re.compile(r'Buckle up,?\s*(?:folks,?\s*)?(?:because\s*)?', re.I), ''),
    (re.compile(r'Fasten your seatbelts,?\s*(?:because\s*)?', re.I), ''),
    (re.compile(r'(?:is|are)\s+(?:at it|back at it)\s+again,?\s*', re.I), ''),
    (re.compile(r'dropping\s+(?:another\s+)?bombshell(?:s)?', re.I), 'releasing'),
    (re.compile(r'eye[\s-]?watering', re.I), 'competitive'),
    (re.compile(r'jaw[\s-]?dropping', re.I), 'impressive'),
    (re.compile(r'mind[\s-]?blowing', re.I), 'notable'),
    (re.compile(r'game[\s-]?chang(?:ing|er)', re.I), 'significant'),
    (re.compile(r'this thing is set to make a serious splash', re.I), 'this model enters a competitive segment'),
    (re.compile(r'is here to shake up', re.I), 'targets'),
    (re.compile(r'forget (?:everything you knew about |about )?(?:range )?anxiety,?\s*', re.I), ''),
    (re.compile(r',?\s*folks\b', re.I), ''),
]


def _clean_banned_phrases(html: str) -> str:
    """Remove or replace banned filler phrases that Gemini sometimes ignores."""
    original_len = len(html)
    
    # 1. Remove entire <p> blocks that are pure filler
    html = _BANNED_SENTENCE_PATTERNS.sub('', html)
    
    # 2. Inline replacements for smaller phrases
    for pattern, replacement in _BANNED_INLINE_REPLACEMENTS:
        html = pattern.sub(replacement, html)
    
    # 3. Remove ALT_TEXT / SEO metadata that AI sometimes leaks into visible content
    # Remove entire hidden div block (when AI wraps it correctly)
    html = re.sub(r'<div\s+class="alt-texts"[^>]*>.*?</div>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove raw ALT_TEXT lines (when AI doesn't wrap them in a div)
    html = re.sub(r'(?:^|\n)\s*ALT_TEXT_\d+:.*?(?:\n|$)', '\n', html)
    # Remove "SEO Visual Assets:" header
    html = re.sub(r'<p>\s*(?:<strong>)?SEO Visual Assets:?(?:</strong>)?\s*</p>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'(?:^|\n)\s*SEO Visual Assets:?\s*(?:\n|$)', '\n', html, flags=re.IGNORECASE)

    # 3b. Remove <li> items that describe missing data (banned Cons in prompt)
    _banned_cons_rx = re.compile(
        r'<li>[^<]*(?:'
        r'(?:are|is)\s+not\s+(?:fully\s+)?(?:detailed|specified|disclosed|confirmed|announced|yet\s+public|provided|available)'
        r'|details?\s+(?:have\s+)?not\s+(?:yet\s+)?been\s+(?:released|confirmed|disclosed|provided)'
        r'|(?:specific|full|complete)\s+[^<]*(?:not\s+(?:available|provided|disclosed|released|detailed))'
        r'|not\s+yet\s+confirmed|remain\s+unknown|awaiting\s+(?:official\s+)?confirmation'
        r')[^<]*</li>',
        re.IGNORECASE
    )
    cleaned_cons = _banned_cons_rx.sub('', html)
    if cleaned_cons != html:
        removed_li = html.count('<li>') - cleaned_cons.count('<li>')
        print(f"  🧹 Removed {removed_li} invalid Cons items (missing-data phrases)")
        html = cleaned_cons

    # 4. Clean up empty paragraphs left behind
    html = re.sub(r'<p>\s*</p>', '', html)
    
    cleaned = original_len - len(html)
    if cleaned > 0:
        print(f"  🧹 Post-processing: removed {cleaned} chars of filler")
    
    return html


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

    # Find specs that appear in 5+ different body blocks (raised from 4 to reduce false positives)
    overused = {spec for spec, count in spec_counts.items() if count >= 5}
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


def enhance_existing_article(existing_html: str, specs: dict = None, provider='gemini'):
    """
    Enhance an existing article by enriching it with web search data.
    Instead of regenerating from scratch, takes the existing HTML as a template
    and asks AI to improve it with additional facts.
    
    Args:
        existing_html: The current article HTML content
        specs: Dict with make, model, year etc.
        provider: 'gemini' or 'groq'
    
    Returns:
        dict with 'title', 'content', 'summary' or None if enhancement fails
    """
    import re as _re
    from datetime import datetime
    
    if not existing_html or len(existing_html) < 200:
        return None
    
    # 1. Web search for additional facts
    web_context = ""
    if specs and specs.get('make') and specs.get('model'):
        try:
            from ai_engine.modules.searcher import get_web_context
            web_context = get_web_context(specs)
            if web_context:
                print(f"✓ Enhancement web search successful")
        except Exception as e:
            print(f"⚠️ Enhancement web search failed: {e}")
    
    if not web_context:
        print("⚠️ No web context found for enhancement, skipping")
        return None
    
    # 2. Build enhancement prompt
    current_date = datetime.now().strftime("%B %d, %Y")
    
    try:
        ai = get_ai_provider(provider)
    except Exception:
        try:
            from modules.ai_provider import get_ai_provider as _get
            ai = _get(provider)
        except Exception:
            return None
    
    prompt = f"""TODAY'S DATE: {current_date}

You are an expert automotive journalist. You have an EXISTING article that is already well-written.
Your job is to ENHANCE it — not rewrite it. Keep the same tone, structure, and personality.

EXISTING ARTICLE:
{wrap_untrusted(existing_html, 'EXISTING_ARTICLE')}

CRITICAL WEB DATA — ADD THESE FACTS TO THE ARTICLE:
{wrap_untrusted(web_context, 'WEB_CONTEXT')}
{ANTI_INJECTION_NOTICE}

INSTRUCTIONS:
1. Keep the SAME structure, headings, and overall tone of the existing article
2. ADD any new facts from the web data: sales figures, real test results, market reception, detailed specs
3. FILL IN any sections that are thin or vague with concrete data from the web search
4. FIX any factual errors if the web data contradicts the existing article
5. If the article has a Pros & Cons section, make sure cons are REAL downsides (not "specs unknown")
6. If FreshMotors Verdict is empty or cut off, write a compelling 2-3 sentence verdict
7. Do NOT add filler or padding — only add REAL information
8. Do NOT change the car name, year, or model designation
9. Output ONLY clean HTML (h2, p, ul, li tags) — NO html/head/body tags

OUTPUT the complete enhanced article as HTML."""

    system_prompt = "You are an expert automotive journalist enhancing an existing article with new facts. Keep the original tone and add only real, verified information."
    
    try:
        enhanced = ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,  # Lower temperature for factual enhancement
            max_tokens=16384
        )
        
        if not enhanced or len(enhanced) < 200:
            return None
        
        # Clean up
        enhanced = ensure_html_only(enhanced)
        enhanced = _clean_banned_phrases(enhanced)
        enhanced = _reduce_repetition(enhanced)
        enhanced = _shorten_car_names(enhanced)
        
        # Extract title
        title_match = _re.search(r'<h2[^>]*>(.*?)</h2>', enhanced)
        title = title_match.group(1) if title_match else None
        if title:
            title = _re.sub(r'<[^>]+>', '', title).strip()
        
        # Extract summary
        summary_match = _re.search(r'<p>(.*?)</p>', enhanced)
        summary = ''
        if summary_match:
            summary = _re.sub(r'<[^>]+>', '', summary_match.group(1))[:300]
        
        word_count = len(_re.sub(r'<[^>]+>', ' ', enhanced).split())
        print(f"✓ Enhancement complete: {word_count} words")
        
        return {
            'title': title,
            'content': enhanced,
            'summary': summary,
            'word_count': word_count,
        }
        
    except Exception as e:
        print(f"❌ Enhancement failed: {e}")
        return None


def generate_article(analysis_data, provider='gemini', web_context=None, source_title=None, competitor_context=None):
    """
    Generates a structured HTML article based on the analysis using selected AI provider.
    
    Args:
        analysis_data: The analysis from the transcript
        provider: 'groq' (default) or 'gemini'
        web_context: Optional string containing web search results
        source_title: Original title from RSS/YouTube source (for entity grounding)
        competitor_context: Optional pre-formatted competitor block from competitor_lookup.py
    
    Returns:
        HTML article content
    """
    provider_display = "Groq" if provider == 'groq' else "Google Gemini"
    print(f"Generating article with {provider_display}...")

    has_competitors = bool(competitor_context)
    
    web_data_section = ""
    if web_context:
        web_data_section = f"\nCRITICAL WEB DATA — USE THIS IN YOUR ARTICLE (sales figures, real specs, market reception, test results):\n{wrap_untrusted(web_context, 'WEB_CONTEXT')}\n{ANTI_INJECTION_NOTICE}"

    competitor_section = ""
    if has_competitors:
        competitor_section = (
            f"\n{'='*47}\n"
            f"COMPETITOR REFERENCE (from our database):\n"
            f"{competitor_context}\n"
            f"REQUIRED: Include a <h2>How It Compares</h2> section that uses these exact figures.\n"
            f"{'='*47}\n"
        )
    else:
        competitor_section = (
            "\n⚠️ NO competitor data available from our database for this car.\n"
            "Do NOT include a 'How It Compares' section. Do NOT fabricate competitor comparisons.\n"
            "Instead, add more depth to the Driving Experience and Technology sections.\n"
        )
    
    # Build entity anchor from source title (Layer 1: anti-hallucination)
    entity_anchor = ""
    if source_title:
        try:
            from ai_engine.modules.entity_validator import build_entity_anchor
            entity_anchor = build_entity_anchor(source_title)
            if entity_anchor:
                entity_anchor = f"\n{entity_anchor}\n"
        except Exception:
            pass
    
    current_date = datetime.now().strftime("%B %Y")
    
    # Load few-shot examples
    few_shot_block = ""
    try:
        try:
            from ai_engine.modules.few_shot_examples import get_few_shot_examples
        except ImportError:
            from modules.few_shot_examples import get_few_shot_examples
        few_shot_block = get_few_shot_examples(provider)
    except Exception as e:
        print(f"⚠️ Could not load few-shot examples: {e}")
    
    prompt = f"""
{entity_anchor}
{web_data_section}
{competitor_section}
TODAY'S DATE: {current_date}. Use this to determine what is "upcoming", "current", or "past". Do NOT reference dates that have already passed as future events.

Create a professional, SEO-optimized automotive article based on the analysis below.
Output ONLY clean HTML content (use <h2>, <p>, <ul>, etc.) - NO <html>, <head>, or <body> tags.

═══════════════════════════════════════════════
GOLDEN RULE — TRUTH OVER COMPLETENESS
═══════════════════════════════════════════════
- ONLY state facts that come from the analysis data, web context, or your VERIFIED training knowledge
- If a spec (HP, price, range, torque) is NOT in the source data and you are NOT confident about it → SKIP IT. Do not guess.
- Clearly separate CONFIRMED facts from EXPECTED/RUMORED information:
  ✅ "The BYD Seal produces 313 hp" (confirmed, on sale)
  ✅ "The interior is expected to feature a 15-inch display, based on spy shots" (clearly marked as expected)
  ❌ "The MG7 Electric produces 250 hp and 300 Nm" (fabricated numbers)
- It is BETTER to write a shorter, accurate article than a longer one full of made-up specs
- When comparing to competitors, ONLY use numbers you are confident about

CRITICAL REQUIREMENTS:
1. **Title** — descriptive, engaging, unique
   Include: YEAR, BRAND, MODEL, and if available PRICE or VERSION
   NO static prefixes like "First Drive:". NO HTML entities.
   If the model name contains a NUMBER that represents a spec (e.g. "TANG 1240" where 1240 = range,
   "EX90" where 90 = battery kWh), EXPLAIN IT in the title or subtitle:
   ✅ "2026 BYD TANG 1240: 7-Seater PHEV with 1,240 km Range for $26,000"
   ❌ "2026 BYD TANG 1240: A PHEV SUV Starting at $26,000" (what is 1240?)
   Example: "2025 BYD Seal 06 GT: A Powerful Electric Hatchback for $25,000"

2. **Engaging Opening** — write like a journalist, not a spec sheet:
   ✅ "BYD's latest plug-in hybrid SUV undercuts most competitors by $10,000 — and matches their range"
   ✅ "The Zeekr 7X brings 421 hp and 600 km of range to a segment dominated by Tesla"
   ✅ "AITO's M8 REV has already racked up over 80,000 orders — and it's been on sale for just a month"
   ❌ "The 2026 MG7 Electric Sedan is a new vehicle that promises to deliver..." (boring, generic)
   ❌ "Hold on to your hats, folks" / "Buckle up" (clickbait)
   The opening should hook readers with the MOST INTERESTING FACT from the source data.

3. **Write with PERSONALITY** — your tone should feel like an expert journalist, not a database:
   - Use CONFIDENT, opinionated language: "This is a serious contender" not "This vehicle is positioned in the market"
   - Give the car a PERSONALITY: "This is the daily driver for someone who's outgrown their Model 3"
   - Add real-world context: "600 km WLTP range means weekend trips without touching a charger"
   - Explain what specs MEAN for the buyer, not just list numbers
   - USE WEB CONTEXT DATA: If web search found sales figures, orders, market reception, awards,
     or real-world test data — INCLUDE IT in the article. This is the most valuable data you have.
     ✅ "Over 80,000 firm orders within a month of launch" — this is GOLD, always include real numbers
     ✅ "Edmunds testing showed 0-60 in 4.8 seconds" — real test data beats factory claims
     ❌ Ignoring web search data and only writing about dimensions and price — NEVER do this

3b. **Car Name Usage** — DO NOT repeat the full name ("The 2026 BYD TANG 1240") every sentence.
   - First mention: full name with year → "The 2026 BYD TANG 1240"
   - After that: use SHORT forms → "the TANG 1240", "the TANG", "this SUV", "it", "the car"
   - NEVER start 3 consecutive paragraphs with "The [Year] [Brand] [Model]"

4. **Competitor comparisons** — use them ONLY when you have REAL data:
   - 1-2 well-chosen comparisons are better than 4 forced ones
   - ONLY compare specs you are confident about
   ✅ "At $28,100, it costs nearly half what a Model Y does in Europe"
   ❌ "It competes with the Tesla Model 3 (250 hp), BMW i4 (335 hp), Hyundai Ioniq 5 (320 hp), Audi e-tron (355 hp)..." (list spam)

5. **Word count**: TARGET 1000-1400 words. Aim for 1100-1300 words as the sweet spot.
    MINIMUM REQUIREMENT: 1000 words (articles shorter than this will be retried).
    If source data is rich (full specs, features, pricing), write a COMPREHENSIVE 1200-1400 word article.
    QUALITY always beats QUANTITY. Every sentence should earn its place.

    **STRUCTURE REQUIREMENT**: Your article MUST contain between 3 and 7 <h2> section headings
    (not counting the title). Use this range consistently — never fewer than 3, never more than 7.
    Do NOT pad with long feature lists or exhaustive option packages.
    DO include deep technical explanations — what does the powertrain architecture mean for the driver?
    DO explain real-world implications of specs — what does 1508 km range mean for road trips?

6. **THIN DATA MODE** — If the source only has 3-5 confirmed specs:
   - Write 600-700 words using ONLY what you know. Do NOT pad.
   - Use structure: Introduction → What We Know → Pricing → Verdict.
   - SKIP Performance, Technology, Driving Experience sections entirely.
   - Do NOT write paragraphs explaining what you DON'T know.
   - A tight 450-word article with 4 solid paragraphs > a bloated 1000-word article full of repetition.

7. ═══ ANTI-REPETITION (CRITICAL — your article will be POST-PROCESSED to catch violations) ═══
   Do NOT repeat the same fact, number, or claim more than ONCE in the entire article.
   If you've stated "92% efficiency" in the introduction → do NOT restate it in later sections.
   Each paragraph must add NEW information, not rephrase previous paragraphs.

   ❌ BAD (will be auto-detected and trimmed):
   "The M8 REV has 1505 km range. [para 1]
    With its impressive 1505 km range, the M8 REV... [para 3]
    The 1505 km combined range means... [para 5]
    ...offering 1505 km of travel... [para 8]"

   ✅ GOOD (state once, build on it):
   "The M8 REV's 1505 km combined range — enough for Shanghai to Beijing without stopping. [para 1]
    That figure translates to roughly two weeks of average commuting on a single tank+charge. [para 5]"

   RULE: Any spec/number appearing in 3+ separate paragraphs = REPETITION = article will be trimmed.
   RULE: Any descriptive phrase ("6-seater", "commanding presence") appearing 3+ times = REPETITION.

26. **REGION-NEUTRAL writing**:
   - Do NOT focus on a single country's market (no "in Australia", "in the US", etc.)
   - Present prices in the ORIGINAL currency from the source, but don't frame the article around one country
   - Use STANDARD CURRENCY CODES: CNY (not RMB), JPY (not ¥), KRW, EUR, GBP, AUD, etc.
   - ALWAYS include approximate USD conversion: "CNY 299,800 (approximately $42,000)"
   - NEVER speculate about US market entry, US tariffs, or North American availability for Chinese or European EVs. Do NOT add sections like "Will it come to the US?".
   - Do NOT reference country-specific safety ratings (ANCAP, IIHS, NHTSA) as the main focus — mention briefly if relevant
   - Do NOT include country-specific warranty terms, servicing plans, or dealer networks
   - Write for a GLOBAL car enthusiast audience
   - If the source is from one country (e.g. an Australian review), extract the universal car facts and skip the local market commentary

⚠️ CRITICAL MODEL ACCURACY WARNING:
- CAREFULLY verify the EXACT car model from the video title and transcript
- DO NOT confuse similar model names (e.g., "Zeekr 7X" vs "Zeekr 007" are DIFFERENT cars)
- If uncertain, use the EXACT name from the video title

NEGATIVE CONSTRAINTS:
- NO "Advertisement", "Ad Space", or "Sponsor" blocks
- NO placeholder text like "[Insert Image Here]"
- NO social media links, navigation menus, or "Read more" links
- NO HTML <html>, <head>, or <body> tags

═══════════════════════════════════════════════
CRITICAL — OMIT EMPTY SECTIONS
═══════════════════════════════════════════════
If you have NO real data for a section → DO NOT INCLUDE THAT SECTION AT ALL.
Do NOT write a section that says "details are under wraps" or "figures have not been released".
❌ NEVER write a paragraph explaining WHY you don't have data.
❌ NEVER write "As a journalist, I wish I could..." or "the truth is..."
❌ NEVER write an entire section about what MIGHT be or what we CAN EXPECT.
If Performance has no confirmed specs → OMIT the Performance section entirely.
If Technology has no confirmed features → OMIT the Technology section entirely.
A 500-word article with 4 solid sections > 1200-word article with 8 empty ones.

BANNED PHRASES — article will be REJECTED if these appear:
- "specific horsepower figures are not available" or any "not specified" for specs
- "have not yet been officially released" / "are currently confidential"
- "details are under wraps" / "details are yet to be revealed"
- "expected to be equipped" / "anticipated to be" / "potentially with"
- "While a comprehensive driving review is pending"
- "specific [X] figures are still emerging"
- "The [brand] is committed to [generic goal]"
- "making waves in the [X] segment" / "setting a new benchmark"
- "I wish I could" / "the truth is" / "without concrete information"
- "it's reasonable to expect" / "we'd anticipate" / "we can expect"
- "As a journalist" / "While I haven't personally"
- Any sentence that says you DON'T HAVE information → DELETE that sentence
- If you don't know a spec → SKIP the claim. Don't pad with filler.

BANNED TONE — DO NOT write like a clickbait blog:
- "Hold on to your hats" / "Buckle up" / "Fasten your seatbelts"
- "eye-watering" / "jaw-dropping" / "mind-blowing" / "game-changing"
- "this thing is set to make a serious splash" / "dropping a bombshell"
- "Forget [X]" / "Forget everything you knew"
- "is here to shake up" / "disrupting the market"
- "folks" / "guys" / "people" (casual address)
- Excessive exclamation marks
- Write with CONFIDENCE and AUTHORITY, not hype. Let the specs speak for themselves.

PROS & CONS RULES:
- ONLY list things that are KNOWN and REAL.
- Cons must describe REAL WEAKNESSES of the product/technology itself:
  ✅ "No Apple CarPlay — a dealbreaker for many"
  ✅ "Heavy 2.5-ton curb weight hurts handling"
  ✅ "Interior plastics feel cheap for the price point"
  ❌ "Currently in research phase" — NOT a con (it's the product's stage, not a flaw)
  ❌ "No commercial availability" — NOT a con
  ❌ "Further details not yet public" — NOT a con (it's missing info)
  ❌ "Limited charging infrastructure" — NOT a con of the CAR itself
  ❌ "Specs are unknown" or "pricing unavailable" — NOT a con, it's missing data
  ❌ "No international availability confirmed" — NOT a con unless competitors ARE available globally
  ❌ "Specific performance metrics... are not yet public" — NOT a con
  ❌ "Detailed battery specifications... have not been released" — NOT a con
  ❌ "Not yet been officially announced" — NOT a con
  ❌ ANY con that mentions specs/details being "not available", "not released", "not detailed", or "not public" — DELETE IT
- If you cannot find 3 real Cons → list only what you have.
  2 genuine Cons > 4 filler Cons. NEVER pad the list.
- Cons should be about the CAR's actual weaknesses, not about missing press info.

WHY THIS MATTERS section — add context about the car's significance:
- What gap does this car fill in the market?
- Why should someone pay attention to this model?
- What does this mean for the brand's lineup?

Required Structure (OMIT any section where you have NO data):
- <h2>[Year] [Brand] [Model] [Version]: [Engaging Hook]</h2>
- Introduction paragraph with hook + key confirmed specs
- <h2>Performance & Specs</h2> — ONLY if you have real numbers.
  Include ONLY specs you have data for. Skip unknown ones entirely.
  If HP is in kW, convert: 1 kW ≈ 1.34 hp.
  If NO specs are available → OMIT this section.

  ═══ POWERTRAIN SPEC TEMPLATE (MANDATORY for this section) ═══
  For EACH motor/engine in the car, list SEPARATELY:

  ▸ PLATFORM: [e.g. SEA (Geely), e-Platform 3.0 (BYD), MEB (VW), CMA (Volvo/Geely), E-GMP (Hyundai/Kia)] — ONLY if known
  ▸ VOLTAGE ARCHITECTURE: [400V or 800V] — determines charging speed. 800V = ultra-fast DC charging (10-80% in ~18 min)
  ▸ POWERTRAIN TYPE: [BEV | EREV | PHEV | ICE | Hybrid]
  ▸ MOTOR 1 (traction): [type e.g. permanent magnet] — [HP] / [kW] — [torque Nm] — drives [front/rear/all]
  ▸ MOTOR 2 (if dual-motor): [type] — [HP] / [kW] — [torque Nm] — drives [front/rear]
  ▸ RANGE EXTENDER (if EREV/PHEV): [engine type e.g. 1.5T turbo] — [HP] / [kW]
    ⚠️ This is a GENERATOR — it does NOT drive the wheels. NEVER list this as the car's power.
  ▸ TOTAL SYSTEM OUTPUT: [combined HP] — this is the headline number readers care about
  ▸ BATTERY: [capacity kWh] — [chemistry e.g. LFP/NMC/ternary lithium] — [supplier e.g. CATL/BYD]
  ▸ RANGE: [electric-only km] + [combined km if EREV/PHEV] — [test cycle: WLTP/CLTC/EPA]
  ▸ 0-100 km/h: [seconds] — ONLY if confirmed
  ▸ TOP SPEED: [km/h] — ONLY if confirmed
  ▸ DIMENSIONS: length × width × height (mm), wheelbase (mm), curb weight (kg)

  ⚠️ CRITICAL EREV/PHEV/HYBRID RULES:
  - The RANGE EXTENDER is a generator that charges the battery. It does NOT drive the wheels.
  - NEVER list range extender HP as the car's total power.
  - ALWAYS clarify: "The 1.5T range extender (XX kW) charges the battery;
    the electric traction motor (XX kW / XX HP) drives the [rear/all] wheels."
  - If the source only provides ONE power figure for an EREV → it could be the range extender.
    Research which motor it refers to before publishing.

  ⚠️ SANITY CHECKS — if these fail, the data is likely WRONG:
  - Full-size SUV (5+ meters) with TOTAL power under 150 HP → VERIFY, almost certainly wrong
  - Sports car / GT with under 200 HP → VERIFY
  - Any car with 0-100 under 5s but under 300 HP → VERIFY
  - EREV with only one HP figure → it might be the generator, NOT the traction motor
  ═══════════════════════════════════════════════

- <h2>Design & Interior</h2> — Styling, materials, space.
  Compare design language to ONE well-known car if the comparison is genuine and insightful.
  Focus on what IS visible/confirmed, not what might be.
  Describe cabin layout, screen sizes, materials quality, seating capacity, cargo space.
- <h2>Technology & Features</h2> — List SPECIFIC items from the source data.
  Include ADAS/autonomous driving hardware (radars, cameras, LiDAR), infotainment chip,
  audio system, connectivity (4G/5G), V2L capability, smart keys, OTA updates.
  Only mention features that are confirmed. If NO features are confirmed → OMIT this section.
- <h2>Driving Experience</h2> — How does this car FEEL to drive?
  On-road refinement, off-road capability (if SUV), ride comfort, noise levels, steering feel,
  suspension type (air, adaptive, etc.), ground clearance, approach/departure angles (if SUV/off-road).
  If the source has driving impressions — include them. If not, describe what the specs SUGGEST:
  e.g. "With 2,185 kg curb weight and AWD, expect planted highway stability but reduced agility in tight corners"
  This section brings the car to life — make the reader FEEL what it's like behind the wheel.
  If NO driving data exists → OMIT this section.
- <h2>Pricing & Availability</h2> — CONCISE, 3-5 bullet points:
  <ul><li>Only confirmed prices and markets</li></ul>
  Do NOT fabricate MSRP prices. If pricing is unknown, say "pricing has not been announced yet."
- <h2>Pros & Cons</h2> — Use <ul><li> tags. Punchy, specific, based on REAL attributes:
  ✅ "1602 km range crushes everything in its class"
  ✅ "No Apple CarPlay — a dealbreaker for many"
  ❌ "Range is impressive" (too vague)
  ❌ "Specs are unknown" (NOT a con — it's missing info)
- <h2>FreshMotors Verdict</h2> — THIS SECTION IS MANDATORY AND MUST CONTAIN REAL CONTENT (minimum 60-80 words).
  Write a compelling, opinionated verdict about who should buy this car and why.
  Be specific: "The daily driver for someone who's outgrown their Model 3" or
  "A rugged weekend warrior that doubles as a comfortable commuter".
  Mention 1-2 standout strengths, 1 weakness, and a final recommendation.
  ⚠️ DO NOT leave this section empty or with only the heading — it MUST have a full paragraph of at least 60 words.

AT THE VERY END, add:
<div class="alt-texts" style="display:none">
ALT_TEXT_1: [descriptive alt text for hero/exterior image]
ALT_TEXT_2: [descriptive alt text for interior image]
ALT_TEXT_3: [descriptive alt text for detail/tech image]
</div>

{few_shot_block}

Analysis Data:
{analysis_data}

{f'FINAL CHECK: The vehicle name MUST be exactly as specified in the MANDATORY VEHICLE IDENTITY section above. If you wrote a different model name or number, your article is WRONG. Go back and fix it.' if entity_anchor else ''}

Remember: TARGET 1100-1300 words. Each main section (Performance, Design, Technology, Driving Experience) must have at least 2 full paragraphs. Write with depth — explain what specs mean for real-world driving, not just listing numbers. Do NOT stop writing early. FreshMotors Verdict is MANDATORY and must be written last.
"""
    
    system_prompt = """You are a senior automotive journalist at FreshMotors. You write with technical precision and confident authority — think Autocar or Car and Driver, not a YouTube vlog. You prioritize ACCURACY over completeness: if you don't know a spec, you skip it rather than guess. You write for car enthusiasts who want honest, data-driven analysis. You compare to competitors ONLY when you have real data. Your tone is professional but accessible — authoritative without being dry, engaging without being clickbait. You know major car brands well (including Chinese EVs), but you never fabricate specs you're unsure about. Let the facts and specs make the impression — no hype words needed.

CRITICAL WORD COUNT RULE: Your article MUST be at minimum 1000 words, targeting 1100-1300 words. Count your words as you write. Every major section (Performance, Design, Technology, Driving Experience) must have at least 2 full paragraphs. Do NOT stop writing until you have covered all sections with sufficient depth. SHORT articles will be automatically rejected and regenerated."""
    
    try:
        # Use AI provider factory
        ai = get_ai_provider(provider)
        
        MIN_WORD_COUNT = 1000  # Minimum acceptable article length
        MAX_RETRIES = 3       # Retry if too short or missing structure
        
        article_content = None
        for attempt in range(MAX_RETRIES):
            current_prompt = prompt
            if attempt > 0 and article_content:
                # Smart retry: detect what's missing and ask for targeted improvements
                analysis = _detect_missing_sections(article_content, word_count, has_competitors=has_competitors)
                if analysis['needs_retry']:
                    current_prompt = analysis['retry_prompt'] + prompt
                    missing_str = ', '.join(analysis['missing_sections']) if analysis['missing_sections'] else 'none'
                    thin_str = ', '.join(analysis['thin_sections']) if analysis['thin_sections'] else 'none'
                    print(f"🔄 Smart Retry #{attempt}: {word_count} words | missing: {missing_str} | thin: {thin_str}")
                else:
                    break  # Article structure is fine, no point retrying
            
            article_content = ai.generate_completion(
                prompt=current_prompt,
                system_prompt=system_prompt,
                temperature=0.65,
                max_tokens=16384
            )
            
            if not article_content:
                raise Exception(f"{provider_display} returned empty article")
            
            # Check word count
            stripped = re.sub(r'<[^>]+>', ' ', article_content)
            word_count = len(stripped.split())
            print(f"  Attempt {attempt + 1}: {word_count} words, {len(article_content)} chars")
            
            if word_count >= MIN_WORD_COUNT:
                # Also check structure quality on first attempt
                if attempt == 0:
                    analysis = _detect_missing_sections(article_content, word_count, has_competitors=has_competitors)
                    if analysis['needs_retry'] and (analysis['missing_sections'] or analysis['thin_sections']):
                        print(f"  📋 Structure check: needs improvement, will retry")
                        continue  # Force a smart retry even if word count is OK
                break  # Good enough
        
        if word_count < MIN_WORD_COUNT:
            print(f"⚠️ Article still short after {MAX_RETRIES} attempts: {word_count} words")
            
        print(f"✓ Article generated successfully with {provider_display}! Length: {len(article_content)} characters, {word_count} words")
        
        # Post-processing: ensure it's HTML, not Markdown
        article_content = ensure_html_only(article_content)
        article_content = _clean_banned_phrases(article_content)
        article_content = _reduce_repetition(article_content)
        article_content = _shorten_car_names(article_content)
        
        # Проверка качества статьи
        quality = validate_article_quality(article_content)
        if not quality['valid']:
            print("⚠️  Article quality issues:")
            for issue in quality['issues']:
                print(f"   - {issue}")
        
        # Вычисляем время чтения
        reading_time = calculate_reading_time(article_content)
        print(f"📖 Reading time: ~{reading_time} min")

        # Запуск Fact-Checking (если есть web_context)
        if web_context:
            try:
                print("🕵️ Running secondary LLM Fact-Check pass...")
                from ai_engine.modules.fact_checker import run_fact_check
                article_content = run_fact_check(article_content, web_context, provider)
            except Exception as fc_err:
                print(f"⚠️ Fact-check module failed: {fc_err}")
        
        # (Entity validation removed — entity_anchor in prompt is sufficient)
        # (RLAIF Judge removed — was the main source of content truncation/duplication)
        
        # Dedup guard: if the article's first H2 appears twice, trim at second occurrence
        first_h2 = re.search(r'<h2[^>]*>.*?</h2>', article_content, re.DOTALL)
        if first_h2:
            second_pos = article_content.find(first_h2.group(0), first_h2.end())
            if second_pos > 0:
                article_content = article_content[:second_pos].rstrip()
                print(f"  🔁 Dedup guard: trimmed duplicate content at position {second_pos}")

        # Guaranteed verdict injector — runs a separate short API call if verdict is empty/missing
        article_content = _ensure_verdict_written(article_content, analysis_data, provider)

        return article_content
    except Exception as e:
        logger.error(f"Article generation failed with {provider_display}: {e}")
        logger.error(f"Failed analysis_data (first 500 chars): {str(analysis_data)[:500]}")
        print(f"❌ Error during article generation with {provider_display}: {e}")
        
        # Provider fallback: try alternate provider
        fallback = 'gemini' if provider == 'groq' else 'groq'
        fallback_display = 'Google Gemini' if fallback == 'gemini' else 'Groq'
        try:
            print(f"🔄 Retrying with fallback provider: {fallback_display}...")
            ai_fallback = get_ai_provider(fallback)
            article_content = ai_fallback.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.65,
                max_tokens=16384
            )
            if article_content:
                print(f"✓ Fallback successful with {fallback_display}!")
                article_content = ensure_html_only(article_content)
                article_content = _clean_banned_phrases(article_content)
                return article_content
        except Exception as fallback_err:
            logger.error(f"Fallback also failed with {fallback_display}: {fallback_err}")
        
        return ""


def _ensure_verdict_written(html: str, analysis_data, provider: str = 'gemini') -> str:
    """
    Post-generation guarantee: if FreshMotors Verdict section is missing or empty,
    make a short targeted API call to write a proper verdict and inject it.
    """
    import re as _re

    # Check if verdict heading exists and has content
    verdict_match = _re.search(
        r'(<h2[^>]*>[^<]*(?:verdict|conclusion|final)[^<]*</h2>)(.*?)(?=<h2|<div class="alt-texts"|$)',
        html, _re.IGNORECASE | _re.DOTALL
    )

    if verdict_match:
        verdict_content = _re.sub(r'<[^>]+>', ' ', verdict_match.group(2)).strip()
        verdict_words = len(verdict_content.split())
        if verdict_words >= 30:
            return html  # Verdict looks fine
        verdict_heading_html = verdict_match.group(1)
        print(f"  🔧 Verdict injector: found heading but only {verdict_words} words — generating verdict...")
    else:
        verdict_heading_html = '<h2>FreshMotors Verdict</h2>'
        print(f"  🔧 Verdict injector: verdict section missing — generating verdict...")

    # Extract article context for the verdict prompt
    article_text = _re.sub(r'<[^>]+>', ' ', html)[:2500]  # first 2500 chars of plain text

    verdict_prompt = f"""You are writing the final section of an automotive article for FreshMotors.com.

Here is the article so far (plain text summary):
{article_text}

Write ONLY the FreshMotors Verdict section — a single paragraph of 70-100 words.
Rules:
- Be specific and opinionated about WHO should buy this car and WHY
- Mention 1-2 real strengths (use specific specs from the article)  
- Mention 1 genuine weakness or caveat
- End with a clear recommendation
- Write in plain prose — NO bullet points, NO subheadings
- Output ONLY the verdict paragraph wrapped in <p> tags, nothing else
- Do NOT include the <h2>FreshMotors Verdict</h2> heading — just the paragraph

Example of good verdict:
<p>The VOYAH Taishan 1430 is the ultimate long-haul family SUV for buyers who want to leave range anxiety behind permanently. Its 1,430 km combined range and 350 km electric-only capability make it genuinely useful for both daily commutes and cross-country trips, while the Huawei-powered tech stack keeps it feeling premium throughout. The 2.8-ton curb weight is a real-world caveat, but for families prioritizing space and range over outright agility, this is a serious contender at its price point.</p>
"""

    try:
        ai = get_ai_provider(provider)
        verdict_para = ai.generate_completion(
            prompt=verdict_prompt,
            system_prompt="You are a precise automotive journalist. Output only a single <p> paragraph as instructed.",
            temperature=0.7,
            max_tokens=300
        )

        if verdict_para:
            verdict_para = verdict_para.strip()
            # Ensure it's wrapped in <p>
            if not verdict_para.startswith('<p'):
                verdict_para = f'<p>{verdict_para}</p>'

            # Remove any heading the model might have added
            verdict_para = _re.sub(r'<h2[^>]*>.*?</h2>', '', verdict_para, flags=_re.IGNORECASE | _re.DOTALL).strip()

            verdict_block = f'{verdict_heading_html}\n{verdict_para}'

            if verdict_match:
                # Replace the existing empty verdict
                html = html[:verdict_match.start(1)] + verdict_block + html[verdict_match.end():]
            else:
                # Insert before alt-texts div or at the end
                alt_pos = html.find('<div class="alt-texts"')
                if alt_pos > 0:
                    html = html[:alt_pos] + verdict_block + '\n\n' + html[alt_pos:]
                else:
                    html = html.rstrip() + '\n\n' + verdict_block

            print(f"  ✅ Verdict injected ({len(verdict_para.split())} words)")
    except Exception as e:
        print(f"  ⚠️ Verdict injector failed: {e}")

    return html


def ensure_html_only(content):
    """
    Ensures the content is properly formatted HTML.
    Always cleans up markdown bold/italic remnants (**, ***, *).
    Converts markdown lists to HTML lists.
    Wraps bare text blocks in <p> tags.
    """
    if not content or not content.strip():
        return content

    # Step 1: Always clean markdown bold/italic remnants, even in otherwise-HTML content
    # Order matters: handle *** before ** before *
    content = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', content)
    content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
    content = re.sub(r'(?<![\<\s/])\*([^*\n]+?)\*(?![\>/])', r'<em>\1</em>', content)

    # Step 2: Convert markdown headings (## / ###) if present
    content = re.sub(r'^###\s+(.*)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
    content = re.sub(r'^##\s+(.*)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
    content = re.sub(r'^#\s+(.*)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)

    # Step 3: Convert markdown lists (* item, - item) to HTML <ul><li>
    # Process line by line to properly group consecutive list items
    has_md_lists = bool(re.search(r'^\s*[\*\-]\s+', content, re.MULTILINE))
    if has_md_lists and '<li>' not in content:
        lines = content.split('\n')
        result_lines = []
        in_list = False
        for line in lines:
            stripped = line.strip()
            is_list_item = bool(re.match(r'^[\*\-]\s+(.+)', stripped))
            if is_list_item:
                item_text = re.sub(r'^[\*\-]\s+', '', stripped)
                if not in_list:
                    result_lines.append('<ul>')
                    in_list = True
                result_lines.append(f'<li>{item_text}</li>')
            else:
                if in_list:
                    result_lines.append('</ul>')
                    in_list = False
                result_lines.append(line)
        if in_list:
            result_lines.append('</ul>')
        content = '\n'.join(result_lines)

    # Step 4: Wrap bare text blocks in <p> tags (text not inside any HTML tag)
    if '<p>' not in content:
        blocks = content.split('\n\n')
        new_blocks = []
        for b in blocks:
            b = b.strip()
            if not b:
                continue
            if b.startswith('<'):
                new_blocks.append(b)
            else:
                new_blocks.append(f'<p>{b}</p>')
        content = '\n\n'.join(new_blocks)

    # Step 5: Clean up backticks
    content = re.sub(r'```[a-z]*\n?', '', content)
    content = re.sub(r'```', '', content)

    return clean_html_markup(content)


def expand_press_release(press_release_text, source_url, provider='gemini', web_context=None, source_title=None):
    """
    Expands a short press release (200-300 words) into a full automotive article (600-800 words).
    
    Args:
        press_release_text: The original press release content
        source_url: URL of the original press release (for attribution)
        provider: 'groq' (default) or 'gemini'
        web_context: Optional additional context from web search
        source_title: Original title from RSS source (for entity grounding)
    
    Returns:
        HTML article content with proper attribution
    """
    provider_display = "Groq" if provider == 'groq' else "Google Gemini"
    print(f"Expanding press release with {provider_display}...")
    
    web_data_section = ""
    if web_context:
        web_data_section = f"\nADDITIONAL WEB CONTEXT (Use this to enrich the article):\n{wrap_untrusted(web_context, 'WEB_CONTEXT')}\n{ANTI_INJECTION_NOTICE}"
    
    # Build entity anchor from source title (Layer 1: anti-hallucination)
    entity_anchor = ""
    if source_title:
        try:
            from ai_engine.modules.entity_validator import build_entity_anchor
            entity_anchor = build_entity_anchor(source_title)
            if entity_anchor:
                entity_anchor = f"\n{entity_anchor}\n"
        except Exception:
            pass
    
    current_date = datetime.now().strftime("%B %Y")
    
    # Load few-shot examples
    few_shot_block = ""
    try:
        try:
            from ai_engine.modules.few_shot_examples import get_few_shot_examples
        except ImportError:
            from modules.few_shot_examples import get_few_shot_examples
        few_shot_block = get_few_shot_examples(provider)
    except Exception as e:
        print(f"⚠️ Could not load few-shot examples: {e}")
    
    prompt = f"""
{entity_anchor}
{web_data_section}
TODAY'S DATE: {current_date}. Use this to determine what is "upcoming", "current", or "past". Do NOT reference dates that have already passed as future events.

Expand the following press release into a comprehensive, SEO-optimized automotive article.

PRESS RELEASE:
{wrap_untrusted(press_release_text, 'PRESS_RELEASE')}
{ANTI_INJECTION_NOTICE}

SOURCE: {source_url}

═══════════════════════════════════════════════
GOLDEN RULE — TRUTH OVER COMPLETENESS
═══════════════════════════════════════════════
- ONLY use facts that are IN the press release, in the web context, or that you are CONFIDENT about
- If a spec (HP, price, range) is NOT in the press release and you don't KNOW it → SKIP IT
- Clearly mark CONFIRMED vs EXPECTED information:
  ✅ "The BYD Seal produces 313 hp" (confirmed, from press release)
  ✅ "Based on spy shots, the interior appears to feature a large central display" (marked as observation)
  ❌ "The MG7 produces 250 hp and 300 Nm of torque" (fabricated)
- A shorter ACCURATE article is always better than a longer FABRICATED one
- Do NOT invent specs, prices, 0-60 times, or range figures

CRITICAL REQUIREMENTS:
1. **Create UNIQUE content** — do NOT copy press release text verbatim
   - Rephrase in your own voice
   - Add context and analysis
   - Expand on technical details that ARE in the source

2. **Title** — descriptive, engaging, includes YEAR, BRAND, MODEL
   Example: "2025 BYD Seal 06 GT: A Powerful Electric Hatchback for $25,000"
   NO HTML entities (no &quot; or &amp;)

3. **Engaging Opening** — hook the reader immediately:
   ✅ "MG just dropped spy shots of what could reshape the affordable EV sedan segment"
   ❌ "The 2026 MG7 Electric Sedan is a new vehicle that promises to deliver..." (boring)

4. **Competitor comparisons** — ONLY where you have REAL data:
   - 1-2 genuine comparisons are better than 4 forced ones
   ✅ "At $28,100, it costs nearly half what a Model Y does"
   ❌ "Competing with Tesla Model 3, BMW i4, Hyundai Ioniq 5, Audi e-tron, Porsche Taycan..." (spam)

BANNED PHRASES — article REJECTED if these appear:
- "While a comprehensive driving review is pending"
- "specific [X] figures are still emerging"
- "have not yet been officially released" / "are currently confidential"
- "details are under wraps" / "details are yet to be revealed"
- "expected to be equipped" / "anticipated to be" / "potentially with"
- "The [brand] is committed to [generic goal]"
- "making waves in the [X] segment" / "setting a new benchmark"
- "I wish I could" / "the truth is" / "without concrete information"
- "it's reasonable to expect" / "we'd anticipate" / "we can expect"
- "As a journalist" / "While I haven't personally"
- Any sentence that says you DON'T HAVE information → DELETE that sentence
- If unknown → SKIP the claim entirely

═══════════════════════════════════════════════
CRITICAL — OMIT EMPTY SECTIONS
═══════════════════════════════════════════════
If you have NO real data for a section → DO NOT INCLUDE THAT SECTION AT ALL.
Do NOT write a section that says "details are under wraps" or "figures have not been released".
❌ NEVER write a paragraph explaining WHY you don't have data.
❌ NEVER write "As a journalist, I wish I could..." or "the truth is..."
If Performance has no confirmed specs → OMIT the Performance section entirely.
If Technology has no confirmed features → OMIT the Technology section entirely.
A 500-word article with 4 solid sections > 1200-word article with 8 empty ones.

Article Structure (Output ONLY clean HTML — NO <html>/<head>/<body> tags):
OMIT any section where you have NO real data.
- <h2>[Year] [Brand] [Model]: [Engaging Hook]</h2>
- Introduction with hook + key CONFIRMED specs from the press release
- <h2>Performance & Specifications</h2> — ONLY if you have real numbers. If NO specs → OMIT.

  ═══ POWERTRAIN SPEC TEMPLATE (MANDATORY for this section) ═══
  For EACH motor/engine in the car, list SEPARATELY:

  ▸ POWERTRAIN TYPE: [BEV | EREV | PHEV | ICE | Hybrid]
  ▸ MOTOR 1 (traction): [type] — [HP] / [kW] — [torque Nm] — drives [front/rear/all]
  ▸ MOTOR 2 (if dual-motor): [type] — [HP] / [kW] — [torque Nm] — drives [front/rear]
  ▸ RANGE EXTENDER (if EREV/PHEV): [engine type] — [HP] / [kW]
    ⚠️ This is a GENERATOR — it does NOT drive the wheels. NEVER list this as the car's power.
  ▸ TOTAL SYSTEM OUTPUT: [combined HP] — the headline number
  ▸ BATTERY: [capacity kWh] — [chemistry] — [supplier if known]
  ▸ RANGE: [electric-only km] + [combined km if EREV/PHEV] — [cycle: WLTP/CLTC/EPA]
  ▸ 0-100 km/h: [seconds] — ONLY if confirmed
  ▸ DIMENSIONS: length × width × height (mm), wheelbase, curb weight

  ⚠️ CRITICAL for EREV/PHEV/HYBRID:
  - NEVER list range extender HP as the car's total power
  - ALWAYS clarify which motor drives the wheels vs which charges the battery
  - If only ONE power figure exists for an EREV → verify which motor it refers to

  ⚠️ SANITY CHECKS:
  - SUV (5+ meters) with < 150 HP total → almost certainly wrong, verify
  - Sports car with < 200 HP → verify
  - EREV with only one HP figure → might be the generator, not traction motor
  ═══════════════════════════════════════════════

- <h2>Design & Interior</h2> — Only what is visible/confirmed. Compare to ONE car if genuine.
- <h2>Technology & Features</h2> — SPECIFIC items from the press release. If NONE confirmed → OMIT.
- <h2>Why This Matters</h2> — Market context: what gap does this fill? Why should readers care?
- <h2>Pricing & Availability</h2> — ONLY confirmed data. Use <ul><li> tags.
  If pricing unknown, say "pricing has not yet been announced."
- <h2>Pros & Cons</h2> — Punchy, specific, REAL attributes only. Use <ul><li> tags.
  Cons must describe REAL WEAKNESSES — not missing info or product stage:
  ✅ "1602 km range crushes everything in its class"
  ✅ "Interior plastics feel cheap for the price"
  ❌ "Range is impressive" (too vague)
  ❌ "Specs are unknown" (NOT a con — it's missing data, not a car weakness)
  ❌ "No international availability confirmed" (NOT a con unless competitors have it)
  ❌ "Currently in research phase" (NOT a con — it's a product stage)
  ❌ "Further details not yet public" (NOT a con)
  If you cannot find 3 real Cons → list only what you have. 2 genuine > 4 filler.
- Conclusion: who should care and why

AT THE VERY END, add:
<div class="alt-texts" style="display:none">
ALT_TEXT_1: [descriptive alt text for hero/exterior image]
ALT_TEXT_2: [descriptive alt text for interior image]
ALT_TEXT_3: [descriptive alt text for detail/tech image]
</div>
<p class="source-attribution" style="margin-top: 2rem; padding: 1rem; background: #f3f4f6; border-left: 4px solid #3b82f6; font-size: 0.875rem;">
    <strong>Source:</strong> Information based on official press release. 
    <a href="{source_url}" target="_blank" rel="noopener noreferrer" style="color: #3b82f6; text-decoration: underline;">View original press release</a>
</p>

Content Guidelines:
- WORD COUNT TARGET: 700-1200 words. Aim for 800-1000 words. Write comprehensively when data is rich.
- ANTI-REPETITION: Do NOT repeat the same fact/number more than ONCE. Each paragraph must add NEW info.
  The "Why This Matters" section must provide NEW market insights, not repeat the introduction.
- Write for car enthusiasts — sensory language, personality, real-world context
- Explain what specs MEAN for the buyer
- Natural SEO keyword placement (brand, model, year)
- NO placeholder text, ads, social links, or navigation
- REGION-NEUTRAL: Do NOT focus on one country's market. No "in Australia" or "in the US" framing.
  Present prices in the original currency from the source but write for a GLOBAL audience.
  Use STANDARD CURRENCY CODES: CNY (not RMB), JPY (not ¥), KRW, EUR, GBP, AUD, etc.
  ALWAYS include approximate USD conversion: "CNY 299,800 (approximately $42,000)".
  NEVER speculate about US market entry, US tariffs, or North American availability for Chinese/European EVs.
  Skip country-specific safety ratings (ANCAP, IIHS), local warranty terms, and dealer-level details.
  Extract universal car facts from region-specific reviews.

⚠️ MODEL ACCURACY: Use the EXACT car model name from the press release.

{f'FINAL CHECK: The vehicle name MUST be exactly as specified in the MANDATORY VEHICLE IDENTITY section above. If you wrote a different model name or number, your article is WRONG.' if entity_anchor else ''}

{few_shot_block}

Remember: Every sentence should earn its place. Be accurate, engaging, and helpful.
"""
    
    system_prompt = "You are a senior automotive journalist at FreshMotors. You transform press releases into engaging, unique articles with personality and genuine insight. You prioritize ACCURACY: if a spec isn't in the source and you don't know it for certain, you skip it rather than guess. You compare to competitors ONLY when you have real data. Your writing feels like a knowledgeable friend explaining a car, not a corporate rewrite. Be entertaining, accurate, and opinionated where you have basis."
    
    try:
        # Use AI provider factory
        ai = get_ai_provider(provider)
        article_content = ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.65,
            max_tokens=16384
        )
        
        if not article_content:
            raise Exception(f"{provider_display} returned empty article")
            
        print(f"✓ Press release expanded successfully with {provider_display}! Length: {len(article_content)} characters")
        
        # Post-processing: ensure it's HTML, not Markdown
        article_content = ensure_html_only(article_content)
        article_content = _clean_banned_phrases(article_content)
        
        # (review_article removed — rules consolidated into main prompt)
            
        # Запуск Fact-Checking (если есть web_context)
        if web_context:
            try:
                print("🕵️ Running secondary LLM Fact-Check pass for Press Release...")
                from ai_engine.modules.fact_checker import run_fact_check
                article_content = run_fact_check(article_content, web_context, provider)
            except Exception as fc_err:
                print(f"⚠️ Fact-check module failed: {fc_err}")
        
        # Validate quality
        quality = validate_article_quality(article_content)
        if not quality['valid']:
            print("⚠️  Article quality issues:")
            for issue in quality['issues']:
                print(f"  - {issue}")
            
            # Fix truncation: trim to last complete paragraph
            if any('truncated' in i for i in quality['issues']):
                logger.warning("[ARTICLE-GEN] Content truncated by AI token limit, trimming to last complete tag")
                # Find last closing tag (</p>, </ul>, </h2>, </div>)
                import re as _re
                last_tag = _re.search(r'.*(</(p|ul|ol|h2|h3|div|li)>)', article_content, _re.DOTALL)
                if last_tag:
                    article_content = article_content[:last_tag.end()]
                    print(f"  → Trimmed to {len(article_content)} chars")
        
        # (Entity validation removed — entity_anchor in prompt is sufficient)
        # (RLAIF Judge removed — was the main source of content truncation/duplication)
        
        # Dedup guard: if the article's first H2 appears twice, trim at second occurrence
        first_h2 = re.search(r'<h2[^>]*>.*?</h2>', article_content, re.DOTALL)
        if first_h2:
            second_pos = article_content.find(first_h2.group(0), first_h2.end())
            if second_pos > 0:
                article_content = article_content[:second_pos].rstrip()
                print(f"  🔁 Dedup guard: trimmed duplicate content at position {second_pos}")
        
        return article_content
        
    except Exception as e:
        logger.error(f"Press release expansion failed with {provider_display}: {e}")
        logger.error(f"Failed press_release_text (first 500 chars): {str(press_release_text)[:500]}")
        print(f"❌ Error expanding press release with {provider_display}: {str(e)}")
        
        # Provider fallback
        fallback = 'gemini' if provider == 'groq' else 'groq'
        fallback_display = 'Google Gemini' if fallback == 'gemini' else 'Groq'
        try:
            print(f"🔄 Retrying with fallback provider: {fallback_display}...")
            ai_fallback = get_ai_provider(fallback)
            article_content = ai_fallback.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.65,
                max_tokens=3500
            )
            if article_content:
                print(f"✓ Fallback successful with {fallback_display}!")
                article_content = ensure_html_only(article_content)
                article_content = _clean_banned_phrases(article_content)
                return article_content
        except Exception as fallback_err:
            logger.error(f"Fallback also failed with {fallback_display}: {fallback_err}")
        
        raise

