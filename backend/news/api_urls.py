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
    AdminNotificationViewSet, VehicleSpecsViewSet
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
from .api_views import (
    CurrencyRatesView, CurrentUserView, ChangePasswordView, EmailPreferencesView,
    RequestEmailChangeView, VerifyEmailChangeView,
    PasswordResetRequestView, PasswordResetConfirmView, NewsletterSubscribeView
)
from .search_analytics_views import (
    SearchAPIView, AnalyticsOverviewAPIView, AnalyticsTopArticlesAPIView,
    AnalyticsViewsTimelineAPIView, AnalyticsCategoriesAPIView, GSCAnalyticsAPIView
)
from .cars_views import CarBrandsListView, CarBrandDetailView, CarModelDetailView

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
    
    # Car Catalog endpoints
    path('cars/brands/', CarBrandsListView.as_view(), name='car_brands_list'),
    path('cars/brands/<slug:brand_slug>/', CarBrandDetailView.as_view(), name='car_brand_detail'),
    path('cars/brands/<slug:brand_slug>/models/<slug:model_slug>/', CarModelDetailView.as_view(), name='car_model_detail'),
    
    # API endpoints
    path('', include(router.urls)),
]

