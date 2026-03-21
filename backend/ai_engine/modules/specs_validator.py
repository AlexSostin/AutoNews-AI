"""
Vehicle specs validation and database lookup utilities.

- _validate_specs: sanitize AI-extracted specs against realistic ranges.
- _get_internal_specs_context: check VehicleSpecs DB for verified data.
- _get_competitor_context_safe: look up competitor cars for comparison.
"""
import re
import logging

logger = logging.getLogger(__name__)


def _validate_specs(specs: dict) -> dict:
    """Sanitize extracted specs — reject garbage values that AI sometimes hallucinates."""
    if not specs:
        return specs

    # Define realistic ranges for numeric fields
    RANGES = {
        'horsepower': (50, 2500),
        'torque': (50, 2500),       # Nm
        'top_speed': (80, 500),     # km/h
        'range': (50, 2500),        # km
    }
    for key, (lo, hi) in RANGES.items():
        val = specs.get(key)
        if not val or val == 'Not specified':
            continue
        nums = re.findall(r'\d+', str(val))
        if nums:
            n = int(nums[0])
            if not (lo <= n <= hi):
                print(f"⚠️ Specs validation: {key}={val!r} out of range ({lo}-{hi}), clearing")
                specs[key] = None

    # Validate year
    year = specs.get('year')
    if year:
        year_nums = re.findall(r'\d{4}', str(year))
        if year_nums and not (2018 <= int(year_nums[0]) <= 2028):
            print(f"⚠️ Specs validation: year={year!r} out of range, clearing")
            specs['year'] = None

    # Validate acceleration (0-100 in 1.5-25 seconds)
    accel = specs.get('acceleration')
    if accel and accel != 'Not specified':
        accel_nums = re.findall(r'[\d.]+', str(accel))
        if accel_nums:
            a = float(accel_nums[0])
            if not (1.5 <= a <= 25):
                print(f"⚠️ Specs validation: acceleration={accel!r} out of range, clearing")
                specs['acceleration'] = None

    return specs


def _get_internal_specs_context(specs: dict) -> str:
    """Check our VehicleSpecs DB for verified specs and return context string for prompt."""
    try:
        from news.models.vehicles import VehicleSpecs
        _make = specs.get('make', '')
        _model = specs.get('model', '')
        if not (_make and _model and _make != 'Not specified'):
            return ""
        existing = VehicleSpecs.objects.filter(
            make__iexact=_make,
            model_name__icontains=_model,
        ).order_by('-id').first()
        if not existing:
            print(f"ℹ️ No existing VehicleSpecs for {_make} {_model}")
            return ""
        parts = [
            f"Make: {existing.make}",
            f"Model: {existing.model_name}",
        ]
        field_map = [
            ('trim_name', 'Trim'), ('model_year', 'Year'),
            ('power_hp', 'Power (hp)'), ('power_kw', 'Power (kW)'),
            ('torque_nm', 'Torque (Nm)'), ('battery_kwh', 'Battery (kWh)'),
            ('acceleration_0_100', '0-100 (s)'),
            ('fuel_type', 'Fuel Type'), ('body_type', 'Body Type'),
            ('drivetrain', 'Drivetrain'),
        ]
        for attr, label in field_map:
            val = getattr(existing, attr, None)
            if val:
                parts.append(f"{label}: {val}")
        range_val = existing.range_wltp or existing.range_cltc or existing.range_epa or existing.range_km
        if range_val:
            parts.append(f"Range: {range_val} km")
        if existing.price_usd_from:
            parts.append(f"Price: from ${existing.price_usd_from:,}")
        if len(parts) > 4:
            ctx = (
                "\n═══ VERIFIED SPECS FROM OUR DATABASE (HIGH PRIORITY) ═══\n"
                "We already have this car in our database with VERIFIED specs.\n"
                "Use these as GROUND TRUTH — they override web search data:\n"
                + "\n".join(f"  ▸ {p}" for p in parts)
                + "\n\nIf your article contradicts these numbers, YOUR article is WRONG.\n"
                "═══════════════════════════════════════════════\n"
            )
            print(f"✅ Internal DB match: {existing.make} {existing.model_name} — injecting verified specs")
            return ctx
        else:
            print(f"ℹ️ Internal DB match found but sparse data ({len(parts)} fields)")
            return ""
    except Exception as e:
        print(f"⚠️ Internal spec verification failed (non-fatal): {e}")
        return ""


def _get_competitor_context_safe(specs: dict, send_progress) -> tuple:
    """Safely look up competitor cars from DB. Returns (context_str, competitor_data_list)."""
    try:
        from ai_engine.modules.competitor_lookup import get_competitor_context
        _make = specs.get('make', '')
        _model = specs.get('model', '')
        _fuel_raw = specs.get('powertrain_type') or specs.get('fuel_type') or ''
        _fuel_map = {
            'ev': 'EV', 'electric': 'EV', 'bev': 'EV',
            'phev': 'PHEV', 'plug-in': 'PHEV',
            'hybrid': 'Hybrid',
            'erev': 'EREV', 'rev': 'EREV', 'range extender': 'EREV',
            'gas': 'Gas', 'petrol': 'Gas', 'ice': 'Gas',
            'diesel': 'Diesel', 'hydrogen': 'Hydrogen',
        }
        _fuel_type = _fuel_map.get(_fuel_raw.lower().strip(), '')
        _body_type = specs.get('body_type', '')
        _power_hp = None
        _price_usd = None
        try:
            hp_match = re.search(r'(\d+)\s*(?:hp|HP|bhp)', specs.get('horsepower', ''))
            if hp_match:
                _power_hp = int(hp_match.group(1))
            _price_usd = int(specs.get('price_usd', 0) or 0) or None
        except Exception:
            pass
        if _make and _model:
            send_progress(4, 64, "🏆 Finding similar cars for comparison...")
            ctx, data = get_competitor_context(
                make=_make, model_name=_model,
                fuel_type=_fuel_type, body_type=_body_type,
                power_hp=_power_hp, price_usd=_price_usd,
            )
            if ctx:
                print(f"✓ Competitor context: {len(data)} cars found for comparison")
            else:
                print("ℹ️ No competitor context — no matching cars in DB yet")
            return ctx, data
    except Exception as e:
        print(f"⚠️ Competitor lookup failed (non-fatal): {e}")
    return "", []
