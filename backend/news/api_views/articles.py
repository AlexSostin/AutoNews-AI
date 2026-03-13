from rest_framework import viewsets, status, filters
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Avg, Case, Count, Exists, IntegerField, OuterRef, Q, Subquery, Value, When
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, AllowAny, IsAdminUser
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.models import User
from django.utils import timezone
from ..models import (
    Article, Category, Tag, TagGroup, CarSpecification,
    ArticleImage, VehicleSpecs, Rating, Favorite,
)
from ..serializers import (
    ArticleListSerializer, ArticleDetailSerializer,
    CarSpecificationSerializer, VehicleSpecsSerializer,
)
from ._shared import invalidate_article_cache, trigger_nextjs_revalidation, IsStaffOrReadOnly, is_valid_youtube_url
from .mixins import ArticleGenerationMixin, ArticleEngagementMixin, ArticleEnrichmentMixin
import os
import sys
import re
import logging
import json

logger = logging.getLogger(__name__)


class ArticleViewSet(
    ArticleGenerationMixin,
    ArticleEngagementMixin,
    ArticleEnrichmentMixin,
    viewsets.ModelViewSet,
):
    """
    ArticleViewSet — core CRUD + mixin-based actions.

    Mixins provide:
    - ArticleGenerationMixin: generate_from_youtube, translate_enhance, reformat_content, regenerate
    - ArticleEngagementMixin: rate, get_user_rating, increment_views, recommended, submit_feedback,
      ab_title, ab_click, ab_stats, ab_pick_winner, ab_image, ab_image_click, ab_image_stats,
      ab_image_pick_winner, trending, popular, reset_all_views, similar_articles
    - ArticleEnrichmentMixin: extract_specs, re_enrich, bulk_re_enrich, bulk_re_enrich_status,
      debug_vehicle_specs
    """
    queryset = Article.objects.filter(is_deleted=False).select_related('specs').prefetch_related('categories', 'tags', 'gallery').annotate(
        avg_rating=Avg('ratings__rating'),
        num_ratings=Count('ratings'),
    )
    permission_classes = [IsStaffOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content', 'summary']
    ordering_fields = ['created_at', 'views', 'title']
    ordering = ['-created_at']

    def get_object(self):
        """Support both slug and numeric ID lookup.
        
        Public pages use slug: /articles/tesla-model-3/
        Admin pages use ID:    /articles/126/
        """
        queryset = self.filter_queryset(self.get_queryset())
        lookup_value = self.kwargs.get(self.lookup_field, '')
        
        # If the lookup value is numeric, search by pk instead of slug
        if lookup_value.isdigit():
            obj = get_object_or_404(queryset, pk=int(lookup_value))
        else:
            obj = get_object_or_404(queryset, slug=lookup_value)
        
        self.check_object_permissions(self.request, obj)
        return obj
    
    def get_permissions(self):
        """
        Allow anyone to rate articles and check their rating,
        but require staff for other write operations
        """
        if self.action in ['rate', 'get_user_rating', 'increment_views', 'submit_feedback']:
            return [AllowAny()]
        return super().get_permissions()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ArticleListSerializer
        return ArticleDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Handle search parameter for combined title + content search
        search_query = self.request.query_params.get('search', '')
        is_list = self.action == 'list'
        
        # Determine if user is admin based on request authentication
        is_admin = self.request.user.is_authenticated and self.request.user.is_staff
        
        if is_list:
            # PUBLIC USER: only show published (unless admin)
            if not is_admin:
                queryset = queryset.filter(is_published=True)
            
            # Apply search filter — PostgreSQL Full-Text Search with ranking
            if search_query:
                if len(search_query) >= 2:
                    # Full-Text Search with weighted ranking: title A > summary B > content C
                    search_vector = SearchVector('title', weight='A') + \
                                    SearchVector('summary', weight='B') + \
                                    SearchVector('content', weight='C')
                    search_q = SearchQuery(search_query, search_type='websearch')
                    queryset = queryset.annotate(
                        search_rank=SearchRank(search_vector, search_q)
                    ).filter(search_rank__gt=0.0).order_by('-search_rank')
                else:
                    # Fallback for single-character queries
                    queryset = queryset.filter(
                        Q(title__icontains=search_query) |
                        Q(content__icontains=search_query)
                    )
            
            # Apply tag filter
            tag_slug = self.request.query_params.get('tag')
            if tag_slug:
                queryset = queryset.filter(tags__slug=tag_slug)
            
            # Apply category filter
            category_slug = self.request.query_params.get('category')
            if category_slug:
                queryset = queryset.filter(categories__slug=category_slug)

            # Apply status filter (admin only)
            status_filter = self.request.query_params.get('status')
            if status_filter and is_admin:
                if status_filter == 'published':
                    queryset = queryset.filter(is_published=True)
                elif status_filter == 'draft':
                    queryset = queryset.filter(is_published=False)
            
            # Defer heavy fields to avoid loading full content in list views
            queryset = queryset.defer(
                'content', 'content_original',
                'seo_description', 'meta_keywords',
                'engagement_score', 'engagement_updated_at',
                'generation_metadata',
            )
        else:
            # Detail view: For non-admin users, only show published articles
            if not is_admin:
                queryset = queryset.filter(is_published=True)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Cache article list for anonymous users (60s), admins always get fresh data."""
        if request.user.is_authenticated:
            return super().list(request, *args, **kwargs)
        return self._cached_list(request, *args, **kwargs)

    @method_decorator(cache_page(60, key_prefix='articles_list'))  # Cache for 1 minute
    def _cached_list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def perform_destroy(self, instance):
        """Soft delete: mark as deleted instead of removing from DB"""
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])
        
        # Audit log
        try:
            from news.models import AdminActionLog
            AdminActionLog.log(instance, self.request.user, 'delete', details={
                'title': instance.title[:100],
            })
        except Exception:
            pass
        
        # Invalidate cache
        try:
            invalidate_article_cache()
        except Exception:
            pass

    def perform_create(self, serializer):
        """After creating a new article, invalidate cache so it appears on the public site."""
        instance = serializer.save()
        try:
            invalidate_article_cache(article_id=instance.id, slug=instance.slug)
        except Exception as e:
            logger.warning(f"Cache invalidation after create failed: {e}")
        # Also trigger revalidation for specific article page
        try:
            trigger_nextjs_revalidation(paths=['/', '/articles', f'/articles/{instance.slug}'])
        except Exception:
            pass

    def update(self, request, *args, **kwargs):
        """Override update to handle image deletion flags and cache invalidation"""
        kwargs['partial'] = True  # Always allow partial updates
        
        # Clone QueryDict to make it mutable (needed for admin form data)
        if hasattr(request.data, '_mutable'):
            request.data._mutable = True

        # Fix: Convert JSON string for categories and tags to proper format
        categories_raw = request.data.get('categories')
        if isinstance(categories_raw, str):
            try:
                categories = json.loads(categories_raw)
                if isinstance(categories, list):
                    request.data.setlist('categories', [str(c) for c in categories])
            except (json.JSONDecodeError, ValueError):
                pass

        tags_raw = request.data.get('tags')
        if isinstance(tags_raw, str):
            try:
                tags = json.loads(tags_raw)
                if isinstance(tags, list):
                    request.data.setlist('tags', [str(t) for t in tags])
            except (json.JSONDecodeError, ValueError):
                pass

        # Helper to check for boolean flags in form data (which come as strings 'true'/'false')
        def is_true(key):
            val = request.data.get(key)
            return val and str(val).lower() == 'true'

        # Strip internal-only warnings from content before saving
        import re
        content = request.data.get('content')
        if content and 'entity-mismatch-warning' in content:
            cleaned = re.sub(
                r'<div[^>]*class="entity-mismatch-warning"[^>]*>[\s\S]*?</div>',
                '', content
            ).strip()
            if hasattr(request.data, '_mutable'):
                request.data._mutable = True
            request.data['content'] = cleaned
            logger.info(f"[UPDATE] Stripped entity-mismatch-warning from article content")

        # Perform update in atomic transaction
        try:
            from django.db import transaction
            with transaction.atomic():
                response = super().update(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in ArticleViewSet.update super().update: {e}")
            raise
        
        # Then handle deletions if successful
        if response.status_code == 200:
            try:
                instance = self.get_object()
                changed = False
                
                if is_true('delete_image'):
                    instance.image = None
                    changed = True
                if is_true('delete_image_2'):
                    instance.image_2 = None
                    changed = True
                if is_true('delete_image_3'):
                    instance.image_3 = None
                    changed = True
                    
                if changed:
                    instance.save()
                    serializer = self.get_serializer(instance)
                    response = Response(serializer.data)
                
                # If title was changed, clear stale A/B variants
                try:
                    from news.models import ArticleTitleVariant
                    if 'title' in request.data:
                        deleted_count, _ = ArticleTitleVariant.objects.filter(article=instance).delete()
                        if deleted_count:
                            logger.info(f"[UPDATE] Cleared {deleted_count} stale A/B variants for article {instance.id}")
                except Exception:
                    pass
                
                # Selectively invalidate cache
                try:
                    invalidate_article_cache(
                        article_id=instance.id,
                        slug=instance.slug
                    )
                except Exception as cache_err:
                    logger.warning(f"Failed to invalidate article cache: {cache_err}")
                
                # Log admin action
                try:
                    from news.models import AdminActionLog
                    AdminActionLog.log(instance, request.user, 'edit_save', details={
                        'image_source': request.data.get('image_source', ''),
                        'has_new_image': bool(request.data.get('image')),
                    })
                except Exception:
                    pass
                    
            except Exception as inner_err:
                logger.error(f"Error in ArticleViewSet.update post-processing: {inner_err}")
                
        return response

    # ── Publish Queue ────────────────────────────────────────────────
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def publish_queue(self, request):
        """Return draft + scheduled articles for the Publish Queue UI."""
        articles = Article.objects.filter(
            is_deleted=False,
            is_published=False,
        ).select_related('specs').prefetch_related('categories').order_by(
            # Scheduled first (by time), then unscheduled (by created_at)
            'scheduled_publish_at',  # NULLs go last in PostgreSQL with default ordering
            '-created_at',
        ).defer('content', 'content_original', 'generation_metadata')

        data = []
        for a in articles[:50]:  # max 50
            cats = [{'id': c.id, 'name': c.name, 'slug': c.slug} for c in a.categories.all()]
            img_url = ''
            if a.image:
                try:
                    url = a.image.url
                    if url and not url.startswith('http'):
                        # Cloudinary may return relative path — build absolute URI
                        url = request.build_absolute_uri(url)
                    img_url = url or ''
                except Exception:
                    raw = str(a.image)
                    if raw.startswith('http'):
                        img_url = raw
                    else:
                        img_url = ''

            data.append({
                'id': a.id,
                'title': a.title,
                'slug': a.slug,
                'image': img_url,
                'summary': (a.summary or '')[:120],
                'categories': cats,
                'scheduled_publish_at': a.scheduled_publish_at.isoformat() if a.scheduled_publish_at else None,
                'created_at': a.created_at.isoformat(),
                'is_published': a.is_published,
            })

        # Stats
        total_drafts = Article.objects.filter(is_deleted=False, is_published=False).count()
        scheduled = Article.objects.filter(
            is_deleted=False, is_published=False,
            scheduled_publish_at__isnull=False,
        ).count()
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timezone.timedelta(days=1)
        publishing_today = Article.objects.filter(
            is_deleted=False, is_published=False,
            scheduled_publish_at__gte=today_start,
            scheduled_publish_at__lt=today_end,
        ).count()

        return Response({
            'articles': data,
            'stats': {
                'total_drafts': total_drafts,
                'scheduled': scheduled,
                'unscheduled': total_drafts - scheduled,
                'publishing_today': publishing_today,
            },
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def batch_schedule(self, request):
        """Auto-assign scheduled_publish_at to multiple articles with interval.

        Body: { article_ids: [1,2,3], start_time: "ISO", interval_hours: 3 }
        """
        article_ids = request.data.get('article_ids', [])
        start_time_str = request.data.get('start_time')
        interval_hours = float(request.data.get('interval_hours', 3))

        if not article_ids:
            return Response({'error': 'article_ids required'}, status=status.HTTP_400_BAD_REQUEST)
        if not start_time_str:
            return Response({'error': 'start_time required'}, status=status.HTTP_400_BAD_REQUEST)

        from datetime import timedelta, datetime as dt
        try:
            # Python stdlib ISO parse (strip trailing Z for compatibility)
            cleaned = start_time_str.replace('Z', '+00:00')
            start_time = dt.fromisoformat(cleaned)
            if timezone.is_naive(start_time):
                start_time = timezone.make_aware(start_time)
        except Exception:
            return Response({'error': 'Invalid start_time format'}, status=status.HTTP_400_BAD_REQUEST)

        updated = []
        for i, aid in enumerate(article_ids):
            try:
                article = Article.objects.get(pk=aid, is_deleted=False)
                scheduled_at = start_time + timedelta(hours=interval_hours * i)
                article.scheduled_publish_at = scheduled_at
                article.is_published = False  # ensure it stays draft until scheduler picks it up
                article.save(update_fields=['scheduled_publish_at', 'is_published'])
                updated.append({
                    'id': article.id,
                    'title': article.title[:80],
                    'scheduled_publish_at': scheduled_at.isoformat(),
                })
            except Article.DoesNotExist:
                continue

        return Response({
            'success': True,
            'scheduled_count': len(updated),
            'articles': updated,
        })
