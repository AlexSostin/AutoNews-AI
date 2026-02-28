from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import YouTubeChannel
from ..serializers import YouTubeChannelSerializer
from ._shared import invalidate_article_cache
import os
import sys
import logging

logger = logging.getLogger(__name__)


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
        from django.conf import settings

        try:
            manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
            if not os.path.exists(manage_py):
                manage_py = os.path.join(os.path.dirname(settings.BASE_DIR), 'manage.py')
            
            if not os.path.exists(manage_py):
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
            from ai_engine.modules.youtube_client import YouTubeClient
            client = YouTubeClient()
            
            # Always use channel_url for resolution (channel_id may be stale/invalid)
            identifier = channel.channel_url
            
            # Fetch latest 10 videos
            videos = client.get_latest_videos(identifier, max_results=10)
            
            return Response({
                'channel': channel.name,
                'videos': videos
            })
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error fetching videos for '{channel.name}': {error_msg}")
            
            # Detect quota exceeded
            if 'quota' in error_msg.lower():
                return Response(
                    {'error': 'YouTube API quota exceeded. Please try again tomorrow.'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        from django.conf import settings

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
