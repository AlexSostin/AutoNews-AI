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
    r'|horsepower and torque figures are not specified'
    r'|exact battery capacity is not specified'
    r'|further details .{3,30} will be released'
    r'|pricing details .{3,30} have not been officially announced'
    r')[^<]*?</p>',
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

def generate_article(analysis_data, provider='groq', web_context=None):
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

CRITICAL REQUIREMENTS:
1. Title MUST be descriptive, engaging, and unique.
   Include: YEAR, BRAND, MODEL, and if available, PRICE or specific VERSION/TRIM.
   NO static prefixes like "First Drive:".
   Example: "2025 BYD Seal 06 GT Review: A Powerful Electric Hatchback for $25,000"
   Example: "Testing the 2024 Tesla Model 3 Highland: Significant Updates to a Best-Seller"
2. NO HTML entities in title (use plain text, no &quot; or &amp;)
3. Structure with clear sections using <h2> headings
4. Include specific numbers, stats, and comparisons for SEO
5. Use natural keywords related to the car brand, model, year
6. Write engaging, informative content — MINIMUM 800 words, ideally 1000-1200 words. Articles under 600 words will be REJECTED.
7. ALWAYS include these sections: Introduction, Design/Exterior, Interior/Tech, Performance/Powertrain, Competitors, Verdict/Pricing

⚠️ CRITICAL MODEL ACCURACY WARNING:
- CAREFULLY verify the EXACT car model from the video title and transcript
- DO NOT confuse similar model names (e.g., "Zeekr 7X" vs "Zeekr 007" are DIFFERENT cars)
- Pay attention to spaces, numbers, and letters in model names
- If the video title says "Zeekr 7X", write "Zeekr 7X" NOT "Zeekr 007"
- If uncertain about the model, use the EXACT name from the video title
- Double-check model names before writing - accuracy is CRITICAL

NEGATIVE CONSTRAINTS (DO NOT INCLUDE):
- NO "Advertisement", "Ad Space", or "Sponsor" blocks
- NO placeholder text like "Article image 1" or "[Insert Image Here]"
- NO social media links (Subscribe, Follow us)
- NO navigation menus or headers/footers
- NO "Read more" links
- NO HTML <html>, <head>, or <body> tags

BANNED PHRASES — using ANY of these will make the article REJECTED:
- "specific horsepower figures are not available"
- "horsepower and torque figures are not specified"
- "exact battery capacity is not specified"
- "expected to be equipped"
- "anticipated to be a key component"
- "potentially with"
- "likely running"
- "is expected to feature"
- Any form of "not specified" for HP, torque, battery, or range
- Listing "HP not specified" as a Con
If a car EXISTS and is on SALE, do NOT use speculative language. Write as FACT.

BANNED FILLER PATTERNS — these make articles feel FAKE and AI-generated:
- "While a comprehensive driving review is pending" → WRITE a driving section based on specs and your knowledge
- "specific [X] figures are still emerging" → USE YOUR KNOWLEDGE or omit the claim entirely
- "The [brand] is committed to [generic goal]" → GIVE A CONCRETE EXAMPLE instead
- "making waves in the [X] segment" → REPLACE with a specific comparison
- "setting a new benchmark" → SAY what benchmark and compared to WHOM
- "The overall design reflects [brand]'s commitment to..." → DESCRIBE what it actually looks like
- Never write a paragraph that says you don't have data — either provide data or skip that point
- Never pad sections with obvious filler just to hit word count
- If you truly lack data for a section, write 2 strong sentences instead of 5 weak ones

WRITING PERSONALITY — make articles feel ALIVE, inspired by CarWow and Doug DeMuro style:
- COMPARE the design to recognizable cars: "The rear silhouette echoes the BMW iX, but with sharper, more aggressive character lines"
- Use SENSORY language: "The dashboard wraps around you like a cockpit" instead of "The interior is spacious"
- Give the car a PERSONALITY: "This is the car for someone who wants Tesla range without the Tesla minimalism"
- Be OPINIONATED: "The ride quality is genuinely impressive — better than the Model Y, not quite BMW iX3 level"
- Use the CarWow breakdown approach: break complex specs into what they MEAN for the buyer
- Add real-world context: "1602 km CLTC range means roughly 1000 km on the highway — that's London to Edinburgh and back without charging"
- Reference competing models BY NAME in every section — readers want context, not generic praise
- Use humor and personality when appropriate, like Mat Watson would: "The boot is enormous — you could probably fit a small family in there. Not that you should."

