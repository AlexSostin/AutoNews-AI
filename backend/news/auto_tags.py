"""
Smart Auto-Tag System for FreshMotors articles.

3-Layer Pipeline:
  Layer 1: Extract tags from CarSpecification / VehicleSpecs (free, instant)
  Layer 2: AI extraction via Gemini for articles without structured data
  Layer 3: Tag normalization with deduplication and group assignment
"""
import re
import logging
from django.utils.text import slugify

logger = logging.getLogger(__name__)

# ============================================================
# KNOWN BRANDS DICTIONARY (50+ automotive brands)
# ============================================================
KNOWN_BRANDS = {
    # Chinese brands
    'byd', 'xiaomi', 'xpeng', 'zeekr', 'geely', 'dongfeng', 'nio', 'li auto',
    'changan', 'gac', 'voyah', 'avatr', 'lynk & co', 'smart', 'polestar',
    'wey', 'tank', 'haval', 'ora', 'leapmotor', 'neta', 'jidu', 'deepal',
    'denza', 'yangwang', 'fangchengbao', 'im motors', 'im', 'rising auto', 'seres',
    'hyptec', 'onvo', 'firefly', 'hongqi', 'baic', 'arcfox', 'gwm', 'chery',
    'jetour', 'exeed', 'forthing', 'leopard', 'fcb',
    # European brands
    'bmw', 'mercedes-benz', 'mercedes', 'audi', 'porsche', 'volkswagen', 'vw',
    'volvo', 'rolls-royce', 'bentley', 'ferrari', 'lamborghini', 'maserati',
    'alfa romeo', 'fiat', 'peugeot', 'citroen', 'renault', 'skoda', 'seat',
    'cupra', 'mini', 'bugatti', 'mclaren', 'aston martin', 'lotus',
    'land rover', 'range rover', 'jaguar',
    # Japanese brands
    'toyota', 'honda', 'nissan', 'mazda', 'subaru', 'mitsubishi', 'suzuki',
    'lexus', 'infiniti', 'acura', 'daihatsu',
    # Korean brands
    'hyundai', 'kia', 'genesis',
    # American brands
    'tesla', 'ford', 'chevrolet', 'gm', 'gmc', 'cadillac', 'chrysler',
    'dodge', 'jeep', 'ram', 'buick', 'lincoln', 'rivian', 'lucid',
    'fisker', 'canoo',
    # Others
    'tata', 'mahindra', 'vinfast',
}

# Normalize brand names to display form
BRAND_DISPLAY_NAMES = {
    'byd': 'BYD', 'bmw': 'BMW', 'gm': 'GM', 'gmc': 'GMC', 'gac': 'GAC',
    'nio': 'NIO', 'vw': 'Volkswagen', 'xiaomi': 'XIAOMI', 'xpeng': 'XPENG',
    'zeekr': 'ZEEKR', 'ev': 'EV', 'suv': 'SUV', 'phev': 'PHEV', 'mpv': 'MPV',
    'awd': 'AWD', 'fwd': 'FWD', 'rwd': 'RWD', '4wd': '4WD',
    'mercedes-benz': 'Mercedes-Benz', 'mercedes': 'Mercedes-Benz',
    'rolls-royce': 'Rolls-Royce', 'rolls royce': 'Rolls-Royce',
    'land rover': 'Land Rover', 'range rover': 'Range Rover',
    'alfa romeo': 'Alfa Romeo', 'aston martin': 'Aston Martin',
    'li auto': 'Li Auto', 'lynk & co': 'Lynk & Co',
    'im motors': 'IM Motors', 'rising auto': 'Rising Auto',
    'dongfeng': 'Dongfeng', 'geely': 'Geely', 'voyah': 'VOYAH',
    'avatr': 'AVATR', 'deepal': 'Deepal', 'denza': 'Denza',
    'yangwang': 'YangWang', 'fangchengbao': 'Fangchengbao',
    'hyptec': 'Hyptec', 'onvo': 'ONVO', 'firefly': 'Firefly',
    'hongqi': 'Hongqi', 'baic': 'BAIC', 'arcfox': 'ArcFox', 'gwm': 'GWM',
    'chery': 'Chery', 'jetour': 'Jetour', 'exeed': 'Exeed',
    'forthing': 'Forthing', 'im': 'IM', 'leopard': 'Leopard', 'fcb': 'FCB',
    'toyota': 'Toyota', 'honda': 'Honda', 'nissan': 'Nissan',
    'mazda': 'Mazda', 'subaru': 'Subaru', 'suzuki': 'Suzuki',
    'lexus': 'Lexus', 'infiniti': 'Infiniti', 'acura': 'Acura',
    'hyundai': 'Hyundai', 'kia': 'Kia', 'genesis': 'Genesis',
    'tesla': 'Tesla', 'ford': 'Ford', 'chevrolet': 'Chevrolet',
    'cadillac': 'Cadillac', 'chrysler': 'Chrysler', 'dodge': 'Dodge',
    'jeep': 'Jeep', 'ram': 'RAM', 'buick': 'Buick', 'lincoln': 'Lincoln',
    'rivian': 'Rivian', 'lucid': 'Lucid', 'fisker': 'Fisker',
    'ferrari': 'Ferrari', 'lamborghini': 'Lamborghini', 'porsche': 'Porsche',
    'audi': 'Audi', 'volkswagen': 'Volkswagen', 'volvo': 'Volvo',
    'bentley': 'Bentley', 'maserati': 'Maserati', 'mini': 'MINI',
    'bugatti': 'Bugatti', 'mclaren': 'McLaren', 'lotus': 'Lotus',
    'peugeot': 'Peugeot', 'citroen': 'Citroën', 'renault': 'Renault',
    'skoda': 'Škoda', 'cupra': 'CUPRA', 'polestar': 'Polestar',
    'smart': 'Smart', 'jaguar': 'Jaguar',
    'mitsubishi': 'Mitsubishi', 'daihatsu': 'Daihatsu',
    'tata': 'Tata', 'mahindra': 'Mahindra', 'vinfast': 'VinFast',
    'wey': 'WEY', 'tank': 'Tank', 'haval': 'Haval', 'ora': 'ORA',
    'leapmotor': 'Leapmotor', 'neta': 'Neta', 'jidu': 'JIDU',
    'seres': 'SERES', 'changan': 'Changan', 'canoo': 'Canoo',
}

