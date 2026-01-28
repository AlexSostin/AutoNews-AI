from groq import Groq
import sys
import os

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
Create a professional, SEO-optimized automotive article based on the analysis below.
Output ONLY clean HTML content (use <h2>, <p>, <ul>, etc.) - NO <html>, <head>, or <body> tags.

CRITICAL REQUIREMENTS:
1. Title MUST be in format: "First Drive: YEAR BRAND MODEL - Brief Description"
   Example: "First Drive: 2026 Tesla Model 3 - Revolutionary Electric Sedan"
2. NO HTML entities in title (use plain text, no &quot; or &amp;)
3. Structure with clear sections using <h2> headings
4. Include specific numbers, stats, and comparisons for SEO
5. Use natural keywords related to the car brand, model, year
6. Write engaging, informative content (aim for 800-1200 words)

NEGATIVE CONSTRAINTS (DO NOT INCLUDE):
- NO "Advertisement", "Ad Space", or "Sponsor" blocks
- NO placeholder text like "Article image 1" or "[Insert Image Here]"
- NO social media links (Subscribe, Follow us)
- NO navigation menus or headers/footers
- NO "Read more" links
- NO HTML <html>, <head>, or <body> tags


Required Structure:
- <h2>Title: First Drive: [Year] [Brand] [Model] - [One-line description]</h2>
- Introduction paragraph (2-3 sentences with key specs)
- <h2>Performance & Specs</h2> - Include specific numbers (HP, torque, 0-60, range, battery, price)
- <h2>Design & Interior</h2> - Describe styling, materials, space
- <h2>Technology & Features</h2> - Highlight tech innovations
- <h2>Driving Experience</h2> - Handling, comfort, real-world performance
- <h2>US Market Availability & Pricing</h2> - IMPORTANT: Include:
  * Will this car be sold in the United States? (Yes/No with timeline)
  * Expected US pricing (MSRP in USD, mention trims if applicable)
  * Import taxes and fees if applicable (federal, state, customs duties)
  * Any federal or state EV tax credits/incentives if electric/hybrid
  * Comparison to competitor pricing in US market
  * Registration and ownership costs considerations
- <h2>Global Market & Regional Availability</h2> - CRITICAL: Include:
  * List which major regions will get this car: North America, Europe, Asia, Middle East, Australia, South America
  * Mention specific countries or markets where it will be sold
  * Timeline for each region (e.g., "Europe Q2 2026, Asia Q3 2026")
  * Any regional exclusives or variations (different trims, specs by region)
  * Pricing differences between major markets
- <h2>Pros & Cons</h2> with <ul> lists (be specific!)
- Conclusion paragraph with recommendation and target buyer

Writing Style:
- Professional automotive journalism
- Include comparisons to competitors when relevant
- Mention target audience (families, enthusiasts, eco-conscious, etc.)
- Use descriptive language but stay factual
- Natural keyword placement for SEO

Analysis Data:
{analysis_data}

Remember: Clean title with NO HTML entities! Write comprehensive, engaging content!
"""
    
    system_prompt = "You are a professional automotive journalist. Write engaging, SEO-optimized articles with specific data and comparisons."
    
    try:
        # Use AI provider factory
        ai = get_ai_provider(provider)
        article_content = ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.8,
            max_tokens=3000
        )
        
        if not article_content:
            raise Exception(f"{provider_display} returned empty article")
            
        print(f"✓ Article generated successfully with {provider_display}! Length: {len(article_content)} characters")
        
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
        print(f"❌ Error during article generation with {provider_display}: {e}")
        return ""
