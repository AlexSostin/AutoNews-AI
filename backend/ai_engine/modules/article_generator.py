from groq import Groq
import sys
import os
import logging
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
    
    prompt = f"""
{web_data_section}
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
6. Write engaging, informative content (aim for 800-1200 words)

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


Required Structure:
- <h2>[Year] [Brand] [Model] [Version] Review: [Hook/Description]</h2>
- Introduction paragraph (2-3 sentences with key specs)
- <h2>Performance & Specs</h2> - Include specific numbers (HP, torque, 0-60, range, battery, price)
- <h2>Design & Interior</h2> - Describe styling, materials, space
- <h2>Technology & Features</h2> - Highlight tech innovations
- <h2>Driving Experience</h2> - Handling, comfort, real-world performance
- <h2>US Market Availability & Pricing</h2> - IMPORTANT: Write this as flowing paragraphs and HTML lists. Include:
  <ul>
    <li>Will this car be sold in the United States? (Yes/No with timeline)</li>
    <li>Expected US pricing (MSRP in USD, mention trims if applicable)</li>
    <li>Import taxes and fees if applicable (federal, state, customs duties)</li>
    <li>Any federal or state EV tax credits/incentives if electric/hybrid</li>
    <li>Comparison to competitor pricing in US market</li>
    <li>Registration and ownership costs considerations</li>
  </ul>
  If exact US data is unavailable, analyze the brand's current US strategy:
  - If the brand has NO US presence (e.g., BYD, Chery), explain WHY (tariffs, regulations) and give equivalent pricing context
  - If the brand IS in the US, estimate based on existing lineup pricing
  Do NOT fabricate prices or dates. Do NOT use asterisks (*) or markdown bullets — only <ul><li> HTML tags.
- <h2>Global Market & Regional Availability</h2> - CRITICAL: Format this section with clear structure:
  * Use <h3> sub-headings for each major region (e.g., <h3>Asia</h3>, <h3>Europe</h3>, <h3>North America</h3>)
  * Under each region, use <ul> and <li> tags to list specific countries and details
  * Example format:
    <h3>Asia</h3>
    <ul>
      <li><strong>China:</strong> Available Q1 2026, starting at ¥280,000</li>
      <li><strong>Singapore:</strong> Expected Q2 2026, pricing TBA</li>
      <li><strong>Thailand:</strong> Launch planned for Q3 2026</li>
    </ul>
  * Include timeline, pricing differences, and regional variations for each market
  * Keep each bullet point concise (1-2 sentences max)
- <h2>Pros & Cons</h2> - CRITICAL: Use <ul> and <li> tags for the lists. Each pro and con MUST be a separate <li> item.
  Example:
  <h3>Pros</h3>
  <ul>
    <li>Pro item 1</li>
    <li>Pro item 2</li>
  </ul>
  <h3>Cons</h3>
  <ul>
- Conclusion paragraph with recommendation and target buyer

AT THE VERY END, after the conclusion, add this block:
<div class="alt-texts" style="display:none">
ALT_TEXT_1: [descriptive alt text for a hero/exterior image]
ALT_TEXT_2: [descriptive alt text for an interior image]
ALT_TEXT_3: [descriptive alt text for a detail/tech image]
</div>

Writing Style:
- Combine technical expertise with engaging, accessible language
- Explain what specs mean for the driver in real life (e.g., "314 hp means 0-60 in 5.9s — enough to merge confidently on any highway")
- Include comparisons to competitors when relevant
- Mention target audience (families, enthusiasts, eco-conscious, etc.)
- Natural keyword placement for SEO
- Be factual — never invent specs, prices, or release dates

Analysis Data:
{analysis_data}

Remember: Be creative with the title, but include all facts! Write comprehensive, engaging content!
"""
    
    system_prompt = "You are a senior automotive expert at FreshMotors. Combine deep technical knowledge with engaging, accessible writing. Explain specs in terms of real-world driving impact. Be factual — never fabricate data. Write SEO-optimized content with specific numbers and competitor comparisons."
    
    try:
        # Use AI provider factory
        ai = get_ai_provider(provider)
        article_content = ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=3000
        )
        
        if not article_content:
            raise Exception(f"{provider_display} returned empty article")
            
        print(f"✓ Article generated successfully with {provider_display}! Length: {len(article_content)} characters")
        
        # Post-processing: ensure it's HTML, not Markdown
        article_content = ensure_html_only(article_content)
        
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
    
    prompt = f"""
{web_data_section}
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

3. **Article Structure** (Output ONLY clean HTML - NO <html>, <head>, or <body> tags):
   - <h2>[Year] [Brand] [Model] [Version]: [Engaging Hook]</h2>
   - Introduction paragraph (2-3 sentences with key specs)
   - <h2>Performance & Specifications</h2> - Detailed specs, power, range, battery
   - <h2>Design & Interior</h2> - Styling, materials, space, comfort
   - <h2>Technology & Features</h2> - Infotainment, safety, innovations
   - <h2>Driving Experience</h2> - Handling, comfort, real-world performance
   - <h2>US Market Availability & Pricing</h2> - Write as flowing paragraphs and HTML lists:
      <ul>
        <li>Will it be sold in the US? (Yes/No with timeline)</li>
        <li>Expected US pricing (MSRP in USD)</li>
        <li>Import taxes/fees if applicable</li>
        <li>Federal/state EV incentives if electric/hybrid</li>
        <li>Comparison to US competitors</li>
      </ul>
      If exact US data is unavailable, analyze the brand's US strategy (tariffs, regulations) and provide equivalent pricing context.
      Do NOT fabricate prices or dates. Do NOT use asterisks (*) or markdown bullets — only <ul><li> HTML tags.
   - <h2>Global Market & Regional Availability</h2>
     * Use <h3> for regions (Asia, Europe, North America)
     * Use <ul><li> for country-specific details
     * Include timelines and pricing for each market
   - <h2>Pros & Cons</h2>
     * <h3>Pros</h3> <ul><li>Pro 1</li><li>Pro 2</li></ul>
     * <h3>Cons</h3> <ul><li>Con 1</li><li>Con 2</li></ul>
   - Conclusion paragraph with recommendation
   
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
   - Include comparisons to similar vehicles
   - Explain technical features in detail
   - Discuss target audience and use cases
   - Add expert analysis and insights

5. **SEO Optimization**:
   - Natural keyword placement (brand, model, year, EV/hybrid)
   - Include specific numbers and stats
   - Use descriptive headings
   - Write engaging, informative content

⚠️ CRITICAL MODEL ACCURACY WARNING:
- CAREFULLY verify the EXACT car model from the press release
- DO NOT confuse similar model names (e.g., "Zeekr 7X" vs "Zeekr 007")
- Pay attention to spaces, numbers, and letters in model names
- Use the EXACT name from the press release

NEGATIVE CONSTRAINTS (DO NOT INCLUDE):
- NO copied text from the press release
- NO "Advertisement" or "Sponsor" blocks
- NO placeholder text or [Insert Image Here]
- NO social media links
- NO HTML <html>, <head>, or <body> tags

Remember: Create ORIGINAL content based on the facts, add value through analysis and context!
"""
    
    system_prompt = "You are a senior automotive expert at FreshMotors. Transform press releases into engaging, unique articles. Combine technical depth with accessible writing — explain what specs mean in real life. Be factual, never fabricate data. Provide proper source attribution."
    
    try:
        # Use AI provider factory
        ai = get_ai_provider(provider)
        article_content = ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=3500  # Longer for expanded content
        )
        
        if not article_content:
            raise Exception(f"{provider_display} returned empty article")
            
        print(f"✓ Press release expanded successfully with {provider_display}! Length: {len(article_content)} characters")
        
        # Post-processing: ensure it's HTML, not Markdown
        article_content = ensure_html_only(article_content)
        
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
        raise
