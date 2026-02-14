"""
Backfill author_name and author_channel_url for articles that have youtube_url
but are missing source information. Uses YouTube Data API v3.
"""
import os
import re
import requests
from django.core.management.base import BaseCommand
from news.models import Article


class Command(BaseCommand):
    help = 'Backfill missing author_name/author_channel_url from YouTube API'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show changes without saving')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        api_key = os.getenv('YOUTUBE_API_KEY')

        if not api_key:
            self.stderr.write(self.style.ERROR('YOUTUBE_API_KEY not set'))
            return

        # Find articles with youtube_url but missing author info
        articles = Article.objects.filter(
            youtube_url__isnull=False,
        ).exclude(youtube_url='')

        # Only process those missing author_name OR author_channel_url
        to_fix = []
        for article in articles:
            needs_name = not (article.author_name or '').strip()
            needs_url = not (article.author_channel_url or '').strip()
            if needs_name or needs_url:
                to_fix.append((article, needs_name, needs_url))

        self.stdout.write(f'Found {len(to_fix)} articles needing source backfill')

        if not to_fix:
            return

        # Batch video IDs (YouTube API supports up to 50 per request)
        video_map = {}  # video_id -> (article, needs_name, needs_url)
        for article, needs_name, needs_url in to_fix:
            vid = self._extract_video_id(article.youtube_url)
            if vid:
                video_map[vid] = (article, needs_name, needs_url)
            else:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️ [{article.id}] Cannot extract video ID from: {article.youtube_url}'
                ))

        # Fetch video details in batches of 50
        video_ids = list(video_map.keys())
        fixed = 0

        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            url = 'https://www.googleapis.com/youtube/v3/videos'
            params = {
                'part': 'snippet',
                'id': ','.join(batch),
                'key': api_key,
            }

            try:
                resp = requests.get(url, params=params, timeout=10)
                if resp.status_code != 200:
                    self.stderr.write(self.style.ERROR(f'YouTube API error: {resp.status_code}'))
                    continue

                data = resp.json()
                for item in data.get('items', []):
                    vid = item['id']
                    snippet = item['snippet']
                    channel_title = snippet.get('channelTitle', '')
                    channel_id = snippet.get('channelId', '')
                    channel_url = f'https://www.youtube.com/channel/{channel_id}' if channel_id else ''

                    article, needs_name, needs_url = video_map[vid]
                    updates = []

                    if needs_name and channel_title:
                        article.author_name = channel_title
                        updates.append(f'author_name={channel_title}')

                    if needs_url and channel_url:
                        article.author_channel_url = channel_url
                        updates.append(f'author_channel_url={channel_url[:40]}...')

                    if updates:
                        self.stdout.write(
                            f'  ✅ [{article.id}] {article.title[:50]} → {", ".join(updates)}'
                        )
                        if not dry_run:
                            save_fields = []
                            if needs_name:
                                save_fields.append('author_name')
                            if needs_url:
                                save_fields.append('author_channel_url')
                            article.save(update_fields=save_fields)
                        fixed += 1

            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Error fetching batch: {e}'))

        action = 'Would fix' if dry_run else 'Fixed'
        self.stdout.write(self.style.SUCCESS(f'\n{action} {fixed} articles'))

    def _extract_video_id(self, url):
        if not url:
            return None
        match = re.search(r'(?:v=|/embed/|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
        return match.group(1) if match else None
