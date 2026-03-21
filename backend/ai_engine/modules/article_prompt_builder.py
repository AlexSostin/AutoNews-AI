"""
Article generation — prompt construction, AI calls, and orchestration.

Contains the three main generation entry-points:
- generate_article: Full article from video/analysis data
- expand_press_release: RSS press release → full article
- enhance_existing_article: Enrich an existing article with web data
"""
import os
import re
import logging
from datetime import datetime

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
    from ai_engine.modules.ai_provider import get_ai_provider, get_light_provider
    from ai_engine.modules.prompt_sanitizer import wrap_untrusted, sanitize_for_prompt, ANTI_INJECTION_NOTICE
except ImportError:
    from modules.utils import clean_title, calculate_reading_time, validate_article_quality, clean_html_markup
    from modules.ai_provider import get_ai_provider
    from modules.prompt_sanitizer import wrap_untrusted, sanitize_for_prompt, ANTI_INJECTION_NOTICE

from ai_engine.modules.article_post_processor import (
    post_process_article,
    _detect_missing_sections,
    _dedup_guard,
)
from ai_engine.modules.article_self_review import (
    _self_review_pass,
    _ensure_verdict_written,
)
from ai_engine.modules.html_normalizer import ensure_html_only


# ── Provider fallback (shared helper) ──────────────────────────────────
def _try_fallback_provider(
    provider: str, prompt: str, system_prompt: str,
    caller_prefix: str = 'article',
) -> str:
    """Try the alternate AI provider as a fallback. Returns content or empty string."""
    fallback = 'gemini' if provider == 'groq' else 'groq'
    fallback_display = 'Google Gemini' if fallback == 'gemini' else 'Groq'
    try:
        print(f"🔄 Retrying with fallback provider: {fallback_display}...")
        ai_fallback = get_ai_provider(fallback)
        content = ai_fallback.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.65,
            max_tokens=16384,
            caller=f'{caller_prefix}_fallback'
        )
        if content:
            print(f"✓ Fallback successful with {fallback_display}!")
            return post_process_article(content)
    except Exception as fallback_err:
        logger.error(f"Fallback also failed with {fallback_display}: {fallback_err}")
    return ""

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
            max_tokens=16384,
            caller='article_enhance'
        )
        
        if not enhanced or len(enhanced) < 200:
            return None
        
        # Full post-processing pipeline
        enhanced = post_process_article(enhanced)
        
        # Extract title
        title_match = re.search(r'<h2[^>]*>(.*?)</h2>', enhanced)
        title = title_match.group(1) if title_match else None
        if title:
            title = re.sub(r'<[^>]+>', '', title).strip()
        
        # Extract summary
        summary_match = re.search(r'<p>(.*?)</p>', enhanced)
        summary = ''
        if summary_match:
            summary = re.sub(r'<[^>]+>', '', summary_match.group(1))[:300]
        
        word_count = len(re.sub(r'<[^>]+>', ' ', enhanced).split())
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



