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

# Import AI provider
try:
    from ai_engine.modules.ai_provider import get_ai_provider
except ImportError:
    from modules.ai_provider import get_ai_provider

# Legacy client for backwards compatibility
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def analyze_transcript(transcript_text, video_title=None, provider='groq'):
    """
    Analyzes the transcript to extract car details using selected AI provider.
    
    Args:
        transcript_text: The video transcript text
        video_title: The YouTube video title (optional but recommended for context)
        provider: 'groq' (default) or 'gemini'
    
    Returns:
        Structured analysis text
    """
    provider_name = "Groq" if provider == 'groq' else "Google Gemini"
    print(f"Analyzing transcript with {provider_name}...")
    
    context_str = f"Video Title: {video_title}\n" if video_title else ""
    
    prompt = f"""
Analyze this automotive video transcript and extract key information in STRUCTURED format.
{context_str}
Output format (use these EXACT labels):
Make: [Brand name]
Model: [Base Model name, e.g. "SU7", "Golf"]
Trim/Version: [Specific version or trim, e.g. "Ultra", "Performance", "GTI", "Standard"]
Year: [Model Year]
SEO Title: [Short, clear title - e.g. "2026 Tesla Model 3 Performance Review"]
Engine: [Engine type/size - e.g., "1.5L Turbo" or "Electric motor"]
Horsepower: [HP number - e.g., "300 HP"]
Torque: [Torque - e.g., "400 Nm"]
Acceleration: [0-60 or 0-100 time - e.g., "5.5 seconds"]
Top Speed: [Max speed - e.g., "155 mph"]
Battery: [Battery capacity for EVs - e.g., "75 kWh"]
Range: [Driving range - e.g., "400 km" or "250 miles"]
Price: [Starting price - e.g., "$45,000" or "€50,000"]

Key Features:
- [List main features]
- [Technology highlights]

Pros:
- [List advantages]

Cons:
- [List disadvantages]

Summary: [2-3 sentence overview]

Transcript:
{transcript_text[:15000]}

IMPORTANT: 
1. Use EXACT labels above. 
2. Prioritize facts from the transcript.
3. If technical specs (HP, Battery, Price) are missing in transcript, YOU MAY USE YOUR INTERNAL KNOWLEDGE to fill them if you are confident about the exact car model.
4. If you use internal knowledge, mark it as (estimated) or (standard spec).
5. Be extremely precise with Make, Model, and Trim. Fix typos in transcript (e.g. "Chin L DMI" -> "BYD Qin L DM-i").
6. IMPORTANT: Do not normalize or "correct" model names unless you are 100% sure it's a transcription error. A "YU7" is NOT an "SU7" if they are different models.
"""
    
    system_prompt = "You are an expert automotive analyst. You extract facts from transcripts but also use your vast knowledge of car specifications to fill in gaps when the video omits details. You correct obvious transcription errors (e.g. model names)."
    
    try:
        # Use AI provider factory
        ai = get_ai_provider(provider)
        analysis = ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=2000
        )
        
        if not analysis:
            raise Exception(f"{provider_name} returned empty analysis")
            
        print(f"Analysis complete with {provider_name}. Length: {len(analysis)} characters")
        return analysis
    except Exception as e:
        print(f"Error during analysis with {provider_name}: {e}")
        return ""


def categorize_article(analysis):
    """
    Определяет категорию и теги на основе анализа (БЕСПЛАТНО через Groq).
    """
    print("Categorizing article with AI...")
    
    prompt = f"""
Based on this automotive analysis, determine the best category and relevant tags.

Categories (choose ONE):
- News (новости, анонсы, релизы новых моделей)
- Reviews (обзоры и тест-драйвы автомобилей)
- EVs (электромобили и гибриды)
- Technology (новые технологии в автомобилях)
- Industry (автопром, производство, продажи)
- Comparisons (сравнение моделей)

Tags (choose 5-7 from these categories):
Brand Tags: BMW, Mercedes-Benz, Audi, Tesla, Toyota, Honda, Ford, Volkswagen, Nissan, Hyundai, Kia, Porsche, Volvo, Jaguar, Land Rover, Lexus, Genesis, Rivian, Lucid
Type Tags: EV, Hybrid, PHEV, SUV, Sedan, Coupe, Truck, Sports Car, Hatchback, Wagon
Feature Tags: Electric, Autonomous, Performance, Luxury, Budget, Off-Road, Family

Analysis:
{analysis[:2000]}

Output ONLY in this format (no extra text):
Category: [category_name]
Tags: [tag1], [tag2], [tag3], [tag4], [tag5]
"""
    
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert automotive content categorizer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Низкая температура для точности
            max_tokens=200
        )
        
        result = response.choices[0].message.content if response.choices else ""
        
        # Парсим результат
        category = "Reviews"  # Default
        tags = []
        
        for line in result.split('\n'):
            if line.startswith('Category:'):
                category = line.split(':', 1)[1].strip()
            elif line.startswith('Tags:'):
                tags_str = line.split(':', 1)[1].strip()
                tags = [t.strip() for t in tags_str.split(',')]
        
        print(f"✓ Category: {category}, Tags: {', '.join(tags)}")
        return category, tags
        
    except Exception as e:
        print(f"⚠️  Categorization failed: {e}")
        return "Reviews", []


