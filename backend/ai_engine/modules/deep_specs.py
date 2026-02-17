"""
Deep Specs Enrichment Module — uses AI to generate comprehensive VehicleSpecs.

After an article is published, this module:
1. Takes the extracted make/model/trim + any web context
2. Sends a structured prompt to Gemini/Groq asking for ALL vehicle specifications
3. Parses the JSON response
4. Creates/updates VehicleSpecs record (the /cars/{brand}/{model} card)

This is the "3rd pass" — YouTube transcript → web enrichment → AI deep specs.
"""
import json
import re
import logging

logger = logging.getLogger(__name__)


# Valid choices for constrained fields (must match VehicleSpecs model choices)
VALID_DRIVETRAINS = {'FWD', 'RWD', 'AWD', '4WD'}
VALID_TRANSMISSIONS = {'automatic', 'manual', 'CVT', 'single-speed', 'dual-clutch'}
VALID_BODY_TYPES = {
    'sedan', 'SUV', 'hatchback', 'coupe', 'truck', 'crossover', 'wagon',
    'shooting_brake', 'van', 'convertible', 'pickup', 'liftback', 'fastback',
    'MPV', 'roadster', 'cabriolet', 'targa', 'limousine',
}
VALID_FUEL_TYPES = {'EV', 'Hybrid', 'PHEV', 'Gas', 'Diesel', 'Hydrogen'}
VALID_CURRENCIES = {'USD', 'EUR', 'CNY', 'RUB', 'GBP', 'JPY'}


def _build_prompt(make, model_name, trim, year, existing_specs, web_context):
    """Build the structured prompt for AI spec generation."""
    
    vehicle_id = f"{year or ''} {make} {model_name} {trim or ''}".strip()
    
    # Include any already-known specs for cross-reference
    known_specs = ""
    if existing_specs:
        known_parts = []
        for k, v in existing_specs.items():
            if v and v != 'Not specified' and v != '' and v is not None:
                known_parts.append(f"  {k}: {v}")
        if known_parts:
            known_specs = "\n\nAlready known specs (verify and expand):\n" + "\n".join(known_parts)
    
    web_section = ""
    if web_context:
        # Truncate to avoid context overflow
        web_text = web_context[:3000]
        web_section = f"\n\nWeb research data (use to fill specs):\n{web_text}"
    
    return f"""You are an automotive specifications expert. Provide comprehensive, accurate technical specifications for this vehicle:

**Vehicle: {vehicle_id}**
{known_specs}
{web_section}

Return a JSON object with these fields. Use null for unknown values. Be accurate — do NOT guess.

{{
  "make": "{make}",
  "model_name": "{model_name}",
  "trim_name": "{trim or ''}",
  "year": {year or 'null'},
  
  "drivetrain": "FWD|RWD|AWD|4WD or null",
  "motor_count": "integer or null (for EVs)",
  "motor_placement": "front|rear|front+rear or null",
  
  "power_hp": "integer or null",
  "power_kw": "integer or null",
  "torque_nm": "integer or null",
  "acceleration_0_100": "float seconds or null",
  "top_speed_kmh": "integer or null",
  
  "battery_kwh": "float or null",
  "range_km": "integer or null (best official range)",
  "range_wltp": "integer km or null",
  "range_epa": "integer km or null",
  "range_cltc": "integer km or null",
  
  "charging_time_fast": "string like '30 min to 80%' or null",
  "charging_time_slow": "string like '8 hours' or null",
  "charging_power_max_kw": "integer or null",
  
  "transmission": "automatic|manual|CVT|single-speed|dual-clutch or null",
  "transmission_gears": "integer or null",
  
  "body_type": "sedan|SUV|hatchback|coupe|truck|crossover|wagon|shooting_brake|van|convertible|pickup|liftback|fastback|MPV|roadster|cabriolet|targa|limousine or null",
  "fuel_type": "EV|Hybrid|PHEV|Gas|Diesel|Hydrogen or null",
  "seats": "integer or null",
  
  "length_mm": "integer or null",
  "width_mm": "integer or null",
  "height_mm": "integer or null",
  "wheelbase_mm": "integer or null",
  "weight_kg": "integer or null",
  "cargo_liters": "integer or null",
  "cargo_liters_max": "integer (seats folded) or null",
  "ground_clearance_mm": "integer or null",
  "towing_capacity_kg": "integer or null",
  
  "price_from": "integer (in main market currency) or null",
  "price_to": "integer or null",
  "currency": "USD|EUR|CNY|GBP|JPY or null",
  
  "model_year": "integer or null",
  "country_of_origin": "string or null",
  "platform": "string (e.g. SEA, MEB, E-GMP) or null",
  "voltage_architecture": "integer (400 or 800) or null",
  "suspension_type": "string or null"
}}

IMPORTANT:
- Return ONLY valid JSON, no markdown, no explanation
- Use integers for measurements (mm, kg, kW, km)
- Use float only for acceleration_0_100 and battery_kwh
- For Chinese EVs, include CLTC range. For European, include WLTP. For US, include EPA.
- price_from/price_to should be in the vehicle's primary market currency
- Be conservative: if unsure, use null rather than guessing"""


