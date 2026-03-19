"""
Predecessor Car Comparison — Year-over-year evolution context.

Searches VehicleSpecs DB for the same model from the previous year
and generates a comparison block for the article prompt.
Gives articles unique editorial value: "What changed from 2025 to 2026?"
"""
import logging

logger = logging.getLogger(__name__)


def find_predecessor(make: str, model: str, current_year: int = None) -> dict | None:
    """
    Find the predecessor model in VehicleSpecs DB.
    
    Searches for same make + model_name with a lower model_year.
    Returns the best match (closest year) with full specs.
    """
    if not make or not model:
        return None

    try:
        from news.models.vehicles import VehicleSpecs

        # Build query: same make (case-insensitive) + similar model name
        query = VehicleSpecs.objects.filter(
            make__iexact=make,
            model_name__icontains=model.split()[0],  # Match first word (e.g., "8X" from "8X Ultra")
        )

        if current_year:
            # Must be an older model year
            query = query.filter(model_year__lt=current_year, model_year__isnull=False)
        else:
            # Just find any other entry (older by ID)
            pass

        # Order by year descending to get closest predecessor
        predecessor = query.order_by('-model_year', '-id').first()

        if not predecessor:
            return None

        # Build spec dict
        specs = {
            'make': predecessor.make,
            'model': predecessor.model_name,
            'trim': predecessor.trim_name or '',
            'year': predecessor.model_year,
        }

        # Performance
        if predecessor.power_hp:
            specs['power_hp'] = predecessor.power_hp
        if predecessor.power_kw:
            specs['power_kw'] = predecessor.power_kw
        if predecessor.torque_nm:
            specs['torque_nm'] = predecessor.torque_nm
        if predecessor.acceleration_0_100:
            specs['acceleration_0_100'] = predecessor.acceleration_0_100
        if predecessor.top_speed_kmh:
            specs['top_speed'] = predecessor.top_speed_kmh

        # Battery / Range
        if predecessor.battery_kwh:
            specs['battery_kwh'] = predecessor.battery_kwh
        range_val = predecessor.range_wltp or predecessor.range_cltc or predecessor.range_epa or predecessor.range_km
        if range_val:
            specs['range_km'] = range_val

        # Dimensions
        if predecessor.length_mm:
            specs['length_mm'] = predecessor.length_mm
        if predecessor.wheelbase_mm:
            specs['wheelbase_mm'] = predecessor.wheelbase_mm
        if predecessor.weight_kg:
            specs['weight_kg'] = predecessor.weight_kg

        # Price
        if predecessor.price_from:
            specs['price_from'] = predecessor.price_from
            specs['currency'] = predecessor.currency

        logger.info(f"[PREDECESSOR] Found: {specs['make']} {specs['model']} {specs.get('year', '?')} ({len(specs)-4} spec fields)")
        return specs

    except Exception as e:
        logger.warning(f"[PREDECESSOR] Lookup failed: {e}")
        return None


