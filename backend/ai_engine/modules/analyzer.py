from groq import Groq
import sys
import os
import logging
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
Engine: [Engine type/size - e.g., "1.5L Turbo" or "Electric motor" or "2.0L Turbocharged Inline-4"]
Horsepower: [Number with unit - e.g., "300 hp" or "220 kW". ALWAYS specify hp or kW]
Torque: [Torque with unit - e.g., "400 Nm" or "295 lb-ft". ALWAYS specify Nm or lb-ft]
Acceleration: [0-60 mph or 0-100 km/h time - e.g., "5.5 seconds (0-60 mph)". ALWAYS specify which measurement]
Top Speed: [Max speed with unit - e.g., "155 mph" or "250 km/h". ALWAYS specify mph or km/h]
Drivetrain: [Drive type - "AWD", "FWD", "RWD", or "4WD". Write "Not specified" if not mentioned]
Battery: [Battery capacity for EVs - e.g., "75 kWh"]
Range: [Driving range - e.g., "400 km" or "250 miles". ALWAYS specify km or miles]
Price: [Starting price with currency - e.g., "$45,000" or "€50,000" or "¥169,800"]
  ⚠️ CHINESE PRICE FORMAT: Chinese prices often use 万 (wàn) = 10,000.
  So "11.5万" = ¥115,000 (NOT ¥11,500). "19万" = ¥190,000. "7.98万" = ¥79,800.
  ALWAYS convert 万 to the full number. Output price as: ¥115,000 (not ¥11.5万)

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
3. ONLY include specs that are explicitly mentioned in the transcript or that you are 100% certain about for this exact model/trim.
4. If a spec is NOT mentioned in the transcript and you are NOT 100% certain, write "Not specified" for that field. Do NOT guess or estimate.
5. NEVER use "(estimated)", "(approximate)", "(standard spec)" or similar qualifiers. Either you know the exact spec or leave it as "Not specified".
6. ALWAYS include units: hp or kW for power, Nm or lb-ft for torque, mph or km/h for speed, seconds for acceleration.
7. Be extremely precise with Make, Model, and Trim. Fix typos in transcript (e.g. "Chin L DMI" -> "BYD Qin L DM-i").
8. IMPORTANT: Do not normalize or "correct" model names unless you are 100% sure it's a transcription error. A "YU7" is NOT an "SU7" if they are different models.
"""
    
    system_prompt = "You are an expert automotive analyst. You extract facts from transcripts accurately. You ONLY include specifications that are explicitly stated or that you are 100% certain about. You NEVER guess or estimate — if a spec is unclear, you write 'Not specified'. You always include measurement units. You correct obvious transcription errors in model names."
    
    try:
        # Use AI provider factory
        ai = get_ai_provider(provider)
        analysis = ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.4,
            max_tokens=2000
        )
        
        if not analysis:
            raise Exception(f"{provider_name} returned empty analysis")
            
        print(f"Analysis complete with {provider_name}. Length: {len(analysis)} characters")
        return analysis
    except Exception as e:
        logger.error(f"Analysis failed with {provider_name}: {e}")
        logger.error(f"Transcript (first 300 chars): {str(transcript_text)[:300]}")
        print(f"Error during analysis with {provider_name}: {e}")
        return ""


def _get_db_categories():
    """Fetch category names from the database for the prompt."""
    try:
        import django
        if django.apps.apps.ready:
            from news.models import Category
            categories = Category.objects.filter(is_visible=True).values_list('name', flat=True)
            if categories:
                return list(categories)
    except Exception:
        pass
    # Fallback if DB not available
    return ["News", "Reviews", "EVs", "Technology", "Industry", "Comparisons"]


def _get_db_tags():
    """
    Fetch tags from the database grouped by TagGroup.
    Returns a dict: {group_name: [tag_names]}
    Only includes relevant groups for the AI prompt.
    """
    RELEVANT_GROUPS = ['Manufacturers', 'Body Types', 'Fuel Types', 'Segments', 'Drivetrain', 'Years', 'Models']
    
    try:
        import django
        if django.apps.apps.ready:
            from news.models import Tag, TagGroup
            result = {}
            for group_name in RELEVANT_GROUPS:
                tags = Tag.objects.filter(
                    group__name=group_name
                ).values_list('name', flat=True).order_by('name')
                if tags:
                    result[group_name] = list(tags)
            if result:
                return result
    except Exception:
        pass
    
    # Fallback if DB not available
    return {
        'Manufacturers': ['BMW', 'Mercedes', 'Audi', 'Tesla', 'Toyota', 'Honda', 'Ford',
                          'Volkswagen', 'Nissan', 'Hyundai', 'Kia', 'Porsche', 'Volvo',
                          'BYD', 'NIO', 'XPeng', 'Zeekr', 'Li Auto', 'Xiaomi', 'DongFeng',
                          'Geely', 'Denza', 'VOYAH', 'HUAWEI', 'Rivian', 'Lucid'],
        'Body Types': ['SUV', 'Sedan', 'Coupe', 'Hatchback', 'Crossover', 'Truck',
                       'Wagon', 'MPV', 'Shooting Brake', 'Minivan', 'Pickup'],
        'Fuel Types': ['EV', 'Hybrid', 'PHEV', 'DM-i', 'E‑REV', 'BEV', 'Diesel', 'Gasoline'],
        'Segments': ['Luxury', 'Family', 'Budget', 'Comfort', 'Sport', 'Premium',
                     'Off-road', 'City', 'Supercar'],
        'Drivetrain': ['AWD', 'FWD', 'RWD', '4WD'],
        'Years': ['2024', '2025', '2026', '2027'],
    }


def categorize_article(analysis, provider='groq'):
    """
    Determines category and tags based on analysis using the AI provider factory.
    Uses tags from the database when available, falls back to hardcoded list.
    """
    print("Categorizing article with AI...")
    
    # Fetch categories from DB instead of hardcoding
    db_categories = _get_db_categories()
    categories_str = "\n".join([f"- {cat}" for cat in db_categories])
    
    # Fetch tags from DB grouped by TagGroup
    db_tags = _get_db_tags()
    tags_section = ""
    for group_name, tag_list in db_tags.items():
        tags_section += f"{group_name}: {', '.join(tag_list)}\n"
    
    prompt = f"""
