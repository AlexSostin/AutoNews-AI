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
    
    return f"""You are an automotive specifications database. Your task: fill in ALL known specifications for this vehicle using your knowledge and the provided web data.

**Vehicle: {vehicle_id}**
{known_specs}
{web_section}

Return a JSON object with the fields below. You MUST fill in as many fields as possible using your automotive knowledge. This vehicle is a real production car — you should know its power, dimensions, battery specs, etc. Only use null if the information truly does not exist (e.g., towing capacity for a city car).

{{
  "make": "{make}",
  "model_name": "{model_name}",
  "trim_name": "{trim or ''}",
  "year": {year or 'null'},
  
  "drivetrain": "RWD",
  "motor_count": 1,
  "motor_placement": "rear",
  
  "power_hp": 200,
  "power_kw": 150,
  "torque_nm": 300,
  "acceleration_0_100": 7.5,
  "top_speed_kmh": 180,
  
  "battery_kwh": 66.0,
  "range_km": 400,
  "range_wltp": null,
  "range_epa": null,
  "range_cltc": 500,
  
  "charging_time_fast": "30 min to 80%",
  "charging_time_slow": "8 hours",
  "charging_power_max_kw": 150,
  
  "transmission": "single-speed",
  "transmission_gears": null,
  
  "body_type": "SUV",
  "fuel_type": "EV",
  "seats": 5,
  
  "length_mm": 4500,
  "width_mm": 1850,
  "height_mm": 1600,
  "wheelbase_mm": 2700,
  "weight_kg": 1800,
  "cargo_liters": 400,
  "cargo_liters_max": 1200,
  "ground_clearance_mm": 170,
  "towing_capacity_kg": null,
  
  "price_from": 25000,
  "price_to": 35000,
  "currency": "CNY",
  
  "model_year": 2026,
  "country_of_origin": "China",
  "platform": "SEA",
  "voltage_architecture": 800,
  "suspension_type": "MacPherson strut front, multi-link rear"
}}

CRITICAL RULES:
- Return ONLY valid JSON, no markdown, no explanation
- Use actual INTEGER values (not strings like "200 hp", just 200)
- The example values above are PLACEHOLDERS — replace them with the REAL specifications for {vehicle_id}
- You know this car. Fill in power_hp, torque_nm, battery_kwh, range_km, dimensions, weight, and price
- drivetrain must be exactly one of: FWD, RWD, AWD, 4WD
- body_type must be one of: sedan, SUV, hatchback, coupe, truck, crossover, wagon, shooting_brake, van, convertible, pickup, liftback, fastback, MPV, roadster, cabriolet, targa, limousine
- fuel_type must be one of: EV, Hybrid, PHEV, Gas, Diesel, Hydrogen
- transmission must be one of: automatic, manual, CVT, single-speed, dual-clutch
- currency must be one of: USD, EUR, CNY, RUB, GBP, JPY
- motor_placement is a single string: "front", "rear", or "front+rear" (NOT multiple values)
- For Chinese EVs, always include range_cltc. For European, range_wltp. For US, range_epa
- price_from/price_to should be in CNY for Chinese-market vehicles, USD for US-market
- DO NOT return all nulls — that is a failure. You must provide at least power, range, and dimensions"""


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


# Garbage values for trim_name that should be treated as empty
_GARBAGE_TRIM_VALUES = {'None', 'null', 'none', 'N/A', 'n/a', 'Not specified', 'not specified', 'Standard', '-'}


def _sanitize_trim(value):
    """Clean up trim_name — return '' for garbage/null-like values."""
    if value is None:
        return ''
    s = str(value).strip()
    if s in _GARBAGE_TRIM_VALUES:
        return ''
    return s