# ============================================================
# TAG ALIASES — map variations to canonical names
# ============================================================
TAG_ALIASES = {
    # Fuel types
    'electric vehicle': 'EV', 'battery electric': 'EV', 'bev': 'EV',
    'electric': 'Electric', 'ev': 'EV',
    'plug-in hybrid': 'PHEV', 'plug in hybrid': 'PHEV', 'phev': 'PHEV',
    'hybrid': 'Hybrid', 'diesel': 'Diesel', 'hydrogen': 'Hydrogen',
    'gasoline': 'Gasoline', 'petrol': 'Gasoline',
    # Drivetrain
    'all wheel drive': 'AWD', 'all-wheel drive': 'AWD', 'awd': 'AWD',
    'front wheel drive': 'FWD', 'front-wheel drive': 'FWD', 'fwd': 'FWD',
    'rear wheel drive': 'RWD', 'rear-wheel drive': 'RWD', 'rwd': 'RWD',
    'four wheel drive': '4WD', '4x4': '4WD', '4wd': '4WD',
    # Body types
    'sport utility vehicle': 'SUV', 'suv': 'SUV',
    'multi purpose vehicle': 'MPV', 'mpv': 'MPV',
    'sedan': 'Sedan', 'coupe': 'Coupe', 'coupé': 'Coupe',
    'crossover': 'Crossover', 'hatchback': 'Hatchback',
    'wagon': 'Wagon', 'estate': 'Wagon',
    'pickup': 'Pickup Truck', 'pickup truck': 'Pickup Truck',
    'convertible': 'Convertible', 'cabriolet': 'Convertible',
    'minivan': 'Minivan', 'supercar': 'Supercar', 'hypercar': 'Supercar',
    # Segments
    'luxury': 'Luxury', 'budget': 'Budget', 'affordable': 'Budget',
    'family': 'Family', 'performance': 'Performance', 'sport': 'Performance',
    'off-road': 'Off-Road', 'offroad': 'Off-Road',
}

# ============================================================
# GROUP ASSIGNMENT — which group each tag type belongs to
# ============================================================
TAG_GROUP_MAP = {
    # Fuel Types
    'EV': 'Fuel Types', 'Electric': 'Fuel Types', 'PHEV': 'Fuel Types',
    'Hybrid': 'Fuel Types', 'Diesel': 'Fuel Types', 'Hydrogen': 'Fuel Types',
    'Gasoline': 'Fuel Types',
    # Drivetrain
    'AWD': 'Drivetrain', 'FWD': 'Drivetrain', 'RWD': 'Drivetrain', '4WD': 'Drivetrain',
    # Body Types
    'SUV': 'Body Types', 'Sedan': 'Body Types', 'Coupe': 'Body Types',
    'Crossover': 'Body Types', 'Hatchback': 'Body Types', 'Wagon': 'Body Types',
    'Pickup Truck': 'Body Types', 'Convertible': 'Body Types', 'Minivan': 'Body Types',
    'MPV': 'Body Types', 'Supercar': 'Body Types',
    # Segments
    'Luxury': 'Segments', 'Budget': 'Segments', 'Family': 'Segments',
    'Performance': 'Segments', 'Off-Road': 'Segments',
    # Tech & Features
    'Autonomous': 'Tech & Features', 'Long-range': 'Tech & Features',
    'Navigation': 'Tech & Features', 'Technology': 'Tech & Features',
    'Advanced': 'Tech & Features',
}