def format_evolution(current_specs: dict, predecessor: dict) -> str:
    """
    Format a comparison block showing year-over-year changes.
    
    Returns formatted string for prompt injection.
    """
    if not predecessor:
        return ''

    pred_year = predecessor.get('year', '?')
    pred_name = f"{predecessor['make']} {predecessor['model']}"
    if predecessor.get('trim'):
        pred_name += f" {predecessor['trim']}"

    lines = [
        f"═══ PREDECESSOR COMPARISON: {pred_name} ({pred_year}) ═══",
        f"Compare the current model with its predecessor ({pred_year}) when relevant.",
        f"Highlight what improved, changed, or stayed the same.\n",
    ]

    changes = []

    # Power comparison
    if predecessor.get('power_hp') and current_specs.get('horsepower'):
        try:
            old_hp = int(str(predecessor['power_hp']).replace(',', ''))
            new_hp = int(str(current_specs['horsepower']).replace(',', '').replace(' hp', '').replace('hp', ''))
            diff = new_hp - old_hp
            if diff != 0:
                sign = '+' if diff > 0 else ''
                changes.append(f"Power: {old_hp} hp → {new_hp} hp ({sign}{diff} hp)")
        except (ValueError, TypeError):
            pass

    # Range comparison
    if predecessor.get('range_km') and current_specs.get('range'):
        try:
            old_range = int(str(predecessor['range_km']).replace(',', ''))
            new_range_str = str(current_specs['range']).replace(' km', '').replace('km', '').replace(',', '')
            new_range = int(new_range_str)
            diff = new_range - old_range
            if diff != 0:
                sign = '+' if diff > 0 else ''
                changes.append(f"Range: {old_range} km → {new_range} km ({sign}{diff} km)")
        except (ValueError, TypeError):
            pass

    # Battery comparison
    if predecessor.get('battery_kwh') and current_specs.get('battery_kwh'):
        try:
            old_bat = float(str(predecessor['battery_kwh']))
            new_bat_str = str(current_specs['battery_kwh']).replace(' kWh', '').replace('kWh', '')
            new_bat = float(new_bat_str)
            if old_bat != new_bat:
                changes.append(f"Battery: {old_bat} kWh → {new_bat} kWh")
        except (ValueError, TypeError):
            pass

    # Acceleration comparison
    if predecessor.get('acceleration_0_100') and current_specs.get('acceleration_0_100'):
        try:
            old_acc = float(str(predecessor['acceleration_0_100']).replace('s', ''))
            new_acc_str = str(current_specs['acceleration_0_100']).replace('s', '').replace(' ', '')
            new_acc = float(new_acc_str)
            diff = round(new_acc - old_acc, 1)
            if diff != 0:
                sign = '+' if diff > 0 else ''
                changes.append(f"0-100: {old_acc}s → {new_acc}s ({sign}{diff}s)")
        except (ValueError, TypeError):
            pass

    # Price comparison
    if predecessor.get('price_from') and current_specs.get('price'):
        try:
            old_price = int(str(predecessor['price_from']).replace(',', ''))
            # Try to extract number from new price
            import re
            price_match = re.search(r'[\d,]+', str(current_specs['price']).replace(',', ''))
            if price_match:
                new_price = int(price_match.group().replace(',', ''))
                diff = new_price - old_price
                if abs(diff) > 100:
                    sign = '+' if diff > 0 else ''
                    currency = predecessor.get('currency', 'USD')
                    changes.append(f"Starting price: {currency} {old_price:,} → {new_price:,} ({sign}{diff:,})")
        except (ValueError, TypeError):
            pass

    if changes:
        lines.append("Key changes from predecessor:")
        for change in changes:
            lines.append(f"  • {change}")
    else:
        # Still provide predecessor specs for context even without direct comparison
        lines.append("Predecessor specs for reference:")
        spec_fields = [
            ('power_hp', 'Power', 'hp'),
            ('range_km', 'Range', 'km'),
            ('battery_kwh', 'Battery', 'kWh'),
            ('acceleration_0_100', '0-100', 's'),
            ('weight_kg', 'Weight', 'kg'),
        ]
        for key, label, unit in spec_fields:
            val = predecessor.get(key)
            if val:
                lines.append(f"  • {label}: {val} {unit}")

    lines.append("\nMention the predecessor comparison naturally in 1-2 sentences within the article.")
    lines.append("═══════════════════════════════════════════════\n")

    return '\n'.join(lines)


