"""
Backfill VehicleSpecs for existing articles using ML regex extraction.

Usage:
    python manage.py backfill_vehicle_specs          # ML-only (free, instant)
    python manage.py backfill_vehicle_specs --with-ai # ML + Gemini deep_specs
    python manage.py backfill_vehicle_specs --dry-run  # Preview without creating
    python manage.py backfill_vehicle_specs --all       # Re-process ALL articles
"""

from django.core.management.base import BaseCommand
from news.models import Article, VehicleSpecs, CarSpecification
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backfill VehicleSpecs from articles using ML regex extraction'

    def add_arguments(self, parser):
        parser.add_argument('--with-ai', action='store_true',
                            help='Also use Gemini to fill missing fields')
        parser.add_argument('--dry-run', action='store_true',
                            help='Preview what would be created without saving')
        parser.add_argument('--all', action='store_true',
                            help='Process all articles, not just missing ones')

    def handle(self, *args, **options):
        from ai_engine.modules.content_recommender import extract_specs_from_text

        dry_run = options['dry_run']
        with_ai = options['with_ai']
        process_all = options['all']

        # Find articles needing VehicleSpecs
        car_specs = CarSpecification.objects.filter(
            article__is_published=True,
            article__is_deleted=False
        ).exclude(make='').select_related('article')

        if not process_all:
            # Only articles that don't have VehicleSpecs yet
            articles_with_vs = VehicleSpecs.objects.filter(
                article__isnull=False
            ).values_list('article_id', flat=True)
            car_specs = car_specs.exclude(article_id__in=articles_with_vs)

        total = car_specs.count()
        self.stdout.write(f"\n{'[DRY RUN] ' if dry_run else ''}Processing {total} articles...\n")

        created = 0
        updated = 0
        errors = 0

        for cs in car_specs:
            article = cs.article
            try:
                # Step 1: ML regex extraction (free)
                ml_specs = extract_specs_from_text(article.title, article.content)
                ml_specs['make'] = cs.make
                ml_specs['model_name'] = cs.model or ''
                ml_specs['trim_name'] = cs.trim or ''
                ml_specs['article'] = article

                field_count = len(ml_specs) - 1  # Exclude 'article'
                status = f"  {'📋' if not dry_run else '👀'} [{article.id}] {cs.make} {cs.model} — {field_count} fields"

                if dry_run:
                    self.stdout.write(f"{status} (dry run)")
                    continue

                # Step 2: Optionally use Gemini for deeper specs
                if with_ai:
                    try:
                        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
                        deep_result = generate_deep_vehicle_specs(
                            article,
                            specs={'make': cs.make, 'model': cs.model, 'trim': cs.trim},
                            provider='gemini',
                        )
                        if deep_result:
                            self.stdout.write(f"{status} + AI ✅")
                            created += 1
                            continue
                    except Exception as e:
                        self.stdout.write(f"  ⚠️ AI failed: {e}, using ML-only")

                # Step 3: Create VehicleSpecs from ML data
                vs, was_created = VehicleSpecs.objects.update_or_create(
                    make=ml_specs.get('make', ''),
                    model_name=ml_specs.get('model_name', ''),
                    trim_name=ml_specs.get('trim_name', ''),
                    defaults={k: v for k, v in ml_specs.items()
                              if k not in ('make', 'model_name', 'trim_name')},
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                self.stdout.write(f"{status} {'✅ created' if was_created else '🔄 updated'}")

            except Exception as e:
                errors += 1
                self.stdout.write(f"  ❌ [{article.id}] Error: {e}")

        self.stdout.write(f"\n{'[DRY RUN] ' if dry_run else ''}Done! Created: {created}, Updated: {updated}, Errors: {errors}\n")
