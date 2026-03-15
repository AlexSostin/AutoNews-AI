"""
Django management command to scan RSS feeds and create pending articles.

Usage:
    python manage.py scan_rss_feeds --all
    python manage.py scan_rss_feeds --feed-id 5
    python manage.py scan_rss_feeds --dry-run
"""
import json
import time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from news.models import RSSFeed, RSSNewsItem
from ai_engine.modules.rss_aggregator import RSSAggregator

# Redis key for progress tracking (read by /rss-feeds/scan_progress/ endpoint)
RSS_PROGRESS_KEY = 'rss_scan_progress'
RSS_PROGRESS_TTL = 600  # 10 minutes


def _set_progress(redis_client, done: int, total: int, feed_name: str = ''):
    """Write scan progress to Redis so the frontend can poll it."""
    if redis_client is None:
        return
    try:
        data = {
            'done': done,
            'total': total,
            'percent': round((done / total) * 100) if total else 100,
            'current_feed': feed_name,
            'finished': done >= total,
            'ts': time.time(),
        }
        redis_client.setex(RSS_PROGRESS_KEY, RSS_PROGRESS_TTL, json.dumps(data))
    except Exception:
        pass  # Never let progress tracking break the scan


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
        parser.add_argument(
            '--no-ai',
            action='store_true',
            help='Disable AI enhancement (create basic articles from press releases)',
        )

    def handle(self, *args, **options):
        aggregator = RSSAggregator()
        use_ai = not options['no_ai']  # AI enabled by default

        # --- Auto-cleanup: delete new/read items older than 7 days (skip favorites) ---
        cutoff_7d = timezone.now() - timedelta(days=7)
        deleted_count, _ = RSSNewsItem.objects.filter(
            status__in=['new', 'read'],
            is_favorite=False,
            created_at__lt=cutoff_7d,
        ).delete()
        if deleted_count:
            self.stdout.write(self.style.WARNING(f'🗑  Cleaned up {deleted_count} RSS items older than 7 days'))

        # --- Cleanup favorites older than 60 days (they've served as ML signal) ---
        cutoff_60d = timezone.now() - timedelta(days=60)
        fav_deleted, _ = RSSNewsItem.objects.filter(
            is_favorite=True,
            created_at__lt=cutoff_60d,
        ).delete()
        if fav_deleted:
            self.stdout.write(self.style.WARNING(f'🗑  Cleaned up {fav_deleted} favorite RSS items older than 60 days'))


        # --- RSS Intelligence: extract brands & models from recent titles ---
        try:
            from news.rss_intelligence import process_rss_intelligence
            intel = process_rss_intelligence()
            if intel['brands_created']:
                self.stdout.write(self.style.SUCCESS(
                    f'🧠 Intelligence: discovered {len(intel["brands_created"])} new brand(s): '
                    f'{", ".join(intel["brands_created"])}'
                ))
            if intel['models_created']:
                self.stdout.write(self.style.SUCCESS(
                    f'🧠 Intelligence: discovered {len(intel["models_created"])} new model(s): '
                    f'{", ".join(intel["models_created"])}'
                ))
            if not intel['brands_created'] and not intel['models_created']:
                self.stdout.write(f'🧠 Intelligence: scanned {intel["items_scanned"]} items, no new discoveries')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️  Intelligence pass failed: {e}'))

        # Connect to Redis for progress tracking (optional — won't break if unavailable)
        redis_client = None
        try:
            import redis as redis_lib
            from django.conf import settings as django_settings
            redis_url = getattr(django_settings, 'REDIS_URL', None) or 'redis://127.0.0.1:6379/1'
            redis_client = redis_lib.Redis.from_url(redis_url, socket_connect_timeout=1)
            redis_client.ping()
        except Exception:
            redis_client = None  # Redis unavailable — progress won't be tracked

        # Determine which feeds to scan
        if options['feed_id']:
            feeds = list(RSSFeed.objects.filter(id=options['feed_id']))
            if not feeds:
                self.stdout.write(self.style.ERROR(f'RSS Feed with ID {options["feed_id"]} not found'))
                return
        elif options['all']:
            all_enabled_feeds = RSSFeed.objects.filter(is_enabled=True)
            feeds = []
            now = timezone.now()
            for feed in all_enabled_feeds:
                if not feed.last_checked:
                    feeds.append(feed)
                else:
                    age_minutes = (now - feed.last_checked).total_seconds() / 60
                    if age_minutes >= feed.scan_frequency:
                        feeds.append(feed)
        else:
            self.stdout.write(self.style.ERROR('Please specify --all or --feed-id'))
            return

        if not feeds:
            self.stdout.write(self.style.WARNING('No RSS feeds found or none require scanning based on frequency'))
            return

        feeds_list = feeds
        total = len(feeds_list)

        ai_status = '🤖 AI Enhancement: ENABLED' if use_ai else '📝 AI Enhancement: DISABLED'
        self.stdout.write(f'\n📡 Scanning {total} RSS feed(s)...')
        self.stdout.write(f'{ai_status}\n')

        # Initialize progress at 0
        _set_progress(redis_client, 0, total, feeds_list[0].name if feeds_list else '')

        total_created = 0

        for idx, feed in enumerate(feeds_list, 1):
            self.stdout.write(f'\n🔍 [{idx}/{total}] Processing: {feed.name}')
            self.stdout.write(f'   URL: {feed.feed_url}')

            # Update progress: currently scanning this feed
            _set_progress(redis_client, idx - 1, total, feed.name)

            if options['dry_run']:
                self.stdout.write(self.style.WARNING('   [DRY RUN MODE]'))
                feed_data = aggregator.fetch_feed(feed.feed_url)
                if feed_data:
                    self.stdout.write(self.style.SUCCESS(f'   ✓ Found {len(feed_data.entries)} entries'))
                    for i, entry in enumerate(feed_data.entries[:options['limit']], 1):
                        title = entry.get('title', 'Untitled')
                        self.stdout.write(f'     {i}. {title[:70]}')
                else:
                    self.stdout.write(self.style.ERROR('   ✗ Failed to fetch feed'))
            else:
                try:
                    created = aggregator.process_feed(feed, limit=options['limit'], use_ai=use_ai)
                    total_created += created

                    if created > 0:
                        self.stdout.write(self.style.SUCCESS(f'   ✓ Created {created} pending article(s)'))
                    else:
                        self.stdout.write(self.style.WARNING('   ⚠ No new articles (all duplicates or insufficient content)'))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   ✗ Error: {e}'))

            # Mark this feed as done
            _set_progress(redis_client, idx, total, feeds_list[idx].name if idx < total else '')

        # Mark 100% finished
        _set_progress(redis_client, total, total, '')

        if not options['dry_run']:
            self.stdout.write(f'\n✅ Scan complete! Total articles created: {total_created}\n')
        else:
            self.stdout.write(f'\n✅ Dry run complete! (No articles created)\n')
