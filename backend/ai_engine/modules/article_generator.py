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
    from ai_engine.modules.utils import clean_title, calculate_reading_time, validate_article_quality
    from ai_engine.modules.ai_provider import get_ai_provider
except ImportError:
    from modules.utils import clean_title, calculate_reading_time, validate_article_quality
    from modules.ai_provider import get_ai_provider

# Legacy Groq client for backwards compatibility
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# ── Banned phrase post-processing ──────────────────────────────────────────
# Gemini sometimes ignores prompt bans.  This is the safety net.

_BANNED_SENTENCE_PATTERNS = re.compile(
    r'<p>[^<]*?('
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
    # Lazy Cons
    r'|While specific cons .{3,60} aren\'t detailed'
    r'|While specific cons .{3,60} not .{3,30} detailed'
    r'|the complexity inherent in'
    r'|might be a consideration for some buyers'
    # Empty "still emerging" paragraphs
    r'|are still emerging'
    r'|remain to be seen'
    r'|only time will tell'
    r'|it remains to be seen'
    ')[^<]*?</p>',
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
    (re.compile(r'the market response has been .{3,30}phenomenal:?\s*', re.I), 'Market response: '),
    (re.compile(r'it\'s clear (?:that )?', re.I), ''),
]


def _clean_banned_phrases(html: str) -> str:
    """Remove or replace banned filler phrases that Gemini sometimes ignores."""
    original_len = len(html)
    
    # 1. Remove entire <p> blocks that are pure filler
    html = _BANNED_SENTENCE_PATTERNS.sub('', html)
    
    # 2. Inline replacements for smaller phrases
    for pattern, replacement in _BANNED_INLINE_REPLACEMENTS:
        html = pattern.sub(replacement, html)
    
    # 3. Clean up empty paragraphs left behind
    html = re.sub(r'<p>\s*</p>', '', html)
    
    cleaned = original_len - len(html)
    if cleaned > 0:
        print(f"  🧹 Post-processing: removed {cleaned} chars of filler")
    
    return html

