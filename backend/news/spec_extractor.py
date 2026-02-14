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
Price: [With currency symbol, e.g. "$45,000" or "¥169,800"]

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

    # Extract price from content: "$29,400" or "¥169,800"
    price_match = re.search(r'(?:starting\s+(?:price|at|from)|price[:\s]+|priced\s+(?:at|from)|MSRP[:\s]+|costs?\s+)[\s]*(\$[\d,]+(?:\.\d+)?)', content, re.IGNORECASE)
    if not price_match:
        price_match = re.search(r'(\$[\d,]+(?:\.\d+)?)', content)
    if price_match:
        specs['price'] = price_match.group(1)

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
            specs['price'] = line.split(':', 1)[1].strip()
    return specs


def save_specs_for_article(article, specs: dict) -> CarSpecification | None:
    """Create or update CarSpecification for an article from extracted specs dict.
    Applies normalization (canonical make names, clean HP).
    Returns the CarSpecification instance, or None if specs are insufficient.
    """
    make = specs.get('make', '')
    model = specs.get('model', '')

    if not make or make == 'Not specified':
        return None

    # Normalize
    make = normalize_make(make)
    hp_raw = specs.get('horsepower', '')
    hp_clean = normalize_hp(hp_raw)

    def _val(key, default=''):
        """Get spec value, skip 'Not specified', truncate to max length."""
        v = specs.get(key, default)
        if v == 'Not specified':
            return default
        return str(v)[:MAX_FIELD_LENGTH] if v else default

    spec_data = {
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
        'release_date': '',
    }

    try:
        car_spec, created = CarSpecification.objects.update_or_create(
            article=article,
            defaults=spec_data,
        )
        action = 'Created' if created else 'Updated'
        logger.info(f'{action} CarSpecification for [{article.id}] {make} {model}')
        return car_spec
    except Exception as e:
        logger.error(f'Failed to save CarSpecification for [{article.id}]: {e}')
        return None