def generate_article(analysis_data, provider='gemini', web_context=None, source_title=None, competitor_context=None, competitor_makes=None):
    """
    Generates a structured HTML article based on the analysis using selected AI provider.
    
    Args:
        analysis_data: The analysis from the transcript
        provider: 'groq' (default) or 'gemini'
        web_context: Optional string containing web search results
        source_title: Original title from RSS/YouTube source (for entity grounding)
        competitor_context: Optional pre-formatted competitor block from competitor_lookup.py
        competitor_makes: Optional list of brand names from competitor_lookup (for hallucination guard)
    
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
            f"REQUIRED: Include a <h2>How It Compares</h2> section.\n"
            f"\n"
            f"⚠️ CRITICAL RULES FOR COMPARISON CARDS:\n"
            f"1. Use ONLY the competitors listed above from our database. Do NOT add cars that are not listed above.\n"
            f"2. EVERY competitor card MUST include at least 2 compare-row items (Power + Price at minimum).\n"
            f"3. If you cannot fill in specs for a competitor — DO NOT add a card for it.\n"
            f"4. An EMPTY card (just a name, no specs) is WORSE than no card at all — it will be REJECTED.\n"
            f"5. Copy the EXACT numbers from the competitor reference above into the cards.\n"
            f"6. EVERY compare-card-name MUST include the full BRAND + MODEL name.\n"
            f"   ✅ 'Avatr 06 REV', 'XPENG P7 Plus', 'BYD Seal 06 GT'\n"
            f"   ❌ '06 REV', 'P7 Plus', 'Seal 06 GT' — never use model name without brand\n"
            f"7. BRAND vs TECH PARTNER — use the CAR BRAND, not the technology supplier:\n"
            f"   Avatr (NOT Huawei) · Denza (NOT BYD) · AITO (NOT Huawei) · Zeekr (NOT Geely)\n"
            f"   Huawei/CATL/Qualcomm = tech partners, mention only in body text for their specific contribution\n"
            f"8. ALL CARDS MUST USE IDENTICAL ROW LABELS — every card (featured + competitors) must \n"
            f"   have the EXACT SAME compare-row labels in the EXACT SAME ORDER.\n"
            f"   ✅ Card A: Power / Range / Price   Card B: Power / Range / Price\n"
            f"   ❌ Card A: 0-100 / Range / Price   Card B: Power / Range / Price — FORBIDDEN!\n"
            f"   If you don't know a value for one card, write 'N/A' rather than changing the label.\n"
            f"9. POWER is MANDATORY in every compare-card. If HP is unknown, calculate from kW (× 1.34).\n"
            f"   NEVER substitute Power with 0-100 KM/H. Both can coexist as separate rows.\n"
            f"\n"
            f"Format each competitor as a CARD using this HTML:\n"
            f'<div class="compare-grid">\n'
            f'  <div class="compare-card featured">\n'
            f'    <div class="compare-badge">This Vehicle</div>\n'
            f'    <div class="compare-card-name">[Year] [Brand] [Model]</div>\n'
            f'    <div class="compare-row"><span class="k">Power</span><span class="v">421 hp</span></div>\n'
            f'    <div class="compare-row"><span class="k">Range</span><span class="v">620 km WLTP</span></div>\n'
            f'    <div class="compare-row"><span class="k">Price</span><span class="v">$34,300</span></div>\n'
            f'  </div>\n'
            f'  <div class="compare-card">\n'
            f'    <div class="compare-card-name">[Year] [Brand] [Competitor Model]</div>\n'
            f'    <div class="compare-row"><span class="k">Power</span><span class="v">300 hp</span></div>\n'
            f'    <div class="compare-row"><span class="k">Range</span><span class="v">450 km</span></div>\n'
            f'    <div class="compare-row"><span class="k">Price</span><span class="v">$42,000</span></div>\n'
            f'  </div>\n'
            f'</div>\n'
            f"The first card (class='featured') is ALWAYS the subject car. Other cards are competitors FROM THE LIST ABOVE ONLY.\n"
            f"After the cards, write 1-2 paragraphs analyzing the comparison.\n"
            f"\n⚠️ PRICE-AWARE COMPARISONS — CRITICAL:\n"
            f"- Only compare with vehicles in a SIMILAR price range (within ±40% of subject car price).\n"
            f"- A $22,000 car compared to a $61,000 car is NONSENSICAL and looks unprofessional.\n"
            f"- If NO provided competitor is within a reasonable price range, DO NOT INCLUDE the 'How It Compares' section AT ALL.\n"
            f"- It is BETTER to omit the section than to make a nonsensical comparison.\n"
            f"- Comparison makes sense: $22k vs $27k, $45k vs $55k, $80k vs $100k.\n"
            f"- Comparison does NOT make sense: $22k vs $61k, $25k vs $80k.\n"
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
    
    # Load correction memory (learning loop from past fact-check fixes)
    correction_block = ""
    try:
        from ai_engine.modules.correction_memory import get_correction_examples
        correction_block = get_correction_examples(n=15)
        if correction_block:
            print(f"  📝 Loaded correction memory into prompt")
    except Exception as e:
        print(f"⚠️ Could not load correction memory: {e}")
    
    # Load editorial memory (learning loop from editor style corrections)
    editorial_block = ""
    try:
        from ai_engine.modules.editorial_memory import get_style_examples
        editorial_block = get_style_examples(n=3)
        if editorial_block:
            print(f"  📝 Loaded editorial memory ({editorial_block.count('Example')} patterns) into prompt")
    except Exception as e:
        print(f"⚠️ Could not load editorial memory: {e}")
    
    # Load predecessor comparison (year-over-year evolution context)
    predecessor_block = ""
    try:
        from ai_engine.modules.predecessor_lookup import get_predecessor_context
        # Extract make/model from source_title (e.g. "Zeekr 8X. Очень быстрый жесткий люкс.")
        _make = ''
        _model = ''
        _year = None
        if source_title:
            # Try to identify brand from title words
            title_words = source_title.replace('.', ' ').replace(',', ' ').split()
            # Known brands often appear as first 1-2 words
            for i in range(min(2, len(title_words))):
                from news.models.vehicles import VehicleSpecs
                candidate = title_words[i]
                if VehicleSpecs.objects.filter(make__iexact=candidate).exists():
                    _make = candidate
                    if i + 1 < len(title_words):
                        _model = title_words[i + 1]
                    break
            # Extract year if present
            import re as _re
            year_match = _re.search(r'\b(202[0-9])\b', source_title)
            if year_match:
                _year = int(year_match.group(1))
        if _make and _model:
            # Build minimal specs dict for comparison
            _current_specs = {}
            if isinstance(analysis_data, dict):
                _current_specs = analysis_data
            predecessor_block = get_predecessor_context(_make, _model, _current_specs, year=_year)
            if predecessor_block:
                print(f"  🚗 Loaded predecessor comparison into prompt")
    except Exception as e:
        print(f"⚠️ Could not load predecessor comparison: {e}")
    
    # Load current exchange rates for accurate price conversions
    exchange_rates_block = ""
    try:
        from ai_engine.modules.currency_service import get_rates_for_prompt
        exchange_rates_block = get_rates_for_prompt()
        print(f"  💱 Loaded exchange rates into prompt")
    except Exception as e:
        print(f"⚠️ Could not load exchange rates: {e}")
    
    prompt = f"""
{entity_anchor}
{web_data_section}
{competitor_section}
{exchange_rates_block}
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
   The title MUST hook the reader with the most impressive fact.
   FORMAT: "[Year] [Brand] [Model]: [Engaging hook with standout spec or price]"
   MINIMUM 50 characters. MAXIMUM 90 characters.
   NO static prefixes like "First Drive:". NO HTML entities.
   If the model name contains a NUMBER that represents a spec (e.g. "TANG 1240" where 1240 = range,
   "EX90" where 90 = battery kWh), EXPLAIN IT in the title or subtitle:
   ✅ "2026 BYD TANG 1240: 7-Seater PHEV with 1,240 km Range for $26,000"
   ❌ "2026 BYD TANG 1240: A PHEV SUV Starting at $26,000" (what is 1240?)
   Example: "2025 BYD Seal 06 GT: A Powerful Electric Hatchback for $25,000"

   ⚠️ MODEL NAME CONSISTENCY — CRITICAL:
   - The model name in your title MUST match the model in the Verdict and throughout the article.
   - "BYD SONG" and "BYD SONG Plus" are DIFFERENT vehicles. Do NOT mix them.
   - "Zeekr 7X" and "Zeekr 007" are DIFFERENT vehicles. Do NOT confuse model numbers.
   - If the source says "SONG DM-i" — write "SONG DM-i" everywhere, NOT "Song Plus DM-i" in the verdict.
   - BEFORE submitting: verify the EXACT model name appears identically in title, opening, specs block, and verdict.

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
   - ⚠️ HYBRID RANGE RULE: For PHEVs and EREVs, explicitly state BOTH the electric-only range and the combined range (e.g., "120 km EV / 1,200 km Combined"). Do not just say "120 km range".
   - USE WEB CONTEXT DATA: If web search found sales figures, orders, market reception, awards,
     or real-world test data — INCLUDE IT in the article. This is the most valuable data you have.
     ✅ "Over 80,000 firm orders within a month of launch" — this is GOLD, always include real numbers
     ✅ "Edmunds testing showed 0-60 in 4.8 seconds" — real test data beats factory claims
     ❌ Ignoring web search data and only writing about dimensions and price — NEVER do this

