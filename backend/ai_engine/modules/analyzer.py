from groq import Groq
import sys

# Import config from ai_engine
try:
    from ai_engine.config import GROQ_API_KEY, GROQ_MODEL
except ImportError:
    from config import GROQ_API_KEY, GROQ_MODEL

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def analyze_transcript(transcript_text):
    """
    Analyzes the transcript to extract car details using Groq (super fast!).
    """
    print("Analyzing transcript with Groq...")
    
    prompt = f"""
Analyze this automotive video transcript and extract key information in STRUCTURED format.

Output format (use these EXACT labels):
Make: [Brand name]
Model: [Model name]
Year: [Year if mentioned, else estimate based on context]
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

IMPORTANT: Use exact labels above. If info not available, write "Not specified".
"""
    
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert automotive analyst. Provide detailed, structured analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        analysis = response.choices[0].message.content if response.choices else ""
        
        if not analysis:
            raise Exception("Groq returned empty analysis")
            
        print(f"Analysis complete. Length: {len(analysis)} characters")
        return analysis
    except Exception as e:
        print(f"Error during analysis: {e}")
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
        'year': None,
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
        elif line.startswith('Year:'):
            year_str = line.split(':', 1)[1].strip()
            try:
                specs['year'] = int(year_str) if year_str.isdigit() else None
            except:
                pass
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
