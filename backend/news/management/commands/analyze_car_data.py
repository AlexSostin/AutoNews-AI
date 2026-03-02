"""
Find duplicate VehicleSpecs, validate data consistency, and detect price anomalies.

Usage:
    python manage.py analyze_car_data                # Run all checks
    python manage.py analyze_car_data --duplicates    # Only duplicates
    python manage.py analyze_car_data --validate      # Only cross-validation
    python manage.py analyze_car_data --prices        # Only price anomalies
    python manage.py analyze_car_data --enrich        # Preview enrichment opportunities
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'ML-powered car data analysis: duplicates, validation, price anomalies'

    def add_arguments(self, parser):
        parser.add_argument('--duplicates', action='store_true',
                            help='Find duplicate VehicleSpecs')
        parser.add_argument('--validate', action='store_true',
                            help='Cross-validate CarSpec vs VehicleSpecs')
        parser.add_argument('--prices', action='store_true',
                            help='Detect price anomalies')
        parser.add_argument('--enrich', action='store_true',
                            help='Preview data enrichment opportunities')
        parser.add_argument('--threshold', type=float, default=0.80,
                            help='Similarity threshold for duplicates (default: 0.80)')

    def handle(self, *args, **options):
        from ai_engine.modules.content_recommender import (
            find_duplicate_specs, validate_specs_consistency,
            detect_price_anomalies, enrich_specs_from_similar
        )

        run_all = not any([options['duplicates'], options['validate'],
                           options['prices'], options['enrich']])

        # ── Duplicates ──────────────────────────────────
        if run_all or options['duplicates']:
            self.stdout.write('\n' + '═' * 60)
            self.stdout.write('  🔍 VehicleSpecs Duplicate Detection')
            self.stdout.write('═' * 60 + '\n')

            dupes = find_duplicate_specs(threshold=options['threshold'])
            if dupes:
                for d in dupes:
                    a, b = d['spec_a'], d['spec_b']
                    self.stdout.write(
                        f"  ⚠️  [{a['id']}] {a['make']} {a['model']} "
                        f"↔ [{b['id']}] {b['make']} {b['model']} "
                        f"— similarity {d['score']:.1%}"
                    )
                self.stdout.write(f"\n  Total: {len(dupes)} potential duplicates\n")
            else:
                self.stdout.write('  ✅ No duplicates found\n')

        # ── Cross-Validation ────────────────────────────
        if run_all or options['validate']:
            self.stdout.write('\n' + '═' * 60)
            self.stdout.write('  ✅ CarSpec ↔ VehicleSpecs Validation')
            self.stdout.write('═' * 60 + '\n')

            mismatches = validate_specs_consistency()
            if mismatches:
                for m in mismatches:
                    self.stdout.write(
                        f"  ⚠️  [{m['article_id']}] {m['article_title']}\n"
                        f"      {m['field']}: CarSpec={m['carspec_value']} "
                        f"vs VehicleSpecs={m['vehiclespecs_value']} "
                        f"(diff {m['diff_percent']}%)"
                    )
                self.stdout.write(f"\n  Total: {len(mismatches)} mismatches\n")
            else:
                self.stdout.write('  ✅ All data consistent\n')

        # ── Price Anomalies ─────────────────────────────
        if run_all or options['prices']:
            self.stdout.write('\n' + '═' * 60)
            self.stdout.write('  💰 Price Anomaly Detection')
            self.stdout.write('═' * 60 + '\n')

            anomalies = detect_price_anomalies()
            if anomalies:
                for a in anomalies:
                    self.stdout.write(
                        f"  ⚠️  {a['make']} {a['model']}: ${a['price_usd']:,} "
                        f"— {a['reason']}"
                    )
                self.stdout.write(f"\n  Total: {len(anomalies)} anomalies\n")
            else:
                self.stdout.write('  ✅ All prices within normal range\n')

        # ── Enrichment Preview ──────────────────────────
        if run_all or options['enrich']:
            self.stdout.write('\n' + '═' * 60)
            self.stdout.write('  📊 Data Enrichment Opportunities')
            self.stdout.write('═' * 60 + '\n')

            from news.models import VehicleSpecs
            total_enrichable = 0

            for vs in VehicleSpecs.objects.filter(article__isnull=False):
                enrichments = enrich_specs_from_similar(vs.id, dry_run=True)
                if enrichments:
                    total_enrichable += 1
                    fields = ', '.join(enrichments.keys())
                    self.stdout.write(
                        f"  📋 [{vs.id}] {vs.make} {vs.model_name} "
                        f"— {len(enrichments)} fields: {fields}"
                    )

            if total_enrichable > 0:
                self.stdout.write(f"\n  Total: {total_enrichable} specs can be enriched\n")
            else:
                self.stdout.write('  ✅ All specs are fully filled\n')

        self.stdout.write('\n✅ Analysis complete!\n')
