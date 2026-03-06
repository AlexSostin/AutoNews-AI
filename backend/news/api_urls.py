from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status as http_status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
import logging

logger = logging.getLogger('news')
from .api_views import (
    ArticleViewSet, CategoryViewSet, TagViewSet, TagGroupViewSet, 
    CommentViewSet, RatingViewSet, CarSpecificationViewSet, 
    ArticleImageViewSet, SiteSettingsViewSet, UserViewSet, AdminUserManagementViewSet,
    FavoriteViewSet, SubscriberViewSet,
    YouTubeChannelViewSet, RSSFeedViewSet, RSSNewsItemViewSet, PendingArticleViewSet,
    AdminNotificationViewSet, VehicleSpecsViewSet, BrandAliasViewSet,
    ArticleFeedbackViewSet, GenerateAIImageView,
    SearchPhotosView, SaveExternalImageView, ProxyImageView,
    AdPlacementViewSet,
    AutomationSettingsView, AutomationStatsView, AutomationTriggerView,
    SiteThemeView, ThemeAnalyticsView, CapsuleFeedbackView,
    AdminActionStatsView, FrontendEventLogViewSet, BackendErrorLogViewSet, HealthSummaryView, NavBadgesView
)
from .health import health_check, health_check_detailed, readiness_check
from .api_views.system_graph import SystemGraphView, EmbeddingStatsView
from .ab_testing_views import (
    ABImpressionView, ABClickView, ABTestsListView,
    ABPickWinnerView, ABAutoPickView
)
from .api_views.two_factor import (
    TwoFactorSetupView, TwoFactorConfirmView, TwoFactorVerifyView,
    TwoFactorGoogleVerifyView, TwoFactorDisableView, TwoFactorStatusView
)


