"""
Specs Enrichment Module — fills missing vehicle specs from web search data.
Cross-references multiple sources to find HP, torque, price, and other specs
that may be missing from the YouTube transcript analysis.
"""
import re
import logging

logger = logging.getLogger(__name__)

# Patterns for extracting specs from scraped text
SPEC_PATTERNS = {
    'horsepower': [
        # "204 hp", "310 horsepower", "150 PS", "100 bhp"
        re.compile(r'(\d{2,4})\s*(?:hp|horsepower|bhp|PS|cv)\b', re.IGNORECASE),
        # "110kW", "110 kW", "72.5 kW" — convert to HP later
        re.compile(r'(\d{2,4}(?:\.\d)?)\s*kW\b', re.IGNORECASE),
        # Chinese: "100马力", "100匹"
        re.compile(r'(\d{2,4})\s*(?:马力|匹)', re.IGNORECASE),
        # "power: 150", "max power 150"
        re.compile(r'(?:max\.?\s*)?power[:\s]+?(\d{2,4})\s*(?:hp|kW|PS|bhp)', re.IGNORECASE),
    ],
    'torque': [
        # "400 Nm", "295 lb-ft", "300 lb·ft"
        re.compile(r'(\d{2,4})\s*(?:Nm|N·m|N\xb7m)\b', re.IGNORECASE),
        re.compile(r'(\d{2,4})\s*(?:lb[·\-]?ft|pound[·\-]?feet)\b', re.IGNORECASE),
    ],
    'battery': [
        # "75 kWh", "100-kWh battery"
        re.compile(r'(\d{2,3}(?:\.\d)?)\s*[-]?\s*kWh\b', re.IGNORECASE),
    ],
    'range_km': [
        # "610 km range", "range of 550 km", "WLTP range: 450 km"
        re.compile(r'(?:range[:\s]*(?:of\s*)?|WLTP[:\s]*)(\d{2,4})\s*(?:km|kilometers)\b', re.IGNORECASE),
        re.compile(r'(\d{2,4})\s*(?:km|kilometers)\s*(?:range|of\s*range)', re.IGNORECASE),
    ],
    'range_miles': [
        re.compile(r'(?:range[:\s]*(?:of\s*)?|EPA[:\s]*)(\d{2,3})\s*(?:miles|mi)\b', re.IGNORECASE),
        re.compile(r'(\d{2,3})\s*(?:miles|mi)\s*(?:range|of\s*range)', re.IGNORECASE),
    ],
    'acceleration': [
        # "0-60 in 5.2 seconds", "0-100 km/h: 4.5s", "4.5 sec 0-62"
        re.compile(r'0[-–](?:60|62|100)[^:]*?(\d+\.?\d*)\s*(?:s|sec|seconds)\b', re.IGNORECASE),
        re.compile(r'(\d+\.?\d*)\s*(?:s|sec|seconds)\s*(?:0[-–](?:60|62|100))', re.IGNORECASE),
    ],
    'top_speed': [
        # "top speed of 210 km/h", "155 mph top speed"
        re.compile(r'top\s*speed[:\s]*(?:of\s*)?(\d{2,3})\s*(?:km/h|kph|mph)\b', re.IGNORECASE),
        re.compile(r'(\d{2,3})\s*(?:km/h|kph|mph)\s*(?:top\s*speed)', re.IGNORECASE),
    ],
    'price_usd': [
        # "$27,000", "MSRP $45,000", "starting at $35,990"
        re.compile(r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b'),
    ],
    'price_cny': [
        # "¥190,000", "¥19万", "售价19.98万"
        re.compile(r'¥\s*(\d{1,3}(?:,\d{3})*)\b'),
        re.compile(r'¥?\s*(\d+\.?\d*)\s*万', re.IGNORECASE),
    ],
    'engine': [
        # "2.0L turbo", "1.5L", "2.0-liter", "electric motor"
        re.compile(r'(\d\.\d[L-]\s*(?:turbo(?:charged)?|naturally\s*aspirated|inline|V\d)?)', re.IGNORECASE),
    ],
    'cargo': [
        # "450-liter cargo", "trunk: 500 liters", "cargo space: 450L"
        re.compile(r'(?:cargo|trunk|boot|luggage)[:\s]*(?:space[:\s]*)?(\d{2,4})\s*(?:L|liter|litre|litres|liters)\b', re.IGNORECASE),
        re.compile(r'(\d{2,4})\s*(?:L|liter|litre|litres|liters)\s*(?:cargo|trunk|boot)\b', re.IGNORECASE),
    ],
    'screen_size': [
        # "15.6-inch screen", "12.3" display", "10.25-inch touchscreen"
        re.compile(r'(\d{1,2}\.?\d?)\s*[-]?\s*inch\s*(?:screen|display|touchscreen|infotainment)\b', re.IGNORECASE),
    ],
    'drivetrain': [
        # "FWD", "RWD", "AWD", "4WD"
        re.compile(r'\b(FWD|RWD|AWD|4WD|2WD)\b'),
        # "front-wheel drive", "rear-wheel drive", "all-wheel drive"
        re.compile(r'(front[- ]wheel[- ]drive|rear[- ]wheel[- ]drive|all[- ]wheel[- ]drive|four[- ]wheel[- ]drive)', re.IGNORECASE),
        # Chinese: 前驱 (FWD), 后驱 (RWD), 四驱 (AWD/4WD)
        re.compile(r'(前驱|前轮驱动|后驱|后轮驱动|四驱|全轮驱动)'),
    ],
}


def _extract_values_from_text(text, pattern_key):
    """Extract all matching values for a spec from text."""
    values = []
    patterns = SPEC_PATTERNS.get(pattern_key, [])
    for pattern in patterns:
        for match in pattern.finditer(text):
            values.append(match.group(1).replace(',', ''))
    return values


def _most_common(values):
    """Return the most commonly found value across sources, or first if tie."""
    if not values:
        return None
    # Count occurrences
    counts = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    # Sort by count (descending), then by first appearance
    sorted_vals = sorted(counts.keys(), key=lambda x: (-counts[x], values.index(x)))
    winner = sorted_vals[0]
    if len(counts) > 1:
        logger.info(f"  Cross-ref: found {counts}, using '{winner}'")
    return winner


def enrich_specs_from_web(specs, web_context):
    """
    Enriches specs dict with data extracted from web search results.
    Cross-references multiple sources — uses the most commonly found value.
    
    Args:
        specs: dict from extract_specs_dict (may have 'Not specified' gaps)
        web_context: string from get_web_context (scraped web pages)
    
    Returns:
        Updated specs dict with filled-in values
    """
    if not web_context or len(web_context) < 50:
        return specs
    
    enriched_count = 0
    
    # --- Horsepower ---
    if not specs.get('horsepower'):
        hp_values = _extract_values_from_text(web_context, 'horsepower')
        kw_values = _extract_values_from_text(web_context, 'horsepower')  # kW patterns
        
        # Check for kW values separately and convert
        kw_only = []
        for pattern in SPEC_PATTERNS['horsepower']:
            if 'kW' in pattern.pattern:
                for match in pattern.finditer(web_context):
                    kw_val = float(match.group(1))
                    hp_val = str(int(kw_val * 1.341))  # kW to HP
                    kw_only.append(hp_val)
        
        # Filter: only values from the hp patterns (not kW)
        hp_direct = []
        for pattern in SPEC_PATTERNS['horsepower']:
            if 'kW' not in pattern.pattern:
                for match in pattern.finditer(web_context):
                    hp_direct.append(match.group(1))
        
        all_hp = hp_direct + kw_only
        best_hp = _most_common(all_hp)
        if best_hp:
            try:
                specs['horsepower'] = int(best_hp)
                enriched_count += 1
                logger.info(f"  ✓ Enriched HP: {specs['horsepower']} hp (from {len(all_hp)} sources)")
            except ValueError:
                pass
    
    # --- Torque ---
    if specs.get('torque') in (None, 'Not specified', ''):
        torque_values = _extract_values_from_text(web_context, 'torque')
        best_torque = _most_common(torque_values)
        if best_torque:
            # Determine unit
            nm_count = len([v for v in _extract_values_from_text(web_context, 'torque')
                          if re.search(r'Nm|N·m', web_context[max(0, web_context.find(v)-5):web_context.find(v)+20], re.IGNORECASE)])
            unit = 'Nm' if nm_count > 0 else 'lb-ft'
            specs['torque'] = f"{best_torque} {unit}"
            enriched_count += 1
            logger.info(f"  ✓ Enriched torque: {specs['torque']}")
    
    # --- Battery ---
    if specs.get('battery') in (None, 'Not specified', ''):
        battery_values = _extract_values_from_text(web_context, 'battery')
        best = _most_common(battery_values)
        if best:
            specs['battery'] = f"{best} kWh"
            enriched_count += 1
            logger.info(f"  ✓ Enriched battery: {specs['battery']}")
    
    # --- Range ---
    if specs.get('range') in (None, 'Not specified', ''):
        km_values = _extract_values_from_text(web_context, 'range_km')
        mi_values = _extract_values_from_text(web_context, 'range_miles')
        if km_values:
            best = _most_common(km_values)
            specs['range'] = f"{best} km"
            enriched_count += 1
            logger.info(f"  ✓ Enriched range: {specs['range']}")
        elif mi_values:
            best = _most_common(mi_values)
            specs['range'] = f"{best} miles"
            enriched_count += 1
    
    # --- Acceleration ---
    if specs.get('acceleration') in (None, 'Not specified', ''):
        accel_values = _extract_values_from_text(web_context, 'acceleration')
        best = _most_common(accel_values)
        if best:
            specs['acceleration'] = f"{best} seconds (0-100 km/h)"
            enriched_count += 1
            logger.info(f"  ✓ Enriched acceleration: {specs['acceleration']}")
    
    # --- Top Speed ---
    if specs.get('top_speed') in (None, 'Not specified', ''):
        speed_values = _extract_values_from_text(web_context, 'top_speed')
        best = _most_common(speed_values)
        if best:
            # Detect unit from context
            specs['top_speed'] = f"{best} km/h"
            enriched_count += 1
            logger.info(f"  ✓ Enriched top speed: {specs['top_speed']}")
    
    # --- Drivetrain ---
    if specs.get('drivetrain') in (None, 'Not specified', ''):
        dt_values = _extract_values_from_text(web_context, 'drivetrain')
        # Normalize to standard abbreviations
        normalized = []
        for v in dt_values:
            v_lower = v.lower().replace('-', ' ').replace('  ', ' ')
            if v_lower in ('fwd', 'front wheel drive', '前驱', '前轮驱动'):
                normalized.append('FWD')
            elif v_lower in ('rwd', 'rear wheel drive', '后驱', '后轮驱动'):
                normalized.append('RWD')
            elif v_lower in ('awd', 'all wheel drive', '四驱', '全轮驱动'):
                normalized.append('AWD')
            elif v_lower in ('4wd', 'four wheel drive'):
                normalized.append('4WD')
            else:
                normalized.append(v.upper())
        best = _most_common(normalized)
        if best:
            specs['drivetrain'] = best
            enriched_count += 1
            logger.info(f"  ✓ Enriched drivetrain: {specs['drivetrain']}")
    
    if enriched_count > 0:
        print(f"🔍 Enriched {enriched_count} specs from web sources")
    else:
        print(f"ℹ️  No additional specs found in web sources")
    
    return specs


def build_enriched_analysis(specs, web_context):
    """
    Builds an enriched analysis string that combines original specs
    with web-enriched data. This is passed to the article generator.
    """
    enriched = enrich_specs_from_web(specs.copy(), web_context)
    
    lines = []
    lines.append(f"Make: {enriched.get('make', 'Not specified')}")
    lines.append(f"Model: {enriched.get('model', 'Not specified')}")
    lines.append(f"Trim/Version: {enriched.get('trim', 'Not specified')}")
    lines.append(f"Year: {enriched.get('year', 'Not specified')}")
    lines.append(f"Engine: {enriched.get('engine', 'Not specified')}")
    
    hp = enriched.get('horsepower')
    lines.append(f"Horsepower: {f'{hp} hp' if hp else 'Not specified'}")
    lines.append(f"Torque: {enriched.get('torque', 'Not specified')}")
    lines.append(f"Acceleration: {enriched.get('acceleration', 'Not specified')}")
    lines.append(f"Top Speed: {enriched.get('top_speed', 'Not specified')}")
    lines.append(f"Drivetrain: {enriched.get('drivetrain', 'Not specified')}")
    lines.append(f"Battery: {enriched.get('battery', 'Not specified')}")
    lines.append(f"Range: {enriched.get('range', 'Not specified')}")
    lines.append(f"Price: {enriched.get('price', 'Not specified')}")
    
    return '\n'.join(lines), enriched