def generate_article(analysis_data, provider='gemini', web_context=None):
    """
    Generates a structured HTML article based on the analysis using selected AI provider.
    
    Args:
        analysis_data: The analysis from the transcript
        provider: 'groq' (default) or 'gemini'
        web_context: Optional string containing web search results
    
    Returns:
        HTML article content
    """
    provider_display = "Groq" if provider == 'groq' else "Google Gemini"
    print(f"Generating article with {provider_display}...")
    
    web_data_section = ""
    if web_context:
        web_data_section = f"\nADDITIONAL WEB CONTEXT (Use this to fill missing specs/facts):\n{web_context}\n"
    
    current_date = datetime.now().strftime("%B %Y")
    
    prompt = f"""
{web_data_section}
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
   Example: "2025 BYD Seal 06 GT: A Powerful Electric Hatchback for $25,000"

2. **Engaging Opening** — start with an INTRIGUING hook, not a dry summary:
   ✅ "MG just pulled the covers off spy shots of what could be one of the most affordable electric sedans in 2026"
   ✅ "Forget everything you knew about Chinese EVs — the Zeekr 7X rewrites the rulebook"
   ❌ "The 2026 MG7 Electric Sedan is a new vehicle that promises to deliver..." (boring, generic)

3. **Write for car enthusiasts** — make readers feel the car:
   - Use SENSORY language: "The dashboard wraps around you like a cockpit" not "The interior is spacious"
   - Give the car a PERSONALITY: "This is the daily driver for someone who's outgrown their Model 3"
   - Add real-world context: "600 km WLTP range means weekend trips without touching a charger"
   - Explain what specs MEAN for the buyer, not just list numbers

4. **Competitor comparisons** — use them ONLY when you have REAL data:
   - 1-2 well-chosen comparisons are better than 4 forced ones
   - ONLY compare specs you are confident about
   ✅ "At $28,100, it costs nearly half what a Model Y does in Europe"
   ❌ "It competes with the Tesla Model 3 (250 hp), BMW i4 (335 hp), Hyundai Ioniq 5 (320 hp), Audi e-tron (355 hp)..." (list spam)

5. **Word count**: HARD LIMIT 400-750 words. NEVER exceed 750 words.
   If source data is thin (spy shots, teaser), a 400-500 word article is PERFECTLY FINE.
   QUALITY always beats QUANTITY. Every sentence should earn its place.
   Do NOT pad with long feature lists or exhaustive option packages.
   Count your words. If you're over 750, CUT the weakest paragraphs.

7. **ANTI-REPETITION**: Do NOT repeat the same fact, number, or claim more than ONCE.
   If you've stated "92% efficiency" in the introduction → do NOT restate it in later sections.
   Each paragraph must add NEW information, not rephrase previous paragraphs.
   The "Why This Matters" section must provide NEW market insights, not repeat the introduction.
   ❌ BAD: Mentioning the same spec in Introduction, Technology, Why This Matters, AND Conclusion.
   ✅ GOOD: State the spec once, then build on it with context, comparisons, or implications.

6. **REGION-NEUTRAL writing**:
   - Do NOT focus on a single country's market (no "in Australia", "in the US", etc.)
   - Present prices in the ORIGINAL currency from the source, but don't frame the article around one country
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
- <h2>Design & Interior</h2> — Styling, materials, space.
  Compare design language to ONE well-known car if the comparison is genuine and insightful.
  Focus on what IS visible/confirmed, not what might be.
- <h2>Technology & Features</h2> — List SPECIFIC items from the source data.
  Only mention features that are confirmed. If NO features are confirmed → OMIT this section.
- <h2>Pricing & Availability</h2> — CONCISE, 3-5 bullet points:
  <ul><li>Only confirmed prices and markets</li></ul>
  Do NOT fabricate MSRP prices. If pricing is unknown, say "pricing has not been announced yet."
- <h2>Pros & Cons</h2> — Use <ul><li> tags. Punchy, specific, based on REAL attributes:
  ✅ "1602 km range crushes everything in its class"
  ✅ "No Apple CarPlay — a dealbreaker for many"
  ❌ "Range is impressive" (too vague)
  ❌ "Specs are unknown" (NOT a con — it's missing info)
- Conclusion: who should buy this car and why. Be specific.

AT THE VERY END, add:
<div class="alt-texts" style="display:none">
ALT_TEXT_1: [descriptive alt text for hero/exterior image]
ALT_TEXT_2: [descriptive alt text for interior image]
ALT_TEXT_3: [descriptive alt text for detail/tech image]
</div>

Analysis Data:
{analysis_data}

Remember: Write like you're explaining to a car-enthusiast friend. Be helpful, accurate, and entertaining. Quality over quantity — every sentence should earn its place.
"""
    
    system_prompt = """You are a senior automotive journalist at FreshMotors. You write like CarWow's Mat Watson — technically precise, with genuine personality and humor. You prioritize ACCURACY over completeness: if you don't know a spec, you skip it rather than guess. You write for car enthusiasts who want honest, engaging analysis. You compare to competitors ONLY when you have real data. Your articles feel like a conversation with a knowledgeable friend, not a corporate press release. You know major car brands well (including Chinese EVs), but you never fabricate specs you're unsure about. Be entertaining, be accurate, be opinionated where you have real basis for opinions."""
    
    try:
        # Use AI provider factory
        ai = get_ai_provider(provider)
        
        MIN_WORD_COUNT = 300  # Minimum acceptable article length (lowered to allow shorter accurate articles)
        MAX_RETRIES = 2       # Retry if too short
        
        article_content = None
        for attempt in range(MAX_RETRIES):
            current_prompt = prompt
            if attempt > 0:
                # On retry, add stronger length instructions
                current_prompt = (
                    "⚠️ IMPORTANT: Your previous response was TOO SHORT. "
                    f"You MUST write AT LEAST 800 words (you wrote only ~{word_count} words). "
                    "Include ALL sections: intro, design, performance, tech, competitors, verdict. "
                    "DO NOT abbreviate or summarize. Write a COMPLETE, FULL-LENGTH article.\n\n"
                    + prompt
                )
                print(f"🔄 Retry #{attempt}: previous attempt was only {word_count} words, need 800+")
            
            article_content = ai.generate_completion(
                prompt=current_prompt,
                system_prompt=system_prompt,
                temperature=0.65,
                max_tokens=6000
            )
            
            if not article_content:
                raise Exception(f"{provider_display} returned empty article")
            
            # Check word count
            stripped = re.sub(r'<[^>]+>', ' ', article_content)
            word_count = len(stripped.split())
            print(f"  Attempt {attempt + 1}: {word_count} words, {len(article_content)} chars")
            
            if word_count >= MIN_WORD_COUNT:
                break  # Good enough
        
        if word_count < MIN_WORD_COUNT:
            print(f"⚠️ Article still short after {MAX_RETRIES} attempts: {word_count} words")
            
        print(f"✓ Article generated successfully with {provider_display}! Length: {len(article_content)} characters, {word_count} words")
        
        # Post-processing: ensure it's HTML, not Markdown
        article_content = ensure_html_only(article_content)
        article_content = _clean_banned_phrases(article_content)
        
        # Проверка качества статьи
        quality = validate_article_quality(article_content)
        if not quality['valid']:
            print("⚠️  Article quality issues:")
            for issue in quality['issues']:
                print(f"   - {issue}")
        
        # Вычисляем время чтения
        reading_time = calculate_reading_time(article_content)
        print(f"📖 Reading time: ~{reading_time} min")

        
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
                max_tokens=4096
            )
            if article_content:
                print(f"✓ Fallback successful with {fallback_display}!")
                article_content = ensure_html_only(article_content)
                article_content = _clean_banned_phrases(article_content)
                return article_content
        except Exception as fallback_err:
            logger.error(f"Fallback also failed with {fallback_display}: {fallback_err}")
        
        return ""

