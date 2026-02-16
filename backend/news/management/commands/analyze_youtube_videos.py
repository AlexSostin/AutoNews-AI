"""
Fetch all videos from a YouTube channel and compare with existing articles.
Shows which videos have articles and which don't.

Usage:
    python manage.py analyze_youtube_videos              # All channels
    python manage.py analyze_youtube_videos --channel-id 1   # Specific channel
    python manage.py analyze_youtube_videos --year 2026     # Filter by year
    python manage.py analyze_youtube_videos --missing-only  # Only show missing
"""
import os
import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from news.models import YouTubeChannel, Article, PendingArticle


class Command(BaseCommand):
    help = 'Analyze YouTube channel videos vs existing articles'

    def add_arguments(self, parser):
        parser.add_argument('--channel-id', type=int, help='Specific channel DB id')
        parser.add_argument('--year', type=int, default=2026, help='Filter by year (default: 2026)')
        parser.add_argument('--max-videos', type=int, default=200, help='Max videos to fetch (default: 200)')
        parser.add_argument('--missing-only', action='store_true', help='Only show videos without articles')

    def handle(self, *args, **options):
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            self.stderr.write(self.style.ERROR('YOUTUBE_API_KEY not set'))
            return

        year = options['year']
        max_videos = options['max_videos']
        missing_only = options['missing_only']

        if options['channel_id']:
            channels = YouTubeChannel.objects.filter(id=options['channel_id'])
        else:
            channels = YouTubeChannel.objects.filter(is_enabled=True)

        if not channels.exists():
            self.stderr.write(self.style.ERROR('No channels found'))
            return

        base_url = "https://www.googleapis.com/youtube/v3"

        for channel in channels:
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write(self.style.SUCCESS(f"📺 Channel: {channel.name}"))
            self.stdout.write(f"   URL: {channel.channel_url}")
            self.stdout.write(f"{'='*70}\n")

            # Get channel ID
            channel_id = channel.channel_id
            if not channel_id:
                from ai_engine.modules.youtube_client import YouTubeClient
                client = YouTubeClient(api_key)
                channel_id = client._get_channel_id(channel.channel_url)
                if not channel_id:
                    self.stderr.write(f"  ❌ Could not resolve channel ID")
                    continue

            # Get uploads playlist
            resp = requests.get(f"{base_url}/channels", params={
                'part': 'contentDetails,statistics',
                'id': channel_id,
                'key': api_key,
            })
            if resp.status_code != 200:
                self.stderr.write(f"  ❌ API error: {resp.status_code}")
                continue

            data = resp.json()
            if not data.get('items'):
                self.stderr.write(f"  ❌ Channel not found")
                continue

            uploads_playlist = data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            total_videos = int(data['items'][0]['statistics'].get('videoCount', 0))
            self.stdout.write(f"  Total videos on channel: {total_videos}")

            # Fetch all videos with pagination
            all_videos = []
            next_page = None
            fetched = 0

            while fetched < max_videos:
                batch_size = min(50, max_videos - fetched)
                params = {
                    'part': 'snippet,contentDetails',
                    'playlistId': uploads_playlist,
                    'maxResults': batch_size,
                    'key': api_key,
                }
                if next_page:
                    params['pageToken'] = next_page

                resp = requests.get(f"{base_url}/playlistItems", params=params)
                if resp.status_code != 200:
                    self.stderr.write(f"  ❌ Playlist API error: {resp.status_code}")
                    break

                page_data = resp.json()
                items = page_data.get('items', [])
                if not items:
                    break

                for item in items:
                    snippet = item['snippet']
                    video_id = item['contentDetails']['videoId']
                    published = snippet['publishedAt'][:10]  # YYYY-MM-DD
                    pub_year = int(published[:4])

                    all_videos.append({
                        'id': video_id,
                        'title': snippet['title'],
                        'published': published,
                        'year': pub_year,
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                    })

                fetched += len(items)
                next_page = page_data.get('nextPageToken')
                if not next_page:
                    break

            self.stdout.write(f"  Fetched: {len(all_videos)} videos\n")

            # Filter by year
            year_videos = [v for v in all_videos if v['year'] == year]
            self.stdout.write(f"  Videos in {year}: {len(year_videos)}\n")

            # Check which ones have articles
            existing_urls = set(
                Article.objects.filter(youtube_url__isnull=False)
                .exclude(youtube_url='')
                .values_list('youtube_url', flat=True)
            )
            pending_urls = set(
                PendingArticle.objects.filter(youtube_url__isnull=False)
                .exclude(youtube_url='')
                .values_list('youtube_url', flat=True)
            )

            has_article = []
            has_pending = []
            missing = []

            for v in year_videos:
                if v['url'] in existing_urls:
                    has_article.append(v)
                elif v['url'] in pending_urls:
                    has_pending.append(v)
                else:
                    missing.append(v)

            # Print results
            if not missing_only:
                self.stdout.write(self.style.SUCCESS(f"\n  ✅ Already have article ({len(has_article)}):"))
                for v in has_article:
                    self.stdout.write(f"     [{v['published']}] {v['title']}")

                if has_pending:
                    self.stdout.write(self.style.WARNING(f"\n  ⏳ Pending/Draft ({len(has_pending)}):"))
                    for v in has_pending:
                        self.stdout.write(f"     [{v['published']}] {v['title']}")

            self.stdout.write(self.style.ERROR(f"\n  ❌ Missing — no article ({len(missing)}):"))
            for v in missing:
                self.stdout.write(f"     [{v['published']}] {v['title']}")
                self.stdout.write(f"        {v['url']}")

            # Summary
            self.stdout.write(f"\n{'─'*70}")
            self.stdout.write(f"  📊 SUMMARY for {year}:")
            self.stdout.write(self.style.SUCCESS(f"     ✅ Have article:  {len(has_article)}"))
            self.stdout.write(self.style.WARNING(f"     ⏳ Pending:       {len(has_pending)}"))
            self.stdout.write(self.style.ERROR(f"     ❌ Missing:       {len(missing)}"))
            coverage = (len(has_article) / len(year_videos) * 100) if year_videos else 0
            self.stdout.write(f"     📈 Coverage:      {coverage:.0f}%")
            self.stdout.write(f"{'─'*70}\n")
