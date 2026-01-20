from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .api_views import (
    ArticleViewSet, CategoryViewSet, TagViewSet, 
    CommentViewSet, RatingViewSet, CarSpecificationViewSet, 
    ArticleImageViewSet, SiteSettingsViewSet, UserViewSet,
    FavoriteViewSet
)

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

urlpatterns = [
    # JWT Auth
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API endpoints
    path('', include(router.urls)),
]