MANDATORY COMPETITOR REFERENCES (at least ONE comparison per section):
- Performance: compare HP, torque, 0-60 directly to 2-3 rivals by name
  Example: "268 hp puts it against the Tesla Model Y Long Range (299 hp) and IONIQ 5 (320 hp) — slightly less power, but at a fraction of the price"
- Design: compare styling and proportions to recognizable cars
  Example: "Unlike the boxy NIO ES6, the G7 REV goes for sleek coupe-SUV lines similar to the Mercedes EQE SUV"
- Technology: compare infotainment, ADAS, features to established benchmarks
  Example: "The 15-inch screen matches Tesla's approach, but XPENG adds physical climate buttons that Tesla controversially removed"
- Price: always compare to at least 2 rivals with concrete numbers
  Example: "At $28,100, it undercuts the Model Y ($44,990) by over $16,000"

Required Structure:
- <h2>[Year] [Brand] [Model] [Version] Review: [Hook/Description]</h2>
- Introduction paragraph (2-3 sentences with key specs)
- <h2>Performance & Specs</h2> - MUST include ALL of these with CONCRETE NUMBERS:
  * Horsepower (HP) and kilowatts (kW) — MANDATORY, no excuses
  * Torque in Nm or lb-ft
  * 0-60 mph or 0-100 km/h time
  * Battery capacity in kWh (for EVs)
  * Range in km and miles
  * Starting price
  HOW TO FIND HP: Check the analysis data, web context, AND your own training knowledge.
  You are an automotive expert — you KNOW the specs of major car models (BYD, Tesla, Zeekr, NIO, Li Auto, etc.).
  If HP is in kW, convert: 1 kW ≈ 1.34 hp (e.g., 200 kW = 268 hp).
  NEVER write that specs are "unavailable" or "not specified" — USE YOUR KNOWLEDGE.
- <h2>Design & Interior</h2> - Describe styling, materials, space, cargo volume.
  MUST include at least ONE comparison to a well-known car's design language.
- <h2>Technology & Features</h2> - This section MUST include at least 4-5 SPECIFIC, CONCRETE items:
  * Infotainment screen size and system name (e.g., "15.4-inch AMOLED touchscreen")
  * ADAS / driver assistance features (name them specifically)
  * Connectivity (Apple CarPlay, Android Auto, wireless charging)
  * OTA update capability
  * Digital instrument cluster details
  * Sound system (brand, speakers count)
  * Safety tech (collision avoidance, blind spot monitoring, etc.)
  CRITICAL: Do NOT write "likely" or "potentially" — state features as FACTS.
  If not in the transcript, use the web context or your training knowledge. Write at least 2 full paragraphs.
- <h2>Driving Experience</h2> - Handling, comfort, real-world performance.
  NEVER write "a driving review is pending". You are an automotive expert — describe the expected drive based on platform, weight, motor setup, and your knowledge of similar cars.
- <h2>Pricing & Availability</h2> - Keep this section CONCISE (3-5 bullet points max):
  <ul>
    <li>Starting price in USD, EUR, and CNY (where applicable)</li>
    <li>Key trim levels with prices if known</li>
    <li>Markets where confirmed available (do NOT fabricate launch dates)</li>
    <li>2-3 competitors with prices for comparison</li>
  </ul>
  Do NOT focus on any single market (US, Europe, China). Write as a GLOBAL automotive news article.
  Do NOT fabricate specific MSRP prices or launch dates — use only confirmed data.
  Use ONLY <ul><li> HTML tags, never asterisks (*) or markdown.
- <h2>Pros & Cons</h2> - CRITICAL: Use <ul> and <li> tags. Each pro/con MUST be a separate <li> item.
  Write pros/cons like a CarWow video summary — punchy, specific, comparative:
  Good: "1602 km range crushes everything in its class"
  Bad: "Range is impressive" (too vague)
  Good: "No Apple CarPlay — a dealbreaker for many"
  Bad: "Limited connectivity options" (too generic)
