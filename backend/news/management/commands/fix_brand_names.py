"""
Management command to normalize brand names across CarSpecification and VehicleSpecs.

Usage:
    python manage.py fix_brand_names          # Dry run (shows changes)
    python manage.py fix_brand_names --apply  # Apply changes
"""
from django.core.management.base import BaseCommand
from news.models import CarSpecification, VehicleSpecs


# Brand rename rules: old_make -> new_make
BRAND_RENAMES = {
    'DongFeng VOYAH': 'VOYAH',
    'Dongfeng VOYAH': 'VOYAH',
    'dongfeng voyah': 'VOYAH',
    'Zeekr': 'ZEEKR',
    'zeekr': 'ZEEKR',
}

# Fields that must be English-only (translate common Russian words)
RUSSIAN_TO_ENGLISH = {
    'передняя': 'front',
    'задняя': 'rear',
    'многорычажная': 'multi-link',
    'независимая': 'independent',
    'пневматическая': 'air',
    'подвеска': 'suspension',
    'ориентировочно': '',
    'примерно': '',
    'Топ с дроном': 'Top with Drone',
    'Базовая': 'Base',
    'Средняя': 'Mid',
    'Топовая': 'Top',
}


class Command(BaseCommand):
    help = 'Normalize brand names and clean non-English text in CarSpecification and VehicleSpecs'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Apply changes (default: dry run)')

    def handle(self, *args, **options):
        apply = options['apply']
        mode = 'APPLYING' if apply else 'DRY RUN'
        self.stdout.write(self.style.WARNING(f'\\n=== Brand Normalization ({mode}) ===\\n'))

        # 1. Fix brand names
        self._fix_brands(apply)

        # 2. Fix Russian text in VehicleSpecs string fields
        self._fix_russian_text(apply)

        # 3. Show summary of all unique makes
        self._show_brand_summary()

        if not apply:
            self.stdout.write(self.style.WARNING('\\n⚠️  Dry run. Use --apply to apply changes.'))

    def _fix_brands(self, apply):
        self.stdout.write(self.style.MIGRATE_HEADING('\\n--- Brand Renames ---'))

        for old_make, new_make in BRAND_RENAMES.items():
            # CarSpecification
            cs_count = CarSpecification.objects.filter(make=old_make).count()
            if cs_count > 0:
                self.stdout.write(f'  CarSpecification: "{old_make}" → "{new_make}" ({cs_count} records)')
                if apply:
                    CarSpecification.objects.filter(make=old_make).update(make=new_make)

            # VehicleSpecs
            vs_count = VehicleSpecs.objects.filter(make=old_make).count()
            if vs_count > 0:
                self.stdout.write(f'  VehicleSpecs: "{old_make}" → "{new_make}" ({vs_count} records)')
                if apply:
                    VehicleSpecs.objects.filter(make=old_make).update(make=new_make)

            if cs_count == 0 and vs_count == 0:
                pass  # Skip non-matching rules silently

    def _fix_russian_text(self, apply):
        self.stdout.write(self.style.MIGRATE_HEADING('\\n--- Russian Text Cleanup ---'))

        text_fields = ['trim_name', 'suspension_type', 'motor_placement',
                        'charging_time_fast', 'charging_time_slow', 'platform']

        fixed_count = 0
        for spec in VehicleSpecs.objects.all():
            changes = {}
            for field in text_fields:
                value = getattr(spec, field) or ''
                if not value:
                    continue

                new_value = value
                for ru, en in RUSSIAN_TO_ENGLISH.items():
                    if ru in new_value:
                        new_value = new_value.replace(ru, en).strip()

                # Clean up double spaces and leading/trailing separators
                new_value = ' '.join(new_value.split())
                new_value = new_value.strip(' —-,;')

                if new_value != value:
                    changes[field] = (value, new_value)

            if changes:
                fixed_count += 1
                self.stdout.write(f'  VehicleSpecs [{spec.id}] {spec.make} {spec.model_name} {spec.trim_name}:')
                for field, (old, new) in changes.items():
                    self.stdout.write(f'    {field}: "{old}" → "{new}"')
                    if apply:
                        setattr(spec, field, new)
                if apply:
                    spec.save(update_fields=list(changes.keys()))

        if fixed_count == 0:
            self.stdout.write('  No Russian text found.')
        else:
            self.stdout.write(f'  Total: {fixed_count} records {"fixed" if apply else "to fix"}')

    def _show_brand_summary(self):
        self.stdout.write(self.style.MIGRATE_HEADING('\\n--- Current Brands (after changes) ---'))

        # CarSpecification brands
        cs_makes = (
            CarSpecification.objects
            .exclude(make='')
            .values_list('make', flat=True)
            .distinct()
            .order_by('make')
        )
        self.stdout.write('  CarSpecification makes:')
        for make in cs_makes:
            count = CarSpecification.objects.filter(make=make).count()
            self.stdout.write(f'    {make} ({count} specs)')

        # VehicleSpecs brands
        vs_makes = (
            VehicleSpecs.objects
            .exclude(make='')
            .values_list('make', flat=True)
            .distinct()
            .order_by('make')
        )
        self.stdout.write('  VehicleSpecs makes:')
        for make in vs_makes:
            count = VehicleSpecs.objects.filter(make=make).count()
            self.stdout.write(f'    {make} ({count} specs)')
