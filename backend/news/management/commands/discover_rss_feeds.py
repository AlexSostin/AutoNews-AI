"""
Management command to discover automotive RSS feeds.

Usage:
    python manage.py discover_rss_feeds                   # Discover with license check
    python manage.py discover_rss_feeds --skip-license    # Faster: skip license checking
    python manage.py discover_rss_feeds --add-green       # Auto-add all green feeds
"""

from django.core.management.base import BaseCommand
from news.models import RSSFeed
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Discover automotive RSS feeds from curated sources'

    def add_arguments(self, parser):
        parser.add_argument('--skip-license', action='store_true', help='Skip license checking (faster)')
        parser.add_argument('--add-green', action='store_true', help='Auto-add feeds with green license status')

    def handle(self, *args, **options):
        from ai_engine.modules.feed_discovery import discover_feeds

        self.stdout.write("🔍 Discovering automotive RSS feeds...\n")

        check_license = not options['skip_license']
        results = discover_feeds(check_license=check_license)

        # Display results
        status_icons = {'green': '🟢', 'yellow': '🟡', 'red': '🔴', 'unchecked': '❓'}
        
        added_count = 0
        for r in results:
            icon = status_icons.get(r['license_status'], '❓')
            feed_status = '✅ Valid RSS' if r['feed_valid'] else '❌ No RSS'
            added_tag = ' [ALREADY ADDED]' if r['already_added'] else ''
            
            self.stdout.write(f"\n{icon} {r['name']}{added_tag}")
            self.stdout.write(f"   {feed_status} | {r['website_url']}")
            if r['feed_url']:
                self.stdout.write(f"   RSS: {r['feed_url']}")
                if r['feed_title']:
                    self.stdout.write(f"   Title: {r['feed_title']} ({r['entry_count']} entries)")
            
            # Auto-add green feeds if requested
            if (options['add_green'] and r['license_status'] == 'green' 
                    and r['feed_valid'] and not r['already_added'] and r['feed_url']):
                try:
                    feed = RSSFeed.objects.create(
                        name=r['name'],
                        feed_url=r['feed_url'],
                        website_url=r['website_url'],
                        source_type=r['source_type'],
                        is_enabled=True,
                        license_status=r['license_status'],
                        license_details=r['license_details'],
                    )
                    from django.utils import timezone
                    feed.license_checked_at = timezone.now()
                    feed.save(update_fields=['license_checked_at'])
                    added_count += 1
                    self.stdout.write(self.style.SUCCESS(f"   ➕ Added to database!"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Failed to add: {e}"))

        # Summary
        total = len(results)
        green = sum(1 for r in results if r['license_status'] == 'green')
        yellow = sum(1 for r in results if r['license_status'] == 'yellow')
        red = sum(1 for r in results if r['license_status'] == 'red')
        valid = sum(1 for r in results if r['feed_valid'])
        already = sum(1 for r in results if r['already_added'])

        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(f"📊 Total: {total} | Valid RSS: {valid} | Already added: {already}")
        self.stdout.write(f"🟢 Green: {green} | 🟡 Yellow: {yellow} | 🔴 Red: {red}")
        if added_count:
            self.stdout.write(self.style.SUCCESS(f"➕ Added {added_count} new feeds"))