def ensure_html_only(content):
    """
    Ensures the content is properly formatted HTML.
    Always cleans up markdown bold/italic remnants (**, ***, *).
    If no HTML lists exist, also converts markdown lists to HTML.
    """
    has_html_lists = "<li>" in content and "<ul>" in content
    has_html_structure = "<p>" in content or "<h2>" in content

    # Step 1: Always clean markdown bold/italic remnants, even in otherwise-HTML content
    # Order matters: handle *** before ** before *
    # ***bold italic*** → <strong><em>...</em></strong>
    content = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', content)
    # **bold** → <strong>...</strong>
    content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
    # *italic* (but NOT inside HTML tags or URLs) → <em>...</em>
    # Only match * that is NOT preceded/followed by space (to avoid messing with list markers)
    content = re.sub(r'(?<![<\s/])\*([^*\n]+?)\*(?![>*/])', r'<em>\1</em>', content)

    # Step 2: If content already has proper HTML lists, we're done
    if has_html_lists and has_html_structure:
        return content

    # Step 3: If there are remaining markdown patterns, convert lists too
    needs_list_conversion = bool(re.search(r'^\s*[\*\-]\s+', content, re.MULTILINE))
    
    if needs_list_conversion and not has_html_lists:
        print("🔧 Detected Markdown list patterns. Converting to HTML...")
        if markdown:
            html_content = markdown.markdown(content, extensions=['extra', 'sane_lists'])
            return html_content
        else:
            print("⚠️ Warning: 'markdown' module not found. Using enhanced fallback conversion.")
            
            # Clean up backticks
            content = re.sub(r'```[a-z]*\n?', '', content)
            content = re.sub(r'```', '', content)
            
            # Convert headings
            content = re.sub(r'^###\s+(.*)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
            content = re.sub(r'^##\s+(.*)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
            content = re.sub(r'^#\s+(.*)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)
            
            # Convert simple lists
            content = re.sub(r'^\*\s+(.*)$', r'<li>\1</li>', content, flags=re.MULTILINE)
            content = re.sub(r'^\-\s+(.*)$', r'<li>\1</li>', content, flags=re.MULTILINE)
            
            # Wrap lists
            if '<li>' in content:
                 content = content.replace('<li>', '<ul><li>', 1)
                 content = content.replace('</li>\n\n', '</li></ul>\n\n')
            
            # Paragraphs - wrap anything not in a tag
            if "<p>" not in content:
                blocks = content.split('\n\n')
                new_blocks = []
                for b in blocks:
                    b = b.strip()
                    if not b: continue
                    if b.startswith('<'):
                        new_blocks.append(b)
                    else:
                        new_blocks.append(f"<p>{b}</p>")
                content = '\n\n'.join(new_blocks)
                
            return content

    return content


def expand_press_release(press_release_text, source_url, provider='gemini', web_context=None):
    """
    Expands a short press release (200-300 words) into a full automotive article (600-800 words).
    
    Args:
        press_release_text: The original press release content
        source_url: URL of the original press release (for attribution)
        provider: 'groq' (default) or 'gemini'
        web_context: Optional additional context from web search
    
    Returns:
        HTML article content with proper attribution
    """
    provider_display = "Groq" if provider == 'groq' else "Google Gemini"
    print(f"Expanding press release with {provider_display}...")
    
    web_data_section = ""
    if web_context:
        web_data_section = f"\nADDITIONAL WEB CONTEXT (Use this to enrich the article):\n{web_context}\n"
    
    current_date = datetime.now().strftime("%B %Y")
    
    prompt = f"""
{web_data_section}
TODAY'S DATE: {current_date}. Use this to determine what is "upcoming", "current", or "past". Do NOT reference dates that have already passed as future events.

Expand the following press release into a comprehensive, SEO-optimized automotive article.

PRESS RELEASE:
{press_release_text}

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
- HARD WORD LIMIT: 400-750 words. NEVER exceed 750. Count your words. Cut weakest paragraphs if over.
- ANTI-REPETITION: Do NOT repeat the same fact/number more than ONCE. Each paragraph must add NEW info.
  The "Why This Matters" section must provide NEW market insights, not repeat the introduction.
- Write for car enthusiasts — sensory language, personality, real-world context
- Explain what specs MEAN for the buyer
- Natural SEO keyword placement (brand, model, year)
- NO placeholder text, ads, social links, or navigation
- REGION-NEUTRAL: Do NOT focus on one country's market. No "in Australia" or "in the US" framing.
  Present prices in the original currency from the source but write for a GLOBAL audience.
  Skip country-specific safety ratings (ANCAP, IIHS), local warranty terms, and dealer-level details.
  Extract universal car facts from region-specific reviews.

⚠️ MODEL ACCURACY: Use the EXACT car model name from the press release.

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
            max_tokens=6000  # Increased for better quality content
        )
        
        if not article_content:
            raise Exception(f"{provider_display} returned empty article")
            
        print(f"✓ Press release expanded successfully with {provider_display}! Length: {len(article_content)} characters")
        
        # Post-processing: ensure it's HTML, not Markdown
        article_content = ensure_html_only(article_content)
        article_content = _clean_banned_phrases(article_content)
        
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

