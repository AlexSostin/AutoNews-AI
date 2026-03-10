"""
Shared module for extracting and normalizing car specifications.
Used by:
  - post_save signal (auto-create on article publish)
  - backfill_missing_specs management command
  - normalize_specs management command
"""
import re
import logging
from news.models import Article, CarSpecification

logger = logging.getLogger(__name__)

MAX_FIELD_LENGTH = 50  # DB varchar(50) limit

# Minimum plausible car prices per currency (to catch extraction errors)
PRICE_SANITY = {
    '$': 5_000,    # USD — even a beater is $5k+
    '¥': 50_000,   # CNY — €/¥ Japanese yen would be 500k, but ¥ here = CNY usually
    '€': 5_000,
    '£': 5_000,
    'CNY': 50_000,
    'RMB': 50_000,
}

# Canonical make names mapping (lowercase -> correct case)
MAKE_CANONICAL = {
    'xpeng': 'XPENG',
    'zeekr': 'ZEEKR',
    'byd': 'BYD',
    'nio': 'NIO',
    'gwm': 'GWM',
    'im': 'IM',
    'dongfeng voyah': 'DongFeng VOYAH',
    'dongfeng': 'DongFeng',
    'huawei': 'Huawei',
    'xiaomi': 'Xiaomi',
    'geely': 'Geely',
    'toyota': 'Toyota',
    'smart': 'Smart',
    'avatr': 'Avatr',
    'arcfox': 'ArcFox',
}

# Article IDs that are news/non-car content - skip them
SKIP_ARTICLE_IDS = {73, 76}


def normalize_make(make: str) -> str:
    """Normalize make name to canonical form."""
    canonical = MAKE_CANONICAL.get(make.lower().strip())
    return canonical if canonical else make


def normalize_hp(hp_str: str) -> str:
    """Normalize horsepower to just a number string like '300'.
    Frontend adds 'hp' suffix itself.
    """
    if not hp_str or hp_str.strip() in ('0', 'None', 'Not specified', 'N/A'):
        return ''

    hp_str = hp_str.strip()

    # Handle "X kW" (convert to hp: 1 kW ≈ 1.34 hp)
    kw_match = re.match(r'^(\d+)\s*kW$', hp_str, re.IGNORECASE)
    if kw_match:
        kw = int(kw_match.group(1))
        hp = round(kw * 1.341)
        return str(hp)

    # Handle "Over X hp" / "Up to X hp"
    prefix_match = re.match(r'(?:over|up to|approximately)\s+(\d+)', hp_str, re.IGNORECASE)
    if prefix_match:
        return prefix_match.group(1)

    # Handle "X hp / Y hp" (dual motor) - take higher
    dual_match = re.findall(r'(\d+)\s*(?:hp|HP|horsepower)', hp_str)
    if len(dual_match) >= 2:
        highest = max(int(x) for x in dual_match)
        return str(highest)

    # Handle "X horsepower (Y kW)" or "X hp" or "X HP" or "X horsepower"
    match = re.search(r'(\d+)\s*(?:hp|HP|horsepower|Horse\s*Power)', hp_str)
    if match:
        return match.group(1)

    # If it's just a number
    if hp_str.isdigit():
        return hp_str

    # Can't parse - return as-is
    return hp_str


def normalize_price(price_str: str) -> str:
    """Clean up price string and do a basic sanity check.
    Returns empty string if price looks like an extraction error (too low).
    """
    if not price_str:
        return ''
    price_str = price_str.strip()

    # Detect currency symbol / prefix
    currency_key = None
    numeric_part = price_str
    for sym in ('CNY', 'RMB', '$', '¥', '€', '£'):
        if price_str.upper().startswith(sym.upper()):
            currency_key = sym
            numeric_part = price_str[len(sym):].strip().replace(',', '')
            break

    if currency_key and currency_key in PRICE_SANITY:
        try:
            value = float(numeric_part.split()[0])  # handle trailing text
            if value < PRICE_SANITY[currency_key]:
                logger.warning(
                    f'Price sanity FAIL — {price_str!r} is suspiciously low '
                    f'(min {PRICE_SANITY[currency_key]:,} for {currency_key}). Discarding.'
                )
                return ''
        except (ValueError, IndexError):
            pass  # can't parse numeric part — keep as-is

    return price_str


