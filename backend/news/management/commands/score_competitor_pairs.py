"""
score_competitor_pairs management command.

Updates CompetitorPairLog.engagement_score_at_log for all entries
where the linked article has been published for 48+ hours.

Run nightly via cron or every 6h as a low-priority task.

Usage:
    python manage.py score_competitor_pairs
    python manage.py score_competitor_pairs --min-age 24   # 24h minimum age
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Update CompetitorPairLog engagement scores from published article data. "
        "Run nightly to feed the ML learning loop."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-age',
            type=int,
            default=48,
            help='Minimum article age in hours before scoring (default: 48)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=500,
            help='Maximum pairs to score per run (default: 500)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be scored without saving',
        )

    def handle(self, *args, **options):
        from news.models.system import CompetitorPairLog

        min_age_hours = options['min_age']
        limit = options['limit']
        dry_run = options['dry_run']

        cutoff = timezone.now() - timedelta(hours=min_age_hours)

        # Pairs that haven't been scored yet (or scored > 7 days ago for refresh)
        refresh_cutoff = timezone.now() - timedelta(days=7)
        qs = CompetitorPairLog.objects.filter(
            engagement_score_at_log__isnull=True,
            created_at__lte=cutoff,
        ) | CompetitorPairLog.objects.filter(
            engagement_scored_at__lte=refresh_cutoff,
            created_at__lte=cutoff,
        )
        qs = qs.select_related('article').order_by('created_at')[:limit]

        total = qs.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Found {total} CompetitorPairLog entries to score "
                f"(min_age={min_age_hours}h, limit={limit})"
            )
        )

        updated = 0
        skipped = 0
        now = timezone.now()

        for pair in qs:
            article = pair.article
            if not article:
                skipped += 1
                continue

            score = article.engagement_score
            if score is None:
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(
                    f"  [DRY-RUN] {pair.subject_make} {pair.subject_model} vs "
                    f"{pair.competitor_make} {pair.competitor_model} → "
                    f"engagement={score:.2f}"
                )
            else:
                pair.engagement_score_at_log = score
                pair.engagement_scored_at = now
                pair.save(update_fields=['engagement_score_at_log', 'engagement_scored_at'])

            updated += 1

        msg = (
            f"{'[DRY-RUN] ' if dry_run else ''}"
            f"Scored {updated} pairs, skipped {skipped} (no article or score)."
        )
        self.stdout.write(self.style.SUCCESS(msg))
        logger.info(f"score_competitor_pairs: {msg}")
