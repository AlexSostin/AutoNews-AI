from rest_framework import viewsets, status, filters
from django.db.models import Avg, Case, Count, Exists, IntegerField, OuterRef, Q, Subquery, Value, When
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, BasePermission, AllowAny, IsAdminUser
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from ..models import (
    Article, Category, Tag, TagGroup, Comment, Rating, CarSpecification, 
    ArticleImage, SiteSettings, Favorite, Subscriber, NewsletterHistory,
    YouTubeChannel, RSSFeed, RSSNewsItem, PendingArticle, AdminNotification,
    VehicleSpecs, NewsletterSubscriber, BrandAlias, AutomationSettings
)
from ..serializers import (
    ArticleListSerializer, ArticleDetailSerializer, 
    CategorySerializer, TagSerializer, TagGroupSerializer, CommentSerializer, 
    RatingSerializer, CarSpecificationSerializer, ArticleImageSerializer,
    SiteSettingsSerializer, FavoriteSerializer, SubscriberSerializer, NewsletterHistorySerializer,
    YouTubeChannelSerializer, RSSFeedSerializer, RSSNewsItemSerializer, PendingArticleSerializer,
    AdminNotificationSerializer, VehicleSpecsSerializer, BrandAliasSerializer,
    AutomationSettingsSerializer
)
import os
import sys
import re
import logging

logger = logging.getLogger(__name__)


# Added inter-module imports
from .articles import invalidate_article_cache, ArticleViewSet




