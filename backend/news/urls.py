from django.urls import path
from . import views
from .feeds import LatestArticlesFeed, LatestArticlesAtomFeed, CategoryFeed

app_name = 'news'

urlpatterns = [
    path('', views.home, name='home'),
    path('article/<slug:slug>/', views.article_detail, name='article_detail'),
    path('category/<slug:slug>/', views.category_list, name='category_list'),
    path('logout/', views.logout_view, name='logout'),
    path('about/', views.about_page, name='about'),
    path('privacy/', views.privacy_page, name='privacy'),
    path('contact/', views.contact_page, name='contact'),
    path('search/', views.search, name='search'),
    path('article/<slug:slug>/rate/', views.rate_article, name='rate_article'),
    # RSS/Atom Feeds
    path('feed/rss/', LatestArticlesFeed(), name='rss_feed'),
    path('feed/atom/', LatestArticlesAtomFeed(), name='atom_feed'),
    path('feed/category/<slug:category_slug>/rss/', CategoryFeed(), name='category_feed'),
]