- Conclusion paragraph with recommendation and target buyer. Be specific about WHO should buy this car and WHY.

AT THE VERY END, after the conclusion, add this block:
<div class="alt-texts" style="display:none">
ALT_TEXT_1: [descriptive alt text for a hero/exterior image]
ALT_TEXT_2: [descriptive alt text for an interior image]
ALT_TEXT_3: [descriptive alt text for a detail/tech image]
</div>

Writing Style:
- Write like the best automotive YouTubers (CarWow, Doug DeMuro) — technically precise but with personality
- Explain what specs mean for the driver in real life (e.g., "314 hp means 0-60 in 5.9s — enough to merge confidently on any highway")
- ALWAYS include comparisons to competitors — this is what readers care about most
- Mention target audience (families, enthusiasts, eco-conscious, etc.)
- Natural keyword placement for SEO
- Be factual — never invent specs, prices, or release dates
- WRITE WITH AUTHORITY — you are an automotive expert, not a speculator
- NEVER use "is expected to", "is anticipated", "potentially", "likely" for cars that are already on sale
- If the car is already available in any market, describe its features as FACTS, not predictions
- Be OPINIONATED — readers want your expert take, not a bland press release rewrite

Analysis Data:
{analysis_data}

Remember: Write like you're explaining to a friend who's considering buying this car. Be helpful, specific, and entertaining!
"""
    
    system_prompt = """You are a senior automotive journalist at FreshMotors with 15+ years of hands-on experience testing vehicles worldwide. You write like a mix of CarWow's Mat Watson and Doug DeMuro — technically precise but with genuine personality, humor, and strong opinions. You ALWAYS compare cars to their competitors because that's what readers actually care about. You have extensive knowledge of ALL major car brands including Chinese EVs (BYD, Zeekr, NIO, Li Auto, XPeng, Chery, Geely, GAC). You KNOW their specs from memory. When writing, ALWAYS include concrete HP/kW numbers — you are NEVER allowed to write that specs are 'not specified'. Your articles should feel like a conversation with a knowledgeable friend, not a corporate press release. Be opinionated, be specific, be entertaining. If a car is already on sale, describe it as FACT, not prediction."""
    
    try:
        # Use AI provider factory
        ai = get_ai_provider(provider)
        
        MIN_WORD_COUNT = 400  # Minimum acceptable article length
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
                max_tokens=4096
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


def expand_press_release(press_release_text, source_url, provider='groq', web_context=None):
    """
    Expands a short press release (200-300 words) into a full automotive article (800-1200 words).
    
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

You are a professional automotive journalist. Expand the following press release into a comprehensive, SEO-optimized article.

PRESS RELEASE:
{press_release_text}

SOURCE: {source_url}

CRITICAL REQUIREMENTS:
1. **Create UNIQUE content** - DO NOT copy text from the press release verbatim
   - Rephrase all information in your own words
   - Add context, analysis, and comparisons
   - Expand on technical details
   
2. **Title MUST be descriptive and engaging**
   - Include: YEAR, BRAND, MODEL, and key feature or price
   - Example: "2025 BYD Seal 06 GT Review: A Powerful Electric Hatchback for $25,000"
   - NO HTML entities in title (use plain text)

BANNED FILLER PATTERNS — these make articles feel FAKE and AI-generated:
- "While a comprehensive driving review is pending" → WRITE about it using your expertise
- "specific [X] figures are still emerging" → USE YOUR KNOWLEDGE or omit the claim
- "The [brand] is committed to [generic goal]" → GIVE A CONCRETE EXAMPLE instead
- "making waves in the [X] segment" → REPLACE with a specific comparison
- "setting a new benchmark" → SAY what benchmark and compared to WHOM
- Never write a paragraph that says you don't have data — either provide data or skip that point
- If you truly lack data for a section, write 2 strong sentences instead of 5 weak ones

WRITING PERSONALITY — make articles feel ALIVE, like CarWow and Doug DeMuro:
- COMPARE the design to recognizable cars: "The rear silhouette echoes the BMW iX, but sharper"
- Use SENSORY language instead of generic descriptions
- Give the car a PERSONALITY: "This is the car for someone who wants Tesla range without Tesla minimalism"
- Be OPINIONATED: give your expert take, not a bland rewrite
- Reference competing models BY NAME in every section — readers want context
- Break complex specs into what they MEAN for the buyer

