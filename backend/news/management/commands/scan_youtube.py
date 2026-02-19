from django.core.management.base import BaseCommand
from django.utils import timezone
from news.models import YouTubeChannel, PendingArticle, Article
from ai_engine.modules.youtube_client import YouTubeClient
from ai_engine.main import create_pending_article
import time

class Command(BaseCommand):
    help = 'Scan YouTube channels for new videos'

    def add_arguments(self, parser):
        parser.add_argument('--channel_id', type=int, help='Scan specific channel ID')
        parser.add_argument('--limit', type=int, default=3, help='Max videos to check per channel')

    def handle(self, *args, **options):
        self.stdout.write("🚀 Starting YouTube scan...")
        
        # 1. Init Client
        try:
            client = YouTubeClient()
        except Exception as e:
            self.stderr.write(f"❌ Error initializing YouTube client: {e}")
            return

        # 2. Get Channels
        if options['channel_id']:
            channels = YouTubeChannel.objects.filter(id=options['channel_id'], is_enabled=True)
        else:
            channels = YouTubeChannel.objects.filter(is_enabled=True)
            
        self.stdout.write(f"📋 Found {channels.count()} channels to scan")
        
        total_created = 0
        
        for channel in channels:
            self.stdout.write(f"\n📺 Scanning channel: {channel.name} ({channel.channel_url})")
            
            # Update last_checked
            channel.last_checked = timezone.now()
            channel.save()
            
            # Fetch videos
            videos = client.get_latest_videos(channel.channel_url, max_results=options['limit'])
            if not videos:
                self.stdout.write("   ⚠️ No videos found or API error")
                continue
                
            self.stdout.write(f"   ✓ Found {len(videos)} videos. Checking for new ones...")
            
            new_articles = 0
            for video in videos:
                video_id = video['id']
                video_url = video['url']
                video_title = video['title']
                
                # Check duplicates (Fast check before calling heavy AI)
                if Article.objects.filter(youtube_url=video_url).exists():
                    # self.stdout.write(f"   - Skipping {video_title[:30]}... (Already exists)")
                    continue
                    
                if PendingArticle.objects.filter(video_id=video_id).exists():
                    # self.stdout.write(f"   - Skipping {video_title[:30]}... (Already pending)")
                    continue
                
                self.stdout.write(f"   ★ Processing new video: {video_title}...")
                
                # Generate!
                try:
                    result = create_pending_article(
                        youtube_url=video_url,
                        channel_id=channel.id,
                        video_title=video_title,
                        video_id=video_id
                    )
                    
                    if result['success']:
                        self.stdout.write(f"     ✅ Created article: {result.get('pending_id')}")
                        new_articles += 1
                        total_created += 1
                        
                        # Update channel stats
                        channel.last_video_id = video_id
                        channel.videos_processed += 1
                        channel.save()
                        
                    elif result.get('reason') in ('duplicate', 'duplicate_pending'):
                        self.stdout.write(f"     ⏭️  Skipped (same car already covered): {result.get('error', 'duplicate')}")
                    else:
                        self.stdout.write(f"     ❌ Failed: {result.get('error')}")
                        
                except Exception as e:
                     self.stdout.write(f"     ❌ Error: {e}")
                
            self.stdout.write(f"   -> Created {new_articles} pending articles")
            
        self.stdout.write(f"\n✨ Scan finished. Total new articles: {total_created}")
