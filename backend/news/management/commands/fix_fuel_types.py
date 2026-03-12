"""
Management command: fix_fuel_types

Auto-fills empty fuel_type in VehicleSpecs based on model_name and trim keywords.
Also fixes known data quality issues (Aito duplicated trims, wrong fuel types).

Usage:
    python manage.py fix_fuel_types --dry-run   # Preview changes
    python manage.py fix_fuel_types              # Apply changes
"""
from django.core.management.base import BaseCommand
from news.models.vehicles import VehicleSpecs
import re


# Keyword → fuel_type mapping (order matters — first match wins)
FUEL_TYPE_RULES = [
    # EREV / Range Extender
    (r'\bEREV\b', 'EREV'),
    (r'\bREV\b', 'EREV'),
    (r'\brange.?extender\b', 'EREV'),
    # PHEV / Plug-in Hybrid
    (r'\bPHEV\b', 'PHEV'),
    (r'\bDM[\s-]?i\b', 'PHEV'),
    (r'\bDM[\s-]?p\b', 'PHEV'),
    (r'\bPlug[\s-]?in\b', 'PHEV'),
    # Hybrid (non-plug-in)
    (r'\bHEV\b', 'Hybrid'),
    (r'\bHybrid\b', 'Hybrid'),
    # Pure EV
    (r'\bBEV\b', 'EV'),
    (r'\bEV\b', 'EV'),
    (r'\bElectric\b', 'EV'),
    # Gas / ICE
    (r'\bICE\b', 'Gas'),
    (r'\bDiesel\b', 'Diesel'),
    (r'\bTurbo\b', 'Gas'),  # weak signal but useful for otherwise empty
]

# Known data fixes: (id, field_updates)
AITO_FIXES = {
    79: {
        'trim_name': '',        # was '6' (wrong)
        'fuel_type': 'EREV',    # was 'Hybrid' (M7 REV is EREV)
    },
    82: {
        'model_name': 'M9 EREV',   # was 'M9 EREV 6-Seater' (duplication with trim)
        'trim_name': '6-Seater',   # keep this one
        'fuel_type': 'EREV',       # was empty
    },
    84: {
        'fuel_type': 'EREV',   # was 'EV' (M8 REV is range extender, not pure EV)
    },
}


class Command(BaseCommand):
    help = 'Auto-fill empty fuel_type and fix known data quality issues in VehicleSpecs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them',
        )
        parser.add_argument(
            '--skip-aito',
            action='store_true',
            help='Skip Aito-specific fixes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_aito = options['skip_aito']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN — no changes will be saved ===\n'))

        total_fixed = 0

        # ── Part 1: Fix known Aito issues ────────────────────────────────
        if not skip_aito:
            self.stdout.write(self.style.HTTP_INFO('\n── Fixing known Aito data issues ──'))
            for spec_id, updates in AITO_FIXES.items():
                try:
                    v = VehicleSpecs.objects.get(id=spec_id)
                    changes = []
                    for field, new_val in updates.items():
                        old_val = getattr(v, field)
                        if old_val != new_val:
                            changes.append(f'  {field}: {old_val!r} → {new_val!r}')
                            if not dry_run:
                                setattr(v, field, new_val)
                    if changes:
                        if not dry_run:
                            v.save(update_fields=list(updates.keys()))
                        self.stdout.write(
                            f'  ID {spec_id}: {v.make} {v.model_name}\n' +
                            '\n'.join(changes)
                        )
                        total_fixed += 1
                    else:
                        self.stdout.write(f'  ID {spec_id}: already correct')
                except VehicleSpecs.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'  ID {spec_id}: not found in DB'))

        # ── Part 2: Auto-fill empty fuel_type ─────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('\n── Auto-filling empty fuel_type ──'))
        from django.db.models import Q
        empty_fuel = VehicleSpecs.objects.filter(Q(fuel_type='') | Q(fuel_type__isnull=True))
        empty_count = empty_fuel.count()
        self.stdout.write(f'  Found {empty_count} entries with empty fuel_type')

        filled = 0
        skipped = 0
        for v in empty_fuel:
            # Search in model_name + trim_name combined
            search_text = f'{v.model_name} {v.trim_name or ""}'.strip()
            detected_fuel = None

            for pattern, fuel_type in FUEL_TYPE_RULES:
                if re.search(pattern, search_text, re.IGNORECASE):
                    detected_fuel = fuel_type
                    break

            # Secondary: check if battery exists (implies EV/PHEV)
            if not detected_fuel and v.battery_kwh and v.battery_kwh > 0:
                # Has battery but no keyword — likely EV
                detected_fuel = 'EV'

            if detected_fuel:
                if not dry_run:
                    v.fuel_type = detected_fuel
                    v.save(update_fields=['fuel_type'])
                self.stdout.write(
                    f'  ✓ {v.make} {v.model_name} → {detected_fuel}'
                    f'  (matched: "{search_text}")'
                )
                filled += 1
            else:
                skipped += 1

        # ── Summary ───────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('\n── Summary ──'))
        self.stdout.write(f'  Aito fixes: {total_fixed}')
        self.stdout.write(f'  fuel_type filled: {filled}/{empty_count}')
        self.stdout.write(f'  Remaining empty: {skipped}')

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  DRY RUN complete. Run without --dry-run to apply changes.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Done! Fixed {total_fixed + filled} entries total.'
            ))
