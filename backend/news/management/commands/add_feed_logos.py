"""
Management command to add RSS feed logos to pending articles without images.
"""
from django.core.management.base import BaseCommand
from news.models import PendingArticle
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Add RSS feed logos to pending articles that have no images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Find all RSS pending articles
        all_rss_articles = PendingArticle.objects.filter(rss_feed__isnull=False)
        
        # Filter articles without valid images
        articles_to_update = []
        for article in all_rss_articles:
            # Check if images is empty, None, or contains only empty strings
            if not article.images or article.images == [] or article.images == [''] or all(not img for img in article.images):
                articles_to_update.append(article)
        
        total = len(articles_to_update)
        self.stdout.write(f'\n📝 Found {total} RSS articles without valid images\n')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made\n'))
        
        updated = 0
        skipped = 0
        
        for article in articles_to_update:
            if article.rss_feed and article.rss_feed.logo_url:
                if dry_run:
                    self.stdout.write(
                        f'  Would update: {article.title[:60]} -> {article.rss_feed.logo_url}'
                    )
                else:
                    article.images = [article.rss_feed.logo_url]
                    article.save(update_fields=['images'])
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Updated: {article.title[:60]}')
                    )
                updated += 1
            else:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠ No logo for feed: {article.rss_feed.name if article.rss_feed else "Unknown"}')
                    )
                skipped += 1
        
        self.stdout.write('\n' + '='*60)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'\n✅ Would update {updated} articles'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully updated {updated} articles!'))
        
        if skipped > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  Skipped {skipped} articles (no feed logo)'))
        
        self.stdout.write('')