Based on this automotive analysis, determine the best category and relevant tags.

Categories (choose ONE):
{categories_str}

Tags (choose 5-8 relevant tags from these groups):
RULES:
- ALWAYS include at least one tag from Manufacturers (the car brand)
- ALWAYS include a Year tag if the model year is mentioned (e.g., "2026")
- ALWAYS include the correct Body Type. Use these guidelines:
  * "Sedan" — traditional 3-box car with separate trunk (BYD Qin, Tesla Model 3)
  * "SUV" — larger, tall vehicles with raised ride height (BYD Tang, Tesla Model X)
  * "Crossover" — car-based SUV, smaller/lower than traditional SUV (e.g., compact crossovers)
  * "Hatchback" — 2-box car with rear lift gate (VW Golf, BYD Dolphin)
  * "Coupe" — 2-door sporty vehicle or 4-door coupe-styled sedan
  * "MPV" — multi-purpose van / people carrier (BYD D9, Zeekr 009)
  * "Pickup" — truck with open bed
  * Do NOT confuse Sedan with Hatchback or SUV with Crossover
- Include the correct Fuel Type:
  * "DM-i" — BYD's plug-in hybrid system
  * "PHEV" — non-BYD plug-in hybrids
  * "EV" or "BEV" — fully electric
  * "E-REV" — extended-range EV (Li Auto, VOYAH)
  * "Hybrid" — non-plug-in hybrid (Toyota HEV)
- Include a Segment tag if applicable (Luxury, Budget, Sport, etc.)

{tags_section}
Analysis:
{analysis[:2000]}

