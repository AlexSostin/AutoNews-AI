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
from typing import Dict, Optional

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
  "combined_range_km": null,
  
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
- range_km is PURE ELECTRIC range only. For PHEVs/DM-i/EREV, this is how far the car goes on battery alone (typically 50-200km), NOT the combined gasoline+electric range (which can be 1000+ km)
- range_cltc/range_wltp/range_epa are also PURE ELECTRIC range measured by that standard
- combined_range_km is the TOTAL range for PHEVs/DM-i/EREV (gas+electric combined). For BYD DM-i vehicles this is typically 1000-1200km. For pure EVs, set to null
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

# Trailing words from article titles that are NOT part of model names
_MODEL_STOP_WORDS = {
    'sets', 'redefines', 'challenges', 'pioneers', 'reveals', 'gets',
    'launches', 'introduces', 'features', 'offers', 'breaks', 'takes',
    'makes', 'earns', 'wins', 'debuts', 'shows', 'leads', 'dominates',
    'delivers', 'targets', 'combines', 'promises', 'brings', 'hits',
    'enters', 'aims', 'boasts', 'claims', 'highlights', 'marks',
    'a', 'an', 'the', 'for', 'with', 'is', 'in', 'on', 'at', 'to',
    'two', 'three', 'four', 'five', 'new', 'and', 'its', 'as',
}


def _sanitize_trim(value):
    """Clean up trim_name — return '' for garbage/null-like values."""
    if value is None:
        return ''
    s = str(value).strip()
    if s in _GARBAGE_TRIM_VALUES:
        return ''
    return s


def _clean_model_name(model_name, make):
    """Normalize model_name: strip brand prefix and trailing parser noise."""
    if not model_name:
        return model_name
    
    # Strip brand prefix (word-boundary safe: "IM LS9" → "LS9", but "IMPERIAL" stays)
    if make and model_name.lower().startswith(make.lower() + ' '):
        cleaned = model_name[len(make):].strip()
        if cleaned:  # Don't strip if it would leave empty
            model_name = cleaned
    
    # Strip trailing verbs/articles from title parser noise
    # "HS6 Sets" → "HS6", but "07 REV" stays (neither word is a stop word)
    words = model_name.split()
    while len(words) > 1 and words[-1].lower() in _MODEL_STOP_WORDS:
        words.pop()
    model_name = ' '.join(words)
    
    return model_name


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
        
        # Normalize model_name — strip brand prefix and parser noise
        original_model_name = model_name
        model_name = _clean_model_name(model_name, make)
        if model_name != original_model_name:
            print(f"📝 Model name normalized: '{original_model_name}' → '{model_name}'")
        
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
        
        # If model_name was normalized, also clean up records under the old name
        if model_name != original_model_name:
            old_records = VehicleSpecs.objects.filter(
                make__iexact=make,
                model_name__iexact=original_model_name,
            )
            if old_records.exists():
                # Transfer data from old to new: keep the old record but rename it
                for old_rec in old_records:
                    old_rec.model_name = model_name
                    old_rec.save(update_fields=['model_name'])
                print(f"📝 Renamed {old_records.count()} VehicleSpecs: '{original_model_name}' → '{model_name}'")
        
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
            # Check for suspicious PHEV ranges before skipping
            # Small battery (<50kWh) with huge range (>500km) = likely combined range, not electric
            needs_range_fix = False
            if existing.battery_kwh and existing.battery_kwh < 50:
                fix_fields = []
                if existing.range_km and existing.range_km > 500:
                    fix_fields.append('range_km')
                if existing.range_cltc and existing.range_cltc > 500:
                    fix_fields.append('range_cltc')
                if existing.range_wltp and existing.range_wltp > 500:
                    fix_fields.append('range_wltp')
                if fix_fields:
                    needs_range_fix = True
                    print(f"⚠️ PHEV suspicious range for {make} {model_name}: "
                          f"battery={existing.battery_kwh}kWh but {', '.join(f'{f}={getattr(existing, f)}' for f in fix_fields)}")
                    # Clear suspicious values so re-enrichment fills correct ones
                    for f in fix_fields:
                        setattr(existing, f, None)
                    existing.save(update_fields=fix_fields)
                    print(f"   🧹 Cleared {', '.join(fix_fields)} — will re-enrich with corrected prompt")
            
            if not needs_range_fix:
                # Already has good data — skip
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
        
        # Validate PHEV range — warn if it looks like combined range
        fuel = data.get('fuel_type', '')
        if fuel in ('PHEV', 'Hybrid') or (data.get('battery_kwh') and data.get('range_km')):
            battery = _safe_float(data.get('battery_kwh'))
            range_val = _safe_int(data.get('range_km'))
            if battery and battery < 30 and range_val and range_val > 500:
                print(f"⚠️ PHEV range suspicious: {range_val}km on {battery}kWh — this may be combined range, not pure electric")
        
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
            'combined_range_km': _safe_int(data.get('combined_range_km')),
            
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


# ══════════════════════════════════════════════════════════════════
#  Specs Extractor (AI-powered extraction from article content)
# ══════════════════════════════════════════════════════════════════

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
        from ai_engine.modules.ai_provider import get_ai_provider
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


# ══════════════════════════════════════════════════════════════════
#  Spec Refill (AI-powered gap filler for low-coverage specs)
# ══════════════════════════════════════════════════════════════════

# The 10 key fields we consider for coverage
KEY_SPEC_FIELDS = [
    'make', 'model', 'engine', 'horsepower', 'torque',
    'zero_to_sixty', 'top_speed', 'drivetrain', 'price', 'year',
]


