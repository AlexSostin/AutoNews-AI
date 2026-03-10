import logging
import json
import html as html_lib
import os
import re

logger = logging.getLogger(__name__)

try:
    from ai_engine.modules.prompt_sanitizer import wrap_untrusted, ANTI_INJECTION_NOTICE
except ImportError:
    from modules.prompt_sanitizer import wrap_untrusted, ANTI_INJECTION_NOTICE

def run_fact_check(article_html: str, web_context: str, provider: str = 'gemini', source_title: str = None) -> str:
    """
    Runs a secondary LLM pass to extract factual claims from the generated article
    and cross-reference them against the raw web context.
    If hallucinations are found, injects a warning banner into the HTML.
    """
    if not web_context or len(web_context.strip()) < 50:
        return article_html # No context to check against
        
    try:
        from ai_engine.modules.ai_provider import get_ai_provider
    except ImportError:
        from modules.ai_provider import get_ai_provider

    ai = get_ai_provider(provider)
    
    # Build entity verification section if source_title is provided
    entity_check_section = ""
    if source_title:
        entity_check_section = f"""
    5. CRITICAL: Verify the EXACT car model name. The original source title is: "{source_title}"
       - Check if the article uses the SAME model name and number as the source title.
       - If the article says "Leopard 7" but the source says "Leopard 8", this is a CRITICAL hallucination.
       - Model name/number mismatches are the HIGHEST PRIORITY issue to flag.
"""
    
    prompt = f"""
    You are an expert fact-checker. Your job is to verify the numerical claims in the ARTICLE against the provided WEB CONTEXT.
    
    WEB CONTEXT (Ground Truth):
    {wrap_untrusted(web_context, 'WEB_CONTEXT')}
    
    ARTICLE TEXT TO VERIFY:
    {wrap_untrusted(article_html, 'ARTICLE')}
    {ANTI_INJECTION_NOTICE}
    
    Instructions:
    1. Extract 3-5 key numerical claims from the ARTICLE (like Price, Horsepower, Range, Battery size, 0-100 km/h).
    2. Check if these claims are supported by the WEB CONTEXT.
    3. If a claim in the ARTICLE contradicts the WEB CONTEXT, or is completely fabricated (not found in context), flag it.
    4. Return your analysis as a JSON object with the following structure:
    {{
        "hallucinations_found": true/false,
        "issues": [
            "Article claims price is $20,000, but web context states it starts at $30,000.",
            "Article claims 500 HP, but this is not mentioned in the web context."
        ]
    }}
{entity_check_section}
    Respond ONLY with valid JSON. Do not include markdown formatting like ```json or any other text.
    """
    
    system_prompt = "You are a strict fact-checking AI. You only output valid parseable JSON."
    
    try:
        response = ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=1000
        )
        
        # Clean response to ensure it's parseable JSON
        clean_json = response.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        elif clean_json.startswith("```"):   # bare fence without language tag
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
            
        result = json.loads(clean_json.strip())
        
        if result.get('hallucinations_found') and result.get('issues'):
            logger.warning(f"Fact-check detected issues: {result['issues']}")
            
            # Formulate the warning HTML
            # html_lib.escape prevents XSS from LLM-returned issue text
            # str() guard: LLM may return dicts/lists instead of strings
            issues_list = "".join(f"<li>{html_lib.escape(str(issue))}</li>" for issue in result['issues'])
            # Store issues as JSON in data attribute so the editor can use them for auto-resolve
            # Escape <> to prevent innerHTML XSS if frontend reads data-issues
            issues_json = json.dumps(result['issues']).replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
            warning_html = f"""
            <div class="ai-editor-note ai-fact-check-block" data-issues="{issues_json}" style="background-color: #fef0f0; border-left: 4px solid #f56c6c; padding: 15px; margin-bottom: 20px;">
                <h4 style="color: #f56c6c; margin-top: 0;">⚠️ AI Fact-Check Warning</h4>
                <p>The following discrepancies were detected between the generated text and the web sources:</p>
                <ul>{issues_list}</ul>
                <p><em>Please review and correct these numbers before publishing.</em></p>
            </div>
            """
            
            # Inject at the very top of the article
            return warning_html + article_html
            
        return article_html
        
    except Exception as e:
        logger.error(f"Fact-checking failed: {e}. Skipping validation.")
        return article_html


def _extract_car_info_from_html(article_html: str) -> dict:
    """
    Try to extract make/model/trim from the article HTML title or heading.
    Returns dict with 'make', 'model', 'trim' or empty dict.
    """
    # Try <h1> or <h2> first
    heading_match = re.search(r'<h[12][^>]*>([^<]+)</h[12]>', article_html, re.I)
    title_text = heading_match.group(1) if heading_match else ''

    if not title_text:
        # Try first 200 chars of plain text
        plain = re.sub(r'<[^>]+>', ' ', article_html[:500])
        title_text = plain.strip()[:200]

    # Pattern: "2025 BYD TANG L DM P AWD" or similar
    m = re.match(
        r'(?:20\d{2}\s+)?(\S+)\s+(.+?)(?:\s+(?:Review|Walk-?around|Overview|Specs|Comparison|Test|–|:))',
        title_text, re.I
    )
    if not m:
        m = re.match(r'(?:20\d{2}\s+)?(\S+)\s+(.+)', title_text, re.I)

    if m:
        return {'make': m.group(1).strip(), 'model': m.group(2).strip()[:40]}
    return {}