Output ONLY in this format (no extra text):
Category: [category_name]
Tags: [tag1], [tag2], [tag3], [tag4], [tag5]
"""
    
    try:
        # Use AI provider factory (not hardcoded Groq)
        ai = get_ai_provider(provider)
        result = ai.generate_completion(
            prompt=prompt,
            system_prompt="You are an expert automotive content categorizer. Choose tags that exactly match the provided options.",
            temperature=0.2,  # Low temperature for deterministic categorization
            max_tokens=200
        )
        
        if not result:
            raise Exception("Empty response from AI")
        
        # Parse result
        category = "Reviews"  # Default
        tags = []
        
        # Build a lookup of all valid tag names (lowercase → exact name)
        all_valid_tags = {}
        for tag_list in db_tags.values():
            for tag_name in tag_list:
                all_valid_tags[tag_name.lower()] = tag_name
        
        for line in result.split('\n'):
            if line.startswith('Category:'):
                cat_name = line.split(':', 1)[1].strip()
                # Validate against DB categories (fuzzy match)
                matched = False
                for db_cat in db_categories:
                    if cat_name.lower() == db_cat.lower():
                        category = db_cat  # Use exact DB name
                        matched = True
                        break
                if not matched:
                    category = cat_name  # Use AI output as-is
            elif line.startswith('Tags:'):
                tags_str = line.split(':', 1)[1].strip()
                raw_tags = [t.strip() for t in tags_str.split(',') if t.strip()]
                # STRICT validation: only accept tags that exist in DB
                # This prevents AI hallucinations like "Hyundai is not relevant here"
                for raw_tag in raw_tags:
                    # Quick sanity check — real tags are short (1-3 words max)
                    if len(raw_tag) > 30 or len(raw_tag.split()) > 4:
                        print(f"  ⚠️ Rejected hallucinated tag: '{raw_tag}'")
                        continue
                    matched_name = all_valid_tags.get(raw_tag.lower())
                    if matched_name:
                        tags.append(matched_name)
                    else:
                        print(f"  ⚠️ Tag not in DB, skipped: '{raw_tag}'")
        
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
        'drivetrain': 'Not specified',
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
        elif line.startswith('Drivetrain:') or line.startswith('Drive:'):
            specs['drivetrain'] = line.split(':', 1)[1].strip()
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
    Handles formats: $45,000, €50,000, ¥320,000, ¥11.5万, 45000 USD, etc.
    """
    price_str = None
    
    # Find Price line in analysis
    for line in analysis.split('\n'):
        if line.strip().startswith('Price:'):
            price_str = line.split(':', 1)[1].strip()
            break
    
    if not price_str or price_str.lower() == 'not specified':
        return None
    
    # Handle Chinese 万 (wàn = 10,000) format FIRST
    # Matches: ¥11.5万, 11.5万元, ¥7.98万
    wan_match = re.search(r'[¥]?(\d+\.?\d*)\s*万', price_str)
    if wan_match:
        amount_wan = float(wan_match.group(1))
        amount_cny = amount_wan * 10000  # 11.5万 = 115,000
        amount_usd = amount_cny / 7.25
        logger.info(f"Converted Chinese 万 price: {price_str} → ¥{amount_cny:,.0f} → ${amount_usd:,.0f}")
        return round(amount_usd, 2)
    
    # Extract number from price string
    # Remove commas and spaces
    clean_price = price_str.replace(',', '').replace(' ', '')
    
    # Find the number (support decimals like 115000.00)
    match = re.search(r'[\$€¥£]?(\d+(?:\.\d+)?)', clean_price)
    if not match:
        return None
    
    amount = float(match.group(1))
    
    # Detect currency and convert to USD
    if '€' in price_str or 'EUR' in price_str.upper():
        amount = amount * 1.09
    elif '¥' in price_str or 'CNY' in price_str.upper() or 'RMB' in price_str.upper():
        # Could be CNY or JPY
        if amount > 1000000:
            # Likely JPY (Japanese Yen) — very high numbers
            amount = amount / 148.5
        else:
            # CNY to USD
            amount = amount / 7.25
    elif '£' in price_str or 'GBP' in price_str.upper():
        amount = amount * 1.27
    # USD is default ($ or no symbol)
    
    # Sanity check: car prices should be reasonable ($1,000 - $10M)
    if amount < 1000 or amount > 10000000:
        logger.warning(f"Price out of range after conversion: {price_str} → ${amount:,.0f}")
        return None
    
    return round(amount, 2)