3b. **Car Name Usage** — DO NOT repeat the full name ("The 2026 BYD TANG 1240") every sentence.
   - First mention: full name with year → "The 2026 BYD TANG 1240"
   - After that: use SHORT forms → "the TANG 1240", "the TANG", "this SUV", "it", "the car"
   - NEVER start 3 consecutive paragraphs with "The [Year] [Brand] [Model]"

3c. **BRAND vs TECHNOLOGY PARTNER — CRITICAL NAMING RULE**:
   YouTube titles often mix car brand names with technology partner names (e.g. "HUAWEI AVATR", "CATL BYD", "Qualcomm Mercedes").
   YOU MUST use your automotive knowledge and web context to CORRECTLY distinguish:
   - The **CAR BRAND** (the manufacturer/marque that appears on the badge) — use this as the brand name
   - **Technology partners** (companies that supply software, batteries, chips, platforms) — mention ONLY in relevant technical context

   RULES:
   - Use ONLY the official car brand name in the title, H2 headings, and specs block
   - Technology partners should be mentioned ONLY when discussing their specific contribution (e.g. "Huawei's ADS system", "CATL-supplied battery")
   - NEVER combine brand + partner as the car name (e.g. "Avatr HUAWEI 07" is WRONG → "Avatr 07" is correct)
   - NEVER use a technology partner name as if it were the car brand

   EXAMPLES:
   ✅ "2026 Avatr 07 REV" — Avatr is the car brand
   ✅ "powered by Huawei's ADS 2.0 autonomous driving system" — Huawei mentioned for their tech contribution
   ✅ "equipped with a 40 kWh CATL battery pack" — CATL mentioned as battery supplier
   ❌ "2026 Avatr HUAWEI 07 REV" — HUAWEI is NOT part of the car name
   ❌ "The HUAWEI 07 REV delivers 343 hp" — HUAWEI is not the brand, Avatr is
   ❌ "The CATL BYD Seal" — CATL is a supplier, not the brand name

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

