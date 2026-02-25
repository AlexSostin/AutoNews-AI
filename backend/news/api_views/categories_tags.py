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
from .articles import invalidate_article_cache, IsStaffOrReadOnly




class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = None  # Return all categories for dropdowns
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    lookup_field = 'slug'
    
    def get_queryset(self):
        """Filter categories by visibility for non-authenticated users"""
        queryset = super().get_queryset()
        # Admins see all categories, public users only see visible ones
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_visible=True)
        # Annotate article count to avoid N+1 queries in serializer
        if self.action == 'list':
            from django.db.models import Q
            queryset = queryset.annotate(
                _article_count=Count('articles', filter=Q(articles__is_published=True))
            )
        return queryset

    def get_object(self):
        """Support lookup by both slug and ID"""
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]
        
        try:
            if lookup_value.isdigit():
                obj = queryset.get(id=lookup_value)
            else:
                obj = queryset.get(slug=lookup_value)
        except Category.DoesNotExist:
            from django.shortcuts import get_object_or_404
            filter_kwargs = {self.lookup_field: lookup_value}
            obj = get_object_or_404(queryset, **filter_kwargs)
        
        self.check_object_permissions(self.request, obj)
        return obj

    def list(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return super().list(request, *args, **kwargs)
        return self._cached_list(request, *args, **kwargs)

    @method_decorator(cache_page(300))  # Cache for 5 minutes
    def _cached_list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        super().perform_create(serializer)
        invalidate_article_cache()  # Clear cache on write

    def perform_update(self, serializer):
        super().perform_update(serializer)
        invalidate_article_cache()

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        invalidate_article_cache()

class TagGroupViewSet(viewsets.ModelViewSet):
    queryset = TagGroup.objects.all()
    serializer_class = TagGroupSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = None  # Return all tags
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        # select_related to avoid N+1 for group_name in serializer
        queryset = queryset.select_related('group')
        # Annotate article count to avoid N+1 queries in serializer
        if self.action == 'list':
            queryset = queryset.annotate(
                _article_count=Count('article')
            )
        return queryset

    def list(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return super().list(request, *args, **kwargs)
        return self._cached_list(request, *args, **kwargs)

    @method_decorator(cache_page(300))  # Cache for 5 minutes
    def _cached_list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        super().perform_create(serializer)
        invalidate_article_cache()

    def perform_update(self, serializer):
        super().perform_update(serializer)
        invalidate_article_cache()

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        invalidate_article_cache()