def extract_specs_from_content(article) -> dict | None:
    """Extract car specs from article content.
    Tries AI (Gemini) first, falls back to regex extraction from title/content.
    Returns dict with keys: make, model, trim, engine, horsepower, torque,
    acceleration, top_speed, drivetrain, price.
    Returns None if extraction fails or article is not about a car.
    """
    # Try AI extraction first
    specs = _extract_specs_ai(article)
    if specs and specs.get('make') and specs['make'] != 'Not specified':
        logger.info(f'AI extraction succeeded for [{article.id}]')
        return specs

    # Fallback: regex extraction from title + content
    logger.info(f'AI extraction failed for [{article.id}], trying regex fallback')
    specs = _extract_specs_regex(article)
    if specs and specs.get('make'):
        logger.info(f'Regex extraction succeeded for [{article.id}]: {specs.get("make")} {specs.get("model")}')
        return specs

    return None


def _extract_specs_ai(article) -> dict | None:
    """AI-based spec extraction using Gemini."""
    from ai_engine.modules.ai_provider import get_ai_provider

    # Strip HTML tags for cleaner text
    content = re.sub(r'<[^>]+>', ' ', article.content or '')
    content = re.sub(r'\s+', ' ', content).strip()
    content = content[:4000]  # Limit length

    prompt = f"""Extract car specifications from this article.
Title: {article.title}

Content:
{content}

Output ONLY these fields with EXACT labels:
Make: [Brand name, e.g. "NIO", "BYD", "Xpeng", "Toyota"]
Model: [Model name without brand, e.g. "ET9", "Leopard 5", "Highlander"]
Trim/Version: [Trim if mentioned, else "Not specified"]
Engine: [Engine type, e.g. "Electric Dual Motor", "1.5L Turbo PHEV", "2.0L Inline-4"]
Horsepower: [Number with unit, e.g. "300 hp" or "220 kW"]
Torque: [With unit, e.g. "400 Nm"]
Acceleration: [0-60 mph or 0-100 km/h time, e.g. "5.5 seconds (0-60 mph)"]
Top Speed: [With unit, e.g. "155 mph" or "250 km/h"]
Drivetrain: [AWD/FWD/RWD/4WD or "Not specified"]
Price: [PRIMARY market launch price in its NATIVE currency with symbol.
  - Chinese cars: use CNY price (¥168,000 or CNY 168,000), NOT the USD equivalent
  - US/EU cars: use USD or EUR as appropriate
  - Include the full price, e.g. "¥168,800" NOT just "¥19" or truncated values
  - If ONLY a USD/EUR conversion is mentioned for a Chinese car, still write that (e.g. "$23,000")
  - Write "Not specified" if NO price is in the article]

IMPORTANT:
1. Only include specs EXPLICITLY mentioned in the content.
2. Write "Not specified" if a spec is not found in the text.
3. NEVER guess, estimate, or use qualifiers like "(estimated)".
4. If the article is clearly NOT about a specific car model, output Make: Not specified
"""

    system_prompt = (
        "You are an automotive data extractor. Extract only facts explicitly "
        "stated in the text. Never guess. Use 'Not specified' for unknown fields."
    )

    try:
        ai = get_ai_provider('gemini')
        result = ai.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=500,
        )
        return _parse_specs(result)
    except Exception as e:
        logger.error(f'AI extraction error for article {article.id}: {e}')
        return None


# Known car brands for regex matching
KNOWN_BRANDS = {
    'ZEEKR', 'BYD', 'NIO', 'XPENG', 'GWM', 'Geely', 'Toyota', 'Honda',
    'Xiaomi', 'Huawei', 'Smart', 'Avatr', 'ArcFox', 'DongFeng', 'Chery',
    'GAC', 'SAIC', 'MG', 'Lynk', 'Polestar', 'Volvo', 'BMW', 'Mercedes',
    'Audi', 'Volkswagen', 'Ford', 'Tesla', 'Hyundai', 'Kia', 'Li Auto',
    'Leopard', 'Denza', 'Jetour', 'Haval', 'Tank', 'Wey', 'Hongqi', 'JAC',
    'Changan', 'Voyah', 'IM', 'Lancia', 'Rivian', 'Lucid',
}


