"""
Backfill seo_description for all existing articles.

Generates a concise, keyword-rich meta description (120-160 chars)
from CarSpecification data + VehicleSpecs, falling back to title-based generation.

Usage:
    python manage.py backfill_seo_descriptions          # dry-run (preview only)
    python manage.py backfill_seo_descriptions --apply   # actually update DB
"""
import re
from django.core.management.base import BaseCommand
from news.models import Article, CarSpecification


def _extract_year_from_title(title: str):
    """Extract 4-digit year from article title."""
    match = re.search(r'\b(20[2-3]\d)\b', title)
    return match.group(1) if match else ''


def _clean_hp(hp_str: str) -> str:
    """Normalize horsepower: '544 HPHP' -> '544', '500HP' -> '500'."""
    if not hp_str:
        return ''
    cleaned = re.sub(r'\s*(HP|hp|PS|ps|bhp|BHP)+', '', hp_str).strip()
    match = re.match(r'(\d[\d,]*)', cleaned)
    return match.group(1) if match else ''


def _detect_fuel_type(specs):
    """Detect fuel type from specs engine string."""
    if not specs:
        return ''
    engine = (specs.engine or '').lower()
    model_name = (specs.model_name or '').lower()
    combined = f"{engine} {model_name}"
    
    if any(kw in combined for kw in ('dm-i', 'dm-p', 'dmi', 'dmp')):
        return 'plug-in hybrid'
    if any(kw in combined for kw in ('phev', 'plug-in hybrid')):
        return 'plug-in hybrid'
    if any(kw in combined for kw in ('erev', 'range extender', 'range-extender')):
        return 'extended-range EV'
    if any(kw in combined for kw in ('electric', ' ev ', 'bev', 'kwh', 'battery electric')):
        return 'electric'
    if 'hybrid' in combined:
        return 'hybrid'
    return ''


def _detect_body_type(specs, title: str):
    """Detect body type from specs or title."""
    combined = f"{(specs.model_name if specs else '')} {title}".lower()
    if any(kw in combined for kw in ('suv', 'crossover')):
        return 'SUV'
    if any(kw in combined for kw in ('sedan', 'saloon')):
        return 'sedan'
    if any(kw in combined for kw in ('hatchback', 'hatch')):
        return 'hatchback'
    if any(kw in combined for kw in ('coupe', 'coupé', 'gt')):
        return 'coupe'
    if any(kw in combined for kw in ('truck', 'pickup', 'pick-up')):
        return 'pickup truck'
    if any(kw in combined for kw in ('mpv', 'minivan', 'van', 'seater')):
        return 'MPV'
    if any(kw in combined for kw in ('wagon', 'estate', 'touring')):
        return 'wagon'
    if any(kw in combined for kw in ('convertible', 'roadster', 'spider', 'cabriolet')):
        return 'convertible'
    return 'vehicle'


def _get_model_from_title(title: str, year: str) -> tuple:
    """Extract make and model from title as fallback."""
    # Remove year
    clean = title.replace(year, '').strip() if year else title
    # Remove common suffixes — but NOT hyphens in model names like DM-i, X-Trail
    clean = re.sub(r'\s*[:|].*$', '', clean)  # only colon/pipe, NOT hyphen
    clean = re.sub(r'\s+(Review|Specs|Price|Test|Drive|First Look|Unveiled).*$', '', clean, flags=re.IGNORECASE)
    
    words = clean.split()
    if len(words) >= 2:
        return words[0], ' '.join(words[1:])
    return '', clean


