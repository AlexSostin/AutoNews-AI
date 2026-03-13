from django.contrib.sitemaps import Sitemap
from .models import Article, Category, Tag, Brand


class ArticleSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Article.objects.filter(is_published=True).order_by('-created_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f'/articles/{obj.slug}'


class CategorySitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return f'/category/{obj.slug}/'


class BrandSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Brand.objects.filter(is_visible=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f'/brands/{obj.slug}'


class TagSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.4

    def items(self):
        return Tag.objects.all()

    def location(self, obj):
        return f'/tag/{obj.slug}'