def _extract_specs_regex(article) -> dict | None:
    """Regex-based spec extraction from title and content. No AI needed."""
    title = article.title or ''
    content = re.sub(r'<[^>]+>', ' ', article.content or '')
    content = re.sub(r'\s+', ' ', content).strip()

    specs = {}

    # Extract make and model from title
    # Common patterns: "2026 ZEEKR 007GT EV Review", "BYD Leopard 5 Review"
    for brand in KNOWN_BRANDS:
        pattern = rf'\b{re.escape(brand)}\b\s+([A-Za-z0-9][A-Za-z0-9\s\-]*?)(?:\s+(?:EV|Review|Revealed|Launch|Test|Drive|First|Look|Specs|Price|vs\b|–|-|:|\|))'
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            specs['make'] = brand
            specs['model'] = match.group(1).strip()
            break

    if not specs.get('make'):
        # Try broader pattern: "YYYY Brand Model ..."
        year_brand = re.match(r'(\d{4})\s+(\w+)\s+([\w\-]+)', title)
        if year_brand:
            year, brand_candidate, model_candidate = year_brand.groups()
            # Check if brand is known
            for known in KNOWN_BRANDS:
                if brand_candidate.upper() == known.upper():
                    specs['make'] = known
                    specs['model'] = model_candidate
                    break

    if not specs.get('make'):
        return None

    # Extract price from content — supports ¥, $, €, £, CNY, RMB
    # First try to find a contextual price ("starting at ...", "priced from ...")
    price_match = re.search(
        r'(?:starting\s+(?:price|at|from)|price[:\s]+|priced\s+(?:at|from)|MSRP[:\s]+|costs?\s+)'
        r'[\s]*([¥$€£]\s*[\d,]+(?:\.\d+)?|(?:CNY|RMB|USD|EUR|GBP)\s+[\d,]+(?:\.\d+)?)',
        content, re.IGNORECASE
    )
    if not price_match:
        # Broader: any price-like token in the content
        price_match = re.search(
            r'([¥$€£]\s*[\d]{2,3}(?:[,\d]+)(?:\.\d+)?|(?:CNY|RMB)\s+[\d,]+(?:\.\d+)?)',
            content
        )
    if price_match:
        raw_price = price_match.group(1).replace(' ', '')
        validated = normalize_price(raw_price)
        if validated:
            specs['price'] = validated

    # Extract horsepower from content
    hp_match = re.search(r'(\d+)\s*(?:hp|HP|horsepower|Horse\s*Power)', content)
    if hp_match:
        specs['horsepower'] = hp_match.group(1)

    # Extract engine type
    if re.search(r'\b(?:electric|EV|BEV|battery\s+electric)\b', content, re.IGNORECASE):
        specs['engine'] = 'Electric'
    elif re.search(r'\bPHEV\b|plug.in\s+hybrid', content, re.IGNORECASE):
        specs['engine'] = 'PHEV'
    elif re.search(r'\bhybrid\b', content, re.IGNORECASE):
        specs['engine'] = 'Hybrid'

    # Extract drivetrain
    dt_match = re.search(r'\b(AWD|FWD|RWD|4WD|all.wheel|front.wheel|rear.wheel)\b', content, re.IGNORECASE)
    if dt_match:
        dt = dt_match.group(1).upper()
        if 'ALL' in dt: dt = 'AWD'
        elif 'FRONT' in dt: dt = 'FWD'
        elif 'REAR' in dt: dt = 'RWD'
        specs['drivetrain'] = dt

    return specs


def _parse_specs(text: str) -> dict:
    """Parse AI output into specs dict."""
    specs = {}
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('Make:'):
            specs['make'] = line.split(':', 1)[1].strip()
        elif line.startswith('Model:'):
            specs['model'] = line.split(':', 1)[1].strip()
        elif line.startswith('Trim/Version:'):
            specs['trim'] = line.split(':', 1)[1].strip()
        elif line.startswith('Engine:'):
            specs['engine'] = line.split(':', 1)[1].strip()
        elif line.startswith('Horsepower:'):
            specs['horsepower'] = line.split(':', 1)[1].strip()
        elif line.startswith('Torque:'):
            specs['torque'] = line.split(':', 1)[1].strip()
        elif line.startswith('Acceleration:'):
            specs['acceleration'] = line.split(':', 1)[1].strip()
        elif line.startswith('Top Speed:'):
            specs['top_speed'] = line.split(':', 1)[1].strip()
        elif line.startswith('Drivetrain:') or line.startswith('Drive:'):
            specs['drivetrain'] = line.split(':', 1)[1].strip()
        elif line.startswith('Price:'):
            raw = line.split(':', 1)[1].strip()
            validated = normalize_price(raw)
            if validated and validated != 'Not specified':
                specs['price'] = validated
    return specs