def find_siblings(make: str, model: str, body_type: str = None, max_results: int = 3) -> list[dict]:
    """
    Find 'sibling' models — same brand, similar segment.
    E.g., Zeekr 8X → Zeekr 9X, Zeekr 7X (same brand, both SUVs)
    
    Returns list of spec dicts for the closest siblings.
    """
    if not make:
        return []

    try:
        from news.models.vehicles import VehicleSpecs

        # Same brand, different model, with real specs (power_hp not null)
        model_first_word = model.split()[0] if model else ''
        query = VehicleSpecs.objects.filter(
            make__iexact=make,
            power_hp__isnull=False,
        )

        # Exclude the current model
        if model_first_word:
            query = query.exclude(model_name__istartswith=model_first_word)

        # Prefer same body type if available
        if body_type:
            same_body = query.filter(body_type=body_type)
            if same_body.exists():
                query = same_body

        # Deduplicate by model name (take latest year)
        seen_models = set()
        results = []
        for spec in query.order_by('-model_year', '-id'):
            key = spec.model_name.split()[0]  # First word: "7X" from "7X EV"
            if key not in seen_models:
                seen_models.add(key)
                entry = {
                    'make': spec.make,
                    'model': spec.model_name,
                    'trim': spec.trim_name or '',
                    'year': spec.model_year,
                }
                if spec.power_hp:
                    entry['power_hp'] = spec.power_hp
                if spec.battery_kwh:
                    entry['battery_kwh'] = spec.battery_kwh
                range_val = spec.range_wltp or spec.range_cltc or spec.range_epa or spec.range_km
                if range_val:
                    entry['range_km'] = range_val
                if spec.body_type:
                    entry['body_type'] = spec.body_type
                if spec.price_from:
                    entry['price_from'] = spec.price_from
                    entry['currency'] = spec.currency
                if spec.acceleration_0_100:
                    entry['acceleration_0_100'] = spec.acceleration_0_100
                results.append(entry)
                if len(results) >= max_results:
                    break

        if results:
            logger.info(f"[SIBLINGS] Found {len(results)} siblings for {make} {model}: "
                        f"{[s['model'] for s in results]}")
        return results

    except Exception as e:
        logger.warning(f"[SIBLINGS] Lookup failed: {e}")
        return []


def format_siblings(make: str, model: str, siblings: list[dict]) -> str:
    """
    Format a sibling comparison block for prompt injection.
    Shows related models from the same brand for context.
    """
    if not siblings:
        return ''

    lines = [
        f"═══ BRAND LINEUP CONTEXT: {make} ═══",
        f"The {make} {model} has these siblings in the {make} lineup.",
        f"You may briefly mention how it fits within the range (1-2 sentences).\n",
        f"Siblings:",
    ]

    for s in siblings:
        parts = [f"  • {s['make']} {s['model']}"]
        if s.get('year'):
            parts.append(f"({s['year']})")
        specs_parts = []
        if s.get('power_hp'):
            specs_parts.append(f"{s['power_hp']} hp")
        if s.get('battery_kwh'):
            specs_parts.append(f"{s['battery_kwh']} kWh")
        if s.get('range_km'):
            specs_parts.append(f"{s['range_km']} km range")
        if s.get('price_from'):
            sym = {'CNY': '¥', 'USD': '$', 'EUR': '€'}.get(s.get('currency', 'USD'), '$')
            specs_parts.append(f"from {sym}{s['price_from']:,}")
        if specs_parts:
            parts.append(f"— {', '.join(specs_parts)}")
        lines.append(' '.join(parts))

    lines.append("\nDo NOT write a full comparison — just position this car within its brand's lineup naturally.")
    lines.append("═══════════════════════════════════════════════\n")

    return '\n'.join(lines)


def get_predecessor_context(make: str, model: str, current_specs: dict, year: int = None) -> str:
    """
    Main entry point: find predecessor and format comparison.
    Falls back to sibling context if no predecessor found.
    
    Priority:
      1. Predecessor (same model, earlier year) → year-over-year comparison
      2. Siblings (same brand, same body type) → brand lineup context
    """
    # Try predecessor first
    predecessor = find_predecessor(make, model, current_year=year)
    if predecessor:
        return format_evolution(current_specs, predecessor)

    # Fallback: find siblings from the same brand
    # Try to determine body type from current specs
    body_type = None
    if isinstance(current_specs, dict):
        body_type = current_specs.get('body_type')

    siblings = find_siblings(make, model, body_type=body_type)
    if siblings:
        return format_siblings(make, model, siblings)

    return ''
