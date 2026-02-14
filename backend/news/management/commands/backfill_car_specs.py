"""
Backfill CarSpecification make/model fields from model_name.

Older records only have model_name (e.g. "BYD Leopard 8") but empty make/model.
This command parses model_name to populate make and model fields.
"""
from django.core.management.base import BaseCommand
from news.models import CarSpecification


# Known automotive brands for matching
KNOWN_BRANDS = [
    'BYD', 'Geely', 'XPeng', 'Xpeng', 'NIO', 'Nio', 'Zeekr', 'ZEEKR',
    'Li Auto', 'Li', 'VOYAH', 'Voyah', 'Denza', 'DENZA',
    'DongFeng', 'Dongfeng', 'Changan', 'CHANGAN', 'GAC', 'Aion',
    'Great Wall', 'Haval', 'Tank', 'Wey', 'WEY',
    'MG', 'SAIC', 'Chery', 'Jetour', 'Omoda', 'Jaecoo',
    'Honda', 'Toyota', 'Mazda', 'Nissan', 'Subaru', 'Mitsubishi',
    'Hyundai', 'Kia', 'Genesis',
    'BMW', 'Mercedes', 'Mercedes-Benz', 'Audi', 'Volkswagen', 'VW', 'Porsche',
    'Ford', 'Chevrolet', 'Tesla', 'Rivian', 'Lucid',
    'Volvo', 'Polestar', 'Lotus', 'Xiaomi', 'Huawei', 'AITO',
    'Smart', 'Lynk & Co', 'Lynk', 'FAW', 'Bestune', 'BAIC', 'JAC',
    'Leapmotor', 'Neta', 'Seres', 'iCAR', 'IM Motors',
]


class Command(BaseCommand):
    help = 'Backfill CarSpecification make/model from model_name'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show changes without saving')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Find specs with empty make but non-empty model_name
        specs = CarSpecification.objects.filter(make='').exclude(model_name='')
        
        if not specs.exists():
            self.stdout.write(self.style.SUCCESS('✅ No specs need backfilling!'))
            return

        self.stdout.write(f'\n🔍 Found {specs.count()} specs to backfill:\n')
        
        updated = 0
        for spec in specs:
            name = spec.model_name.strip()
            make, model = self._parse_brand_model(name)
            
            if make:
                self.stdout.write(
                    f'  "{name}" → make="{make}", model="{model}"'
                )
                if not dry_run:
                    spec.make = make
                    spec.model = model
                    spec.save(update_fields=['make', 'model'])
                updated += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠️ Could not parse: "{name}"')
                )

        action = "Would update" if dry_run else "Updated"
        self.stdout.write(self.style.SUCCESS(f'\n✅ {action} {updated}/{specs.count()} specs'))

    def _parse_brand_model(self, model_name: str) -> tuple:
        """Parse "BYD Leopard 8" → ("BYD", "Leopard 8")"""
        # Sort brands by length (longer first) to match "Li Auto" before "Li"
        sorted_brands = sorted(KNOWN_BRANDS, key=len, reverse=True)
        
        for brand in sorted_brands:
            if model_name.lower().startswith(brand.lower()):
                remainder = model_name[len(brand):].strip()
                if remainder:
                    return brand, remainder
                    
        # Fallback: first word is brand, rest is model
        parts = model_name.split(None, 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        
        return '', model_name
