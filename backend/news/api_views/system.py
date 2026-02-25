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
from .articles import IsStaffOrReadOnly




class SiteSettingsViewSet(viewsets.ModelViewSet):
    queryset = SiteSettings.objects.all()
    serializer_class = SiteSettingsSerializer
    permission_classes = [IsStaffOrReadOnly]
    
    @method_decorator(cache_page(300))  # Cache settings for 5 minutes — rarely changes
    def list(self, request):
        """Return the single settings instance"""
        settings = SiteSettings.load()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Always return the single settings instance"""
        settings = SiteSettings.load()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """Always update the single settings instance"""
        settings = SiteSettings.load()
        serializer = self.get_serializer(settings, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class CurrencyRatesView(APIView):
    """
    Get current exchange rates for USD to EUR and CNY.
    Cached for 1 hour to avoid excessive API calls.
    """
    permission_classes = [AllowAny]
    
    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    def get(self, request):
        cache_key = 'currency_rates_usd'
        rates = cache.get(cache_key)
        
        if not rates:
            try:
                # Using free exchangerate-api.com
                response = http_requests.get(
                    'https://open.er-api.com/v6/latest/USD',
                    timeout=10
                )
                data = response.json()
                
                if data.get('result') == 'success':
                    all_rates = data.get('rates', {})
                    rates = {
                        'USD': 1.0,
                        'EUR': all_rates.get('EUR', 0.92),
                        'CNY': all_rates.get('CNY', 7.25),
                        'GBP': all_rates.get('GBP', 0.79),
                        'JPY': all_rates.get('JPY', 148.5),
                        'updated_at': data.get('time_last_update_utc', '')
                    }
                    cache.set(cache_key, rates, 60 * 60)  # Cache for 1 hour
                else:
                    # Fallback rates
                    rates = {
                        'USD': 1.0,
                        'EUR': 0.92,
                        'CNY': 7.25,
                        'GBP': 0.79,
                        'JPY': 148.5,
                        'updated_at': 'fallback'
                    }
            except Exception as e:
                logger.warning(f"Failed to fetch currency rates: {e}")
                rates = {
                    'USD': 1.0,
                    'EUR': 0.92,
                    'CNY': 7.25,
                    'GBP': 0.79,
                    'JPY': 148.5,
                    'updated_at': 'fallback'
                }
        
        return Response(rates)

class AdminNotificationViewSet(viewsets.ModelViewSet):
    """
    Admin notifications management.
    Shows notifications for comments, subscribers, errors, etc.
    """
    queryset = AdminNotification.objects.all()
    serializer_class = AdminNotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter notifications for admin users only"""
        if not self.request.user.is_staff:
            return AdminNotification.objects.none()
        return AdminNotification.objects.all().order_by('-created_at')
    
    def list(self, request):
        """Get all notifications with unread count"""
        queryset = self.get_queryset()
        
        # Optional filters
        is_unread = request.query_params.get('unread', None)
        notification_type = request.query_params.get('type', None)
        limit = request.query_params.get('limit', None)
        
        if is_unread == 'true':
            queryset = queryset.filter(is_read=False)
        
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        # Get counts before limiting
        unread_count = self.get_queryset().filter(is_read=False).count()
        total_count = self.get_queryset().count()
        
        if limit:
            queryset = queryset[:int(limit)]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'notifications': serializer.data,
            'unread_count': unread_count,
            'total_count': total_count
        })
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a single notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        count = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({
            'status': 'all marked as read',
            'count': count
        })
    
    @action(detail=False, methods=['post'])
    def clear_all(self, request):
        """Delete all read notifications"""
        count, _ = self.get_queryset().filter(is_read=True).delete()
        return Response({
            'status': 'cleared read notifications',
            'count': count
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get just the unread count (for polling)"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})
    
    @action(detail=False, methods=['post'])
    def create_test(self, request):
        """Create a test notification (for development)"""
        if not request.user.is_superuser:
            return Response({'error': 'Superuser required'}, status=status.HTTP_403_FORBIDDEN)
        
        notification = AdminNotification.create_notification(
            notification_type=request.data.get('type', 'info'),
            title=request.data.get('title', 'Test Notification'),
            message=request.data.get('message', 'This is a test notification.'),
            link=request.data.get('link', ''),
            priority=request.data.get('priority', 'normal')
        )
        serializer = self.get_serializer(notification)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class AdPlacementViewSet(viewsets.ModelViewSet):
    """Admin ViewSet for managing ad placements.
    
    GET /api/v1/ads/                  — list all ads (admin)
    POST /api/v1/ads/                 — create ad (admin)
    GET /api/v1/ads/{id}/             — get ad details (admin)
    PUT /api/v1/ads/{id}/             — update ad (admin)
    DELETE /api/v1/ads/{id}/          — delete ad (admin)
    POST /api/v1/ads/{id}/track_click/ — track click (public)
    GET /api/v1/ads/active/           — get active ads for position (public)
    """
    
    def get_serializer_class(self):
        from news.serializers import AdPlacementSerializer
        return AdPlacementSerializer
    
    def get_permissions(self):
        if self.action in ('active', 'track_click'):
            return [AllowAny()]
        return [IsAdminUser()]
    
    def get_queryset(self):
        from news.models import AdPlacement
        qs = AdPlacement.objects.all()
        
        # Filter by position
        position = self.request.query_params.get('position')
        if position:
            qs = qs.filter(position=position)
        
        # Filter by active status
        active = self.request.query_params.get('active')
        if active == 'true':
            qs = qs.filter(is_active=True)
        elif active == 'false':
            qs = qs.filter(is_active=False)
        
        # Filter by ad type
        ad_type = self.request.query_params.get('ad_type')
        if ad_type:
            qs = qs.filter(ad_type=ad_type)
        
        return qs
    
    @action(detail=False, methods=['get'], url_path='active')
    def active(self, request):
        """Public endpoint: get currently active ads for a position.
        GET /api/v1/ads/active/?position=header
        """
        from news.models import AdPlacement
        from django.utils import timezone
        from django.db.models import Q, F
        
        position = request.query_params.get('position')
        if not position:
            return Response({'results': []})
        
        now = timezone.now()
        qs = AdPlacement.objects.filter(
            is_active=True,
            position=position,
        ).filter(
            Q(start_date__isnull=True) | Q(start_date__lte=now)
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        ).order_by('-priority')
        
        # Track impressions
        qs.update(impressions=F('impressions') + 1)
        
        serializer = self.get_serializer(qs, many=True)
        return Response({'results': serializer.data})
    
    @action(detail=True, methods=['post'], url_path='track-click')
    def track_click(self, request, pk=None):
        """Public endpoint: track ad click.
        POST /api/v1/ads/{id}/track-click/
        """
        from news.models import AdPlacement
        from django.db.models import F
        ad = self.get_object()
        AdPlacement.objects.filter(pk=ad.pk).update(clicks=F('clicks') + 1)
        return Response({'success': True, 'redirect': ad.link})

class SiteThemeView(APIView):
    """Public endpoint — returns current site theme (no auth required)."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        settings = AutomationSettings.load()
        theme = settings.site_theme if settings.site_theme != 'default' else ''
        return Response({'theme': theme})

class ThemeAnalyticsView(APIView):
    """Track which theme visitors choose — anonymous analytics."""
    permission_classes = [AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='6/h', method='POST', block=True))
    def post(self, request):
        theme = request.data.get('theme', '')
        if not theme or len(theme) > 30:
            return Response({'error': 'Invalid theme'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create anonymous session hash from IP + User-Agent
        import hashlib
        raw = f"{request.META.get('REMOTE_ADDR', '')}-{request.META.get('HTTP_USER_AGENT', '')}"
        session_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
        
        from news.models import ThemeAnalytics
        # Upsert: update if same session already recorded, else create
        ThemeAnalytics.objects.update_or_create(
            session_hash=session_hash,
            defaults={'theme': theme},
        )
        
        return Response({'status': 'ok'})
    
    def get(self, request):
        """Admin-only: get theme popularity stats."""
        if not request.user.is_staff:
            return Response({'detail': 'Admin only'}, status=status.HTTP_403_FORBIDDEN)
        
        from news.models import ThemeAnalytics
        from django.db.models import Count
        
        stats = (
            ThemeAnalytics.objects
            .values('theme')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        total = ThemeAnalytics.objects.count()
        
        return Response({
            'total_users': total,
            'themes': [
                {
                    'theme': s['theme'],
                    'count': s['count'],
                    'percent': round(s['count'] / total * 100, 1) if total else 0,
                }
                for s in stats
            ],
        })

class AutomationSettingsView(APIView):
    """GET/PUT automation settings (singleton)."""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        settings = AutomationSettings.load()
        serializer = AutomationSettingsSerializer(settings)
        return Response(serializer.data)
    
    def put(self, request):
        settings = AutomationSettings.load()
        serializer = AutomationSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AutomationStatsView(APIView):
    """GET automation statistics overview with safety & decision data."""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        from news.models import AutoPublishLog
        
        settings = AutomationSettings.load()
        settings.reset_daily_counters()
        
        # Count pending articles by quality
        pending_total = PendingArticle.objects.filter(status='pending').count()
        pending_high_quality = PendingArticle.objects.filter(
            status='pending',
            quality_score__gte=settings.auto_publish_min_quality
        ).count()
        
        # Today's published articles  
        today = timezone.now().date()
        published_today = Article.objects.filter(
            is_published=True,
            created_at__date=today
        ).count()
        
        # === Safety Overview: feed counts by safety_score & image_policy ===
        from news.models import RSSFeed
        enabled_feeds = RSSFeed.objects.filter(is_enabled=True)
        all_feeds_list = list(enabled_feeds.values('license_status', 'image_policy', 'safety_checks'))
        
        safety_counts = {'safe': 0, 'review': 0, 'unsafe': 0}
        image_policy_counts = {'original': 0, 'pexels_only': 0, 'pexels_fallback': 0, 'unchecked': 0}
        
        for f_data in all_feeds_list:
            # Compute safety_score the same way the model property does
            checks = f_data.get('safety_checks') or {}
            license_st = f_data.get('license_status', 'unchecked')
            
            if license_st == 'red':
                ss = 'unsafe'
            elif not checks:
                ss = 'review'
            else:
                passed = sum(1 for c in checks.values() if isinstance(c, dict) and c.get('passed'))
                total = len([c for c in checks.values() if isinstance(c, dict)])
                if total == 0:
                    ss = 'review'
                elif passed == total and license_st == 'green':
                    ss = 'safe'
                else:
                    ss = 'review'
            
            safety_counts[ss] = safety_counts.get(ss, 0) + 1
            
            img_pol = f_data.get('image_policy') or ''
            if img_pol in image_policy_counts:
                image_policy_counts[img_pol] += 1
            else:
                image_policy_counts['unchecked'] += 1
        
        # === Eligible articles breakdown ===
        eligible_qs = PendingArticle.objects.filter(
            status='pending',
            quality_score__gte=settings.auto_publish_min_quality
        ).select_related('rss_feed')
        
        eligible_safe = 0
        eligible_review = 0
        eligible_unsafe = 0
        for pa in eligible_qs:
            feed = pa.rss_feed
            if feed:
                ss = getattr(feed, 'safety_score', 'review')
                if ss == 'safe':
                    eligible_safe += 1
                elif ss == 'unsafe':
                    eligible_unsafe += 1
                else:
                    eligible_review += 1
            else:
                eligible_review += 1
        
        # === Decision Log: last 30 decisions ===
        recent_decisions = AutoPublishLog.objects.order_by('-created_at')[:30]
        decisions_data = [
            {
                'id': d.id,
                'title': d.article_title[:80],
                'decision': d.decision,
                'reason': d.reason,
                'quality_score': d.quality_score,
                'safety_score': d.safety_score,
                'image_policy': d.image_policy,
                'feed_name': d.feed_name,
                'source_type': d.source_type,
                'has_image': d.has_image,
                'source_is_youtube': d.source_is_youtube,
                'created_at': d.created_at,
            }
            for d in recent_decisions
        ]
        
        # === Decision breakdown (all-time counts) ===
        from django.db.models import Count
        breakdown_qs = AutoPublishLog.objects.values('decision').annotate(count=Count('id'))
        decision_breakdown = {item['decision']: item['count'] for item in breakdown_qs}
        total_decisions = sum(decision_breakdown.values())
        
        # Recent auto-published (for backwards compatibility)
        recent_auto = PendingArticle.objects.filter(
            status='published',
            is_auto_published=True
        ).order_by('-reviewed_at')[:10]
        
        return Response({
            'pending_total': pending_total,
            'pending_high_quality': pending_high_quality,
            'published_today': published_today,
            'auto_published_today': settings.auto_publish_today_count,
            'rss_articles_today': settings.rss_articles_today,
            'youtube_articles_today': settings.youtube_articles_today,
            # Safety overview
            'safety_overview': {
                'safety_counts': safety_counts,
                'image_policy_counts': image_policy_counts,
                'total_feeds': len(all_feeds_list),
            },
            # Eligible breakdown
            'eligible': {
                'total': eligible_safe + eligible_review + eligible_unsafe,
                'safe': eligible_safe,
                'review': eligible_review,
                'unsafe': eligible_unsafe,
            },
            # Decision log
            'recent_decisions': decisions_data,
            'decision_breakdown': decision_breakdown,
            'total_decisions': total_decisions,
            # Legacy
            'recent_auto_published': [
                {
                    'id': p.id,
                    'title': p.title[:80],
                    'quality_score': p.quality_score,
                    'published_at': p.reviewed_at,
                }
                for p in recent_auto
            ],
        })

class AutomationTriggerView(APIView):
    """POST manual triggers for automation tasks."""
    permission_classes = [IsAdminUser]
    
    TASK_LOCK_MAP = {
        'rss': 'rss',
        'youtube': 'youtube',
        'auto-publish': 'auto_publish',
        'score': 'score',
        'deep-specs': 'deep_specs',
    }
    
    def post(self, request, task_type):
        import threading
        from news.models import AutomationSettings
        
        # Check lock — return 409 if task is already running
        lock_name = self.TASK_LOCK_MAP.get(task_type)
        if lock_name:
            settings = AutomationSettings.load()
            lock_field = f'{lock_name}_lock'
            if getattr(settings, lock_field, False):
                return Response(
                    {'error': f'{task_type} is already running', 'status': 'locked'},
                    status=status.HTTP_409_CONFLICT
                )
        
        if task_type == 'rss':
            from news.scheduler import _run_rss_scan
            threading.Thread(target=_run_rss_scan, daemon=True).start()
            return Response({'message': 'RSS scan triggered', 'status': 'running'})
        
        elif task_type == 'youtube':
            from news.scheduler import _run_youtube_scan
            threading.Thread(target=_run_youtube_scan, daemon=True).start()
            return Response({'message': 'YouTube scan triggered', 'status': 'running'})
        
        elif task_type == 'auto-publish':
            from news.scheduler import _run_auto_publish
            threading.Thread(target=_run_auto_publish, daemon=True).start()
            return Response({'message': 'Auto-publish triggered', 'status': 'running'})
        
        elif task_type == 'score':
            from news.scheduler import _score_new_pending_articles
            threading.Thread(target=_score_new_pending_articles, daemon=True).start()
            return Response({'message': 'Quality scoring triggered', 'status': 'running'})
        
        elif task_type == 'deep-specs':
            from news.scheduler import _run_deep_specs_backfill
            threading.Thread(target=_run_deep_specs_backfill, daemon=True).start()
            return Response({'message': 'VehicleSpecs backfill triggered', 'status': 'running'})
        
        return Response(
            {'error': f'Unknown task type: {task_type}'},
            status=status.HTTP_400_BAD_REQUEST
        )

class AdminActionStatsView(APIView):
    """
    GET /api/v1/admin/action-stats/
    Returns aggregated statistics about admin actions on articles.
    Staff only.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_staff:
            return Response({'detail': 'Staff only.'}, status=status.HTTP_403_FORBIDDEN)
        
        from news.models import AdminActionLog
        from django.db.models import Count, Avg, Q
        from django.utils import timezone
        from datetime import timedelta
        
        # Total counts by action type
        by_action = dict(
            AdminActionLog.objects.values_list('action')
            .annotate(count=Count('id'))
            .values_list('action', 'count')
        )
        
        total = sum(by_action.values())
        
        # Recent 20 actions
        recent = list(
            AdminActionLog.objects.select_related('article', 'user')
            .values(
                'id', 'action', 'success', 'details', 'created_at',
                'article__id', 'article__title',
                'user__username',
            )
            .order_by('-created_at')[:20]
        )
        
        # Insights
        insights = {}
        
        # Most reformatted articles (multiple reformats = content quality issue)
        most_reformatted = list(
            AdminActionLog.objects.filter(action='reformat', success=True)
            .values('article__id', 'article__title')
            .annotate(count=Count('id'))
            .filter(count__gte=2)
            .order_by('-count')[:5]
        )
        insights['most_reformatted'] = most_reformatted
        
        # Most regenerated articles
        most_regenerated = list(
            AdminActionLog.objects.filter(action='regenerate', success=True)
            .values('article__id', 'article__title')
            .annotate(count=Count('id'))
            .filter(count__gte=2)
            .order_by('-count')[:5]
        )
        insights['most_regenerated'] = most_regenerated
        
        # Average reformat reduction percentage
        reformat_details = AdminActionLog.objects.filter(
            action='reformat', success=True, details__isnull=False
        ).values_list('details', flat=True)
        
        reductions = []
        for d in reformat_details:
            if isinstance(d, dict) and 'reduction_pct' in d:
                reductions.append(d['reduction_pct'])
        
        insights['avg_reformat_reduction_pct'] = round(sum(reductions) / len(reductions), 1) if reductions else 0
        
        # Actions in last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        weekly_by_action = dict(
            AdminActionLog.objects.filter(created_at__gte=week_ago)
            .values_list('action')
            .annotate(count=Count('id'))
            .values_list('action', 'count')
        )
        insights['last_7_days'] = weekly_by_action
        
        return Response({
            'total_actions': total,
            'by_action': by_action,
            'recent_actions': recent,
            'insights': insights,
        })