8. **REGION-NEUTRAL writing**:
   - Do NOT focus on a single country's market (no "in Australia", "in the US", etc.)
   - Present prices in the ORIGINAL currency from the source, but don't frame the article around one country
   - Use STANDARD CURRENCY CODES: CNY (not RMB), JPY (not ¥), KRW, EUR, GBP, AUD, etc.
   - ALWAYS include approximate USD conversion: "CNY 299,800 (approximately $42,000)"
   - NEVER speculate about US market entry, US tariffs, or North American availability for Chinese or European EVs. Do NOT add sections like "Will it come to the US?".
   - Do NOT reference country-specific safety ratings (ANCAP, IIHS, NHTSA) as the main focus — mention briefly if relevant
   - Do NOT include country-specific warranty terms, servicing plans, or dealer networks
   - Write for a GLOBAL car enthusiast audience
   - If the source is from one country (e.g. an Australian review), extract the universal car facts and skip the local market commentary
   - NEVER mention internal manufacturer codenames (e.g. "2316", "2318", "SG3", "BN7") — these are factory/project codes with zero value to readers. The car has a real name; use that.

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
- ONLY list things that are KNOWN and REAL about the vehicle itself.
- A PRO must describe a real attribute of the vehicle (performance, feature, design, value).
  ❌ NOT a Pro: launch date, brand announcement, scheduled event, press conference
  ❌ NOT a Pro: "Launch scheduled for August 16" — that is a news item, not a vehicle attribute
  ❌ NOT a Pro: "Brand has committed to..." — that is a PR statement
  ✅ PRO examples: "500 hp AWD system", "80% charge in 15 minutes", "550-litre cargo space"
