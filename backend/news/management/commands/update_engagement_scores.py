"""
Management command to update engagement scores for published articles.

Usage:
    python manage.py update_engagement_scores          # last 30 days
    python manage.py update_engagement_scores --all    # all articles
    python manage.py update_engagement_scores --days 7 # last 7 days
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Recalculate engagement scores for published articles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all', action='store_true',
            help='Recalculate for all published articles (default: last 30 days)'
        )
        parser.add_argument(
            '--days', type=int, default=30,
            help='Days to look back (default: 30)'
        )

    def handle(self, *args, **options):
        from ai_engine.modules.engagement_scorer import update_engagement_scores

        force_all = options['all']
        days = options['days']

        self.stdout.write(f"📊 Updating engagement scores...")
        if force_all:
            self.stdout.write("   Mode: ALL published articles")
        else:
            self.stdout.write(f"   Mode: articles from last {days} days")

        stats = update_engagement_scores(days_back=days, force_all=force_all)

        self.stdout.write(self.style.SUCCESS(
            f"✅ Done! Updated {stats['updated']}/{stats['total_eligible']} articles. "
            f"Avg: {stats['avg_score']}/10, "
            f"Range: {stats['min_score']} – {stats['max_score']}"
        ))
