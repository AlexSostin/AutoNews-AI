from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import YouTubeChannel
from ..serializers import YouTubeChannelSerializer
from ._shared import invalidate_article_cache
import os
import sys
import json
import uuid
import threading
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
            
            # Enrich with article status (published / pending / null)
            if videos:
                from news.models import Article
                from news.models.content import PendingArticle
                
                video_ids = [v.get('id', '') for v in videos if v.get('id')]
                
                # Check PendingArticle by video_id
                pending_ids = set(
                    PendingArticle.objects.filter(
                        video_id__in=video_ids
                    ).exclude(
                        status='rejected'
                    ).values_list('video_id', flat=True)
                )
                
                # Check published Articles by youtube_url containing video_id
                published_ids = set()
                for vid in video_ids:
                    if vid and Article.objects.filter(
                        youtube_url__contains=vid,
                        is_published=True,
                        is_deleted=False
                    ).exists():
                        published_ids.add(vid)
                
                # Annotate each video
                for v in videos:
                    vid = v.get('id', '')
                    if vid in published_ids:
                        v['article_status'] = 'published'
                    elif vid in pending_ids:
                        v['article_status'] = 'pending'
                    else:
                        v['article_status'] = None
            
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
        """Generate a PendingArticle from a specific video (async).

        Returns a task_id immediately.  The AI pipeline runs in a
        background thread and stores its result in Django cache (Redis).
        Frontend polls /generate_status/?task_id=xxx for progress.
        """
        channel = self.get_object()
        video_url = request.data.get('video_url')
        video_id = request.data.get('video_id')
        video_title = request.data.get('video_title')
        provider = request.data.get('provider', 'gemini')

        if not video_url:
            return Response({'error': 'video_url is required'}, status=status.HTTP_400_BAD_REQUEST)

        task_id = str(uuid.uuid4())

        # Store initial status in cache (Redis) — TTL 10 min
        from django.core.cache import cache
        cache.set(f'gen_task:{task_id}', json.dumps({
            'status': 'running',
            'video_title': video_title or '',
            'channel': channel.name,
        }), timeout=600)

        # Spawn background thread
        def _run_generate(task_id, channel_id, channel_name, video_url, video_id, video_title, provider):
            from django.db import close_old_connections
            close_old_connections()
            try:
                backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ai_engine_dir = os.path.join(backend_dir, 'ai_engine')
                if backend_dir not in sys.path:
                    sys.path.insert(0, backend_dir)
                if ai_engine_dir not in sys.path:
                    sys.path.insert(0, ai_engine_dir)

                from ai_engine.main import create_pending_article
                result = create_pending_article(
                    youtube_url=video_url,
                    channel_id=channel_id,
                    video_title=video_title,
                    video_id=video_id,
                    provider=provider,
                )

                if result.get('success'):
                    invalidate_article_cache()
                    logger.info(f"[ASYNC] Generated pending article for {channel_name}")
                    cache.set(f'gen_task:{task_id}', json.dumps({
                        'status': 'done',
                        'result': result,
                    }), timeout=600)
                else:
                    cache.set(f'gen_task:{task_id}', json.dumps({
                        'status': 'error',
                        'error': result.get('error', 'Generation returned failure'),
                    }), timeout=600)
            except Exception as e:
                logger.error(f"[ASYNC] generate_pending failed: {e}", exc_info=True)
                cache.set(f'gen_task:{task_id}', json.dumps({
                    'status': 'error',
                    'error': str(e)[:500],
                }), timeout=600)
            finally:
                close_old_connections()

        t = threading.Thread(
            target=_run_generate,
            args=(task_id, channel.id, channel.name, video_url, video_id, video_title, provider),
            daemon=True,
        )
        t.start()

        return Response({
            'task_id': task_id,
            'message': f'Generation started for "{video_title or video_url}"',
        })

    @action(detail=False, methods=['get'])
    def generate_status(self, request):
        """Poll status of an async generate_pending task.

        GET /api/v1/youtube-channels/generate_status/?task_id=xxx
        Returns: { status: 'running'|'done'|'error', result?, error? }
        """
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({'error': 'task_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        from django.core.cache import cache
        raw = cache.get(f'gen_task:{task_id}')
        if not raw:
            return Response({'status': 'not_found'}, status=status.HTTP_404_NOT_FOUND)

        data = json.loads(raw)
        return Response(data)
    
    @action(detail=False, methods=['post'])
    def auto_resolve_fact_check(self, request):
        """
        Auto-fix a PendingArticle's fact-check warnings using the stored web context.
        POST body: { "pending_id": <int>, "provider": "gemini" }
        """
        pending_id = request.data.get('pending_id')
        provider = request.data.get('provider', 'gemini')

        if not pending_id:
            return Response({'error': 'pending_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from news.models.content import PendingArticle
            pending = PendingArticle.objects.get(id=pending_id)
        except Exception:
            return Response({'error': 'PendingArticle not found'}, status=status.HTTP_404_NOT_FOUND)

        web_context = pending.specs.get('web_context', '') if pending.specs else ''
        if not web_context:
            return Response({'error': 'No web context stored for this article — cannot auto-resolve'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from ai_engine.modules.fact_checker import auto_resolve_fact_check
            result = auto_resolve_fact_check(pending.content, web_context, provider=provider)
        except Exception as e:
            logger.error(f"auto_resolve_fact_check failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if result.get('error'):
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

        # Save corrected content
        pending.content = result['content']
        pending.save(update_fields=['content'])

        return Response({
            'success': True,
            'replaced': result.get('replaced', []),
            'caveated': result.get('caveated', []),
            'removed': result.get('removed', []),
            'warning': result.get('warning', ''),
            'message': (
                f"Replaced {len(result.get('replaced', []))} claims, "
                f"added caveats to {len(result.get('caveated', []))}, "
                f"removed {len(result.get('removed', []))} contradicted claims."
            )
        })

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
