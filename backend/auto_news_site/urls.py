"""
URL configuration for auto_news_site project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from news.sitemaps import ArticleSitemap, CategorySitemap
from news.admin import CustomAdminSite

# Create custom admin site instance
admin_site = CustomAdminSite(name='custom_admin')

# Register models with custom admin site
from news.models import Article, Category, Tag, CarSpecification, SiteSettings
from news.admin import ArticleAdmin, CategoryAdmin, TagAdmin, SiteSettingsAdmin

admin_site.register(Article, ArticleAdmin)
admin_site.register(Category, CategoryAdmin)
admin_site.register(Tag, TagAdmin)
admin_site.register(SiteSettings, SiteSettingsAdmin)

# Customize admin site
admin.site.site_header = "🚗 AutoNews Admin Panel"
admin.site.site_title = "AutoNews Admin"
admin.site.index_title = "Welcome to AutoNews Management"

sitemaps = {
    'articles': ArticleSitemap,
    'categories': CategorySitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('news.api_urls')),  # API endpoints
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('', include('news.urls')),  # robots.txt is handled in news.urls
]

# Serve media files with CORS headers (works on both dev and production)
from news.views import serve_media_with_cors
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve_media_with_cors, name='media'),
]