def generate_seo_description(article, specs=None) -> str:
    """
    Build a concise, keyword-rich SEO description.
    Target: 120-155 characters.
    """
    year = _extract_year_from_title(article.title)
    make = ''
    model = ''
    hp = ''
    fuel_type = ''
    body_type = ''
    range_info = ''
    price_info = ''

    if specs:
        make = (specs.make or '').strip()
        model = (specs.model or '').strip()
        # For model_name, use it if model is empty
        if not model and specs.model_name:
            # model_name often is "Make Model" so strip the make
            mn = specs.model_name.strip()
            if make and mn.lower().startswith(make.lower()):
                model = mn[len(make):].strip()
            else:
                model = mn
        hp = _clean_hp(specs.horsepower or '')
        fuel_type = _detect_fuel_type(specs)
        body_type = _detect_body_type(specs, article.title)
        
        # Extract range from price/engine fields
        engine_str = specs.engine or ''
        range_match = re.search(r'(\d{3,4})\s*km', engine_str)
        if range_match:
            range_info = f"{range_match.group(1)} km range"
        
        # Price
        price_str = specs.price or ''
        price_match = re.search(r'\$\s*([\d,]+)', price_str)
        if price_match:
            price_info = f"from ${price_match.group(1)}"

    # Fallback for make/model from title
    if not make or not model:
        t_make, t_model = _get_model_from_title(article.title, year)
        if not make:
            make = t_make
        if not model:
            model = t_model

    if not make:
        # Ultimate fallback
        return f"{article.title[:70]} — complete specs, performance, pricing & in-depth expert review."[:155]

    # Deduplicate: if model starts with make (e.g. make='BYD', model='BYD Leopard 5')
    if model and make and model.lower().startswith(make.lower() + ' '):
        model = model[len(make):].strip()
    # Also fix "AVATR AVATR 12" style duplication
    if model and ' ' in model:
        parts = model.split()
        if len(parts) >= 2 and parts[0].upper() == make.upper():
            model = ' '.join(parts[1:])

    # Build description with as many details as fit
    year_str = f"{year} " if year else ""
    hp_str = f" {hp}-HP" if hp else ""
    fuel_str = f" {fuel_type}" if fuel_type else ""
    body_str = f" {body_type}" if body_type and body_type != 'vehicle' else ""

    # Template 1: Full version with range/price (preferred, most keyword-rich)
    if range_info and price_info:
        desc = f"{year_str}{make} {model}{hp_str}{fuel_str}{body_str} review — {range_info}, {price_info}. Full specs & expert analysis."
    elif range_info:
        desc = f"{year_str}{make} {model}{hp_str}{fuel_str}{body_str} review — {range_info}. Complete specs, pricing & expert analysis."
    elif price_info:
        desc = f"{year_str}{make} {model}{hp_str}{fuel_str}{body_str} — {price_info}. Full specs, performance data & expert review."
    else:
        # Template 2: Standard version
        desc = f"{year_str}{make} {model}{hp_str}{fuel_str}{body_str} — complete specs, pricing, performance & in-depth expert review."

    # Extend if too short (< 120 chars)
    if len(desc) < 120:
        additions = [
            " Compare features, pros & cons.",
            " Detailed breakdown of what this car offers.",
            " Everything you need to know before buying.",
        ]
        for add in additions:
            if len(desc) + len(add) <= 155:
                desc = desc.rstrip('.') + '.' + add
                break

    # Trim if too long
    if len(desc) > 158:
        # Try to cut at last sentence boundary
        cut = desc[:155].rfind('.')
        if cut > 100:
            desc = desc[:cut + 1]
        else:
            desc = desc[:155] + '...'

    return desc


class Command(BaseCommand):
    help = 'Backfill seo_description for all articles using specs data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Actually write to database (default is dry-run)',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        mode = "APPLYING" if apply else "DRY-RUN (use --apply to write)"
        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write(f"  SEO Description Backfill — {mode}")
        self.stdout.write(f"{'=' * 70}\n")

        articles = Article.objects.all().order_by('-id')
        updated = 0
        skipped = 0
        too_short = 0

        for article in articles:
            specs = CarSpecification.objects.filter(article=article).first()
            new_seo = generate_seo_description(article, specs)

            old_seo = article.seo_description or ''
            changed = old_seo != new_seo

            if not changed:
                skipped += 1
                continue

            length = len(new_seo)
            length_marker = "✓" if 120 <= length <= 160 else ("⚠️ short" if length < 120 else "⚠️ long")
            if length < 120:
                too_short += 1

            self.stdout.write(
                f"  ID={article.id:3d} | {article.title[:55]}\n"
                f"    OLD: {old_seo[:90]}{'...' if len(old_seo) > 90 else ''}\n"
                f"    NEW: {new_seo}\n"
                f"    LEN: {length} chars {length_marker}\n"
            )

            if apply:
                # Use QuerySet.update() to bypass Article.save() method
                Article.objects.filter(id=article.id).update(seo_description=new_seo)

            updated += 1

        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write(f"  Results: {updated} updated | {skipped} unchanged | {too_short} under 120 chars")
        self.stdout.write(f"  Total articles: {articles.count()}")
        if not apply and updated > 0:
            self.stdout.write(f"  ⚠️  Run with --apply to write changes to DB")
        self.stdout.write(f"{'=' * 70}\n")