# Words that should NEVER become tags
STOP_WORDS = {
    'the', 'and', 'for', 'with', 'from', 'that', 'this', 'will', 'are', 'was',
    'has', 'have', 'been', 'not', 'but', 'can', 'all', 'new', 'first', 'more',
    'than', 'just', 'also', 'how', 'why', 'what', 'its', 'you', 'your', 'our',
    'review', 'drive', 'test', 'look', 'launch', 'announce', 'reveal', 'update',
    'report', 'article', 'news', 'latest', 'upcoming', 'walkaround', 'preview',
    'comparison', 'guide', 'deep', 'dive', 'watch', 'video', 'photo', 'image',
    'car', 'cars', 'vehicle', 'vehicles', 'auto', 'automotive', 'motor', 'motors',
    'model', 'engine', 'spec', 'specs', 'specifications', 'features', 'price',
    'performance', 'range', 'battery', 'charging', 'power',
}


def normalize_tag_name(raw_name):
    """
    Normalize a raw tag name to its canonical form.
    Returns (canonical_name, group_name) or (None, None) if invalid.
    """
    if not raw_name or not isinstance(raw_name, str):
        return None, None

    cleaned = raw_name.strip().lower()

    # Skip too short or stop words
    if len(cleaned) < 2 or cleaned in STOP_WORDS:
        return None, None

    # Skip pure numbers (except years 2020-2030)
    if cleaned.isdigit():
        year = int(cleaned)
        if 2020 <= year <= 2030:
            return cleaned, 'Years'
        return None, None

    # Check aliases first
    if cleaned in TAG_ALIASES:
        canonical = TAG_ALIASES[cleaned]
        group = TAG_GROUP_MAP.get(canonical, None)
        return canonical, group

    # Check if it's a known brand
    if cleaned in KNOWN_BRANDS:
        display = BRAND_DISPLAY_NAMES.get(cleaned, cleaned.title())
        return display, 'Manufacturers'

    # Check if display name maps to a group
    title_case = raw_name.strip()
    if title_case in TAG_GROUP_MAP:
        return title_case, TAG_GROUP_MAP[title_case]

    # Generic title-casing for unknown tags
    return raw_name.strip().title(), None


def find_or_create_tag(name, group_name=None):
    """
    Find existing tag or create new one. Handles deduplication.
    Returns (tag, created) tuple.
    """
    from news.models import Tag, TagGroup

    canonical, auto_group = normalize_tag_name(name)
    if not canonical:
        return None, False

    # Use auto-detected group if none specified
    if not group_name:
        group_name = auto_group

    # Case-insensitive lookup
    existing = Tag.objects.filter(name__iexact=canonical).first()
    if existing:
        # Fix group if misplaced and we know the correct one
        if group_name and not existing.group:
            try:
                grp = TagGroup.objects.get(name=group_name)
                existing.group = grp
                existing.save(update_fields=['group'])
                logger.info(f'🔧 Fixed tag "{existing.name}" → group "{group_name}"')
            except TagGroup.DoesNotExist:
                pass
        return existing, False

    # Create new tag
    group = None
    if group_name:
        group, _ = TagGroup.objects.get_or_create(
            name=group_name,
            defaults={'slug': slugify(group_name)}
        )

    tag = Tag.objects.create(
        name=canonical,
        slug=slugify(canonical),
        group=group,
    )
    logger.info(f'✨ Created tag "{canonical}" in group "{group_name or "ungrouped"}"')
    return tag, True


