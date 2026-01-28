from django.urls import path
from . import views
from .feeds import LatestArticlesFeed, LatestArticlesAtomFeed, CategoryFeed
from .api_root import api_root

app_name = 'news'

urlpatterns = [
    # API root - no HTML templates!
    path('', api_root, name='api_root'),
    
    # RSS/Atom Feeds (still useful for SEO)
    path('feed/rss/', LatestArticlesFeed(), name='rss_feed'),
    path('feed/atom/', LatestArticlesAtomFeed(), name='atom_feed'),
    path('feed/category/<slug:category_slug>/rss/', CategoryFeed(), name='category_feed'),
    
    # Legacy endpoints - keep for backward compatibility
    # But redirect to Next.js frontend
    path('article/<slug:slug>/', views.article_detail, name='article_detail'),
]