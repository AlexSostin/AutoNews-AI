"""
Normalize brand names in VehicleSpecs and CarSpecification tables.

Fixes case variants like 'ZEEKR', 'zeekr', 'Zeekr' → canonical form from BRAND_DISPLAY_NAMES.

Usage:
    python manage.py normalize_makes           # preview only (dry-run)
    python manage.py normalize_makes --apply   # apply changes to DB
"""
from django.core.management.base import BaseCommand
from news.models.vehicles import VehicleSpecs
from news.models import CarSpecification
from news.models.vehicles import normalize_make
from collections import defaultdict


class Command(BaseCommand):
    help = 'Normalize make/brand names in VehicleSpecs and CarSpecification'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Actually apply changes (default is dry-run preview)',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        mode = 'APPLY' if apply else 'DRY-RUN'
        self.stdout.write(f'\n🔧 normalize_makes [{mode}]\n{"=" * 50}')

        total_fixed = 0

        # ── VehicleSpecs ──────────────────────────────────────────────
        self.stdout.write('\n📦 VehicleSpecs:')
        vs_changes = defaultdict(list)  # old_make → [new_make, count]

        for vs in VehicleSpecs.objects.exclude(make='').order_by('make'):
            normalized = normalize_make(vs.make)
            if normalized != vs.make:
                vs_changes[vs.make].append((normalized, vs.id))

        if not vs_changes:
            self.stdout.write('  ✅ All makes already normalized.')
        else:
            for old_make, entries in sorted(vs_changes.items()):
                new_make = entries[0][0]
                ids = [e[1] for e in entries]
                self.stdout.write(
                    self.style.WARNING(
                        f'  "{old_make}" → "{new_make}"  ({len(ids)} records)'
                    )
                )
                if apply:
                    updated = VehicleSpecs.objects.filter(id__in=ids).update(make=new_make)
                    total_fixed += updated

        # ── CarSpecification ─────────────────────────────────────────
        self.stdout.write('\n📄 CarSpecification:')
        cs_changes = defaultdict(list)

        for cs in CarSpecification.objects.exclude(make='').order_by('make'):
            normalized = normalize_make(cs.make)
            if normalized != cs.make:
                cs_changes[cs.make].append((normalized, cs.id))

        if not cs_changes:
            self.stdout.write('  ✅ All makes already normalized.')
        else:
            for old_make, entries in sorted(cs_changes.items()):
                new_make = entries[0][0]
                ids = [e[1] for e in entries]
                self.stdout.write(
                    self.style.WARNING(
                        f'  "{old_make}" → "{new_make}"  ({len(ids)} records)'
                    )
                )
                if apply:
                    updated = CarSpecification.objects.filter(id__in=ids).update(make=new_make)
                    total_fixed += updated

        # ── Summary ──────────────────────────────────────────────────
        self.stdout.write(f'\n{"=" * 50}')
        if apply:
            self.stdout.write(self.style.SUCCESS(f'✅ Fixed {total_fixed} records in DB'))
        else:
            all_changes = len(vs_changes) + len(cs_changes)
            if all_changes:
                self.stdout.write(
                    self.style.WARNING(
                        f'\n⚠️  DRY-RUN: {all_changes} distinct make variants need fixing.\n'
                        f'   Run with --apply to update the database.'
                    )
                )
            else:
                self.stdout.write(self.style.SUCCESS('✅ Nothing to fix — all makes are normalized!'))