def _safe_int(value):
    """Convert to int safely, return None on failure."""
    if value is None:
        return None
    try:
        return int(float(str(value).replace(',', '').replace(' ', '')))
    except (ValueError, TypeError):
        return None


def _safe_float(value):
    """Convert to float safely, return None on failure."""
    if value is None:
        return None
    try:
        return float(str(value).replace(',', ''))
    except (ValueError, TypeError):
        return None


def _validate_choice(value, valid_set):
    """Return value if it's in the valid set, else None."""
    if value and str(value) in valid_set:
        return str(value)
    return None


def _parse_ai_response(response_text):
    """Extract JSON from AI response, handling markdown wrappers."""
    text = response_text.strip()
    
    # Strip markdown code block if present
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    
    return None


def generate_deep_vehicle_specs(article, specs=None, web_context='', provider='gemini'):
    """
    Generate comprehensive VehicleSpecs for an article using AI.
    
    Args:
        article: Article instance (must have id and be saved)
        specs: dict with basic specs from extract_specs_dict (may be None)
        web_context: string from web search enrichment
        provider: 'gemini' or 'groq'
    
    Returns:
        VehicleSpecs instance or None on failure
    """
    try:
        from news.models import VehicleSpecs
        
        # Extract identifiers
        make = ''
        model_name = ''
        trim = ''
        year = None
        
        if specs:
            make = specs.get('make', '') or ''
            model_name = specs.get('model', '') or ''
            trim = specs.get('trim', '') or ''
            year_val = specs.get('year')
            if year_val and str(year_val).isdigit():
                year = int(year_val)
        
        if not make or make == 'Not specified':
            logger.warning(f"Cannot generate deep specs: no make for article #{article.id}")
            return None
        
        if not model_name or model_name == 'Not specified':
            logger.warning(f"Cannot generate deep specs: no model for article #{article.id}")
            return None
        
        # Check if fully populated VehicleSpecs already exists
        existing = VehicleSpecs.objects.filter(
            article=article,
            make__iexact=make,
            model_name__iexact=model_name,
        ).first()
        
        if existing and existing.power_hp and existing.length_mm:
            # Already has performance + dimensions — skip
            print(f"📋 VehicleSpecs already populated for {make} {model_name}")
            return existing
        
        # Build prompt and call AI
        prompt = _build_prompt(make, model_name, trim, year, specs, web_context)
        
        from ai_engine.modules.ai_provider import get_ai_provider
        ai = get_ai_provider(provider)
        
        print(f"🔍 Deep specs enrichment: {make} {model_name} {trim or ''}...")
        response = ai.generate_completion(prompt, temperature=0.2, max_tokens=1500)
        
        data = _parse_ai_response(response)
        if not data:
            print(f"⚠️ Failed to parse AI specs response")
            return None
        
        # Build validated defaults dict
        defaults = {
            'article': article,
            'trim_name': str(data.get('trim_name', trim or ''))[:100],
            
            # Drivetrain
            'drivetrain': _validate_choice(data.get('drivetrain'), VALID_DRIVETRAINS),
            'motor_count': _safe_int(data.get('motor_count')),
            'motor_placement': str(data.get('motor_placement', '') or '')[:50] or None,
            
            # Performance
            'power_hp': _safe_int(data.get('power_hp')),
            'power_kw': _safe_int(data.get('power_kw')),
            'torque_nm': _safe_int(data.get('torque_nm')),
            'acceleration_0_100': _safe_float(data.get('acceleration_0_100')),
            'top_speed_kmh': _safe_int(data.get('top_speed_kmh')),
            
            # EV
            'battery_kwh': _safe_float(data.get('battery_kwh')),
            'range_km': _safe_int(data.get('range_km')),
            'range_wltp': _safe_int(data.get('range_wltp')),
            'range_epa': _safe_int(data.get('range_epa')),
            'range_cltc': _safe_int(data.get('range_cltc')),
            
            # Charging
            'charging_time_fast': str(data.get('charging_time_fast', '') or '')[:100] or None,
            'charging_time_slow': str(data.get('charging_time_slow', '') or '')[:100] or None,
            'charging_power_max_kw': _safe_int(data.get('charging_power_max_kw')),
            
            # Transmission
            'transmission': _validate_choice(data.get('transmission'), VALID_TRANSMISSIONS),
            'transmission_gears': _safe_int(data.get('transmission_gears')),
            
            # General
            'body_type': _validate_choice(data.get('body_type'), VALID_BODY_TYPES),
            'fuel_type': _validate_choice(data.get('fuel_type'), VALID_FUEL_TYPES),
            'seats': _safe_int(data.get('seats')),
            
            # Dimensions
            'length_mm': _safe_int(data.get('length_mm')),
            'width_mm': _safe_int(data.get('width_mm')),
            'height_mm': _safe_int(data.get('height_mm')),
            'wheelbase_mm': _safe_int(data.get('wheelbase_mm')),
            'weight_kg': _safe_int(data.get('weight_kg')),
            'cargo_liters': _safe_int(data.get('cargo_liters')),
            'cargo_liters_max': _safe_int(data.get('cargo_liters_max')),
            'ground_clearance_mm': _safe_int(data.get('ground_clearance_mm')),
            'towing_capacity_kg': _safe_int(data.get('towing_capacity_kg')),
            
            # Pricing
            'price_from': _safe_int(data.get('price_from')),
            'price_to': _safe_int(data.get('price_to')),
            'currency': _validate_choice(data.get('currency'), VALID_CURRENCIES) or 'USD',
            
            # Additional
            'year': year or _safe_int(data.get('year')),
            'model_year': _safe_int(data.get('model_year')),
            'country_of_origin': str(data.get('country_of_origin', '') or '')[:100] or None,
            'platform': str(data.get('platform', '') or '')[:100] or None,
            'voltage_architecture': _safe_int(data.get('voltage_architecture')),
            'suspension_type': str(data.get('suspension_type', '') or '')[:200] or None,
        }
        
        # Remove None values so they don't overwrite existing data
        defaults = {k: v for k, v in defaults.items() if v is not None}
        
        # Create or update
        vehicle_specs, created = VehicleSpecs.objects.update_or_create(
            make=make,
            model_name=model_name,
            article=article,
            defaults=defaults
        )
        
        # Count how many fields were filled
        filled = sum(1 for k, v in defaults.items() 
                     if v is not None and k not in ('article', 'trim_name', 'currency'))
        
        action = "Created" if created else "Updated"
        print(f"📋 {action} VehicleSpecs for {make} {model_name}: {filled} fields populated")
        
        return vehicle_specs
        
    except Exception as e:
        logger.error(f"Deep specs enrichment failed for article #{article.id}: {e}")
        print(f"⚠️ Deep specs enrichment failed: {e}")
        import traceback
        traceback.print_exc()
        return None