- Cons must describe REAL WEAKNESSES of the product/technology itself:
  ✅ "No Apple CarPlay — a dealbreaker for many"
  ✅ "Heavy 2.5-ton curb weight hurts handling"
  ✅ "Interior plastics feel cheap for the price point"
  ✅ "Manual rear seat folding — rivals offer power-fold at this price"
  ❌ "Currently in research phase" — NOT a con (it's the product's stage, not a flaw)
  ❌ "No commercial availability" — NOT a con
  ❌ "Further details not yet public" — NOT a con (it's missing info)
  ❌ "Limited charging infrastructure" — NOT a con of the CAR itself
  ❌ "Specs are unknown" or "pricing unavailable" — NOT a con, it's missing data
  ❌ "No international availability confirmed" — NOT a con unless competitors ARE available globally
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

═══ SPEC BAR (MANDATORY — insert IMMEDIATELY after the introduction paragraph) ═══
Output a compact spec bar with the car's 4-5 most important numbers. Use this EXACT HTML:
<div class="spec-bar">
  <div class="spec-item"><div class="spec-label">STARTING PRICE</div><div class="spec-value">$34,300</div></div>
  <div class="spec-item"><div class="spec-label">RANGE</div><div class="spec-value">620 km WLTP</div></div>
  <div class="spec-item"><div class="spec-label">POWER</div><div class="spec-value">421 hp</div></div>
  <div class="spec-item"><div class="spec-label">0-100 KM/H</div><div class="spec-value">3.8 sec</div></div>
  <div class="spec-item"><div class="spec-label">POWERTRAIN</div><div class="spec-value">BEV AWD</div></div>
</div>
Rules:
- Minimum 3, maximum 6 items.
- POWER is MANDATORY. If exact HP is not given directly, CALCULATE it:
  • From kW: multiply by 1.34 (e.g. 230 kW = 308 hp)
  • From motor specs: sum front + rear motor outputs
  • If only torque/0-100 is known: estimate HP from vehicle class (e.g. 2.98s SUV ≈ 500+ hp)
  • NEVER substitute POWER with "0-100 KM/H" — both are independent specs
  • NEVER omit POWER and NEVER use vague phrases like "impressive" or "powerful" instead of a number
- Skip other items you don't have data for.
═══════════════════════════════════════════════

- <h2>Performance & Specs</h2> — ONLY if you have real numbers.
  Include ONLY specs you have data for. Skip unknown ones entirely.
  If HP is in kW, convert: 1 kW ≈ 1.34 hp.
  If NO specs are available → OMIT this section.

  ═══ POWERTRAIN SPECS TABLE (MANDATORY for this section) ═══
  After your prose paragraphs in Performance, add a clean HTML table summarizing the technical specifications:
  <table class="specs-table">
    <tbody>
      <tr><th>PLATFORM</th><td>SEA (Geely)</td></tr>
      <tr><th>VOLTAGE ARCHITECTURE</th><td>800V</td></tr>
      <tr><th>POWERTRAIN TYPE</th><td>BEV AWD</td></tr>
      <tr><th>MOTOR(S)</th><td>Permanent Magnet Synchronous</td></tr>
      <tr><th>SYSTEM OUTPUT</th><td>421 hp / 310 kW</td></tr>
      <tr><th>TORQUE</th><td>440 Nm</td></tr>
      <tr><th>BATTERY</th><td>77 kWh (NMC, CATL)</td></tr>
      <tr><th>RANGE</th><td>620 km WLTP</td></tr>
      <tr><th>0-100 KM/H</th><td>3.8 sec</td></tr>
      <tr><th>DIMENSIONS</th><td>4,915 mm L × 1,905 mm W × 1,770 mm H</td></tr>
      <tr><th>WHEELBASE</th><td>2,825 mm</td></tr>
    </tbody>
  </table>
  Include ONLY fields you have confirmed data for. Do NOT output messy bullet points for specs. Use the table format above exclusively. Ensure it is placed right after your text paragraphs in the Performance section.
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
- <h2>Pricing & Availability</h2> — CONCISE. If you have a confirmed starting price, you MUST use this heading and include the pricing tag:
  <div class="price-tag"><span class="price-main">$34,300</span> <span class="price-note">Starting · Model Year 2026</span></div>
  If you have multiple trims or price points, output them in a styled table:
  <div class="pricing-table">
    <div class="pricing-row"><span class="p-tier">Entry-Level EREV</span><span class="p-price">CNY 146,900 (approx. $21,300)</span></div>
    <div class="pricing-row"><span class="p-tier">Mid-Range BEV</span><span class="p-price">CNY 156,900 (approx. $22,700)</span></div>
    <div class="pricing-row featured"><span class="p-tier">Flagship BEV (800V)</span><span class="p-price">CNY 176,900 (approx. $25,500)</span></div>
  </div>
  Do NOT use plain <ul> bullet lists for prices or trims. Always use the .pricing-table format. If you don't have multiple trims, you can omit the .pricing-table and just write a short paragraph.
  Do NOT fabricate MSRP prices. If pricing is unknown, say "pricing has not been announced yet."

═══ PROS & CONS (use styled blocks, NOT plain <ul>) ═══
<h2>Pros & Cons</h2>
<div class="pros-cons">
  <div class="pc-block pros">
    <div class="pc-title">Pros</div>
    <ul class="pc-list">
      <li>1602 km range crushes everything in its class</li>
      <li>Sub-$35,000 price undercuts premium rivals by $10k+</li>
    </ul>
  </div>
  <div class="pc-block cons">
    <div class="pc-title">Cons</div>
    <ul class="pc-list">
      <li>No Apple CarPlay — a dealbreaker for many</li>
      <li>Heavy curb weight hurts urban maneuverability</li>
    </ul>
  </div>
</div>
Rules: Punchy, specific, based on REAL attributes. Minimum 3 pros, 2 cons. Never pad.
═══════════════════════════════════════════════

═══ FRESHMOTORS VERDICT (MANDATORY — use dark verdict block) ═══
Wrap in a dark-background verdict container:
<div class="fm-verdict">
  <div class="verdict-label">FreshMotors Verdict</div>
  <p>Your compelling, opinionated verdict about who should buy this car and why. Minimum 60 words.
  Be specific: "The daily driver for someone who's outgrown their Model 3".
  Mention 1-2 standout strengths, 1 weakness, and a final recommendation.</p>
</div>
⚠️ VERDICT UNIQUENESS — CRITICAL:
- Do NOT reuse generic verdict templates across articles. Each verdict must be UNIQUE to this specific vehicle.
- BANNED verdict phrases: "definitive daily driver for the pragmatist", "the definitive [X] for [Y]", "the ultimate [X] for [Y]",
  "refuses to compromise", "outgrown the limitations", "bridge between", "best bang for your buck"
- The verdict must reference THIS car's SPECIFIC specs and unique selling points — not generic category praise.
- A good test: could this verdict apply to 5 other cars? If yes → rewrite it with more specific details.
⚠️ DO NOT leave this section empty — it MUST have a full paragraph of at least 60 words.
⚠️ Do NOT add a separate <h2>FreshMotors Verdict</h2> heading — the verdict-label inside the block IS the heading.
═══════════════════════════════════════════════

AT THE VERY END, add:
<div class="alt-texts" style="display:none">
ALT_TEXT_1: [descriptive alt text for hero/exterior image]
ALT_TEXT_2: [descriptive alt text for interior image]
ALT_TEXT_3: [descriptive alt text for detail/tech image]
</div>

{few_shot_block}

{correction_block}

{editorial_block}

{predecessor_block}

Analysis Data:
{analysis_data}

{f'FINAL CHECK: The vehicle name MUST be exactly as specified in the MANDATORY VEHICLE IDENTITY section above. If you wrote a different model name or number, your article is WRONG. Go back and fix it.' if entity_anchor else ''}

Remember: TARGET 1100-1300 words. Each main section (Performance, Design, Technology, Driving Experience) must have at least 2 full paragraphs. Write with depth — explain what specs mean for real-world driving, not just listing numbers. Do NOT stop writing early. FreshMotors Verdict is MANDATORY and must be written last.
"""
    
    system_prompt = """You are a senior automotive journalist at FreshMotors. You write with technical precision and confident authority — think Autocar or Car and Driver, not a YouTube vlog. You prioritize ACCURACY over completeness: if you don't know a spec, you skip it rather than guess. You write for car enthusiasts who want honest, data-driven analysis. You compare to competitors ONLY when you have real data. Your tone is professional but accessible — authoritative without being dry, engaging without being clickbait. You know major car brands well (including Chinese EVs), but you never fabricate specs you're unsure about. Let the facts and specs make the impression — no hype words needed.

CRITICAL WORD COUNT RULE: Your article MUST be at minimum 1000 words, targeting 1100-1300 words. Count your words as you write. Every major section (Performance, Design, Technology, Driving Experience) must have at least 2 full paragraphs. Do NOT stop writing until you have covered all sections with sufficient depth. SHORT articles will be automatically rejected and regenerated.

⛔ SOURCE FORMAT RULES (ABSOLUTE — violations will cause rejection):
- NEVER mention the word "transcript", "video", "YouTube", "footage", "clip", "reviewer", or any reference to how the source data was collected
- NEVER write phrases like "not detailed in the provided transcript", "as shown in the video", "the transcript mentions", "from the source material", "based on the transcript", "according to the video"
- NEVER explain what information is MISSING from the source — if you don't have data, skip the claim silently
- Write as if you are a journalist who has driven and researched the car yourself, not summarizing someone else's content
- The final article must read as ORIGINAL JOURNALISM, not a summary of a YouTube review"""
    
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
                max_tokens=16384,
                caller='article_generate'
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
        
        # Full post-processing pipeline (unified)
        article_content = post_process_article(article_content, allowed_competitor_makes=competitor_makes or [])
        
        # Validate article quality
        quality = validate_article_quality(article_content)
        if not quality['valid']:
            print("⚠️  Article quality issues:")
            for issue in quality['issues']:
                print(f"   - {issue}")
        
        # Calculate reading time
        reading_time = calculate_reading_time(article_content)
        print(f"📖 Reading time: ~{reading_time} min")

        # Run Fact-Checking — always runs; enriches context from VehicleSpecs DB if no web_context
        try:
            print("🕵️ Running Fact-Check pass (web context + DB verification)...")
            from ai_engine.modules.fact_checker import run_fact_check
            article_content = run_fact_check(article_content, web_context or '', specs, provider)
        except Exception as fc_err:
            print(f"⚠️ Fact-check module failed: {fc_err}")

        
        # (Entity validation removed — entity_anchor in prompt is sufficient)
        # (RLAIF Judge removed — was the main source of content truncation/duplication)
        
        article_content = _dedup_guard(article_content)

        # Guaranteed verdict injector — runs a separate short API call if verdict is empty/missing
        article_content = _ensure_verdict_written(article_content, analysis_data, provider)

        # ── Self-Review Pass ─────────────────────────────────────────────────
        # Second AI call: the same model re-reads its article as an editor.
        # Catches spec inconsistencies, missing premium HTML classes, and readability issues.
        article_content = _self_review_pass(article_content, analysis_data, provider)

        # ── Quality Gate — structural completeness check ─────────────────────
        try:
            from ai_engine.modules.quality_gate import check_quality_gate
            gate_result = check_quality_gate(article_content, has_competitor_data=has_competitors)
            if gate_result['passed']:
                print(f"🚦 Quality Gate: PASS ({gate_result['score']}/100)")
            else:
                print(f"🚦 Quality Gate: FAIL ({gate_result['score']}/100)")
                for issue in gate_result.get('issues', []):
                    print(f"   ⚠️ {issue}")
        except Exception as qg_err:
            print(f"⚠️ Quality gate check failed (non-fatal): {qg_err}")

        return article_content
    except Exception as e:
        logger.error(f"Article generation failed with {provider_display}: {e}")
        logger.error(f"Failed analysis_data (first 500 chars): {str(analysis_data)[:500]}")
        print(f"❌ Error during article generation with {provider_display}: {e}")
        
        # Provider fallback
        return _try_fallback_provider(provider, prompt, system_prompt, 'article_generate')


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
- <h2>Pricing & Availability</h2> — ONLY confirmed data. Use the following structured tags if you have pricing:
  <div class="price-tag"><span class="price-main">$34,300</span> <span class="price-note">Starting</span></div>
  <div class="pricing-table">
    <div class="pricing-row"><span class="p-tier">Standard Range</span><span class="p-price">CNY 200,000</span></div>
    <div class="pricing-row featured"><span class="p-tier">Long Range AWD</span><span class="p-price">CNY 250,000</span></div>
  </div>
  Do NOT use plain <ul> bullet lists for pricing trims.
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
⚠️ BRAND vs TECHNOLOGY PARTNER: YouTube titles and press releases often mix car brands with technology partners.
   Use ONLY the official car brand name (the badge on the car) in the title and headings.
   Technology partners (Huawei, CATL, Qualcomm, etc.) should be mentioned ONLY when discussing their specific contribution.
   ❌ "Avatr HUAWEI 07" → ✅ "Avatr 07" (Huawei is a tech partner, not the brand)

{f'FINAL CHECK: The vehicle name MUST be exactly as specified in the MANDATORY VEHICLE IDENTITY section above. If you wrote a different model name or number, your article is WRONG.' if entity_anchor else ''}

{few_shot_block}

Remember: Every sentence should earn its place. Be accurate, engaging, and helpful.
"""
    
    system_prompt = """You are a senior automotive journalist at FreshMotors. You transform press releases into engaging, unique articles with personality and genuine insight. You prioritize ACCURACY: if a spec isn't in the source and you don't know it for certain, you skip it rather than guess. You compare to competitors ONLY when you have real data. Your writing feels like a knowledgeable friend explaining a car, not a corporate rewrite. Be entertaining, accurate, and opinionated where you have basis.

⛔ SOURCE FORMAT RULES (ABSOLUTE — violations will cause rejection):
- NEVER mention the word "transcript", "video", "YouTube", "footage", "clip", "press release", "source material", or any reference to how the data was collected
- NEVER write phrases like "not detailed in the provided transcript", "as mentioned in the press release", "the source notes", "based on the transcript", "according to the video"
- NEVER explain what information is MISSING — if you don't have data, skip the claim silently. NEVER write "not specified", "not detailed", "not disclosed", "not confirmed", "not provided", "not available", "remain unknown", or any variation.
- Write as ORIGINAL JOURNALISM — the reader should never know where the source data came from

⛔ ANTI-CLICHÉ RULES (Google AdSense compliance):
- NEVER use these AI-typical phrases: "paradigm shift", "tour de force", "game-changer", "game-changing", "redefines the segment", "disrupting the market", "pushing the boundaries", "breath of fresh air", "masterpiece", "technological marvel"
- NEVER use hype language: "jaw-dropping", "mind-blowing", "eye-watering", "nothing short of", "extraordinary", "phenomenal"
- Use SPECIFIC, CONCRETE language instead of vague superlatives

📐 SECTION ORDER — VARY the structure! Do NOT always use the same section order.
Randomly pick ONE of these structures for each article:
- Option A: Performance → Design → Technology → Pricing → Final Verdict
- Option B: Design & First Impressions → Powertrain → Interior Tech → Competitors → Pricing
- Option C: What Makes It Special → Under the Hood → Living With It → Value Proposition
- Option D: The Big Picture → Specs Breakdown → Design Language → Price & Competition
Vary section headers too — don't always use the same H2 titles across articles."""
    
    try:
        # Use AI provider factory
        ai = get_ai_provider(provider)
        article_content = ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.65,
            max_tokens=16384,
            caller='rss_generate'
        )
        
        if not article_content:
            raise Exception(f"{provider_display} returned empty article")
            
        print(f"✓ Press release expanded successfully with {provider_display}! Length: {len(article_content)} characters")
        
        # Full post-processing pipeline (unified)
        article_content = post_process_article(article_content)
        
        # Run Fact-Checking (if web_context available)
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
                last_tag = re.search(r'.*(</(p|ul|ol|h2|h3|div|li)>)', article_content, re.DOTALL)
                if last_tag:
                    article_content = article_content[:last_tag.end()]
                    print(f"  → Trimmed to {len(article_content)} chars")
        
        # (Entity validation removed — entity_anchor in prompt is sufficient)
        # (RLAIF Judge removed — was the main source of content truncation/duplication)
        
        article_content = _dedup_guard(article_content)
        
        return article_content
        
    except Exception as e:
        logger.error(f"Press release expansion failed with {provider_display}: {e}")
        logger.error(f"Failed press_release_text (first 500 chars): {str(press_release_text)[:500]}")
        print(f"❌ Error expanding press release with {provider_display}: {str(e)}")
        
        # Provider fallback
        result = _try_fallback_provider(provider, prompt, system_prompt, 'rss_generate')
        if result:
            return result
        raise

