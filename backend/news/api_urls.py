from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from .api_views import (
    ArticleViewSet, CategoryViewSet, TagViewSet, 
    CommentViewSet, RatingViewSet, CarSpecificationViewSet, 
    ArticleImageViewSet, SiteSettingsViewSet, UserViewSet,
    FavoriteViewSet, SubscriberViewSet,
    YouTubeChannelViewSet, PendingArticleViewSet, AutoPublishScheduleViewSet
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
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'ratings', RatingViewSet, basename='rating')
router.register(r'car-specifications', CarSpecificationViewSet, basename='carspecification')
router.register(r'article-images', ArticleImageViewSet, basename='articleimage')
router.register(r'settings', SiteSettingsViewSet, basename='settings')
router.register(r'users', UserViewSet, basename='user')
router.register(r'favorites', FavoriteViewSet, basename='favorite')
router.register(r'subscribers', SubscriberViewSet, basename='subscriber')
router.register(r'youtube-channels', YouTubeChannelViewSet, basename='youtube-channel')
router.register(r'pending-articles', PendingArticleViewSet, basename='pending-article')
router.register(r'auto-publish-schedule', AutoPublishScheduleViewSet, basename='auto-publish-schedule')
from .api_views import CurrencyRatesView, CurrentUserView, ChangePasswordView, EmailPreferencesView

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
    
    # Currency rates
    path('currency-rates/', CurrencyRatesView.as_view(), name='currency_rates'),
    
    # API endpoints
    path('', include(router.urls)),
]
