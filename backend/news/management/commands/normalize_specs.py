"""
Normalize CarSpecification data:
- Standardize make names (Xpeng -> XPENG, Zeekr -> ZEEKR, etc.)
- Clean horsepower field to just numbers (e.g. "300 horsepower" -> "300 hp")
- Replace "None", "0", empty with "" for cleaner display
"""
import re
from django.core.management.base import BaseCommand
from news.models import CarSpecification


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


class Command(BaseCommand):
    help = 'Normalize CarSpecification make names and horsepower values'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would change')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specs = CarSpecification.objects.all()
        total = specs.count()
        make_fixes = 0
        hp_fixes = 0

        self.stdout.write(f'📊 Processing {total} CarSpecification records...\n')

        for spec in specs:
            changes = []

            # 1. Normalize make name
            make_lower = spec.make.lower().strip()
            canonical = MAKE_CANONICAL.get(make_lower)
            if canonical and spec.make != canonical:
                old_make = spec.make
                if not dry_run:
                    spec.make = canonical
                changes.append(f'make: "{old_make}" → "{canonical}"')
                make_fixes += 1

            # 2. Normalize horsepower
            hp = spec.horsepower or ''
            new_hp = self._normalize_hp(hp)
            if new_hp != hp:
                if not dry_run:
                    spec.horsepower = new_hp
                changes.append(f'hp: "{hp}" → "{new_hp}"')
                hp_fixes += 1

            # 3. Update model_name if make changed
            if changes and not dry_run:
                spec.model_name = f'{spec.make} {spec.model}'.strip()
                spec.save()

            if changes:
                self.stdout.write(
                    f'  [{spec.id}] {spec.model_name}: {" | ".join(changes)}'
                )

        prefix = '[DRY] ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ {prefix}Fixed {make_fixes} make names, {hp_fixes} horsepower values'
        ))

    def _normalize_hp(self, hp_str):
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