def _clean_pipe_value(value):
    """If AI returned 'option1|option2', take the first option."""
    if not value or not isinstance(value, str):
        return value
    if '|' in value:
        return value.split('|')[0].strip()
    return value


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
        
        # Normalize make to canonical brand display name (e.g., "Zeekr" → "ZEEKR")
        try:
            from news.auto_tags import BRAND_DISPLAY_NAMES
            make_lower = make.lower().strip()
            make = BRAND_DISPLAY_NAMES.get(make_lower, make)
        except ImportError:
            pass
        
        # Sanitize and normalize trim_name
        trim = _sanitize_trim(trim)
        
        # Clean up ghost records with garbage trim_name (e.g., 'None', 'null')
        ghost_records = VehicleSpecs.objects.filter(
            make__iexact=make,
            model_name__iexact=model_name,
            trim_name__in=list(_GARBAGE_TRIM_VALUES),
        )
        if ghost_records.exists():
            ghost_count = ghost_records.count()
            ghost_records.delete()
            print(f"🧹 Deleted {ghost_count} ghost VehicleSpecs with garbage trim_name for {make} {model_name}")
        
        # Find existing records — clean up duplicates, keep best
        existing_all = list(VehicleSpecs.objects.filter(
            make__iexact=make,
            model_name__iexact=model_name,
            trim_name__iexact=trim,
        ))
        
        if len(existing_all) > 1:
            # Multiple records with different casing — merge
            best = max(existing_all, key=lambda vs: sum(
                1 for f in vs._meta.fields 
                if getattr(vs, f.name) is not None and f.name not in ('id', 'article', 'make', 'model_name', 'trim_name')
            ))
            for dup in existing_all:
                if dup.id != best.id:
                    print(f"🧹 Deleting duplicate VehicleSpecs #{dup.id} ({dup.make}/{dup.model_name})")
                    dup.delete()
            existing = best
            # Normalize casing on the best record
            update_fields = []
            if existing.make != make:
                existing.make = make
                update_fields.append('make')
            if existing.model_name != model_name:
                existing.model_name = model_name
                update_fields.append('model_name')
            if update_fields:
                existing.save(update_fields=update_fields)
        elif len(existing_all) == 1:
            existing = existing_all[0]
            # Normalize casing if needed — both make AND model_name
            update_fields = []
            if existing.make != make:
                existing.make = make
                update_fields.append('make')
            if existing.model_name != model_name:
                existing.model_name = model_name
                update_fields.append('model_name')
            if update_fields:
                existing.save(update_fields=update_fields)
        else:
            existing = None
        
        if existing and existing.power_hp and existing.length_mm:
            # Already has performance + dimensions — skip
            if existing.article_id != article.id:
                print(f"📋 VehicleSpecs already populated for {make} {model_name} (linked to article #{existing.article_id})")
            else:
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
            print(f"⚠️ Failed to parse AI specs response for {make} {model_name}")
            print(f"   Raw response (first 500 chars): {str(response)[:500]}")
            return None
        
        # Log what Gemini returned
        key_fields = {k: data.get(k) for k in ['power_hp', 'power_kw', 'torque_nm', 'battery_kwh', 'range_km', 'length_mm']}
        print(f"   AI returned key fields: {key_fields}")
        
        # Build validated defaults dict
        defaults = {
            'article': article,
            'trim_name': _sanitize_trim(data.get('trim_name') or trim)[:100],
            
            # Drivetrain
            'drivetrain': _validate_choice(_clean_pipe_value(data.get('drivetrain')), VALID_DRIVETRAINS),
            'motor_count': _safe_int(data.get('motor_count')),
            'motor_placement': _clean_pipe_value(str(data.get('motor_placement', '') or '')[:50]) or None,
            
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
            'transmission': _validate_choice(_clean_pipe_value(data.get('transmission')), VALID_TRANSMISSIONS),
            'transmission_gears': _safe_int(data.get('transmission_gears')),
            
            # General
            'body_type': _validate_choice(_clean_pipe_value(data.get('body_type')), VALID_BODY_TYPES),
            'fuel_type': _validate_choice(_clean_pipe_value(data.get('fuel_type')), VALID_FUEL_TYPES),
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
            'currency': _validate_choice(_clean_pipe_value(data.get('currency')), VALID_CURRENCIES) or 'USD',
            
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
        
        # Always set/update article reference
        defaults['article'] = article
        
        # Derive trim_name for DB lookup (must match unique_together)
        trim_for_lookup = _sanitize_trim(data.get('trim_name') or trim)[:100]
        
        # Create or update — use SAME fields as unique_together: (make, model_name, trim_name)
        vehicle_specs, created = VehicleSpecs.objects.update_or_create(
            make=make,
            model_name=model_name,
            trim_name=trim_for_lookup,
            defaults=defaults
        )
        
        # Validate: warn if too few fields populated
        spec_fields_filled = sum(1 for k in ['power_hp', 'power_kw', 'torque_nm', 'battery_kwh', 'range_km', 'length_mm', 'width_mm', 'weight_kg']
                                 if defaults.get(k) is not None)
        if spec_fields_filled < 3:
            print(f"⚠️ WARNING: Only {spec_fields_filled}/8 key fields filled for {make} {model_name}. AI may have returned empty data.")
        
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
