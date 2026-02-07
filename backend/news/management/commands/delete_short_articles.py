"""
Management command to delete short RSS pending articles.
"""
from django.core.management.base import BaseCommand
from news.models import PendingArticle
import re
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Delete RSS pending articles with less than 500 characters of content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-length',
            type=int,
            default=500,
            help='Minimum content length in characters (default: 500)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        min_length = options['min_length']
        dry_run = options['dry_run']
        
        self.stdout.write(f'\n🔍 Finding RSS articles with less than {min_length} characters...\n')
        
        # Find short articles
        short_articles = []
        all_rss_articles = PendingArticle.objects.filter(
            rss_feed__isnull=False,
            status='pending'
        )
        
        for article in all_rss_articles:
            # Strip HTML tags to get plain text length
            plain_text = re.sub(r'<[^>]+>', '', article.content)
            plain_text = plain_text.strip()
            
            if len(plain_text) < min_length:
                short_articles.append({
                    'id': article.id,
                    'title': article.title,
                    'length': len(plain_text),
                    'feed': article.rss_feed.name if article.rss_feed else 'Unknown'
                })
        
        total = len(short_articles)
        self.stdout.write(f'📊 Found {total} short articles\n')
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ No short articles to delete!'))
            return
        
        # Show articles
        self.stdout.write('Articles to delete:')
        for article in short_articles[:10]:
            self.stdout.write(
                f"  • [{article['feed']}] {article['title'][:60]} ({article['length']} chars)"
            )
        
        if total > 10:
            self.stdout.write(f'  ... and {total - 10} more')
        
        if dry_run:
            self.stdout.write('\n' + self.style.WARNING('🔍 DRY RUN - No articles deleted'))
            return
        
        # Delete articles
        self.stdout.write('\n🗑️  Deleting articles...')
        article_ids = [a['id'] for a in short_articles]
        deleted_count, _ = PendingArticle.objects.filter(id__in=article_ids).delete()
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully deleted {deleted_count} short articles!'))