# Rate-limited token views for security
class RateLimitedTokenObtainPairView(TokenObtainPairView):
    """Token view with rate limiting + login activity logging + 2FA check"""
    @method_decorator(ratelimit(key='ip', rate='5/15m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
        if ',' in ip:
            ip = ip.split(',')[0].strip()
        username = request.data.get('username', '(empty)')
        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == 200:
                # Check if user has 2FA enabled — only for is_staff users
                try:
                    from django.contrib.auth.models import User
                    from news.models import TOTPDevice
                    user = User.objects.get(username__iexact=username)
                    # 2FA is only required for staff/admin accounts, not regular users
                    if user.is_staff:
                        has_2fa = TOTPDevice.objects.filter(user=user, is_confirmed=True).exists()
                        logger.info(f"🔐 2FA check: user={user.username} is_staff=True has_2fa={has_2fa}")
                        if has_2fa:
                            logger.info(f"🔐 Login requires 2FA: user={user.username} ip={ip}")
                            return Response({
                                'requires_2fa': True,
                                'message': 'Please provide your 2FA code.',
                            }, status=200)
                except User.DoesNotExist:
                    logger.warning(f"⚠️ 2FA check: user not found username={username}")
                except Exception as e:
                    logger.error(f"❌ 2FA check ERROR: {type(e).__name__}: {e}")
                logger.info(f"🔑 Login SUCCESS: user={username} ip={ip}")
            return response
        except Exception as e:
            logger.warning(f"🔒 Login FAILED: user={username} ip={ip} reason={type(e).__name__}")
            raise


class RateLimitedTokenRefreshView(TokenRefreshView):
    """Token refresh with rate limiting"""
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    """Blacklist the refresh token for instant logout"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': 'Refresh token is required.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info(f"🚪 Logout: user={request.user.username}")
            return Response({'detail': 'Successfully logged out.'}, status=http_status.HTTP_200_OK)
        except TokenError:
            return Response({'detail': 'Token is invalid or already blacklisted.'}, status=http_status.HTTP_400_BAD_REQUEST)

router = DefaultRouter()
router.register(r'articles', ArticleViewSet, basename='article')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'tag-groups', TagGroupViewSet, basename='taggroup')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'ratings', RatingViewSet, basename='rating')
router.register(r'car-specifications', CarSpecificationViewSet, basename='carspecification')
router.register(r'article-images', ArticleImageViewSet, basename='articleimage')
router.register(r'settings', SiteSettingsViewSet, basename='settings')
router.register(r'users', UserViewSet, basename='user')
router.register(r'favorites', FavoriteViewSet, basename='favorite')
router.register(r'subscribers', SubscriberViewSet, basename='subscriber')
router.register(r'youtube-channels', YouTubeChannelViewSet, basename='youtube-channel')
router.register(r'rss-feeds', RSSFeedViewSet, basename='rss-feed')
router.register(r'rss-news-items', RSSNewsItemViewSet, basename='rss-news-item')
router.register(r'pending-articles', PendingArticleViewSet, basename='pending-article')
router.register(r'notifications', AdminNotificationViewSet, basename='notification')
router.register(r'vehicle-specs', VehicleSpecsViewSet, basename='vehicle-specs')
router.register(r'brand-aliases', BrandAliasViewSet, basename='brand-alias')
router.register(r'feedback', ArticleFeedbackViewSet, basename='feedback')
router.register(r'ads', AdPlacementViewSet, basename='ad')
router.register(r'frontend-events', FrontendEventLogViewSet, basename='frontend-event')
router.register(r'backend-errors', BackendErrorLogViewSet, basename='backend-error')
from .api_views import (
    CurrencyRatesView, CurrentUserView, ChangePasswordView, EmailPreferencesView,
    RequestEmailChangeView, VerifyEmailChangeView,
    PasswordResetRequestView, PasswordResetConfirmView, NewsletterSubscribeView
)
from .search_analytics_views import (
    SearchAPIView, AnalyticsOverviewAPIView, AnalyticsTopArticlesAPIView,
    AnalyticsViewsTimelineAPIView, AnalyticsCategoriesAPIView, GSCAnalyticsAPIView,
    AnalyticsAIStatsAPIView, AnalyticsAIGenerationAPIView, AnalyticsPopularModelsAPIView,
    AnalyticsProviderStatsAPIView, TrackReadMetricView, TrackLinkClickView,
    TrackMicroFeedbackView, TrackPageAnalyticsView, ReadingNowView,
    AnalyticsExtraStatsAPIView
)
from .cars import CarBrandsListView, CarBrandDetailView, CarModelDetailView, BrandCleanupView, BrandViewSet, CarCompareView, CarPickerListView

urlpatterns = [
    # Health check endpoints (for load balancers and monitoring)
    path('health/', health_check, name='health_check'),
    path('health/errors-summary/', HealthSummaryView.as_view(), name='health_errors_summary'),
    path('health/graph-data/', SystemGraphView.as_view(), name='system_graph_data'),
    path('health/embedding-stats/', EmbeddingStatsView.as_view(), name='embedding_stats'),
    path('health/detailed/', health_check_detailed, name='health_check_detailed'),
    path('health/ready/', readiness_check, name='readiness_check'),
    
    # JWT Auth with rate limiting
    path('token/', RateLimitedTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', RateLimitedTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    
    # 2FA endpoints
    path('auth/2fa/setup/', TwoFactorSetupView.as_view(), name='2fa_setup'),
    path('auth/2fa/confirm/', TwoFactorConfirmView.as_view(), name='2fa_confirm'),
    path('auth/2fa/verify/', TwoFactorVerifyView.as_view(), name='2fa_verify'),
    path('auth/2fa/google-verify/', TwoFactorGoogleVerifyView.as_view(), name='2fa_google_verify'),
    path('auth/2fa/disable/', TwoFactorDisableView.as_view(), name='2fa_disable'),
    path('auth/2fa/status/', TwoFactorStatusView.as_view(), name='2fa_status'),
    
    # User auth endpoints
    path('auth/user/', CurrentUserView.as_view(), name='current_user'),
    path('auth/password/change/', ChangePasswordView.as_view(), name='change_password'),
    path('auth/email-preferences/', EmailPreferencesView.as_view(), name='email_preferences'),
    
    # Email verification endpoints
    path('auth/email/request-change/', RequestEmailChangeView.as_view(), name='request_email_change'),
    path('auth/email/verify-code/', VerifyEmailChangeView.as_view(), name='verify_email_change'),
    
    # Password reset endpoints  
    path('auth/password/reset-request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('auth/password/reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # Currency rates
    path('currency-rates/', CurrencyRatesView.as_view(), name='currency_rates'),
    
    # Newsletter subscription
    path('newsletter/subscribe/', NewsletterSubscribeView.as_view(), name='newsletter_subscribe'),
    
    # Search endpoint
    path('search/', SearchAPIView.as_view(), name='search'),
    
    # Analytics endpoints  
    path('analytics/overview/', AnalyticsOverviewAPIView.as_view(), name='analytics_overview'),
    path('analytics/articles/top/', AnalyticsTopArticlesAPIView.as_view(), name='analytics_top_articles'),
    path('analytics/views/timeline/', AnalyticsViewsTimelineAPIView.as_view(), name='analytics_timeline'),
    path('analytics/categories/', AnalyticsCategoriesAPIView.as_view(), name='analytics_categories'),
    path('analytics/gsc/', GSCAnalyticsAPIView.as_view(), name='analytics_gsc'),
    path('analytics/ai-stats/', AnalyticsAIStatsAPIView.as_view(), name='analytics_ai_stats'),
    path('analytics/ai-generation/', AnalyticsAIGenerationAPIView.as_view(), name='analytics_ai_generation'),
    path('analytics/popular-models/', AnalyticsPopularModelsAPIView.as_view(), name='analytics_popular_models'),
    path('analytics/provider-stats/', AnalyticsProviderStatsAPIView.as_view(), name='analytics_provider_stats'),
    path('analytics/read-metrics/', TrackReadMetricView.as_view(), name='analytics_read_metrics'),
    path('analytics/link-click/', TrackLinkClickView.as_view(), name='analytics_link_click'),
    path('analytics/micro-feedback/', TrackMicroFeedbackView.as_view(), name='analytics_micro_feedback'),
    path('analytics/page-events/', TrackPageAnalyticsView.as_view(), name='analytics_page_events'),
    path('analytics/reading-now/<int:article_id>/', ReadingNowView.as_view(), name='analytics_reading_now'),
    path('analytics/extra-stats/', AnalyticsExtraStatsAPIView.as_view(), name='analytics_extra_stats'),
    
    # Car Catalog endpoints
    path('cars/brands/', CarBrandsListView.as_view(), name='car_brands_list'),
    path('cars/brands/<slug:brand_slug>/', CarBrandDetailView.as_view(), name='car_brand_detail'),
    path('cars/brands/<slug:brand_slug>/models/<slug:model_slug>/', CarModelDetailView.as_view(), name='car_model_detail'),
    path('cars/cleanup/', BrandCleanupView.as_view(), name='brand_cleanup'),
    path('cars/compare/', CarCompareView.as_view(), name='car_compare'),
    path('cars/picker/', CarPickerListView.as_view(), name='car_picker'),
    # Admin brand management
    path('admin/brands/', BrandViewSet.as_view({'get': 'list', 'post': 'create'}), name='admin_brands_list'),
    path('admin/brands/sync/', BrandViewSet.as_view({'post': 'sync_from_specs'}), name='admin_brands_sync'),
    path('admin/brands/bulk-merge/', BrandViewSet.as_view({'post': 'bulk_merge'}), name='admin_brands_bulk_merge'),
    path('admin/brands/<int:pk>/', BrandViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'put': 'update', 'delete': 'destroy'}), name='admin_brands_detail'),
    path('admin/brands/<int:pk>/merge/', BrandViewSet.as_view({'post': 'merge'}), name='admin_brands_merge'),
    path('admin/brands/<int:pk>/articles/', BrandViewSet.as_view({'get': 'articles'}), name='admin_brands_articles'),
    path('admin/brands/<int:pk>/move-article/', BrandViewSet.as_view({'post': 'move_article'}), name='admin_brands_move_article'),
    path('admin/brands/<int:pk>/toggle-news-only/', BrandViewSet.as_view({'post': 'toggle_news_only'}), name='admin_brands_toggle_news_only'),
    
    # Admin user management
    path('admin/users/', AdminUserManagementViewSet.as_view({'get': 'list'}), name='admin_users_list'),
    path('admin/users/<int:pk>/', AdminUserManagementViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}), name='admin_users_detail'),
    path('admin/users/<int:pk>/reset-password/', AdminUserManagementViewSet.as_view({'post': 'reset_password'}), name='admin_users_reset_password'),
    
    # Admin action analytics
    path('admin/action-stats/', AdminActionStatsView.as_view(), name='admin_action_stats'),
    
    # Nav badge counts (comments pending, feedback unresolved, new subscribers, rss pending)
    path('nav-badges/', NavBadgesView.as_view(), name='nav_badges'),
    
    # Capsule feedback (public)
    path('capsule-feedback/', CapsuleFeedbackView.as_view(), name='capsule_feedback_post'),
    path('capsule-feedback/<slug:slug>/', CapsuleFeedbackView.as_view(), name='capsule_feedback_get'),
    
    # AI Image Generation
    path('articles/<str:identifier>/generate-ai-image/', GenerateAIImageView.as_view(), name='generate_ai_image'),
    path('articles/<str:identifier>/search-photos/', SearchPhotosView.as_view(), name='search_photos'),
    path('articles/search-photos/', SearchPhotosView.as_view(), name='search_photos_generic'),
    path('articles/<str:identifier>/save-external-image/', SaveExternalImageView.as_view(), name='save_external_image'),
    path('ai-image-styles/', GenerateAIImageView.as_view(), name='ai_image_styles'),
    path('articles/proxy-image/', ProxyImageView.as_view(), name='proxy_image'),
    
    
    # Automation Control Panel
    path('automation/settings/', AutomationSettingsView.as_view(), name='automation_settings'),
    path('automation/stats/', AutomationStatsView.as_view(), name='automation_stats'),
    path('automation/trigger/<str:task_type>/', AutomationTriggerView.as_view(), name='automation_trigger'),
    
    # Public site config
    path('site/theme/', SiteThemeView.as_view(), name='site_theme'),
    path('site/theme-analytics/', ThemeAnalyticsView.as_view(), name='theme_analytics'),
    
    # A/B Testing
    path('ab/impression/', ABImpressionView.as_view(), name='ab_impression'),
    path('ab/click/', ABClickView.as_view(), name='ab_click'),
    path('ab/tests/', ABTestsListView.as_view(), name='ab_tests'),
    path('ab/pick-winner/', ABPickWinnerView.as_view(), name='ab_pick_winner'),
    path('ab/auto-pick/', ABAutoPickView.as_view(), name='ab_auto_pick'),
    
    # API endpoints
    path('', include(router.urls)),
]



