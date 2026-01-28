"""
RSS and Atom feeds for AutoNews
"""
from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from django.urls import reverse
from .models import Article


class LatestArticlesFeed(Feed):
    """RSS feed for latest articles"""
    title = "AutoNews - Latest Articles"
    link = "/articles/"
    description = "Latest automotive news, reviews and insights from AutoNews"
    
    def items(self):
        return Article.objects.filter(is_published=True).order_by('-created_at')[:20]
    
    def item_title(self, item):
        return item.title
    
    def item_description(self, item):
        return item.summary or item.content[:200]
    
    def item_link(self, item):
        return reverse('article-detail', args=[item.slug])
    
    def item_pubdate(self, item):
        return item.created_at
    
    def item_updateddate(self, item):
        return item.updated_at
    
    def item_categories(self, item):
        return [item.category.name] if item.category else []
    
    def item_enclosure_url(self, item):
        if item.image:
            return item.image.url
        return None
    
    def item_enclosure_length(self, item):
        if item.image:
            try:
                return item.image.size
            except:
                return 0
        return 0
    
    def item_enclosure_mime_type(self, item):
        return "image/webp"


class LatestArticlesAtomFeed(LatestArticlesFeed):
    """Atom feed for latest articles"""
    feed_type = Atom1Feed
    subtitle = LatestArticlesFeed.description


class CategoryFeed(Feed):
    """RSS feed for articles in a specific category"""
    
    def get_object(self, request, category_slug):
        from .models import Category
        return Category.objects.get(slug=category_slug)
    
    def title(self, obj):
        return f"AutoNews - {obj.name} Articles"
    
    def link(self, obj):
        return f"/categories/{obj.slug}/"
    
    def description(self, obj):
        return f"Latest articles in {obj.name} category"
    
    def items(self, obj):
        return Article.objects.filter(
            category=obj, 
            is_published=True
        ).order_by('-created_at')[:20]
    
    def item_title(self, item):
        return item.title
    
    def item_description(self, item):
        return item.summary or item.content[:200]
    
    def item_link(self, item):
        return reverse('article-detail', args=[item.slug])
    
    def item_pubdate(self, item):
        return item.created_at