def _build_enriched_context(article_html: str, web_context: str) -> str:
    """
    Enrich the web context by:
    1. Looking up verified specs from our own VehicleSpecs database
    2. Performing targeted web searches for the car
    Appends results to existing web_context.
    """
    car_info = _extract_car_info_from_html(article_html)
    if not car_info.get('make'):
        return web_context

    make = car_info['make']
    model = car_info['model']

    # Phase 1: Check our own VehicleSpecs database for verified data
    try:
        from news.models.vehicles import VehicleSpecs
        existing = VehicleSpecs.objects.filter(
            make__iexact=make,
            model_name__icontains=model.split()[0] if model else '',
        ).order_by('-updated_at').first()
        if existing:
            db_parts = []
            if existing.power_hp:
                db_parts.append(f"Power: {existing.power_hp} hp")
            if existing.power_kw:
                db_parts.append(f"Power: {existing.power_kw} kW")
            if existing.battery_kwh:
                db_parts.append(f"Battery: {existing.battery_kwh} kWh")
            range_val = existing.range_wltp or existing.range_cltc or existing.range_epa or existing.range_km
            if range_val:
                db_parts.append(f"Range: {range_val} km")
            if existing.acceleration_0_100:
                db_parts.append(f"0-100: {existing.acceleration_0_100}s")
            if existing.price_usd_from:
                db_parts.append(f"Price: from ${existing.price_usd_from:,}")
            if existing.torque_nm:
                db_parts.append(f"Torque: {existing.torque_nm} Nm")
            if db_parts:
                web_context = (
                    web_context
                    + f"\n\n--- VERIFIED SPECS FROM INTERNAL DATABASE ({make} {existing.model_name}) ---\n"
                    + "\n".join(db_parts)
                    + "\nThese are our verified specs. Use them to cross-check the article.\n"
                )
                logger.info(f"Fact-checker: injected {len(db_parts)} verified specs from DB")
    except Exception as e:
        logger.debug(f"Fact-checker DB lookup failed (non-fatal): {e}")

    # Phase 2: Additional web search
    try:
        from ai_engine.modules.searcher import search_car_details
        extra_context = search_car_details(make, model)
        if extra_context and len(extra_context) > 100:
            return (
                web_context
                + "\n\n--- ADDITIONAL WEB SEARCH RESULTS ---\n"
                + extra_context[:8000]
            )
    except Exception as e:
        logger.warning(f"Enriched context search failed: {e}")

    return web_context


