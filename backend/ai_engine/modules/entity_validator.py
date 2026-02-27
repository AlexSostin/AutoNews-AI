"""
Entity Validator — Prevents AI model name/number hallucinations.

Extracts key entities (brand, model name, model number) from source titles
and verifies they appear correctly in AI-generated articles.

Zero LLM cost — purely programmatic string matching.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Known automotive brand aliases ─────────────────────────────────────────
# Maps common variations to canonical brand name
BRAND_ALIASES = {
    'byd': 'BYD',
    'fang cheng bao': 'Fang Cheng Bao',
    'yangwang': 'Yangwang',
    'denza': 'Denza',
    'zeekr': 'ZEEKR',
    'geely': 'Geely',
    'chery': 'Chery',
    'nio': 'NIO',
    'xpeng': 'XPeng',
    'li auto': 'Li Auto',
    'aito': 'AITO',
    'avatr': 'Avatr',
    'jiyue': 'JIYUE',
    'smart': 'Smart',
    'mg': 'MG',
    'ora': 'ORA',
    'gwm': 'GWM',
    'haval': 'HAVAL',
    'tank': 'Tank',
    'honda': 'Honda',
    'toyota': 'Toyota',
    'hyundai': 'Hyundai',
    'kia': 'Kia',
    'bmw': 'BMW',
    'mercedes': 'Mercedes',
    'mercedes-benz': 'Mercedes-Benz',
    'audi': 'Audi',
    'porsche': 'Porsche',
    'volkswagen': 'Volkswagen',
    'vw': 'Volkswagen',
    'volvo': 'Volvo',
    'tesla': 'Tesla',
    'ford': 'Ford',
    'chevrolet': 'Chevrolet',
    'cadillac': 'Cadillac',
    'rivian': 'Rivian',
    'lucid': 'Lucid',
    'polestar': 'Polestar',
    'lotus': 'Lotus',
    'mclaren': 'McLaren',
    'ferrari': 'Ferrari',
    'lamborghini': 'Lamborghini',
    'lexus': 'Lexus',
    'mazda': 'Mazda',
    'subaru': 'Subaru',
    'nissan': 'Nissan',
    'infiniti': 'Infiniti',
    'suzuki': 'Suzuki',
    'mitsubishi': 'Mitsubishi',
    'stellantis': 'Stellantis',
    'dodge': 'Dodge',
    'jeep': 'Jeep',
    'ram': 'RAM',
    'fiat': 'Fiat',
    'alfa romeo': 'Alfa Romeo',
    'peugeot': 'Peugeot',
    'citroen': 'Citroen',
    'renault': 'Renault',
    'jaguar': 'Jaguar',
    'land rover': 'Land Rover',
    'range rover': 'Range Rover',
    'mini': 'MINI',
    'vinfast': 'VinFast',
    'tata': 'Tata',
    'mahindra': 'Mahindra',
    'leapmotor': 'Leapmotor',
    'im motors': 'IM Motors',
    'rising auto': 'Rising Auto',
    'deepal': 'Deepal',
    'neta': 'Neta',
    'seres': 'Seres',
    'voyah': 'Voyah',
    'dongfeng': 'Dongfeng',
    'jaecoo': 'Jaecoo',
    'omoda': 'OMODA',
    'maxus': 'MAXUS',
    'lynk & co': 'Lynk & Co',
    'lync & co': 'Lynk & Co',
    'genesis': 'Genesis',
    'ssangyong': 'SsangYong',
}


# ── Model name patterns ──────────────────────────────────────────────────
# Matches alphanumeric model identifiers like "Leopard 8", "Model Y", "7X", "007 GT"
_MODEL_PATTERN = re.compile(
    r'\b('
    # Alphanumeric model names: "Leopard 8", "Seal 06", "Bao 5", "Atto 3"
    r'[A-Z][a-z]+\s+\d+(?:\s*[A-Z]+)?'
    r'|'
    # Numeric-first models: "7X", "007 GT", "001", "009"
    r'\d{1,4}\s*[A-Z]{1,3}'
    r'|'
    # Pure model names with version: "Model Y", "Model 3", "Model S"
    r'Model\s+[A-Z0-9]+'
    r'|'
    # Tanked models: "Tank 300", "Tank 500"
    r'Tank\s+\d+'
    r'|'
    # Known specific patterns: "e-tron", "iX", "EQS", "EQE"
    r'[ei][A-Z][A-Z]?\d*'
    r'|'
    # Simple numeric model: just numbers like "M8", "M9", "X5"
    r'[A-Z]\d{1,2}'
    r')\b'
)

# Year pattern (2020-2030 range)
_YEAR_PATTERN = re.compile(r'\b(20[2-3]\d)\b')


def clean_source_title(title: str) -> str:
    """
    Strip RSS metadata from source titles before entity extraction.
    
    Handles titles like:
    'LEOPARD 5 1310km range starting price $37,900 overview China 🇨🇳 🚗'
    → 'LEOPARD 5'
    
    'BYD Seal 06 GT | Electric | China 🇨🇳'
    → 'BYD Seal 06 GT'
    """
    if not title:
        return title
    
    clean = title
    
    # 1. Remove everything after pipe separators (RSS metadata)
    clean = clean.split('|')[0].strip()
    
    # 2. Remove emoji flags and vehicle emoji
    clean = re.sub(r'[\U0001F1E0-\U0001F1FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF]+', '', clean)
    
    # 3. Remove price patterns: $37,900  €45,000  £30,000  CNY 400,000
    clean = re.sub(r'[\$€£]\s*[\d,]+(?:\.\d+)?', '', clean)
    clean = re.sub(r'\b(?:CNY|USD|EUR|GBP|RMB)\s*[\d,]+(?:\.\d+)?', '', clean, flags=re.IGNORECASE)
    
    # 4. Remove range/spec patterns: 1310km, 500mi, 300kW, 400hp
    clean = re.sub(r'\b\d+(?:\.\d+)?\s*(?:km|mi|kw|hp|kwh|nm|mph|kph)\b', '', clean, flags=re.IGNORECASE)
    
    # 5. Remove common RSS descriptor words
    descriptors = [
        r'\brange\b', r'\bstarting\s+price\b', r'\bprice\b', r'\boverview\b',
        r'\bwalk\s*around\b', r'\bwalkaround\b', r'\bspecs\b', r'\bspecifications\b',
        r'\bfeatures\b', r'\bdetails\b', r'\bhighlights\b', r'\blaunch\b',
        r'\bunveiled\b', r'\brevealed\b', r'\bannounced\b', r'\bofficial\b',
        r'\bnew\b', r'\ball\s*new\b',
    ]
    for desc in descriptors:
        clean = re.sub(desc, '', clean, flags=re.IGNORECASE)
    
    # 6. Remove country names that are metadata, not brand/model
    countries = [
        r'\bChina\b', r'\bGermany\b', r'\bJapan\b', r'\bKorea\b', r'\bUSA\b',
        r'\bUS\b', r'\bUK\b', r'\bIndia\b', r'\bSweden\b', r'\bFrance\b',
        r'\bItaly\b', r'\bSpain\b',
    ]
    for country in countries:
        clean = re.sub(country, '', clean, flags=re.IGNORECASE)
    
    # 7. Collapse whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    return clean


class EntityCheckResult:
    """Result of entity validation."""
    
    def __init__(self):
        self.is_valid = True
        self.source_entities: dict = {}
        self.generated_entities: dict = {}
        self.mismatches: list[str] = []
        self.auto_fixed = False
        self.fixed_html: Optional[str] = None
    
    def __repr__(self):
        status = "✅ PASS" if self.is_valid else "❌ FAIL"
        return f"EntityCheck({status}, mismatches={self.mismatches})"


def extract_entities(title: str) -> dict:
    """
    Extract key automotive entities from a title string.
    
    Returns dict with:
    - year: "2025"
    - brand: "BYD"
    - model_name: "Leopard 8"  (the critical piece — includes number)
    - full_name: "2025 BYD Leopard 8"
    - powertrain: "PHEV" / "EV" / etc.
    """
    if not title:
        return {}
    
    # Clean RSS metadata before extraction
    title = clean_source_title(title)
    
    result = {}
    
    # 1. Extract year
    year_match = _YEAR_PATTERN.search(title)
    if year_match:
        result['year'] = year_match.group(1)
    
    # 2. Extract brand (case-insensitive lookup)
    title_lower = title.lower()
    found_brand = None
    found_brand_pos = len(title)  # position in title, for model extraction
    
    # Sort by length desc to match "Fang Cheng Bao" before "BYD"
    for alias in sorted(BRAND_ALIASES.keys(), key=len, reverse=True):
        pos = title_lower.find(alias)
        if pos != -1:
            found_brand = BRAND_ALIASES[alias]
            found_brand_pos = pos
            break
    
    if found_brand:
        result['brand'] = found_brand
    
    # 3. Extract model name (the most important piece)
    # Strategy: take the part of the title after the brand 
    # and before common suffixes (Review, PHEV, EV, etc.)
    model_name = _extract_model_name(title, found_brand, found_brand_pos)
    if model_name:
        result['model_name'] = model_name
    
    # 4. Extract powertrain type
    pt_match = re.search(r'\b(PHEV|BEV|EV|EREV|HEV|ICE|Hybrid|Electric|Diesel)\b', title, re.IGNORECASE)
    if pt_match:
        result['powertrain'] = pt_match.group(1).upper()
    
    # 5. Build full canonical name
    parts = []
    if result.get('year'):
        parts.append(result['year'])
    if result.get('brand'):
        parts.append(result['brand'])
    if result.get('model_name'):
        parts.append(result['model_name'])
    result['full_name'] = ' '.join(parts)
    
    return result


def _extract_model_name(title: str, brand: Optional[str], brand_pos: int) -> Optional[str]:
    """
    Extract the model name + number from a title, after the brand.
    
    "2025 BYD Leopard 8 PHEV 7-Seater Review" → "Leopard 8"
    "ZEEKR 7X Review" → "7X"
    "2025 BYD Fang Cheng Bao Leopard 8" → "Leopard 8"
    """
    # Remove year
    clean = re.sub(r'\b20[2-3]\d\b', '', title).strip()
    
    # Remove brand (and sub-brand if present)
    if brand:
        # Also remove sub-brands: "Fang Cheng Bao" for BYD
        sub_brands = {
            'BYD': ['Fang Cheng Bao', 'Yangwang', 'Denza'],
            'Geely': ['ZEEKR', 'Lynk & Co', 'Smart'],
            'SAIC': ['IM Motors', 'Rising Auto', 'MG', 'MAXUS'],
            'Changan': ['Deepal', 'Avatr'],
            'Stellantis': ['Peugeot', 'Citroen', 'Fiat', 'Alfa Romeo', 'Jeep', 'Dodge'],
        }
        
        for sb in sub_brands.get(brand, []):
            clean = re.sub(re.escape(sb), '', clean, flags=re.IGNORECASE).strip()
        
        clean = re.sub(re.escape(brand), '', clean, flags=re.IGNORECASE).strip()
    
    # Remove common suffixes
    suffixes = [
        r'\bReview\b', r'\bTest\b', r'\bDrive\b', r'\bFirst Look\b',
        r'\bFirst Drive\b', r'\bWalkaround\b', r'\bWalk\s*Around\b',
        r'\bInterior\b', r'\bExterior\b',
        r'\bPHEV\b', r'\bBEV\b', r'\bEREV\b', r'\bHEV\b', r'\bElectric\b',
        r'\bHybrid\b', r'\bDiesel\b', r'\bGasoline\b',
        r'\b\d+-Seater\b', r'\bSeater\b',
        r'\bAll-Wheel Drive\b', r'\bAWD\b', r'\bFWD\b', r'\bRWD\b', r'\b4WD\b',
        r'\bLong Range\b', r'\bStandard Range\b', r'\bPerformance\b',
        r'\bPro\b', r'\bMax\b', r'\bPlus\b', r'\bUltra\b', r'\bLaunch Edition\b',
        r'\bOverview\b', r'\bSpecs\b', r'\bSpecifications\b',
        r'\bFeatures\b', r'\bDetails\b', r'\bHighlights\b',
        r'\bStarting Price\b', r'\bPrice\b', r'\bRange\b',
        r'\bUnveiled\b', r'\bRevealed\b', r'\bAnnounced\b', r'\bOfficial\b',
        r'\bEV\b',
    ]
    for suffix in suffixes:
        clean = re.sub(suffix, '', clean, flags=re.IGNORECASE).strip()
    
    # Remove prices, ranges with units, emoji, and country names left over
    clean = re.sub(r'[\$€£]\s*[\d,]+', '', clean)  # prices
    clean = re.sub(r'\b\d+(?:\.\d+)?\s*(?:km|mi|kw|hp|kwh|nm)\b', '', clean, flags=re.IGNORECASE)  # specs
    clean = re.sub(r'[\U0001F1E0-\U0001F1FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF]+', '', clean)  # emoji
    
    # Remove common separators and extra whitespace
    clean = re.sub(r'[:\-–—|/]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    if not clean:
        return None
    
    # The remaining text IS the model name (e.g., "Leopard 8", "7X", "Seal 06 GT")
    # Capitalize properly
    return clean.strip()


def validate_entities(source_title: str, generated_html: str) -> EntityCheckResult:
    """
    Compare entities from source title against entities in generated HTML.
    
    This is the main entry point for the validator.
    
    Returns EntityCheckResult with:
    - is_valid: True if entities match
    - mismatches: list of human-readable mismatch descriptions
    - fixed_html: auto-corrected HTML (if mismatches found)
    """
    result = EntityCheckResult()
    
    if not source_title or not generated_html:
        return result
    
    # Extract entities from source
    source = extract_entities(source_title)
    result.source_entities = source
    
    if not source.get('model_name'):
        logger.warning(f"Could not extract model name from source title: {source_title}")
        return result  # Can't validate without a model name
    
    # Extract the <h2> title from generated HTML
    h2_match = re.search(r'<h2[^>]*>(.*?)</h2>', generated_html, re.IGNORECASE | re.DOTALL)
    generated_title = h2_match.group(1) if h2_match else ''
    
    # Strip HTML tags from the extracted title  
    generated_title_clean = re.sub(r'<[^>]+>', '', generated_title).strip()
    
    # Extract entities from generated title
    generated = extract_entities(generated_title_clean)
    result.generated_entities = generated
    
    source_model = source.get('model_name', '').strip()
    generated_model = generated.get('model_name', '').strip()
    
    # ── Check 1: Model name must match ──
    if source_model and generated_model:
        if not _fuzzy_model_match(source_model, generated_model):
            result.is_valid = False
            result.mismatches.append(
                f"Model name mismatch: source='{source_model}' vs generated='{generated_model}'"
            )
            
            # Attempt auto-fix
            fixed = _auto_fix_entity(generated_html, generated_model, source_model)
            if fixed != generated_html:
                result.auto_fixed = True
                result.fixed_html = fixed
                logger.info(
                    f"✅ Entity auto-fix: replaced '{generated_model}' → '{source_model}' "
                    f"in generated article"
                )
    elif source_model and not generated_model:
        # Model name not found in generated title — check body
        if source_model.lower() not in generated_html.lower():
            result.is_valid = False
            result.mismatches.append(
                f"Source model '{source_model}' not found anywhere in generated article"
            )
    
    # ── Check 2: Year should match (if present in source) ──
    source_year = source.get('year')
    generated_year = generated.get('year')
    if source_year and generated_year and source_year != generated_year:
        result.is_valid = False
        result.mismatches.append(
            f"Year mismatch: source='{source_year}' vs generated='{generated_year}'"
        )
    
    # ── Check 3: Brand should match ──
    source_brand = source.get('brand', '').lower()
    generated_brand = generated.get('brand', '').lower()
    if source_brand and generated_brand and source_brand != generated_brand:
        result.is_valid = False
        result.mismatches.append(
            f"Brand mismatch: source='{source.get('brand')}' vs generated='{generated.get('brand')}'"
        )
    
    if result.mismatches:
        logger.warning(
            f"⚠️ Entity validation FAILED for '{source_title}': {result.mismatches}"
        )
    else:
        logger.info(f"✅ Entity validation passed for '{source_title}'")
    
    return result


def _fuzzy_model_match(source: str, generated: str) -> bool:
    """
    Check if two model names refer to the same vehicle.
    Case-insensitive, ignoring minor whitespace differences.
    
    "Leopard 8" vs "Leopard 8" → True
    "Leopard 8" vs "Leopard 7" → False
    "7X" vs "7X" → True
    "Seal 06 GT" vs "Seal 06GT" → True (whitespace)
    """
    # Normalize: lowercase, collapse whitespace
    s = re.sub(r'\s+', ' ', source.strip().lower())
    g = re.sub(r'\s+', ' ', generated.strip().lower())
    
    if s == g:
        return True
    
    # Also try without spaces (for "06 GT" vs "06GT" type mismatches)
    s_nospace = s.replace(' ', '')
    g_nospace = g.replace(' ', '')
    
    return s_nospace == g_nospace


def _auto_fix_entity(html: str, wrong: str, correct: str) -> str:
    """
    Replace wrong entity with correct entity throughout the HTML.
    Case-insensitive replacement, preserving original case pattern.
    """
    # Replace exact matches (case-insensitive)
    pattern = re.compile(re.escape(wrong), re.IGNORECASE)
    return pattern.sub(correct, html)


def inject_entity_warning(html: str, mismatches: list[str]) -> str:
    """
    Inject a visible warning banner into the article HTML about entity mismatches.
    This banner is visible in the admin preview but hidden on the public site.
    """
    issues_html = ''.join(f'<li>{m}</li>' for m in mismatches)
    warning = f"""
    <div class="entity-mismatch-warning" style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin-bottom: 20px;">
        <h4 style="color: #856404; margin-top: 0;">⚠️ Entity Mismatch Detected</h4>
        <p>The AI may have confused the vehicle name. Please verify before publishing:</p>
        <ul>{issues_html}</ul>
        <p><em>This article was auto-corrected. Please review the model name/number.</em></p>
    </div>
    """
    return warning + html


def build_entity_anchor(source_title: str) -> str:
    """
    Build a prompt anchor string from the source title.
    Used by article_generator.py to inject at the top and bottom of the prompt.
    
    Returns something like:
    MANDATORY VEHICLE NAME: "2025 BYD Leopard 8"
    - Brand: BYD
    - Model: Leopard 8
    You MUST use these EXACT names. Do NOT change numbers, letters, or words.
    """
    entities = extract_entities(source_title)
    
    if not entities.get('model_name'):
        return ""
    
    parts = [
        f'═══ MANDATORY VEHICLE IDENTITY (DO NOT ALTER) ═══',
        f'Source title: "{source_title}"',
    ]
    
    if entities.get('year'):
        parts.append(f'Year: {entities["year"]}')
    if entities.get('brand'):
        parts.append(f'Brand: {entities["brand"]}')
    if entities.get('model_name'):
        parts.append(f'Model: {entities["model_name"]}')
    
    parts.append(
        f'You MUST use the EXACT model name "{entities["model_name"]}" throughout the article. '
        f'Do NOT change any numbers, letters, or words in the vehicle name. '
        f'"{entities["model_name"]}" is NOT the same as any similar-sounding model.'
    )
    parts.append('═══════════════════════════════════════════════')
    
    return '\n'.join(parts)