def extract_tags_from_structured_data(article):
    """
    Layer 1: Extract tags from CarSpecification and VehicleSpecs.
    Returns list of (tag_name, group_name) tuples.
    """
    from news.models import CarSpecification, VehicleSpecs

    tags = []

    # From CarSpecification
    car_spec = CarSpecification.objects.filter(article=article).first()
    if car_spec and car_spec.make:
        tags.append((car_spec.make, 'Manufacturers'))

    # From VehicleSpecs (richer data)
    vehicle_specs = VehicleSpecs.objects.filter(article=article).first()
    if vehicle_specs:
        if vehicle_specs.make:
            tags.append((vehicle_specs.make, 'Manufacturers'))
        if vehicle_specs.body_type:
            tags.append((vehicle_specs.body_type, 'Body Types'))
        if vehicle_specs.fuel_type:
            tags.append((vehicle_specs.fuel_type, 'Fuel Types'))
        if vehicle_specs.drivetrain:
            tags.append((vehicle_specs.drivetrain, 'Drivetrain'))
        if vehicle_specs.year:
            tags.append((str(vehicle_specs.year), 'Years'))

    return tags


def extract_tags_from_title(article):
    """
    Layer 1.5: Extract tags by scanning title and content for known brands
    and keywords. No API calls needed.
    """
    tags = []
    title_lower = article.title.lower()
    content_lower = (article.content or '')[:2000].lower()
    combined = f"{title_lower} {content_lower}"

    # Scan for known brands in title (word boundary to avoid false positives)
    for brand in KNOWN_BRANDS:
        pattern = rf'\b{re.escape(brand)}\b'
        if re.search(pattern, title_lower, re.IGNORECASE):
            tags.append((brand, 'Manufacturers'))

    # Extract year from title (e.g. "2026 BYD...")
    year_match = re.search(r'\b(202[0-9])\b', title_lower)
    if year_match:
        tags.append((year_match.group(1), 'Years'))

    # Fuel type keywords in combined text
    fuel_patterns = {
        'electric': ('Electric', 'Fuel Types'),
        r'\bev\b': ('EV', 'Fuel Types'),
        'phev': ('PHEV', 'Fuel Types'),
        'plug-in hybrid': ('PHEV', 'Fuel Types'),
        r'\bhybrid\b': ('Hybrid', 'Fuel Types'),
        'hydrogen': ('Hydrogen', 'Fuel Types'),
    }
    for pattern, (tag_name, group) in fuel_patterns.items():
        if re.search(pattern, combined, re.IGNORECASE):
            tags.append((tag_name, group))

    # Body type keywords
    body_patterns = {
        r'\bsuv\b': ('SUV', 'Body Types'),
        r'\bsedan\b': ('Sedan', 'Body Types'),
        r'\bcoupe\b|coupé': ('Coupe', 'Body Types'),
        r'\bcrossover\b': ('Crossover', 'Body Types'),
        r'\bhatchback\b': ('Hatchback', 'Body Types'),
        r'\bmpv\b': ('MPV', 'Body Types'),
        r'\bwagon\b|estate': ('Wagon', 'Body Types'),
        r'\bconvertible\b|cabriolet': ('Convertible', 'Body Types'),
        r'\bpickup\b': ('Pickup Truck', 'Body Types'),
        r'\bsupercar\b|hypercar': ('Supercar', 'Body Types'),
    }
    for pattern, (tag_name, group) in body_patterns.items():
        if re.search(pattern, combined, re.IGNORECASE):
            tags.append((tag_name, group))

    # Drivetrain keywords
    drive_patterns = {
        r'\bawd\b': ('AWD', 'Drivetrain'),
        r'\brwd\b': ('RWD', 'Drivetrain'),
        r'\bfwd\b': ('FWD', 'Drivetrain'),
        r'\b4wd\b|4x4': ('4WD', 'Drivetrain'),
    }
    for pattern, (tag_name, group) in drive_patterns.items():
        if re.search(pattern, combined, re.IGNORECASE):
            tags.append((tag_name, group))

    # Segment keywords in title only (avoid false matches in content)
    if 'luxury' in title_lower or 'premium' in title_lower:
        tags.append(('Luxury', 'Segments'))
    if 'affordable' in title_lower or 'budget' in title_lower:
        tags.append(('Budget', 'Segments'))
    if 'family' in combined:
        tags.append(('Family', 'Segments'))
    if 'off-road' in combined or 'offroad' in combined:
        tags.append(('Off-Road', 'Segments'))

    return tags


