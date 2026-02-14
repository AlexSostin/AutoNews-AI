"""
Normalize CarSpecification data:
- Standardize make names (Xpeng -> XPENG, Zeekr -> ZEEKR, etc.)
- Clean horsepower field to just numbers (e.g. "300 horsepower" -> "300")
- Replace "None", "0", empty with "" for cleaner display
"""
from django.core.management.base import BaseCommand
from news.models import CarSpecification
from news.spec_extractor import normalize_make, normalize_hp, MAKE_CANONICAL


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
            canonical = normalize_make(spec.make)
            if canonical != spec.make:
                old_make = spec.make
                if not dry_run:
                    spec.make = canonical
                changes.append(f'make: "{old_make}" → "{canonical}"')
                make_fixes += 1

            # 2. Normalize horsepower
            hp = spec.horsepower or ''
            new_hp = normalize_hp(hp)
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