def _is_filled(value) -> bool:
    """Check if a spec value is meaningfully filled."""
    if value is None:
        return False
    s = str(value).strip()
    return s not in ('', 'Not specified', 'None', '0', 'null')


def compute_coverage(specs: dict) -> tuple:
    """
    Compute spec coverage.
    
    Returns:
        (filled_count, total_count, coverage_pct, missing_fields)
    """
    if not specs:
        return 0, len(KEY_SPEC_FIELDS), 0.0, list(KEY_SPEC_FIELDS)
    
    missing = []
    filled = 0
    for field in KEY_SPEC_FIELDS:
        if _is_filled(specs.get(field)):
            filled += 1
        else:
            missing.append(field)
    
    total = len(KEY_SPEC_FIELDS)
    pct = (filled / total) * 100 if total > 0 else 0.0
    return filled, total, pct, missing


def refill_missing_specs(specs: dict, article_content: str,
                         web_context: str = '', provider: str = 'gemini',
                         threshold: float = 70.0) -> dict:
    """
    Check spec coverage and AI-fill missing fields if below threshold.
    
    Args:
        specs: dict from extract_specs_dict (may have 'Not specified' gaps)
        article_content: the generated HTML article
        web_context: raw text from web search
        provider: AI provider name
        threshold: coverage % below which refill triggers (default 70%)
    
    Returns:
        Updated specs dict with `_refill_meta` key showing what was done
    """
    filled, total, coverage, missing = compute_coverage(specs)
    
    meta = {
        'triggered': False,
        'coverage_before': round(coverage, 1),
        'filled_before': filled,
        'missing_before': missing[:],
    }
    
    if coverage >= threshold:
        logger.info(f"[SPEC-REFILL] Coverage {coverage:.0f}% ≥ {threshold}% — skip")
        meta['reason'] = 'coverage_sufficient'
        specs['_refill_meta'] = meta
        return specs
    
    logger.info(f"[SPEC-REFILL] Coverage {coverage:.0f}% < {threshold}% — refilling {len(missing)} fields")
    meta['triggered'] = True
    
    # Build focused prompt
    make = specs.get('make', 'unknown')
    model = specs.get('model', 'unknown')
    
    # Context: article + web search results
    context_parts = []
    if article_content:
        # Use first 3000 chars of article to stay within token budget
        clean_article = article_content[:3000]
        context_parts.append(f"Article content:\n{clean_article}")
    if web_context:
        context_parts.append(f"Web search results:\n{web_context[:2000]}")
    
    context = '\n\n'.join(context_parts)
    
    field_descriptions = {
        'make': 'car manufacturer brand name (e.g. Toyota, BMW, BYD)',
        'model': 'specific model name (e.g. Camry, X5, Seal)',
        'engine': 'engine type/description (e.g. "2.5L 4-cylinder turbo", "dual electric motors")',
        'horsepower': 'peak power in HP (number only)',
        'torque': 'peak torque (e.g. "350 lb-ft" or "475 Nm")',
        'zero_to_sixty': '0-60 mph time in seconds (e.g. "5.2")',
        'top_speed': 'top speed (e.g. "155 mph" or "250 km/h")',
        'drivetrain': 'AWD, FWD, RWD, or 4WD',
        'price': 'starting price with currency (e.g. "$35,000", "€42,900")',
        'year': 'model year (e.g. 2025, 2026)',
    }
    
    missing_desc = '\n'.join(
        f'- {f}: {field_descriptions.get(f, f)}'
        for f in missing
    )
    
    prompt = f"""You are an automotive specifications expert. I have an article about the {make} {model}.

The following specification fields are MISSING. Extract them from the context below.
If a value is truly not mentioned anywhere, use "Not specified".

Missing fields:
{missing_desc}

{context}

Reply with ONLY valid JSON containing the missing field names as keys and their values as strings.
Example: {{"horsepower": "320", "drivetrain": "AWD"}}
No extra text, no markdown, just the JSON object."""

    try:
        from ai_engine.modules.ai_provider import get_ai_provider
        ai = get_ai_provider(provider)
        
        response = ai.generate_completion(
            prompt=prompt,
            temperature=0.2,
            max_tokens=500,
        )
        
        # Parse response
        response_text = response.strip()
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        refill_data = json.loads(response_text)
        
        # Merge into specs
        filled_by_refill = []
        for field in missing:
            value = refill_data.get(field)
            if value and str(value).strip() not in ('', 'Not specified', 'None', 'null'):
                specs[field] = str(value).strip()
                filled_by_refill.append(field)
                logger.info(f"[SPEC-REFILL] ✓ {field} = {value}")
        
        # Compute new coverage
        _, _, coverage_after, missing_after = compute_coverage(specs)
        
        meta['filled_by_refill'] = filled_by_refill
        meta['coverage_after'] = round(coverage_after, 1)
        meta['missing_after'] = missing_after
        meta['provider'] = provider
        
        logger.info(f"[SPEC-REFILL] Coverage: {coverage:.0f}% → {coverage_after:.0f}% "
                     f"(+{len(filled_by_refill)} fields)")
        
    except json.JSONDecodeError as e:
        logger.warning(f"[SPEC-REFILL] JSON parse error: {e}")
        meta['error'] = f'json_parse: {e}'
    except Exception as e:
        logger.warning(f"[SPEC-REFILL] Failed: {e}")
        meta['error'] = str(e)
    
    specs['_refill_meta'] = meta
    return specs