def extract_tags_with_ai(article):
    """
    Layer 2: Use Gemini to extract tags from articles without structured data.
    Returns list of (tag_name, group_name) tuples.
    """
    try:
        from ai_engine.modules.ai_provider import get_ai_provider
        import json

        ai = get_ai_provider('gemini')
        content_preview = (article.content or '')[:800]
        # Strip HTML
        content_preview = re.sub(r'<[^>]+>', ' ', content_preview)
        content_preview = re.sub(r'\s+', ' ', content_preview).strip()

        prompt = f"""Analyze this automotive article and extract structured tags.

Title: "{article.title}"
Content: "{content_preview}"

Return ONLY a valid JSON object (no markdown, no code blocks):
{{
  "brand": "primary car manufacturer name or null",
  "year": model year as integer or null,
  "body_type": "sedan|suv|crossover|coupe|hatchback|wagon|mpv|pickup|convertible|null",
  "fuel_type": "ev|phev|hybrid|diesel|gasoline|hydrogen|null",
  "drivetrain": "awd|fwd|rwd|4wd|null",
  "segment": ["luxury","budget","family","performance","off-road"],
  "topics": ["autonomous","safety","design","motorsport","business","racing","technology"]
}}

Rules:
- brand = the PRIMARY car manufacturer, not a division or sub-brand
- Only include segment/topics that are CLEARLY relevant
- For non-automotive articles (finance, space, sports), set brand to null
- segment and topics are arrays, can be empty []"""

        result = ai.generate_completion(prompt, temperature=0.1, max_tokens=300)

        # Parse JSON from response (handle markdown code blocks)
        json_str = result.strip()
        if '```' in json_str:
            json_str = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', json_str, re.DOTALL)
            json_str = json_str.group(1) if json_str else result.strip()
        # Also handle case where response has extra text
        json_match = re.search(r'\{[^{}]*\}', json_str, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)

        data = json.loads(json_str)

        tags = []
        if data.get('brand'):
            tags.append((data['brand'], 'Manufacturers'))
        if data.get('year') and 2020 <= (data.get('year') or 0) <= 2030:
            tags.append((str(data['year']), 'Years'))
        if data.get('body_type'):
            tags.append((data['body_type'], 'Body Types'))
        if data.get('fuel_type'):
            tags.append((data['fuel_type'], 'Fuel Types'))
        if data.get('drivetrain'):
            tags.append((data['drivetrain'], 'Drivetrain'))
        for seg in (data.get('segment') or []):
            tags.append((seg, 'Segments'))
        for topic in (data.get('topics') or []):
            tags.append((topic, 'Tech & Features'))

        logger.info(f'🤖 AI extracted {len(tags)} tags for article #{article.id}')
        return tags

    except Exception as e:
        logger.warning(f'⚠️ AI tag extraction failed for #{article.id}: {e}')
        return []


def auto_tag_article(article, use_ai=True, max_tags=12):
    """
    Main orchestrator: runs the 3-layer pipeline on a single article.

    Returns dict with results:
      {
        'created': ['BMW', '2026'],    # newly created tags
        'matched': ['Sedan', 'EV'],    # existing tags assigned
        'skipped': ['car', 'the'],     # rejected by normalizer
        'ai_used': True/False,
        'total': 4,
      }
    """
    result = {
        'created': [],
        'matched': [],
        'skipped': [],
        'ai_used': False,
        'total': 0,
    }

    existing_tags = set(article.tags.values_list('name', flat=True))
    all_raw_tags = []

    # Layer 1: Structured data
    structured_tags = extract_tags_from_structured_data(article)
    all_raw_tags.extend(structured_tags)

    # Layer 1.5: Title/content scanning
    title_tags = extract_tags_from_title(article)
    all_raw_tags.extend(title_tags)

    # Layer 2: AI extraction (if we found < 3 useful tags so far)
    if use_ai:
        # Deduplicate what we have so far
        unique_so_far = set()
        for raw_name, _ in all_raw_tags:
            canonical, _ = normalize_tag_name(raw_name)
            if canonical:
                unique_so_far.add(canonical)

        if len(unique_so_far) < 3:
            ai_tags = extract_tags_with_ai(article)
            all_raw_tags.extend(ai_tags)
            result['ai_used'] = True

    # Layer 3: Normalize, deduplicate, and assign
    seen = set()
    tags_added = 0

    for raw_name, group_hint in all_raw_tags:
        if tags_added >= max_tags:
            break

        canonical, auto_group = normalize_tag_name(raw_name)
        if not canonical:
            result['skipped'].append(raw_name)
            continue

        if canonical in seen or canonical in existing_tags:
            continue
        seen.add(canonical)

        group_name = group_hint if group_hint else auto_group
        tag, created = find_or_create_tag(canonical, group_name)
        if not tag:
            result['skipped'].append(raw_name)
            continue

        article.tags.add(tag)
        tags_added += 1

        if created:
            result['created'].append(canonical)
        else:
            result['matched'].append(canonical)

    result['total'] = tags_added
    return result