MANDATORY COMPETITOR REFERENCES (at least ONE per section):
- Performance: compare HP, torque, 0-60 to named rivals
- Design: compare to recognizable cars by name
- Price: compare to at least 2 rivals with concrete numbers

3. **Article Structure** (Output ONLY clean HTML - NO <html>, <head>, or <body> tags):
   - <h2>[Year] [Brand] [Model] [Version]: [Engaging Hook]</h2>
   - Introduction paragraph (2-3 sentences with key specs)
   - <h2>Performance & Specifications</h2> - Detailed specs with CONCRETE NUMBERS. Include comparisons.
   - <h2>Design & Interior</h2> - Styling, materials, space. MUST compare to at least one well-known car.
   - <h2>Technology & Features</h2> - 4-5 SPECIFIC items. Compare to competitors.
   - <h2>Driving Experience</h2> - Based on specs, platform, and your knowledge. NEVER say "review is pending".
   - <h2>Pricing & Availability</h2> - CONCISE (3-5 bullet points max):
      <ul>
        <li>Starting price in USD, EUR, CNY (where applicable)</li>
        <li>Markets where confirmed available</li>
        <li>2-3 competitors with prices for comparison</li>
      </ul>
      Do NOT focus on any single market. Write as global automotive news.
      Do NOT fabricate prices or dates. Use ONLY <ul><li> HTML tags.
   - <h2>Pros & Cons</h2> - Punchy, specific, comparative (CarWow style):
     * Good: "1602 km range crushes everything in its class"
     * Bad: "Range is impressive" (too vague — REJECTED)
   - Conclusion paragraph with recommendation and specific target buyer
   
   AT THE VERY END, after the conclusion and source attribution, add:
   <div class="alt-texts" style="display:none">
   ALT_TEXT_1: [descriptive alt text for hero/exterior image]
   ALT_TEXT_2: [descriptive alt text for interior image]
   ALT_TEXT_3: [descriptive alt text for detail/tech image]
   </div>
   - <p class="source-attribution" style="margin-top: 2rem; padding: 1rem; background: #f3f4f6; border-left: 4px solid #3b82f6; font-size: 0.875rem;">
       <strong>Source:</strong> Information based on official press release. 
       <a href="{source_url}" target="_blank" rel="noopener noreferrer" style="color: #3b82f6; text-decoration: underline;">View original press release</a>
     </p>

4. **Content Expansion Guidelines**:
   - Target length: 800-1200 words
   - Add industry context (market trends, competition)
   - Include comparisons to similar vehicles BY NAME with specific numbers
   - Explain technical features in real-world terms
   - Discuss target audience and use cases
   - Add expert analysis and strong opinions

5. **SEO Optimization**:
   - Natural keyword placement (brand, model, year, EV/hybrid)
   - Include specific numbers and stats
   - Use descriptive headings
   - Write engaging, opinionated content

⚠️ CRITICAL MODEL ACCURACY WARNING:
- CAREFULLY verify the EXACT car model from the press release
- DO NOT confuse similar model names (e.g., "Zeekr 7X" vs "Zeekr 007")
- Use the EXACT name from the press release

NEGATIVE CONSTRAINTS (DO NOT INCLUDE):
- NO copied text from the press release
- NO "Advertisement" or "Sponsor" blocks
- NO placeholder text or [Insert Image Here]
- NO social media links
- NO HTML <html>, <head>, or <body> tags

Remember: Write like you're explaining to a friend who's considering this car. Be helpful, specific, and entertaining!
"""
    
    system_prompt = "You are a senior automotive journalist at FreshMotors. You write like CarWow's Mat Watson and Doug DeMuro — technically precise but with personality, humor, and strong opinions. Transform press releases into engaging, unique articles. ALWAYS compare to competitors by name. Explain what specs mean in real life. Be factual, never fabricate data. Be opinionated — readers want your expert take. Provide proper source attribution."
    
    try:
        # Use AI provider factory
        ai = get_ai_provider(provider)
        article_content = ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.65,
            max_tokens=4096  # Longer for expanded content
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