def auto_resolve_fact_check(article_html: str, web_context: str, provider: str = 'gemini') -> dict:
    """
    Attempts to automatically fix hallucinated claims in the article.

    Strategy (3 tiers — best practice 2026):
    - Tier 1 REPLACE: if correct value found in web context → swap inline
    - Tier 2 CAVEAT:  if claim not in web but plausible → keep with footnote
    - Tier 3 REMOVE:  ONLY if web context directly contradicts the article

    Returns: {
        'content': fixed_html,
        'replaced': [{'claim': '...', 'correct': '...', 'source': '...'}],
        'caveated': [{'claim': '...', 'note': '...'}],
        'removed':  [{'claim': '...', 'reason': '...'}],
    }
    """
    if not web_context or len(web_context.strip()) < 50:
        return {'content': article_html, 'replaced': [], 'caveated': [], 'removed': [],
                'error': 'No web context available'}

    try:
        from ai_engine.modules.ai_provider import get_ai_provider
    except ImportError:
        from modules.ai_provider import get_ai_provider

    # Step 1: Enrich context with targeted search
    enriched_context = _build_enriched_context(article_html, web_context)

    ai = get_ai_provider(provider)

    prompt = f"""You are an expert automotive editor. Your task is to CORRECT factual errors in the ARTICLE below using ONLY the WEB CONTEXT as ground truth.

WEB CONTEXT (Ground Truth — contains verified data from official sources and automotive press):
{wrap_untrusted(enriched_context, 'WEB_CONTEXT')}

ARTICLE TO FIX:
{wrap_untrusted(article_html, 'ARTICLE')}
{ANTI_INJECTION_NOTICE}

## CRITICAL RULES — READ CAREFULLY:

### Rule 1: NEVER DELETE NUMBERS WITHOUT REPLACING THEM
An article with vague text like "a formidable output" or "a battery pack" is WORSE than one with
an unverified "544 hp" or "35.6 kWh". Readers need specific numbers. Your job is to REPLACE wrong
numbers with correct ones, NOT to strip all specifics.

### Rule 2: Three-Tier Correction Strategy
For EACH numerical claim in the article, apply one of these tiers:

**TIER 1 — REPLACE** (best outcome):
If the WEB CONTEXT contains the correct value → replace the wrong number with the correct one.
Example: Article says "544 hp" but web context says "505 kW (687 hp)" → replace with "505 kW (687 hp)".

**TIER 2 — KEEP AS-IS** (acceptable):
If the claim is NOT in the web context but is plausible (could be from the video source) → KEEP the
original number EXACTLY AS-IS with NO inline annotation. Do NOT append "(unverified)" or "(per manufacturer)".
Instead, add the claim to the "caveated" array in your JSON response for editorial tracking.
Example: "35.6 kWh battery pack" → keep as "35.6 kWh battery pack" (no changes to text)

**TIER 3 — REMOVE** (last resort, use sparingly):
ONLY if the web context DIRECTLY CONTRADICTS the number (web says X, article says Y and they are
incompatible) → remove the specific wrong number and replace with the correct one from context.
If no correct value exists in context, use Tier 2 instead.

### Rule 3: Preserve ALL article structure
- Keep all <p>, <h2>, <h3>, <ul>, <li> tags exactly as they are
- Do NOT rewrite sentences — only change the specific numbers/values
- Do NOT add new paragraphs, sections, or content
- Remove the <div class="ai-editor-note ai-fact-check-block"...> warning block from the output

### Rule 4: Return structured JSON
{{
    "fixed_html": "<the corrected article HTML — complete, with warning block removed>",
    "replaced": [
        {{"claim": "544 hp", "correct": "505 kW (687 hp)", "source": "web context"}}
    ],
    "caveated": [
        {{"claim": "35.6 kWh battery", "note": "per manufacturer"}}
    ],
    "removed": [
        {{"claim": "$31,500 USD", "reason": "web context states RMB 400,000-600,000 (~$55,000-$82,000)"}}
    ]
}}

Return ONLY valid JSON. No markdown fences, no extra text.
"""

    system_prompt = (
        "You are a precise automotive fact-correcting editor. "
        "You NEVER delete numbers without replacing them. "
        "You prefer keeping unverified specifics over vague text. "
        "Output only valid JSON."
    )

    try:
        response = ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=8192
        )

        clean_json = response.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]

        result = json.loads(clean_json.strip())

        fixed_html = result.get('fixed_html', article_html)

        # Strip any remaining inline (unverified)/(per manufacturer) tags the LLM might add
        fixed_html = re.sub(r'\s*\((?:unverified|per manufacturer|not independently verified)\)', '', fixed_html)

        # Normalize Chinese currency notation: "RMB 359,800" → "¥359,800 CNY"
        fixed_html = re.sub(r'\bRMB\s+([\d,]+)', r'¥\1 CNY', fixed_html)

        # Sanity check: if fixed_html is dramatically shorter (>40% loss), it means
        # the LLM still stripped too aggressively — fall back to original
        original_text_len = len(re.sub(r'<[^>]+>', '', article_html))
        fixed_text_len = len(re.sub(r'<[^>]+>', '', fixed_html))
        if original_text_len > 200 and fixed_text_len < original_text_len * 0.6:
            logger.warning(
                f"Auto-resolve stripped too much content: {original_text_len} → {fixed_text_len} chars. "
                f"Falling back to original with caveats only."
            )
            # Remove the warning block: count nested <div> tags to avoid stopping at first </div>
            fallback_html = article_html
            block_start = re.search(r'<div\s+class="ai-editor-note[^"]*"', article_html)
            if block_start:
                pos = block_start.start()
                depth = 0
                i = pos
                while i < len(fallback_html):
                    if fallback_html[i:i+4] == '<div':
                        depth += 1
                        i += 4
                    elif fallback_html[i:i+6] == '</div>':
                        depth -= 1
                        i += 6
                        if depth == 0:
                            fallback_html = fallback_html[:pos] + fallback_html[i:]
                            break
                    else:
                        i += 1
            return {
                'content': fallback_html,
                'replaced': [],
                'caveated': [],
                'removed': [],
                'warning': 'LLM stripped too much content — kept original with warning block removed',
            }

        # Save corrections to persistent memory (learning loop)
        replaced = result.get('replaced', [])
        caveated = result.get('caveated', [])
        removed = result.get('removed', [])

        if replaced or removed:
            try:
                from ai_engine.modules.correction_memory import record_corrections
                # Extract article title from HTML
                title_match = re.search(r'<h[12][^>]*>([^<]+)</h[12]>', fixed_html)
                title = title_match.group(1) if title_match else 'Unknown Article'
                record_corrections(title, replaced, caveated, removed)
            except Exception as mem_err:
                logger.warning(f"Correction memory save failed: {mem_err}")

        return {
            'content': fixed_html,
            'replaced': replaced,
            'caveated': caveated,
            'removed': removed,
        }

    except Exception as e:
        logger.error(f"Auto-resolve failed: {e}")
        return {'content': article_html, 'replaced': [], 'caveated': [], 'removed': [],
                'error': str(e)}
