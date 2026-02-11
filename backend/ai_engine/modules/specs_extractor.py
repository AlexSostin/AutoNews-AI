"""
AI-Powered Vehicle Specifications Extractor
Extracts structured vehicle data from article content using Gemini
"""

import json
from typing import Dict, Optional
from ai_engine.modules.ai_provider import get_ai_provider


def extract_vehicle_specs(article, provider: str = 'gemini') -> Dict:
    """
    Extract vehicle specifications from article using AI
    
    Args:
        article: Article model instance
        provider: AI provider ('gemini' or 'groq')
        
    Returns:
        Dict with extracted specs and confidence score
    """
    
    # Prepare content for analysis
    content = f"""
Title: {article.title}

Summary: {article.summary}

Content: {article.content[:4000]}
"""
    
    # Detailed extraction prompt
    prompt = f"""
You are an automotive data extraction expert. Analyze this article and extract vehicle specifications.

Return ONLY valid JSON with these exact fields. Use null for any field not mentioned in the article.
Do NOT make up or guess values - only extract what is explicitly stated.

{{
  "drivetrain": "FWD|RWD|AWD|4WD|null",
  "motor_count": <number or null>,
  "motor_placement": "front|rear|front+rear|all wheels|null",
  
  "power_hp": <number or null>,
  "power_kw": <number or null>,
  "torque_nm": <number or null>,
  "acceleration_0_100": <float or null>,
  "top_speed_kmh": <number or null>,
  
  "battery_kwh": <float or null>,
  "range_km": <number or null>,
  "range_wltp": <number or null>,
  "range_epa": <number or null>,
  
  "charging_time_fast": <string or null>,
  "charging_time_slow": <string or null>,
  "charging_power_max_kw": <number or null>,
  
  "transmission": "automatic|manual|CVT|single-speed|dual-clutch|null",
  "transmission_gears": <number or null>,
  
  "body_type": "sedan|SUV|hatchback|coupe|truck|crossover|wagon|van|null",
  "fuel_type": "EV|Hybrid|PHEV|Gas|Diesel|Hydrogen|null",
  "seats": <number or null>,
  
  "length_mm": <number or null>,
  "width_mm": <number or null>,
  "height_mm": <number or null>,
  "wheelbase_mm": <number or null>,
  "weight_kg": <number or null>,
  "cargo_liters": <number or null>,
  
  "price_from": <number or null>,
  "price_to": <number or null>,
  "currency": "USD|EUR|CNY|RUB|GBP|JPY|null",
  
  "year": <number or null>,
  "model_year": <number or null>,
  "country_of_origin": "<country name or null>",
  
  "confidence": <float 0.0-1.0>
}}

Article to analyze:
{content}

Return ONLY the JSON object, no additional text.
"""
    
    try:
        # Get AI provider
        ai = get_ai_provider(provider)
        
        # Generate response
        response = ai.generate(
            prompt=prompt,
            max_tokens=1500,
            temperature=0.1  # Low temperature for factual extraction
        )
        
        # Parse JSON response
        # Clean response (remove markdown code blocks if present)
        response_text = response.strip()
        if response_text.startswith('```'):
            # Remove ```json and ``` markers
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        
        specs_data = json.loads(response_text.strip())
        
        # Validate and clean data
        cleaned_specs = _clean_specs_data(specs_data)
        
        print(f"✅ Extracted specs for article #{article.id}: {article.title[:50]}...")
        print(f"   Confidence: {cleaned_specs.get('confidence', 0):.2f}")
        
        return cleaned_specs
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error for article #{article.id}: {str(e)}")
        print(f"   Response was: {response[:200]}...")
        return _empty_specs()
        
    except Exception as e:
        print(f"❌ Error extracting specs for article #{article.id}: {str(e)}")
        return _empty_specs()


def _clean_specs_data(data: Dict) -> Dict:
    """
    Clean and validate extracted specs data
    
    Args:
        data: Raw extracted data
        
    Returns:
        Cleaned data dict
    """
    cleaned = {}
    
    # String fields
    string_fields = [
        'drivetrain', 'motor_placement', 'transmission', 
        'body_type', 'fuel_type', 'currency', 'country_of_origin',
        'charging_time_fast', 'charging_time_slow'
    ]
    for field in string_fields:
        value = data.get(field)
        cleaned[field] = value if value and value != 'null' else None
    
    # Integer fields
    int_fields = [
        'motor_count', 'power_hp', 'power_kw', 'torque_nm',
        'top_speed_kmh', 'range_km', 'range_wltp', 'range_epa',
        'charging_power_max_kw', 'transmission_gears', 'seats',
        'length_mm', 'width_mm', 'height_mm', 'wheelbase_mm',
        'weight_kg', 'cargo_liters', 'price_from', 'price_to',
        'year', 'model_year'
    ]
    for field in int_fields:
        value = data.get(field)
        if value is not None and value != 'null':
            try:
                cleaned[field] = int(value)
            except (ValueError, TypeError):
                cleaned[field] = None
        else:
            cleaned[field] = None
    
    # Float fields
    float_fields = ['battery_kwh', 'acceleration_0_100', 'confidence']
    for field in float_fields:
        value = data.get(field)
        if value is not None and value != 'null':
            try:
                cleaned[field] = float(value)
            except (ValueError, TypeError):
                cleaned[field] = None if field != 'confidence' else 0.0
        else:
            cleaned[field] = None if field != 'confidence' else 0.0
    
    # Ensure confidence is between 0 and 1
    if cleaned.get('confidence', 0) > 1.0:
        cleaned['confidence'] = 1.0
    elif cleaned.get('confidence', 0) < 0.0:
        cleaned['confidence'] = 0.0
    
    return cleaned


def _empty_specs() -> Dict:
    """Return empty specs dict with zero confidence"""
    return {
        'drivetrain': None,
        'motor_count': None,
        'motor_placement': None,
        'power_hp': None,
        'power_kw': None,
        'torque_nm': None,
        'acceleration_0_100': None,
        'top_speed_kmh': None,
        'battery_kwh': None,
        'range_km': None,
        'range_wltp': None,
        'range_epa': None,
        'charging_time_fast': None,
        'charging_time_slow': None,
        'charging_power_max_kw': None,
        'transmission': None,
        'transmission_gears': None,
        'body_type': None,
        'fuel_type': None,
        'seats': None,
        'length_mm': None,
        'width_mm': None,
        'height_mm': None,
        'wheelbase_mm': None,
        'weight_kg': None,
        'cargo_liters': None,
        'price_from': None,
        'price_to': None,
        'currency': None,
        'year': None,
        'model_year': None,
        'country_of_origin': None,
        'confidence': 0.0
    }
