from rest_framework import viewsets, status, filters
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
            
            # Apply search filter
            if search_query:
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
    
    def perform_destroy(self, instance):
        """Soft delete: mark as deleted instead of removing from DB"""
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])
        
        # Invalidate cache
        try:
            invalidate_article_cache()
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
