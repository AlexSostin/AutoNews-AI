"""
Management command: cleanup_vehicle_specs

Removes VehicleSpecs entries that have zero useful spec fields —
typically entries auto-created from article titles with no real data.

Usage:
    python manage.py cleanup_vehicle_specs          # dry-run (preview)
    python manage.py cleanup_vehicle_specs --execute # actually delete
"""
from django.core.management.base import BaseCommand
from news.models.vehicles import VehicleSpecs


# Key fields that make a VehicleSpec "real"
KEY_FIELDS = [
    'power_hp', 'power_kw', 'torque_nm', 'battery_kwh',
    'range_km', 'range_wltp', 'range_epa', 'range_cltc',
    'acceleration_0_100', 'top_speed_kmh', 'price_from',
    'weight_kg', 'length_mm',
]


class Command(BaseCommand):
    help = 'Remove VehicleSpecs entries with zero useful spec fields (garbage from titles)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Actually delete entries. Without this flag, runs in dry-run mode.',
        )
        parser.add_argument(
            '--min-fields',
            type=int,
            default=1,
            help='Minimum number of key fields to keep an entry (default: 1)',
        )

    def handle(self, *args, **options):
        execute = options['execute']
        min_fields = options['min_fields']
        
        total = VehicleSpecs.objects.count()
        
        # Find entries with zero key fields
        garbage = []
        real = []
        
        for spec in VehicleSpecs.objects.all().select_related('article'):
            filled = sum(1 for f in KEY_FIELDS if getattr(spec, f, None) is not None)
            if filled < min_fields:
                garbage.append(spec)
            else:
                real.append(spec)
        
        self.stdout.write(f"\n📊 VehicleSpecs Analysis:")
        self.stdout.write(f"  Total entries: {total}")
        self.stdout.write(f"  Real specs (≥{min_fields} key fields): {len(real)}")
        self.stdout.write(f"  Garbage (0 key fields): {len(garbage)}")
        self.stdout.write(f"  Cleanup ratio: {len(garbage)*100//total}%\n")
        
        if garbage:
            self.stdout.write(f"  Sample garbage entries:")
            for spec in garbage[:10]:
                art_title = spec.article.title[:50] if spec.article else 'no article'
                self.stdout.write(f"    ❌ {spec.make} {spec.model_name} (article: {art_title})")
            if len(garbage) > 10:
                self.stdout.write(f"    ... and {len(garbage)-10} more")
        
        if execute:
            ids = [s.id for s in garbage]
            deleted = VehicleSpecs.objects.filter(id__in=ids).delete()
            self.stdout.write(self.style.SUCCESS(f"\n✅ Deleted {deleted[0]} garbage VehicleSpecs entries."))
            self.stdout.write(f"  Remaining: {VehicleSpecs.objects.count()} entries")
        else:
            self.stdout.write(self.style.WARNING(f"\n⚠️  DRY RUN — no entries deleted."))
            self.stdout.write(f"  Run with --execute to actually delete {len(garbage)} entries.")
