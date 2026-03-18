"""
Management command: repair_compare_grids
----------------------------------------
Fixes malformed compare-grid HTML in existing articles where the AI
closed divs too early, leaving compare-row/compare-card elements as
siblings of the compare-grid instead of children inside it.

Usage:
    python manage.py repair_compare_grids            # dry-run (preview only)
    python manage.py repair_compare_grids --apply    # apply to DB
    python manage.py repair_compare_grids --apply --slug zeekr-8x-review  # single article
"""
import logging

from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Repair malformed compare-grid HTML in existing articles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            default=False,
            help='Apply changes to the database (default: dry-run)',
        )
        parser.add_argument(
            '--slug',
            type=str,
            default=None,
            help='Repair a single article by slug',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of articles to process',
        )

    def handle(self, *args, **options):
        from news.models import Article
        from ai_engine.modules.article_post_processor import _repair_compare_grid

        apply = options['apply']
        slug = options['slug']
        limit = options['limit']

        # Find articles that likely have broken compare-grids
        qs = Article.objects.filter(content__contains='compare-grid')
        if slug:
            qs = qs.filter(slug=slug)
        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f"Found {total} articles with compare-grid content")

        if apply:
            self.stdout.write(self.style.WARNING("⚡ APPLY MODE — changes will be saved to DB"))
        else:
            self.stdout.write(self.style.NOTICE("👀 DRY-RUN MODE — pass --apply to save changes"))

        fixed = 0
        skipped = 0

        for article in qs.iterator():
            original = article.content
            repaired = _repair_compare_grid(original)

            if repaired == original:
                skipped += 1
                continue

            fixed += 1
            self.stdout.write(
                f"  🔧 [{article.pk}] {article.slug} — compare-grid repaired"
                f" ({len(original)} → {len(repaired)} chars)"
            )

            if apply:
                with transaction.atomic():
                    Article.objects.filter(pk=article.pk).update(content=repaired)

        self.stdout.write("")
        self.stdout.write(f"Results: {fixed} repaired, {skipped} clean (no changes needed)")

        if fixed > 0 and not apply:
            self.stdout.write(self.style.WARNING(
                f"\n👆 Run with --apply to save {fixed} fixes to the database."
            ))
        elif fixed > 0 and apply:
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Successfully repaired {fixed} articles."
            ))
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ All articles already have valid compare-grid HTML!"))
