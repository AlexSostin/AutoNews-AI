from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from .api_views import (
    ArticleViewSet, CategoryViewSet, TagViewSet, TagGroupViewSet, 
    CommentViewSet, RatingViewSet, CarSpecificationViewSet, 
    ArticleImageViewSet, SiteSettingsViewSet, UserViewSet,
    FavoriteViewSet, SubscriberViewSet,
    YouTubeChannelViewSet, RSSFeedViewSet, RSSNewsItemViewSet, PendingArticleViewSet, AutoPublishScheduleViewSet,
    AdminNotificationViewSet, VehicleSpecsViewSet, BrandAliasViewSet,
    ArticleFeedbackViewSet, GenerateAIImageView,
    SearchPhotosView, SaveExternalImageView,
    AdPlacementViewSet,
    AutomationSettingsView, AutomationStatsView, AutomationTriggerView
)
from .health import health_check, health_check_detailed, readiness_check


# Rate-limited token views for security
class RateLimitedTokenObtainPairView(TokenObtainPairView):
    """Token view with rate limiting to prevent brute-force attacks"""
    @method_decorator(ratelimit(key='ip', rate='5/15m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RateLimitedTokenRefreshView(TokenRefreshView):
    """Token refresh with rate limiting"""
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

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
router.register(r'auto-publish-schedule', AutoPublishScheduleViewSet, basename='auto-publish-schedule')
router.register(r'notifications', AdminNotificationViewSet, basename='notification')
router.register(r'vehicle-specs', VehicleSpecsViewSet, basename='vehicle-specs')
router.register(r'brand-aliases', BrandAliasViewSet, basename='brand-alias')
router.register(r'feedback', ArticleFeedbackViewSet, basename='feedback')
router.register(r'ads', AdPlacementViewSet, basename='ad')
from .api_views import (
    CurrencyRatesView, CurrentUserView, ChangePasswordView, EmailPreferencesView,
    RequestEmailChangeView, VerifyEmailChangeView,
    PasswordResetRequestView, PasswordResetConfirmView, NewsletterSubscribeView
)
from .search_analytics_views import (
    SearchAPIView, AnalyticsOverviewAPIView, AnalyticsTopArticlesAPIView,
    AnalyticsViewsTimelineAPIView, AnalyticsCategoriesAPIView, GSCAnalyticsAPIView,
    AnalyticsAIStatsAPIView
)
from .cars_views import CarBrandsListView, CarBrandDetailView, CarModelDetailView, BrandCleanupView, BrandViewSet

urlpatterns = [
    # Health check endpoints (for load balancers and monitoring)
    path('health/', health_check, name='health_check'),
    path('health/detailed/', health_check_detailed, name='health_check_detailed'),
    path('health/ready/', readiness_check, name='readiness_check'),
    
    # JWT Auth with rate limiting
    path('token/', RateLimitedTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', RateLimitedTokenRefreshView.as_view(), name='token_refresh'),
    
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
    
    # Car Catalog endpoints
    path('cars/brands/', CarBrandsListView.as_view(), name='car_brands_list'),
    path('cars/brands/<slug:brand_slug>/', CarBrandDetailView.as_view(), name='car_brand_detail'),
    path('cars/brands/<slug:brand_slug>/models/<slug:model_slug>/', CarModelDetailView.as_view(), name='car_model_detail'),
    path('cars/cleanup/', BrandCleanupView.as_view(), name='brand_cleanup'),
    # Admin brand management
    path('admin/brands/', BrandViewSet.as_view({'get': 'list', 'post': 'create'}), name='admin_brands_list'),
    path('admin/brands/sync/', BrandViewSet.as_view({'post': 'sync_from_specs'}), name='admin_brands_sync'),
    path('admin/brands/<int:pk>/', BrandViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'put': 'update', 'delete': 'destroy'}), name='admin_brands_detail'),
    path('admin/brands/<int:pk>/merge/', BrandViewSet.as_view({'post': 'merge'}), name='admin_brands_merge'),
    
    # AI Image Generation
    path('articles/<str:identifier>/generate-ai-image/', GenerateAIImageView.as_view(), name='generate_ai_image'),
    path('articles/<str:identifier>/search-photos/', SearchPhotosView.as_view(), name='search_photos'),
    path('articles/<str:identifier>/save-external-image/', SaveExternalImageView.as_view(), name='save_external_image'),
    path('ai-image-styles/', GenerateAIImageView.as_view(), name='ai_image_styles'),
    
    
    # Automation Control Panel
    path('automation/settings/', AutomationSettingsView.as_view(), name='automation_settings'),
    path('automation/stats/', AutomationStatsView.as_view(), name='automation_stats'),
    path('automation/trigger/<str:task_type>/', AutomationTriggerView.as_view(), name='automation_trigger'),
    
    # API endpoints
    path('', include(router.urls)),
]