class YouTubeChannelViewSet(viewsets.ModelViewSet):
    """
    Manage YouTube channels for automatic article generation.
    Staff only.
    """
    queryset = YouTubeChannel.objects.all()
    serializer_class = YouTubeChannelSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        # Extract channel ID from URL if possible
        channel_url = serializer.validated_data.get('channel_url', '')
        channel_id = self._extract_channel_id(channel_url)
        serializer.save(channel_id=channel_id)
    
    def _extract_channel_id(self, url):
        """Try to extract channel ID from YouTube URL"""
        import re
        patterns = [
            r'youtube\.com/channel/([a-zA-Z0-9_-]+)',
            r'youtube\.com/@([a-zA-Z0-9_-]+)',
            r'youtube\.com/c/([a-zA-Z0-9_-]+)',
            r'youtube\.com/user/([a-zA-Z0-9_-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return ''
    
    @action(detail=True, methods=['post'])
    def scan_now(self, request, pk=None):
        """Manually trigger scan for a specific channel (Background Process)"""
        channel = self.get_object()
        
        import subprocess
        import sys
        from django.conf import settings  # <--- Added import
        
        try:
            # In Docker, manage.py is in the current working directory usually, 
            # or rely on relative path from api_views location
            # BASE_DIR is .../backend/auto_news_site (usually) or .../backend
            
            # Try to find manage.py reliably
            manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
            if not os.path.exists(manage_py):
                # Try one level up if settings is in a subdir
                manage_py = os.path.join(os.path.dirname(settings.BASE_DIR), 'manage.py')
            
            if not os.path.exists(manage_py):
                 # Fallback to simple 'manage.py' assuming CWD is correct root
                 manage_py = 'manage.py'

            print(f"🚀 Launching scan for {channel.name} using {manage_py}")
            
            subprocess.Popen(
                [sys.executable, manage_py, 'scan_youtube', '--channel_id', str(channel.id)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            message = f'Background scan started for {channel.name}'
        except Exception as e:
            print(f"❌ Error starting scan: {e}")
            import traceback
            print(traceback.format_exc())
            message = f'Failed to start scan: {str(e)}'
            
        return Response({
            'message': message,
            'channel_id': channel.id
        })
    
    @action(detail=True, methods=['get'])
    def fetch_videos(self, request, pk=None):
        """Fetch latest videos from channel without generating"""
        channel = self.get_object()
        
        try:
            # Add both backend and ai_engine paths for proper imports
            import os
            import sys
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ai_engine_dir = os.path.join(backend_dir, 'ai_engine')
            
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            if ai_engine_dir not in sys.path:
                sys.path.insert(0, ai_engine_dir)
                
            from ai_engine.modules.youtube_client import YouTubeClient
            client = YouTubeClient()
            
            # Use channel_id if available, otherwise url
            identifier = channel.channel_id if channel.channel_id else channel.channel_url
            
            # Fetch latest 10 videos
            videos = client.get_latest_videos(identifier, max_results=10)
            
            return Response({
                'channel': channel.name,
                'videos': videos
            })
        except Exception as e:
            logger.error(f"Error fetching videos: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def generate_pending(self, request, pk=None):
        """Generate a PendingArticle from a specific video"""
        channel = self.get_object()
        video_url = request.data.get('video_url')
        video_id = request.data.get('video_id')
        video_title = request.data.get('video_title')
        provider = request.data.get('provider', 'gemini')
        
        if not video_url:
            return Response({'error': 'video_url is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Add both backend and ai_engine paths for proper imports
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ai_engine_dir = os.path.join(backend_dir, 'ai_engine')
            
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            if ai_engine_dir not in sys.path:
                sys.path.insert(0, ai_engine_dir)
                
            from ai_engine.main import create_pending_article
            
            result = create_pending_article(
                youtube_url=video_url,
                channel_id=channel.id,
                video_title=video_title,
                video_id=video_id,
                provider=provider
            )
            
            if result.get('success'):
                # Invalidate cache to ensure pending counts are updated
                invalidate_article_cache()
                logger.info(f"Cache invalidated after manual generation for channel {channel.name}")
                return Response(result)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error generating pending article: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def scan_all(self, request):
        """Trigger scan for all enabled channels (Background Process)"""
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        import subprocess
        import sys
        from django.conf import settings  # <--- Added import
        
        try:
            manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
            subprocess.Popen(
                [sys.executable, manage_py, 'scan_youtube'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            count = YouTubeChannel.objects.filter(is_enabled=True).count()
            message = f'Background scan started for {count} channels'
        except Exception as e:
            print(f"❌ Error starting scan: {e}")
            message = f'Failed to start scan: {str(e)}'
            count = 0
            
        return Response({
            'message': message,
            'count': count
        })

class RSSFeedViewSet(viewsets.ModelViewSet):
    """
    Manage RSS feeds for automatic article generation.
    Staff only.
    """
    queryset = RSSFeed.objects.all()
    serializer_class = RSSFeedSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['get'])
    def with_pending_counts(self, request):
        """Get RSS feeds with count of pending articles for each"""
        from django.db.models import Count, Q
        
        feeds = RSSFeed.objects.filter(is_enabled=True).annotate(
            pending_count=Count(
                'pending_articles',
                filter=Q(pending_articles__status='pending')
            )
        ).order_by('name')
        
        serializer = self.get_serializer(feeds, many=True)
        data = serializer.data
        
        # Add pending_count to each feed
        for i, feed in enumerate(feeds):
            data[i]['pending_count'] = feed.pending_count
        
        return Response(data)
    @action(detail=True, methods=['post'])
    def scan_now(self, request, pk=None):
        """Manually trigger scan for a specific RSS feed (Background Process)"""
        feed = self.get_object()
        
        import subprocess
        import sys
        from django.conf import settings
        
        try:
            manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
            if not os.path.exists(manage_py):
                manage_py = os.path.join(os.path.dirname(settings.BASE_DIR), 'manage.py')
            
            if not os.path.exists(manage_py):
                manage_py = 'manage.py'

            print(f"🚀 Launching RSS scan for {feed.name} using {manage_py}")
            
            subprocess.Popen(
                [sys.executable, manage_py, 'scan_rss_feeds', '--feed-id', str(feed.id)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            message = f'Background scan started for {feed.name}'
        except Exception as e:
            print(f"❌ Error starting RSS scan: {e}")
            import traceback
            print(traceback.format_exc())
            message = f'Failed to start scan: {str(e)}'
            
        return Response({
            'message': message,
            'feed_id': feed.id
        })
    
    @action(detail=False, methods=['post'])
    def scan_all(self, request):
        """Scan all enabled RSS feeds (Background Process)"""
        import subprocess
        import sys
        from django.conf import settings
        
        try:
            manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
            subprocess.Popen(
                [sys.executable, manage_py, 'scan_rss_feeds', '--all'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            count = RSSFeed.objects.filter(is_enabled=True).count()
            message = f'Background scan started for {count} RSS feeds'
        except Exception as e:
            print(f"❌ Error starting RSS scan: {e}")
            message = f'Failed to start scan: {str(e)}'
            count = 0
            
        return Response({
            'message': message,
            'count': count
        })

    @action(detail=True, methods=['post'])
    def check_license(self, request, pk=None):
        """Check content license (robots.txt + Terms of Use) for this RSS feed's website"""
        feed = self.get_object()
        
        import subprocess
        import sys
        from django.conf import settings
        
        try:
            manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
            if not os.path.exists(manage_py):
                manage_py = os.path.join(os.path.dirname(settings.BASE_DIR), 'manage.py')

            subprocess.Popen(
                [sys.executable, manage_py, 'check_rss_license', '--feed-id', str(feed.id)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            message = f'License check started for {feed.name}'
        except Exception as e:
            print(f"❌ Error starting license check: {e}")
            message = f'Failed to start license check: {str(e)}'
            
        return Response({
            'message': message,
            'feed_id': feed.id
        })
    
    @action(detail=False, methods=['post'])
    def check_all_licenses(self, request):
        """Check content licenses for all RSS feeds (re-checks already checked ones too)"""
        import subprocess
        import sys
        from django.conf import settings
        
        # Support ?unchecked_only=true to only check unchecked feeds
        unchecked_only = request.data.get('unchecked_only', False)
        
        try:
            manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
            flag = '--all-unchecked' if unchecked_only else '--all'
            subprocess.Popen(
                [sys.executable, manage_py, 'check_rss_license', flag],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            if unchecked_only:
                count = RSSFeed.objects.filter(license_status='unchecked').count()
                message = f'License check started for {count} unchecked feeds'
            else:
                count = RSSFeed.objects.filter(is_enabled=True).count()
                message = f'License re-check started for {count} feeds (all enabled)'
        except Exception as e:
            print(f"❌ Error starting license check: {e}")
            message = f'Failed to start license check: {str(e)}'
            count = 0
            
        return Response({
            'message': message,
            'count': count
        })

    @action(detail=False, methods=['post'])
    def discover_feeds(self, request):
        """Discover automotive RSS feeds from curated sources"""
        from ai_engine.modules.feed_discovery import discover_feeds
        
        # Run discovery WITHOUT license check for speed (takes ~30s vs ~5min)
        # License can be checked individually after adding
        try:
            results = discover_feeds(check_license=False)
            
            # For brand sources, auto-set green (press releases are for media)
            for r in results:
                if r['source_type'] == 'brand':
                    r['license_status'] = 'green'
                    r['license_details'] = 'Brand press portal — press releases are meant for media distribution'
            
            return Response({
                'results': results,
                'total': len(results),
                'valid_feeds': sum(1 for r in results if r['feed_valid']),
                'already_added': sum(1 for r in results if r['already_added']),
            })
        except Exception as e:
            return Response({
                'error': str(e),
                'results': [],
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def add_discovered(self, request):
        """Add a discovered feed to the database"""
        name = request.data.get('name')
        feed_url = request.data.get('feed_url')
        website_url = request.data.get('website_url', '')
        source_type = request.data.get('source_type', 'media')
        license_status = request.data.get('license_status', 'unchecked')
        license_details = request.data.get('license_details', '')
        image_policy = request.data.get('image_policy', 'pexels_fallback')
        
        if not feed_url:
            return Response({'error': 'feed_url is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if RSSFeed.objects.filter(feed_url=feed_url).exists():
            return Response({'error': 'Feed URL already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from django.utils import timezone
            feed = RSSFeed.objects.create(
                name=name or 'Discovered Feed',
                feed_url=feed_url,
                website_url=website_url,
                source_type=source_type,
                is_enabled=True,
                license_status=license_status,
                license_details=license_details,
                image_policy=image_policy,
                license_checked_at=timezone.now() if license_status != 'unchecked' else None,
            )
            serializer = self.get_serializer(feed)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def test_feed(self, request):
        """Test an RSS feed URL by fetching and parsing it server-side"""
        import requests as http_requests
        import xml.etree.ElementTree as ET
        
        feed_url = request.data.get('feed_url', '').strip()
        if not feed_url:
            return Response({'error': 'feed_url is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            resp = http_requests.get(feed_url, timeout=15, headers={
                'User-Agent': 'FreshMotors RSS Reader/1.0',
                'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            })
            resp.raise_for_status()
            
            content = resp.text.strip()
            
            # Check if response is HTML instead of XML/RSS
            if content.startswith('<!DOCTYPE') or content.startswith('<html'):
                return Response({
                    'error': 'URL returned an HTML page, not an RSS/XML feed. Check the feed URL.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Try feedparser first (handles more formats)
            try:
                import feedparser
                parsed = feedparser.parse(content)
                if parsed.entries:
                    feed_meta = {
                        'title': parsed.feed.get('title', ''),
                        'link': parsed.feed.get('link', ''),
                        'description': parsed.feed.get('subtitle', '') or parsed.feed.get('description', ''),
                    }
                    entries = []
                    for entry in parsed.entries[:5]:
                        entries.append({
                            'title': entry.get('title', 'No title'),
                            'link': entry.get('link', ''),
                            'published': entry.get('published', ''),
                        })
                    return Response({
                        'success': True,
                        'entries_count': len(parsed.entries),
                        'entries': entries,
                        'feed_meta': feed_meta
                    })
            except ImportError:
                pass
            
            # Fallback to XML parsing
            root = ET.fromstring(content)
            
            entries = []
            items = root.findall('.//item')
            if not items:
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                items = root.findall('.//atom:entry', ns)
            
            for item in items[:5]:
                title = item.findtext('title') or item.findtext('{http://www.w3.org/2005/Atom}title') or 'No title'
                link = item.findtext('link') or ''
                if not link:
                    link_el = item.find('{http://www.w3.org/2005/Atom}link')
                    if link_el is not None:
                        link = link_el.get('href', '')
                published = item.findtext('pubDate') or item.findtext('{http://www.w3.org/2005/Atom}published') or ''
                entries.append({'title': title, 'link': link, 'published': published})
            
            total = len(root.findall('.//item')) or len(root.findall('.//{http://www.w3.org/2005/Atom}entry'))
            
            # Extract feed metadata
            channel = root.find('.//channel') or root
            ns_atom = '{http://www.w3.org/2005/Atom}'
            feed_meta = {
                'title': channel.findtext('title') or root.findtext(f'{ns_atom}title') or '',
                'link': channel.findtext('link') or '',
                'description': channel.findtext('description') or root.findtext(f'{ns_atom}subtitle') or '',
            }
            if not feed_meta['link']:
                link_el = root.find(f'{ns_atom}link')
                if link_el is not None:
                    feed_meta['link'] = link_el.get('href', '')
            
            return Response({
                'success': True,
                'entries_count': total,
                'entries': entries,
                'feed_meta': feed_meta
            })
        except http_requests.exceptions.Timeout:
            return Response({'error': 'Connection timed out. The server may be slow or blocking requests.'}, status=status.HTTP_408_REQUEST_TIMEOUT)
        except http_requests.exceptions.RequestException as e:
            return Response({'error': f'Failed to fetch feed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except ET.ParseError:
            return Response({'error': 'Response is not valid XML/RSS. The URL may not point to an RSS feed.'}, status=status.HTTP_400_BAD_REQUEST)

class RSSNewsItemViewSet(viewsets.ModelViewSet):
    """
    Browse raw RSS news items and generate articles on demand.
    Staff only.
    """
    queryset = RSSNewsItem.objects.select_related('rss_feed', 'pending_article').all()
    serializer_class = RSSNewsItemSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by feed
        feed_id = self.request.query_params.get('feed')
        if feed_id:
            queryset = queryset.filter(rss_feed_id=feed_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # By default, exclude dismissed items
        if not self.request.query_params.get('show_dismissed'):
            queryset = queryset.exclude(status='dismissed')
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Generate an AI article from this RSS news item."""
        news_item = self.get_object()
        
        if news_item.status == 'generated':
            return Response(
                {'error': 'Article already generated for this news item'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        news_item.status = 'generating'
        news_item.save(update_fields=['status'])
        
        try:
            from ai_engine.modules.article_generator import expand_press_release
            from ai_engine.main import extract_title, validate_title, _is_generic_header
            import re
            
            # Strip HTML tags to get plain text for AI
            plain_text = re.sub(r'<[^>]+>', '', news_item.content).strip()
            if not plain_text:
                plain_text = news_item.excerpt
            
            provider = request.data.get('provider', 'gemini')
            if provider not in ('groq', 'gemini'):
                provider = 'gemini'
            
            # Expand with AI
            expanded_content = expand_press_release(
                press_release_text=plain_text,
                source_url=news_item.source_url,
                provider=provider
            )
            
            # Extract and validate title
            ai_title = extract_title(expanded_content)
            if not ai_title or _is_generic_header(ai_title):
                ai_title = news_item.title
            ai_title = validate_title(ai_title)
            
            # Convert markdown to HTML if needed
            if '###' in expanded_content and '<h2>' not in expanded_content:
                try:
                    import markdown
                    expanded_content = markdown.markdown(expanded_content, extensions=['fenced_code', 'tables'])
                except Exception:
                    pass
            
            # Content quality check
            word_count = len(re.sub(r'<[^>]+>', '', expanded_content).split())
            if word_count < 200:
                news_item.status = 'new'
                news_item.save(update_fields=['status'])
                return Response(
                    {'error': f'AI content too short ({word_count} words), try again'},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )
            
            # Build images list — respect feed's image_policy
            feed = news_item.rss_feed
            image_policy = feed.image_policy if feed else 'pexels_fallback'
            
            if image_policy == 'pexels_only':
                # Media site — don't use their images, search Pexels instead
                images = []
                featured_image = ''
            else:
                # 'original' or 'pexels_fallback' — use source image if available
                images = [news_item.image_url] if news_item.image_url else []
                featured_image = news_item.image_url or ''
            
            # Determine image source
            if image_policy == 'pexels_only':
                img_source = 'pexels'
            elif images:
                img_source = 'rss_original'
            else:
                img_source = 'unknown'
            
            # Create PendingArticle
            pending = PendingArticle.objects.create(
                rss_feed=news_item.rss_feed,
                source_url=news_item.source_url,
                content_hash=news_item.content_hash,
                title=ai_title,
                content=expanded_content,
                excerpt=plain_text[:500],
                images=images,
                featured_image=featured_image,
                image_source=img_source,
                suggested_category=news_item.rss_feed.default_category if news_item.rss_feed else None,
                status='pending'
            )
            
            # Update news item
            news_item.status = 'generated'
            news_item.pending_article = pending
            news_item.save(update_fields=['status', 'pending_article'])
            
            return Response({
                'success': True,
                'message': f'Article generated: {ai_title}',
                'pending_article_id': pending.id
            })
            
        except Exception as e:
            logger.error(f'Error generating article from RSS news item {pk}: {e}', exc_info=True)
            news_item.status = 'new'
            news_item.save(update_fields=['status'])
            return Response(
                {'error': f'Generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Dismiss a news item (hide from feed)."""
        news_item = self.get_object()
        news_item.status = 'dismissed'
        news_item.save(update_fields=['status'])
        return Response({'success': True})
    
    @action(detail=False, methods=['post'])
    def bulk_dismiss(self, request):
        """Dismiss multiple news items."""
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        count = RSSNewsItem.objects.filter(id__in=ids).update(status='dismissed')
        return Response({'success': True, 'count': count})

class PendingArticleViewSet(viewsets.ModelViewSet):
    """
    Manage pending articles waiting for review.
    Staff only.
    """
    queryset = PendingArticle.objects.select_related(
        'youtube_channel',
        'rss_feed',
        'suggested_category'
    ).all()
    serializer_class = PendingArticleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'video_title']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = PendingArticle.objects.select_related(
            'youtube_channel',
            'rss_feed',
            'suggested_category'
        ).all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(categories__slug=category)
        
        # Filter by RSS feed ID
        rss_feed_id = self.request.query_params.get('rss_feed')
        if rss_feed_id:
            queryset = queryset.filter(rss_feed_id=rss_feed_id)
        
        # Filter only RSS articles (exclude YouTube)
        only_rss = self.request.query_params.get('only_rss')
        if only_rss == 'true':
            queryset = queryset.filter(rss_feed__isnull=False)
        
        # Filter only YouTube articles (exclude RSS)
        only_youtube = self.request.query_params.get('only_youtube')
        exclude_rss = self.request.query_params.get('exclude_rss')
        if only_youtube == 'true' or exclude_rss == 'true':
            queryset = queryset.filter(youtube_channel__isnull=False)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve and publish a pending article"""
        pending = self.get_object()
        
        if pending.status != 'pending':
            return Response({'error': 'Article is not pending'}, status=status.HTTP_400_BAD_REQUEST)
        
        
        # Create the actual article
        try:
            from django.utils.text import slugify
            import uuid
            
            # Generate unique slug
            base_slug = slugify(pending.title)[:80]
            slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
            
            is_published = request.data.get('publish', True)
            
            # Extract author info from channel if available
            author_name = pending.author_name
            author_channel_url = pending.author_channel_url
            
            if not author_name:
                if pending.youtube_channel:
                    author_name = pending.youtube_channel.name
                    author_channel_url = pending.youtube_channel.channel_url
                elif pending.rss_feed:
                    # For RSS articles, use feed name and source URL
                    author_name = pending.rss_feed.name
                    author_channel_url = pending.source_url or pending.rss_feed.feed_url

            article = Article.objects.create(
                title=pending.title,
                slug=slug,
                content=pending.content,
                summary=pending.excerpt or pending.content[:200],
                is_published=is_published,
                youtube_url=pending.video_url,
                author_name=author_name,
                author_channel_url=author_channel_url,
                image_source=pending.image_source or 'unknown',
            )
            
            # Add category (ManyToMany field)
            # For RSS articles, use suggested_category or fallback to "News"
            if pending.rss_feed:
                if pending.suggested_category:
                    article.categories.add(pending.suggested_category)
                else:
                    # Fallback to "News" category for RSS articles
                    from news.models import Category
                    news_category, _ = Category.objects.get_or_create(
                        slug='news',
                        defaults={'name': 'News', 'description': 'General automotive news'}
                    )
                    article.categories.add(news_category)
            elif pending.suggested_category:
                # For non-RSS articles (YouTube), only add if exists
                article.categories.add(pending.suggested_category)
            
            
            # Handle Images (Upload local files or save Cloudinary URLs)
            logger.info(f"[APPROVE] Processing images for article '{article.title[:50]}'")
            logger.info(f"[APPROVE] pending.images = {pending.images}")
            logger.info(f"[APPROVE] pending.featured_image = {pending.featured_image}")
            
            image_sources = []
            if pending.images and isinstance(pending.images, list):
                image_sources = pending.images[:3]
            elif pending.featured_image:
                image_sources = [pending.featured_image]
            
            if image_sources:
                from django.core.files import File
                from django.core.files.base import ContentFile
                import os
                import requests as img_requests
                for i, image_path in enumerate(image_sources):
                    if not image_path: continue
                    
                    try:
                        file_name = f"{slug}_{i+1}.jpg"
                        content_file = None
                        
                        # Case A+B: Any URL (Cloudinary, Pexels, etc) — download and upload via .save()
                        # Direct assignment to ImageField doesn't work with MediaCloudinaryStorage
                        if image_path.startswith('http'):
                            logger.info(f"[APPROVE] Downloading image {i+1} from URL: {image_path[:100]}")
                            
                            # Extract domain for Referer header
                            from urllib.parse import urlparse
                            parsed = urlparse(image_path)
                            domain = f"{parsed.scheme}://{parsed.netloc}"
                            
                            # Try multiple header combinations for resilience
                            header_variants = [
                                {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                                    'Accept': 'image/*,*/*;q=0.8',
                                },
                                {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                                    'Accept': 'image/*,*/*;q=0.8',
                                    'Referer': domain,
                                },
                                {
                                    'User-Agent': 'Googlebot-Image/1.0',
                                    'Accept': 'image/*',
                                },
                            ]
                            
                            resp = None
                            for attempt, headers in enumerate(header_variants, 1):
                                try:
                                    resp = img_requests.get(image_path, timeout=15, headers=headers)
                                    logger.info(f"[APPROVE] Attempt {attempt}: status={resp.status_code}, size={len(resp.content)} bytes")
                                    if resp.status_code == 200 and len(resp.content) > 1000:
                                        break
                                except Exception as dl_err:
                                    logger.warning(f"[APPROVE] Attempt {attempt} failed: {dl_err}")
                                    resp = None
                            
                            if resp and resp.status_code == 200 and len(resp.content) > 0:
                                # Validate magic bytes — ensure downloaded content is actually an image
                                VALID_MAGIC = [b'\xff\xd8\xff', b'\x89PNG', b'RIFF', b'GIF8']
                                is_valid_image = any(resp.content[:4].startswith(m) for m in VALID_MAGIC)
                                
                                if is_valid_image:
                                    content_file = ContentFile(resp.content, name=file_name)
                                else:
                                    logger.warning(f"[APPROVE] Downloaded content is not a valid image (magic bytes: {resp.content[:4]})")
                            else:
                                logger.warning(f"[APPROVE] Failed to download image after {len(header_variants)} attempts")
                        
                        # Case C: It's a local file relative path
                        elif image_path.startswith('/media/'):
                             from django.conf import settings
                             full_path = os.path.join(settings.BASE_DIR, image_path.lstrip('/'))
                             logger.info(f"[APPROVE] Reading relative image: {full_path}")
                             if os.path.exists(full_path):
                                 with open(full_path, 'rb') as f:
                                     content = f.read()
                                     content_file = ContentFile(content, name=file_name)
                             else:
                                 logger.warning(f"[APPROVE] Local file not found: {full_path}")
                        
                        # Case D: It's a legacy absolute local path
                        elif os.path.exists(image_path):
                            logger.info(f"[APPROVE] Reading local image: {image_path}")
                            with open(image_path, 'rb') as f:
                                content = f.read()
                                content_file = ContentFile(content, name=file_name)
                        else:
                            logger.warning(f"[APPROVE] Image path not recognized/found: {image_path}")
                                
                        # Save to Article via .save() — works with any storage backend
                        if content_file:
                            logger.info(f"[APPROVE] Saving image {i+1} ({file_name}, {len(content_file)} bytes) to article...")
                            if i == 0:
                                article.image.save(file_name, content_file, save=True)
                                logger.info(f"[APPROVE] ✓ Image 1 saved. article.image.url = {article.image.url if article.image else 'NONE'}")
                            elif i == 1:
                                article.image_2.save(file_name, content_file, save=True)
                                logger.info(f"[APPROVE] ✓ Image 2 saved. article.image_2.url = {article.image_2.url if article.image_2 else 'NONE'}")
                            elif i == 2:
                                article.image_3.save(file_name, content_file, save=True)
                                logger.info(f"[APPROVE] ✓ Image 3 saved. article.image_3.url = {article.image_3.url if article.image_3 else 'NONE'}")
                        else:
                            logger.warning(f"[APPROVE] No content_file for image {i+1}")
                                
                    except Exception as img_err:
                        logger.error(f"[APPROVE] Error saving image {image_path}: {img_err}", exc_info=True)
            else:
                logger.warning(f"[APPROVE] No images found in pending article")
            
            # Restore Tags from PendingArticle
            if pending.tags and isinstance(pending.tags, list):
                try:
                    for tag_name in pending.tags:
                        tag_slug = slugify(tag_name)
                        tag, _ = Tag.objects.get_or_create(
                            slug=tag_slug, 
                            defaults={'name': tag_name}
                        )
                        article.tags.add(tag)
                    print(f"  Restored {len(pending.tags)} tags")
                except Exception as e:
                    print(f"  Error restoring tags: {e}")

            # --- Smart tag matching (same logic as translate-enhance) ---
            try:
                all_tags = list(Tag.objects.select_related('group').all())
                title_lower = article.title.lower()
                content_lower = (article.content or '').lower()
                combined_text = f"{title_lower} {content_lower}"
                seo_kw_list = [kw.strip() for kw in (article.meta_keywords or '').split(',') if kw.strip()]
                keywords_text = ' '.join(kw.lower() for kw in seo_kw_list)

                GENERIC_TAGS = {'technology', 'navigation', 'advanced', 'performance', 'budget', 'luxury'}
                existing_tag_names = list(article.tags.values_list('name', flat=True))

                for tag in all_tags:
                    tag_lower = tag.name.lower()
                    matched = False

                    if tag_lower.isdigit():
                        if any(kw.lower() == tag_lower for kw in seo_kw_list):
                            matched = True
                    elif any(kw.lower() == tag_lower for kw in seo_kw_list):
                        matched = True
                    elif len(tag_lower) >= 3 and tag_lower not in GENERIC_TAGS and tag_lower in keywords_text:
                        matched = True
                    elif len(tag_lower) >= 2 and (f' {tag_lower} ' in f' {title_lower} ' or title_lower.startswith(f'{tag_lower} ')):
                        matched = True
                    elif tag.group and tag.group.name in ('Manufacturers', 'Brands', 'Body Types', 'Fuel Types', 'Segments'):
                        if tag_lower not in GENERIC_TAGS and f' {tag_lower} ' in f' {combined_text} ':
                            matched = True
                    elif tag_lower in ('ev', 'electric') and ('electric' in combined_text or ' ev ' in f' {combined_text} ' or 'bev' in combined_text):
                        matched = True
                    elif tag_lower == 'phev' and 'phev' in combined_text:
                        matched = True
                    elif tag_lower == 'hybrid' and 'hybrid' in combined_text:
                        matched = True

                    if matched and tag.name not in existing_tag_names:
                        article.tags.add(tag)
                        existing_tag_names.append(tag.name)

                smart_tags = list(article.tags.values_list('name', flat=True))
                print(f"  🏷️ Smart tags: {', '.join(smart_tags)}")
            except Exception as tag_err:
                logger.warning(f"Smart tag matching failed: {tag_err}")

            # Restore Specs from PendingArticle
            if pending.specs and isinstance(pending.specs, dict):
                try:
                    specs = pending.specs
                    if specs.get('make') != 'Not specified':
                        CarSpecification.objects.update_or_create(
                            article=article,
                            defaults={
                                'model_name': f"{specs.get('make', '')} {specs.get('model', '')}",
                                'engine': specs.get('engine', ''),
                                'horsepower': str(specs.get('horsepower', '')),
                                'torque': specs.get('torque', ''),
                                'zero_to_sixty': specs.get('acceleration', ''),
                                'top_speed': specs.get('top_speed', ''),
                                'price': specs.get('price', ''),
                            }
                        )
                        print("  Restored CarSpecification")
                except Exception as e:
                    print(f"  Error restoring specs: {e}")
            
            # Update pending article
            pending.status = 'published'
            pending.published_article = article
            pending.reviewed_by = request.user
            pending.reviewed_at = timezone.now()
            pending.save()
            
            # Generate A/B title variants
            try:
                from ai_engine.main import generate_title_variants
                generate_title_variants(article, provider='gemini')
            except Exception as ab_err:
                logger.warning(f"A/B title variant generation failed: {ab_err}")
            
            # Deep specs enrichment — auto-fill VehicleSpecs card
            try:
                from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
                # Build specs dict from CarSpecification if available
                specs_dict = None
                web_context = ''
                try:
                    car_spec = CarSpecification.objects.filter(article=article).first()
                    if car_spec:
                        # CarSpecification has no 'year' field — extract from title
                        import re as _re
                        _year = None
                        _y_match = _re.search(r'\b(20[2-3]\d)\b', article.title)
                        if _y_match:
                            _year = int(_y_match.group(1))
                        elif car_spec.release_date:
                            _ry = _re.search(r'(20[2-3]\d)', car_spec.release_date)
                            if _ry:
                                _year = int(_ry.group(1))
                        specs_dict = {
                            'make': car_spec.make or '',
                            'model': car_spec.model or '',
                            'trim': car_spec.trim or '',
                            'year': _year,
                            'horsepower': car_spec.horsepower,
                            'torque': car_spec.torque or '',
                            'acceleration': car_spec.zero_to_sixty or '',
                            'top_speed': car_spec.top_speed or '',
                            'drivetrain': car_spec.drivetrain or '',
                            'price': car_spec.price or '',
                        }
                except Exception:
                    pass
                
                # Web search for better spec accuracy
                if specs_dict and specs_dict.get('make'):
                    try:
                        from ai_engine.modules.searcher import get_web_context
                        web_context = get_web_context(specs_dict)
                    except Exception:
                        pass
                    generate_deep_vehicle_specs(article, specs=specs_dict, web_context=web_context, provider='gemini')
            except Exception as ds_err:
                logger.warning(f"Deep specs enrichment failed: {ds_err}")
            
            # Clear cache so the new article appears on homepage immediately
            # The ArticleViewSet list uses @cache_page(300) for anonymous users
            try:
                from django.core.cache import cache
                invalidate_article_cache(article_id=article.id, slug=article.slug)
                logger.info(f"Cache invalidated after publishing article: {article.slug}")
            except Exception as cache_err:
                logger.warning(f"Failed to invalidate cache: {cache_err}")
            
            return Response({
                'message': 'Article approved successfully' if not is_published else 'Article published successfully',
                'article_id': article.id,
                'article_slug': article.slug
            })
        except Exception as e:
            logger.error(f"Failed to publish article: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a pending article"""
        pending = self.get_object()
        
        if pending.status != 'pending':
            return Response({'error': 'Article is not pending'}, status=status.HTTP_400_BAD_REQUEST)
        
        pending.status = 'rejected'
        pending.reviewed_by = request.user
        pending.reviewed_at = timezone.now()
        pending.review_notes = request.data.get('reason', '')
        pending.save()
        
        return Response({'message': 'Article rejected'})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get statistics about pending articles"""
        # Get base queryset
        queryset = PendingArticle.objects.all()
        
        # Apply source filters
        only_rss = request.query_params.get('only_rss')
        if only_rss == 'true':
            queryset = queryset.filter(rss_feed__isnull=False)
        
        only_youtube = request.query_params.get('only_youtube')
        exclude_rss = request.query_params.get('exclude_rss')
        if only_youtube == 'true' or exclude_rss == 'true':
            queryset = queryset.filter(youtube_channel__isnull=False)
        
        return Response({
            'pending': queryset.filter(status='pending').count(),
            'approved': queryset.filter(status='approved').count(),
            'rejected': queryset.filter(status='rejected').count(),
            'published': queryset.filter(status='published').count(),
            'total': queryset.count()
        })