def save_specs_for_article(article, specs: dict, force_update: bool = False) -> CarSpecification | None:
    """Create or update CarSpecification for an article from extracted specs dict.
    Applies normalization (canonical make names, clean HP).
    MERGE logic (force_update=False): only overwrites EMPTY fields (safe, auto-run mode).
    FORCE mode (force_update=True): overwrites ALL non-empty spec fields from extraction
      — used by the admin re_extract action to correct wrong data.
    Returns the CarSpecification instance, or None if specs are insufficient.
    """
    make = specs.get('make', '')
    model = specs.get('model', '')

    if not make or make == 'Not specified':
        return None

    # Normalize make name, then resolve sub-brand rules
    make = normalize_make(make)
    from news.models import BrandAlias
    make, model = BrandAlias.resolve_with_model(make, model)
    hp_raw = specs.get('horsepower', '')
    hp_clean = normalize_hp(hp_raw)

    def _val(key, default=''):
        """Get spec value, skip 'Not specified', truncate to max length."""
        v = specs.get(key, default)
        if v == 'Not specified':
            return default
        return str(v)[:MAX_FIELD_LENGTH] if v else default

    # New extracted values (may contain empty strings)
    new_data = {
        'model_name': f'{make} {model}'.strip()[:200],
        'make': make[:100],
        'model': model[:100],
        'trim': _val('trim'),
        'engine': _val('engine'),
        'horsepower': hp_clean,
        'torque': _val('torque'),
        'zero_to_sixty': _val('acceleration'),
        'top_speed': _val('top_speed'),
        'drivetrain': _val('drivetrain'),
        'price': _val('price'),
    }

    try:
        # ── Step 1: look up by article (existing behaviour) ──────────────────
        existing = CarSpecification.objects.filter(article=article).first()

        # ── Step 2: if no article-linked spec, look for a make+model master ──
        # Priority: verified master first, then any existing record for same car
        if not existing and make and model:
            master = (
                CarSpecification.objects.filter(make=make, model=model, is_verified=True)
                .order_by('-verified_at')
                .first()
            ) or (
                CarSpecification.objects.filter(make=make, model=model)
                .order_by('-id')
                .first()
            )
            if master and (master.article_id is None or master.article_id == article.id):
                # Free slot on master — link this article to it, no new record needed
                if master.article_id != article.id:
                    master.article = article
                    master.save(update_fields=['article'])
                existing = master
                logger.info(
                    f'[dedup] Linked article [{article.id}] to existing spec '
                    f'[{master.id}] {make} {model} — skipping duplicate creation'
                )

        if existing:
            # MERGE: only overwrite EMPTY fields (never downgrade existing good data)
            updated_fields = []
            locked_fields = {'make', 'model', 'model_name'} if existing.is_make_locked else set()
            if locked_fields:
                logger.info(f'🔒 Make locked for [{article.id}] — preserving admin brand assignment')
            for field, new_value in new_data.items():
                if field in locked_fields:
                    continue
                old_value = getattr(existing, field, '')
                if field in ('make', 'model', 'model_name'):
                    # Identity fields: update if new value is non-empty and different
                    if new_value and new_value != old_value:
                        setattr(existing, field, new_value)
                        updated_fields.append(field)
                else:
                    if force_update:
                        # FORCE mode: overwrite existing value with fresh extraction
                        if new_value and new_value != old_value:
                            setattr(existing, field, new_value)
                            updated_fields.append(field)
                    else:
                        # Spec fields: only fill if currently empty (donor logic)
                        if new_value and not old_value:
                            setattr(existing, field, new_value)
                            updated_fields.append(field)

            if updated_fields:
                existing.save(update_fields=updated_fields)
                logger.info(f'Merged CarSpecification for [{article.id}] {make} {model} — updated: {", ".join(updated_fields)}')
            else:
                logger.info(f'No changes for CarSpecification [{article.id}] {make} {model}')
            return existing
        else:
            # CREATE: first time we see this make+model — create a fresh spec
            car_spec = CarSpecification.objects.create(
                article=article,
                **new_data,
            )
            logger.info(f'Created CarSpecification for [{article.id}] {make} {model}')
            return car_spec
    except Exception as e:
        logger.error(f'Failed to save CarSpecification for [{article.id}]: {e}')
        return None
