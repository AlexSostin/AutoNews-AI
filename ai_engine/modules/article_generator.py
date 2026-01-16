from groq import Groq
from ..config import GROQ_API_KEY, GROQ_MODEL

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def generate_article(analysis_data):
    """
    Generates a structured HTML article based on the analysis using Groq (super fast!).
    """
    print("Generating article with Groq...")
    
    prompt = f"""
Create a professional automotive article based on the analysis below.
Output ONLY clean HTML content (use <h2>, <p>, <ul>, etc.) - NO <html>, <head>, or <body> tags.

CRITICAL REQUIREMENTS:
1. Title MUST be in format: "First Drive: YEAR BRAND MODEL - Brief Description"
   Example: "First Drive: 2026 Tesla Model 3 - Revolutionary Electric Sedan"
2. NO HTML entities in title (use plain text, no &quot; or &amp;)
3. Structure with clear sections using <h2> headings

Required Structure:
- <h2>Title: First Drive: [Year] [Brand] [Model] - [One-line description]</h2>
- Introduction paragraph (2-3 sentences)
- <h2>Performance & Specs</h2> - Include specific numbers (HP, torque, 0-60, range, battery)
- <h2>Design & Interior</h2>
- <h2>Technology</h2>
- <h2>Pros & Cons</h2> with <ul> lists
- Conclusion paragraph

Write professionally but engagingly. Use automotive journalism style.

Analysis Data:
{analysis_data}

Remember: Clean title with NO HTML entities!
"""
    
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional automotive journalist. Write engaging, informative articles."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=3000
        )
        article_content = response.choices[0].message.content if response.choices else ""
        
        if not article_content:
            raise Exception("Groq returned empty article")
            
        print(f"Article generated. Length: {len(article_content)} characters")
        return article_content
    except Exception as e:
        print(f"Error during article generation: {e}")
        return ""
