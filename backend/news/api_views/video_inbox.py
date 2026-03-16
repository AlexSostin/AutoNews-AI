"""API endpoints for YouTube Video Inbox — cherry-pick videos before article generation."""
import logging
import json
import uuid
import threading
from datetime import timedelta

from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from ..models import YouTubeVideoCandidate, YouTubeChannel
from ..serializers import YouTubeVideoCandidateSerializer

logger = logging.getLogger(__name__)


class VideoInboxPagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = 'page_size'
    max_page_size = 100


class VideoInboxViewSet(viewsets.ModelViewSet):
    """
    YouTube Video Inbox — browse discovered videos, approve or dismiss.
    """
    serializer_class = YouTubeVideoCandidateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = VideoInboxPagination
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        """Return candidates from last 30 days, with filters."""
        cutoff = timezone.now() - timedelta(days=30)
        qs = YouTubeVideoCandidate.objects.filter(
            published_at__gte=cutoff
        ).select_related('channel')

        # Status filter (default: new) — only for list views, not detail actions
        # Detail actions (approve, dismiss) must find the object regardless of status
        if self.action == 'list':
            status_filter = self.request.query_params.get('status', 'new')
            if status_filter and status_filter != 'all':
                qs = qs.filter(status=status_filter)

        # Channel filter
        channel_id = self.request.query_params.get('channel_id')
        if channel_id:
            qs = qs.filter(channel_id=channel_id)

        # Keyword search in title
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(title__icontains=search)

        # Quick filter capsules — match title keywords
        capsule = self.request.query_params.get('capsule', '').strip().lower()
        if capsule:
            capsule_keywords = {
                'ev': ['ev', 'electric', 'bev', 'battery'],
                'hybrid': ['hybrid', 'phev', 'dm-i', 'erev', 'rev'],
                'suv': ['suv', 'crossover'],
                'sedan': ['sedan', 'saloon'],
                'review': ['review', 'test drive', 'first drive'],
                'walkaround': ['walkaround', 'walk-around', 'closer look', 'walk around'],
                'price': ['price', 'pricing', 'cost', 'affordable'],
            }
            keywords = capsule_keywords.get(capsule, [capsule])
            q = Q()
            for kw in keywords:
                q |= Q(title__icontains=kw)
            qs = qs.filter(q)

        # Sorting
        ordering = self.request.query_params.get('ordering', '-published_at')
        allowed = ['-published_at', 'published_at', '-view_count', 'view_count',
                   '-duration_seconds', 'duration_seconds', '-created_at']
        if ordering in allowed:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by('-published_at')

        return qs

    @action(detail=False, methods=['post'])
    def scan_channels(self, request):
        """Scan all enabled YouTube channels and save videos as candidates."""
        channels = YouTubeChannel.objects.filter(is_enabled=True)
        if not channels.exists():
            return Response({'message': 'No enabled channels', 'count': 0})

        try:
            from ai_engine.modules.youtube_client import YouTubeClient
            client = YouTubeClient()
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        cutoff = timezone.now() - timedelta(days=30)
        total_new = 0
        errors = []

        for ch in channels:
            try:
                videos = client.get_latest_videos(ch.channel_url, max_results=10)
                if videos:
                    videos = client.enrich_videos_metadata(videos)

                for v in (videos or []):
                    vid = v.get('id')
                    if not vid:
                        continue

                    # Parse published_at
                    pub_at = None
                    if v.get('published_at'):
                        from django.utils.dateparse import parse_datetime
                        pub_at = parse_datetime(v['published_at'])

                    # Skip videos older than 30 days
                    if pub_at and pub_at < cutoff:
                        continue

                    # Upsert — skip if already exists
                    _, created = YouTubeVideoCandidate.objects.get_or_create(
                        video_id=vid,
                        defaults={
                            'channel': ch,
                            'title': v.get('title', '')[:500],
                            'description': v.get('description', '')[:2000],
                            'thumbnail_url': v.get('thumbnail', ''),
                            'duration_seconds': v.get('duration_seconds'),
                            'view_count': v.get('view_count'),
                            'published_at': pub_at,
                        }
                    )
                    if created:
                        total_new += 1

            except Exception as e:
                err_msg = str(e)
                logger.warning(f"Scan error for {ch.name}: {err_msg}")
                errors.append({'channel': ch.name, 'error': err_msg[:200]})
                # If quota exceeded, stop scanning
                if 'quota' in err_msg.lower():
                    break

        return Response({
            'message': f'Scanned {channels.count()} channels, found {total_new} new videos',
            'new_count': total_new,
            'errors': errors,
        })

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a video — mark it as selected for article generation."""
        candidate = self.get_object()
        if candidate.status == 'approved':
            return Response({'message': 'Already approved'})

        candidate.status = 'approved'
        candidate.save(update_fields=['status'])

        return Response({
            'message': f'Approved: {candidate.title[:80]}',
        })

    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Dismiss a video — won't be shown again."""
        candidate = self.get_object()
        candidate.status = 'dismissed'
        candidate.save(update_fields=['status'])
        return Response({'message': f'Dismissed: {candidate.title[:80]}'})

    @action(detail=False, methods=['post'])
    def bulk_approve(self, request):
        """Approve multiple videos at once."""
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': 'ids required'}, status=status.HTTP_400_BAD_REQUEST)

        count = YouTubeVideoCandidate.objects.filter(id__in=ids, status='new').update(status='approved')

        return Response({
            'message': f'Approved {count} videos',
            'count': count,
        })

    @action(detail=False, methods=['post'])
    def bulk_dismiss(self, request):
        """Dismiss multiple videos."""
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': 'ids required'}, status=status.HTTP_400_BAD_REQUEST)

        count = YouTubeVideoCandidate.objects.filter(id__in=ids).update(status='dismissed')
        return Response({'message': f'Dismissed {count} videos'})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Quick stats for the inbox badge."""
        cutoff = timezone.now() - timedelta(days=30)
        qs = YouTubeVideoCandidate.objects.filter(published_at__gte=cutoff)
        return Response({
            'new_count': qs.filter(status='new').count(),
            'approved_count': qs.filter(status='approved').count(),
            'dismissed_count': qs.filter(status='dismissed').count(),
            'channels': list(
                YouTubeChannel.objects.filter(is_enabled=True)
                .values('id', 'name')
                .order_by('name')
            ),
        })

    @action(detail=False, methods=['get'])
    def generate_status(self, request):
        """Poll article generation status."""
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({'error': 'task_id required'}, status=status.HTTP_400_BAD_REQUEST)

        from django.core.cache import cache
        raw = cache.get(f'gen_task:{task_id}')
        if not raw:
            return Response({'status': 'not_found'}, status=status.HTTP_404_NOT_FOUND)

        return Response(json.loads(raw))

    @action(detail=False, methods=['post'])
    def cleanup_old(self, request):
        """Delete candidates older than 30 days."""
        cutoff = timezone.now() - timedelta(days=30)
        count, _ = YouTubeVideoCandidate.objects.filter(
            published_at__lt=cutoff
        ).delete()
        return Response({'message': f'Deleted {count} old candidates'})

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Trigger article generation for an approved video."""
        candidate = self.get_object()

        if candidate.status not in ('approved', 'generating'):
            return Response(
                {'error': 'Video must be approved first'},
                status=status.HTTP_400_BAD_REQUEST
            )

        provider = request.data.get('provider', 'gemini')
        task_id = self._generate_article(candidate, provider=provider)

        return Response({
            'message': f'Generation started: {candidate.title[:80]}',
            'task_id': task_id,
        })

    def _generate_article(self, candidate, provider='gemini'):
        """Spawn background article generation from a candidate."""
        import os
        import sys

        task_id = str(uuid.uuid4())

        # Persist generation state on the model
        candidate.status = 'generating'
        candidate.generation_task_id = task_id
        candidate.generation_error = ''
        candidate.save(update_fields=['status', 'generation_task_id', 'generation_error'])

        from django.core.cache import cache
        cache.set(f'gen_task:{task_id}', json.dumps({
            'status': 'running',
            'video_title': candidate.title,
            'channel': candidate.channel.name,
        }), timeout=600)

        def _run(task_id, candidate_id, channel_id, channel_name, video_url, video_id, video_title, provider):
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
                    generation_source='video_inbox',
                )

                if result.get('success'):
                    cache.set(f'gen_task:{task_id}', json.dumps({
                        'status': 'done', 'result': result,
                    }), timeout=600)
                    # Update model: back to approved (article now exists)
                    YouTubeVideoCandidate.objects.filter(id=candidate_id).update(
                        status='approved',
                        generation_task_id='',
                        generation_error='',
                    )
                else:
                    error_msg = result.get('error', 'Generation failed')
                    cache.set(f'gen_task:{task_id}', json.dumps({
                        'status': 'error',
                        'error': error_msg,
                    }), timeout=600)
                    # Update model: back to approved with error
                    YouTubeVideoCandidate.objects.filter(id=candidate_id).update(
                        status='approved',
                        generation_task_id='',
                        generation_error=error_msg[:500],
                    )
            except Exception as e:
                logger.error(f"[VideoInbox] generate failed: {e}", exc_info=True)
                error_msg = str(e)[:500]
                cache.set(f'gen_task:{task_id}', json.dumps({
                    'status': 'error', 'error': error_msg,
                }), timeout=600)
                # Update model with error
                YouTubeVideoCandidate.objects.filter(id=candidate_id).update(
                    status='approved',
                    generation_task_id='',
                    generation_error=error_msg,
                )
            finally:
                close_old_connections()

        t = threading.Thread(
            target=_run,
            args=(
                task_id,
                candidate.id,
                candidate.channel_id,
                candidate.channel.name,
                f"https://www.youtube.com/watch?v={candidate.video_id}",
                candidate.video_id,
                candidate.title,
                provider,
            ),
            daemon=True,
        )
        t.start()
        return task_id
