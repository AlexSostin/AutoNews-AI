"""
Django management command to scan RSS feeds and create pending articles.

Usage:
    python manage.py scan_rss_feeds --all
    python manage.py scan_rss_feeds --feed-id 5
    python manage.py scan_rss_feeds --dry-run
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from news.models import RSSFeed
from ai_engine.modules.rss_aggregator import RSSAggregator


class Command(BaseCommand):
    help = 'Scan RSS feeds and create pending articles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Scan all enabled RSS feeds',
        )
        parser.add_argument(
            '--feed-id',
            type=int,
            help='Scan specific RSS feed by ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test mode - fetch feeds but don\'t create articles',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Maximum entries to process per feed (default: 10)',
        )

    def handle(self, *args, **options):
        aggregator = RSSAggregator()
        
        # Determine which feeds to scan
        if options['feed_id']:
            feeds = RSSFeed.objects.filter(id=options['feed_id'])
            if not feeds.exists():
                self.stdout.write(self.style.ERROR(f'RSS Feed with ID {options["feed_id"]} not found'))
                return
        elif options['all']:
            feeds = RSSFeed.objects.filter(is_enabled=True)
        else:
            self.stdout.write(self.style.ERROR('Please specify --all or --feed-id'))
            return
        
        if not feeds.exists():
            self.stdout.write(self.style.WARNING('No RSS feeds found'))
            return
        
        self.stdout.write(f'\n📡 Scanning {feeds.count()} RSS feed(s)...\n')
        
        total_created = 0
        
        for feed in feeds:
            self.stdout.write(f'\n🔍 Processing: {feed.name}')
            self.stdout.write(f'   URL: {feed.feed_url}')
            
            if options['dry_run']:
                self.stdout.write(self.style.WARNING('   [DRY RUN MODE]'))
                # Just fetch and parse, don't create articles
                feed_data = aggregator.fetch_feed(feed.feed_url)
                if feed_data:
                    self.stdout.write(self.style.SUCCESS(f'   ✓ Found {len(feed_data.entries)} entries'))
                    for i, entry in enumerate(feed_data.entries[:options['limit']], 1):
                        title = entry.get('title', 'Untitled')
                        self.stdout.write(f'     {i}. {title[:70]}')
                else:
                    self.stdout.write(self.style.ERROR('   ✗ Failed to fetch feed'))
            else:
                # Process feed and create articles
                try:
                    created = aggregator.process_feed(feed, limit=options['limit'])
                    total_created += created
                    
                    if created > 0:
                        self.stdout.write(self.style.SUCCESS(f'   ✓ Created {created} pending article(s)'))
                    else:
                        self.stdout.write(self.style.WARNING('   ⚠ No new articles (all duplicates or insufficient content)'))
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   ✗ Error: {e}'))
        
        if not options['dry_run']:
            self.stdout.write(f'\n✅ Scan complete! Total articles created: {total_created}\n')
        else:
            self.stdout.write(f'\n✅ Dry run complete! (No articles created)\n')
