from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import RSSFeed, RSSNewsItem, PendingArticle
from ..serializers import RSSFeedSerializer
import os
import logging

logger = logging.getLogger(__name__)


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
    def find_feed(self, request):
        """Find RSS feed for any URL — paste a website URL, get its RSS feed info"""
        from ai_engine.modules.feed_discovery import find_feed_by_url
        
        url = request.data.get('url', '').strip()
        if not url:
            return Response({'error': 'url is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = find_feed_by_url(url)
            return Response(result)
        except Exception as e:
            return Response({
                'error': f'Feed discovery failed: {str(e)}',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def search_feeds(self, request):
        """Search web for RSS feeds by keyword — type 'BYD' and find RSS feeds"""
        from ai_engine.modules.feed_discovery import search_feeds_by_keyword
        
        query = request.data.get('query', '').strip()
        if not query:
            return Response({'error': 'query is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            results = search_feeds_by_keyword(query)
            return Response({'results': results})
        except Exception as e:
            return Response({
                'error': f'Feed search failed: {str(e)}',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get per-feed statistics: total items, generated, dismissed, pending"""
        from django.db.models import Count, Q
        
        feeds = RSSFeed.objects.annotate(
            total_items=Count('news_items'),
            generated_count=Count('news_items', filter=Q(news_items__status='generated')),
            dismissed_count=Count('news_items', filter=Q(news_items__status='dismissed')),
            pending_count_items=Count('news_items', filter=Q(news_items__status='new')),
        ).values('id', 'name', 'total_items', 'generated_count', 'dismissed_count', 'pending_count_items')
        
        return Response(list(feeds))

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
