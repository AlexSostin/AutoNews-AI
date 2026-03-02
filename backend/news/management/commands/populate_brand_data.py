"""
Populate Brand ownership data, logos, and metadata.

Usage: python manage.py populate_brand_data [--force]

Idempotent: safe to run multiple times.
- Creates new brands only if they don't exist
- Updates parent/country/logo_url only if not already set (unless --force)
- Creates missing BrandAlias entries
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from news.models import Brand
from news.models.vehicles import BrandAlias


# ─── Automotive Group Ownership Data ───────────────────────────────
# Verified against official corporate structures as of 2025.
# Format: (group_name, country, website, [(child_name, country, website), ...])

AUTOMOTIVE_GROUPS = [
    # ──── Chinese Groups ────
    {
        'name': 'Geely',
        'country': 'China',
        'website': 'https://global.geely.com',
        'description': 'Geely Auto Group — major Chinese automaker, parent of Volvo Cars, ZEEKR, Polestar, Lotus, Lynk & Co, and Smart (JV with Mercedes).',
        'children': [
            {'name': 'ZEEKR', 'country': 'China', 'website': 'https://www.zeekrglobal.com', 'description': 'Premium EV brand by Geely'},
            {'name': 'Smart', 'country': 'China', 'website': 'https://www.smart.com', 'description': 'Urban EV brand (Geely–Mercedes JV)'},
        ],
    },
    {
        'name': 'BYD',
        'country': 'China',
        'website': 'https://www.byd.com',
        'description': 'Build Your Dreams — world\'s largest EV manufacturer. Parent of DENZA, Fang Cheng Bao, and YangWang.',
        'children': [],
    },
    {
        'name': 'DongFeng',
        'country': 'China',
        'website': 'https://www.dongfeng-global.com',
        'description': 'DongFeng Motor Corporation — state-owned Chinese automaker, parent of VOYAH and Forthing.',
        'children': [
            {'name': 'VOYAH', 'country': 'China', 'website': 'https://www.voyah.com', 'description': 'Premium EV brand by DongFeng'},
        ],
    },
    {
        'name': 'NIO',
        'country': 'China',
        'website': 'https://www.nio.com',
        'description': 'Premium Chinese EV brand, known for battery swap technology.',
        'children': [],
    },
    {
        'name': 'XPENG',
        'country': 'China',
        'website': 'https://www.xpeng.com',
        'description': 'Chinese EV maker focused on smart driving and AI.',
        'children': [],
    },
    {
        'name': 'Xiaomi',
        'country': 'China',
        'website': 'https://www.mi.com',
        'description': 'Chinese tech company entering the EV market with SU7 sedan.',
        'children': [],
    },
    {
        'name': 'GWM',
        'country': 'China',
        'website': 'https://www.gwm-global.com',
        'description': 'Great Wall Motors — maker of Haval, Tank, and Ora brands.',
        'children': [],
    },
    {
        'name': 'IM',
        'country': 'China',
        'website': 'https://www.immotors.com',
        'description': 'IM Motors (Zhiji) — premium EV brand by SAIC, Alibaba, and Zhangjiang Hi-Tech.',
        'children': [],
    },
    {
        'name': 'Avatr',
        'country': 'China',
        'website': 'https://www.avatr.com',
        'description': 'Premium EV brand by Changan, Huawei, and CATL.',
        'children': [],
    },
    {
        'name': 'ArcFox',
        'country': 'China',
        'website': 'https://www.arcfox.com',
        'description': 'Premium EV brand by BAIC Group.',
        'children': [],
    },

    # ──── Japanese Groups ────
    {
        'name': 'Toyota',
        'country': 'Japan',
        'website': 'https://www.toyota.com',
        'description': 'Toyota Motor Corporation — world\'s largest automaker by sales. Parent of Lexus.',
        'children': [],
    },
]

# ─── Brand Aliases ─────────────────────────────────────────────────
# Format: (alias, canonical_name, model_prefix)
# model_prefix='' for simple name replacement
BRAND_ALIASES = [
    # DongFeng → VOYAH
    ('DongFeng', 'VOYAH', ''),
    ('DongFeng VOYAH', 'VOYAH', ''),
    ('Dongfeng VOYAH', 'VOYAH', ''),
    ('Dongfeng', 'VOYAH', ''),
    # Huawei → Avatr
    ('Huawei', 'Avatr', ''),
    # Great Wall → GWM
    ('Great Wall', 'GWM', ''),
    ('Great Wall Motors', 'GWM', ''),
    # Geely sub-brands
    ('Geely ZEEKR', 'ZEEKR', ''),
    # SAIC → IM
    ('SAIC', 'IM', ''),
    ('Zhiji', 'IM', ''),
    # BYD sub-brand extraction
    ('BYD', 'DENZA', 'Denza'),  # BYD + model starts with "Denza" → DENZA
    # NIO alternate names
    ('Nio', 'NIO', ''),
    # XPeng variations
    ('Xpeng', 'XPENG', ''),
    ('XPeng', 'XPENG', ''),
]


class Command(BaseCommand):
    help = 'Populate brand ownership data, logos, and metadata'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Force update even if data already exists',
        )

    def handle(self, *args, **options):
        force = options['force']
        created_brands = 0
        updated_brands = 0
        created_aliases = 0

        for group_data in AUTOMOTIVE_GROUPS:
            # Create or get the parent brand
            parent, was_created = self._ensure_brand(group_data, force=force)
            if was_created:
                created_brands += 1
            elif force:
                updated_brands += 1

            # Create child brands
            for child_data in group_data.get('children', []):
                child, was_created = self._ensure_brand(child_data, parent=parent, force=force)
                if was_created:
                    created_brands += 1
                elif force:
                    updated_brands += 1

        # Create aliases
        for alias_name, canonical, prefix in BRAND_ALIASES:
            _, was_created = BrandAlias.objects.get_or_create(
                alias=alias_name,
                model_prefix=prefix,
                defaults={'canonical_name': canonical},
            )
            if was_created:
                created_aliases += 1
                self.stdout.write(f'  + Alias: {alias_name} → {canonical}')

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Done! Brands: {created_brands} created, {updated_brands} updated. '
            f'Aliases: {created_aliases} created.'
        ))

        # Print ownership tree
        self.stdout.write('\n📊 Brand Ownership Tree:')
        for brand in Brand.objects.filter(parent__isnull=True).order_by('name'):
            children = brand.sub_brands.all().order_by('name')
            if children.exists():
                child_names = ', '.join(c.name for c in children)
                self.stdout.write(f'  🏢 {brand.name} ({brand.country}) → [{child_names}]')
            else:
                self.stdout.write(f'  🚗 {brand.name} ({brand.country})')

    def _ensure_brand(self, data, parent=None, force=False):
        """Create or update a brand from data dict. Returns (brand, was_created)."""
        name = data['name']
        defaults = {
            'slug': slugify(name),
            'country': data.get('country', ''),
            'website': data.get('website', ''),
            'description': data.get('description', ''),
        }

        brand, created = Brand.objects.get_or_create(
            name=name,
            defaults=defaults,
        )

        if created:
            self.stdout.write(f'  + Created brand: {name}')
            if parent:
                brand.parent = parent
                brand.save(update_fields=['parent'])
                self.stdout.write(f'    ↳ Parent: {parent.name}')
            return brand, True

        # Brand exists — update only empty fields (or all if --force)
        updated_fields = []
        if (not brand.country or force) and data.get('country'):
            brand.country = data['country']
            updated_fields.append('country')
        if (not brand.website or force) and data.get('website'):
            brand.website = data['website']
            updated_fields.append('website')
        if (not brand.description or force) and data.get('description'):
            brand.description = data['description']
            updated_fields.append('description')
        if parent and (not brand.parent or force):
            brand.parent = parent
            updated_fields.append('parent')

        if updated_fields:
            brand.save(update_fields=updated_fields)
            self.stdout.write(f'  ✏️  Updated {name}: {", ".join(updated_fields)}')
            return brand, False

        self.stdout.write(f'  ⏭ {name}: already up to date')
        return brand, False
