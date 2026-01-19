from groq import Groq
import sys

# Import config from ai_engine
try:
    from ai_engine.config import GROQ_API_KEY, GROQ_MODEL
except ImportError:
    from config import GROQ_API_KEY, GROQ_MODEL

# Import utils
try:
    from ai_engine.modules.utils import clean_title, calculate_reading_time, validate_article_quality
except ImportError:
    from modules.utils import clean_title, calculate_reading_time, validate_article_quality

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def generate_article(analysis_data):
    """
    Generates a structured HTML article based on the analysis using Groq (super fast!).
    """
    print("Generating article with Groq...")
    
    prompt = f"""
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

Required Structure:
- <h2>Title: First Drive: [Year] [Brand] [Model] - [One-line description]</h2>
- Introduction paragraph (2-3 sentences with key specs)
- <h2>Performance & Specs</h2> - Include specific numbers (HP, torque, 0-60, range, battery, price)
- <h2>Design & Interior</h2> - Describe styling, materials, space
- <h2>Technology & Features</h2> - Highlight tech innovations
- <h2>Driving Experience</h2> - Handling, comfort, real-world performance
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
    
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional automotive journalist. Write engaging, SEO-optimized articles with specific data and comparisons."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=3000
        )
        article_content = response.choices[0].message.content if response.choices else ""
        
        if not article_content:
            raise Exception("Groq returned empty article")
            
        print(f"✓ Article generated successfully! Length: {len(article_content)} characters")
        
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
        print(f"❌ Error during article generation: {e}")
        return ""
