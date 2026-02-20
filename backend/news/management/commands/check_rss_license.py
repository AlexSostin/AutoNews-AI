"""
Management command to check content licensing for RSS feed sources.

Usage:
    python manage.py check_rss_license --feed-id 5
    python manage.py check_rss_license --all-unchecked
    python manage.py check_rss_license --all
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from news.models import RSSFeed
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check content licensing (robots.txt + Terms of Use) for RSS feed sources'

    def add_arguments(self, parser):
        parser.add_argument('--feed-id', type=int, help='Check a specific RSS feed by ID')
        parser.add_argument('--all-unchecked', action='store_true', help='Check all feeds with unchecked status')
        parser.add_argument('--all', action='store_true', help='Re-check all feeds')

    def handle(self, *args, **options):
        from ai_engine.modules.license_checker import check_content_license

        if options['feed_id']:
            feeds = RSSFeed.objects.filter(id=options['feed_id'])
            if not feeds.exists():
                self.stderr.write(f"RSS Feed with ID {options['feed_id']} not found")
                return
        elif options['all_unchecked']:
            feeds = RSSFeed.objects.filter(license_status='unchecked')
        elif options['all']:
            feeds = RSSFeed.objects.all()
        else:
            self.stderr.write("Please specify --feed-id, --all-unchecked, or --all")
            return

        total = feeds.count()
        self.stdout.write(f"🔍 Checking content license for {total} feed(s)...\n")

        for i, feed in enumerate(feeds, 1):
            self.stdout.write(f"\n[{i}/{total}] {feed.name}")
            
            url = feed.website_url or feed.feed_url
            if not url:
                self.stdout.write(self.style.WARNING(f"  ⚠️ No URL available, skipping"))
                continue

            self.stdout.write(f"  URL: {url}")

            try:
                result = check_content_license(url, source_type=feed.source_type)
                
                feed.license_status = result['status']
                feed.license_details = result['details']
                feed.license_checked_at = timezone.now()
                
                # Store safety checks breakdown
                safety_checks = result.get('safety_checks', {})
                feed.safety_checks = safety_checks
                
                # Auto-set image_policy based on image_rights check
                image_rights = safety_checks.get('image_rights', {})
                if image_rights.get('passed'):
                    feed.image_policy = 'original'
                else:
                    feed.image_policy = 'pexels_only'
                
                feed.save(update_fields=[
                    'license_status', 'license_details', 'license_checked_at',
                    'safety_checks', 'image_policy',
                ])

                status_icon = {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}.get(result['status'], '❓')
                self.stdout.write(f"  {status_icon} Status: {result['status'].upper()}")
                self.stdout.write(f"  📝 {result['details'][:200]}")
                
                # Show safety checks breakdown
                passed = sum(1 for c in safety_checks.values() if isinstance(c, dict) and c.get('passed'))
                total = len([c for c in safety_checks.values() if isinstance(c, dict)])
                self.stdout.write(f"  📊 Safety: {passed}/{total} checks passed")
                for check_name, check_data in safety_checks.items():
                    if isinstance(check_data, dict):
                        icon = '✅' if check_data.get('passed') else '❌'
                        self.stdout.write(f"     {icon} {check_name}: {check_data.get('detail', '')[:100]}")
                self.stdout.write(f"  📷 Image policy: {feed.image_policy}")

            except Exception as e:
                logger.error(f"License check failed for {feed.name}: {e}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"  ❌ Error: {str(e)[:200]}"))
                
                feed.license_status = 'yellow'
                feed.license_details = f'Check failed: {str(e)[:500]}'
                feed.license_checked_at = timezone.now()
                feed.save(update_fields=['license_status', 'license_details', 'license_checked_at'])

        self.stdout.write(self.style.SUCCESS(f"\n✅ License check complete for {total} feed(s)"))
