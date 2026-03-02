"""
ML-powered car data analysis and health dashboard.

Usage:
    python manage.py analyze_car_data                # Run all checks
    python manage.py analyze_car_data --health       # ML model health report
    python manage.py analyze_car_data --duplicates   # Only duplicates
    python manage.py analyze_car_data --validate     # Only cross-validation
    python manage.py analyze_car_data --prices       # Only price anomalies
    python manage.py analyze_car_data --enrich       # Preview enrichment opportunities
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'ML-powered car data analysis: health, duplicates, validation, prices'

    def add_arguments(self, parser):
        parser.add_argument('--health', action='store_true',
                            help='Show ML model health report with maturity level')
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
            detect_price_anomalies, enrich_specs_from_similar,
            get_ml_health_report,
        )

        has_specific = any([options['health'], options['duplicates'],
                           options['validate'], options['prices'], options['enrich']])
        run_all = not has_specific

        # ── Health Report ───────────────────────────────
        if run_all or options['health']:
            report = get_ml_health_report()
            lvl = report['overall_level']

            self.stdout.write('\n' + '═' * 60)
            self.stdout.write(f'  {lvl["emoji"]} ML Model Health — Level {lvl["level"]}: {lvl["name"]}')
            self.stdout.write('═' * 60)
            self.stdout.write(f'  {lvl["description"]}')
            self.stdout.write(f'  Overall Score: {report["overall_score"]}/100\n')

            # Progress bar
            score = report['overall_score']
            filled = int(score / 5)  # 20 chars total
            bar = '█' * filled + '░' * (20 - filled)
            self.stdout.write(f'  [{bar}] {score}%\n')

            # Data stats
            stats = report['data_stats']
            self.stdout.write('  📊 Data:')
            self.stdout.write(f'     {stats["total_articles"]} articles | '
                              f'{stats["total_vehicle_specs"]} VehicleSpecs | '
                              f'{stats["total_car_specs"]} CarSpecs')
            self.stdout.write(f'     {stats["total_brands"]} brands | '
                              f'{stats["total_aliases"]} aliases | '
                              f'{stats["total_tags"]} tags')
            self.stdout.write(f'     Spec coverage: {stats["spec_coverage_pct"]}% | '
                              f'Completeness: {stats["spec_completeness_pct"]}%')
            self.stdout.write(f'     TF-IDF model: {"✅ trained" if stats["model_trained"] else "❌ not trained"} '
                              f'({stats["model_articles"]} articles)\n')

            # Feature scores
            self.stdout.write('  🔧 Feature Scores:')
            for name, data in report['feature_scores'].items():
                label = name.replace('_', ' ').title()
                mini_bar = '█' * (data['score'] // 10) + '░' * (10 - data['score'] // 10)
                self.stdout.write(
                    f'     {data["status"]} {label:<22s} [{mini_bar}] {data["score"]:>3d}%  {data["details"]}'
                )

            # Next level
            nxt = report.get('next_level')
            if nxt:
                self.stdout.write(f'\n  📈 Next: {nxt["emoji"]} {nxt["name"]} — '
                                  f'need {nxt["articles_needed"]} more articles')

            # Recommendations
            if report['recommendations']:
                self.stdout.write('\n  💡 Recommendations:')
                for r in report['recommendations']:
                    self.stdout.write(f'     {r}')

            self.stdout.write('')

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