def extract_specs_dict(analysis):
    """
    Извлекает структурированные характеристики из анализа для БД.
    """
    specs = {
        'make': 'Not specified',
        'model': 'Not specified',
        'trim': 'Not specified',
        'year': None,
        'seo_title': None,
        'engine': 'Not specified',
        'horsepower': None,
        'torque': 'Not specified',
        'acceleration': 'Not specified',
        'top_speed': 'Not specified',
        'battery': 'Not specified',
        'range': 'Not specified',
        'price': 'Not specified'
    }
    
    # Парсим анализ построчно
    for line in analysis.split('\n'):
        line = line.strip()
        
        if line.startswith('Make:'):
            specs['make'] = line.split(':', 1)[1].strip()
        elif line.startswith('Model:'):
            specs['model'] = line.split(':', 1)[1].strip()
        elif line.startswith('Trim/Version:'):
            specs['trim'] = line.split(':', 1)[1].strip()
        elif line.startswith('Year:'):
            year_str = line.split(':', 1)[1].strip()
            try:
                specs['year'] = int(year_str) if year_str.isdigit() else None
            except:
                pass
        elif line.startswith('SEO Title:'):
            specs['seo_title'] = line.split(':', 1)[1].strip()
        elif line.startswith('Engine:'):
            specs['engine'] = line.split(':', 1)[1].strip()
        elif line.startswith('Horsepower:'):
            hp_str = line.split(':', 1)[1].strip()
            try:
                # Извлекаем число из "300 HP" или "300"
                import re
                match = re.search(r'(\d+)', hp_str)
                if match:
                    specs['horsepower'] = int(match.group(1))
            except:
                pass
        elif line.startswith('Torque:'):
            specs['torque'] = line.split(':', 1)[1].strip()
        elif line.startswith('Acceleration:'):
            specs['acceleration'] = line.split(':', 1)[1].strip()
        elif line.startswith('Top Speed:'):
            specs['top_speed'] = line.split(':', 1)[1].strip()
        elif line.startswith('Battery:'):
            specs['battery'] = line.split(':', 1)[1].strip()
        elif line.startswith('Range:'):
            specs['range'] = line.split(':', 1)[1].strip()
        elif line.startswith('Price:'):
            specs['price'] = line.split(':', 1)[1].strip()
    
    return specs


def extract_price_usd(analysis):
    """
    Extracts price from analysis and converts to USD number.
    Handles formats: $45,000, €50,000, ¥320,000, 45000 USD, etc.
    """
    import re
    
    price_str = None
    
    # Find Price line in analysis
    for line in analysis.split('\n'):
        if line.strip().startswith('Price:'):
            price_str = line.split(':', 1)[1].strip()
            break
    
    if not price_str or price_str.lower() == 'not specified':
        return None
    
    # Extract number from price string
    # Remove commas and spaces
    clean_price = price_str.replace(',', '').replace(' ', '')
    
    # Find the number
    match = re.search(r'[\$€¥£]?(\d+(?:\.\d{2})?)', clean_price)
    if not match:
        return None
    
    amount = float(match.group(1))
    
    # Detect currency and convert to USD
    if '€' in price_str or 'EUR' in price_str.upper():
        # EUR to USD (approximate)
        amount = amount * 1.09
    elif '¥' in price_str or 'CNY' in price_str.upper() or 'RMB' in price_str.upper():
        # CNY to USD
        amount = amount / 7.25
    elif '¥' in price_str and amount > 1000000:
        # Likely JPY (Japanese Yen) - very high numbers
        amount = amount / 148.5
    elif '£' in price_str or 'GBP' in price_str.upper():
        # GBP to USD
        amount = amount * 1.27
    # USD is default ($ or no symbol)
    
    # Sanity check: car prices should be reasonable
    if amount < 1000 or amount > 10000000:
        return None
    
    return round(amount, 2)
