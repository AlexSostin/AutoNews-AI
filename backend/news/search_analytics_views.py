"""
Search and Analytics API Views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta
from news.models import Article, Category, Tag, Comment, Subscriber
from news.serializers import ArticleListSerializer


class SearchAPIView(APIView):
    """
    Smart search with filters
    GET /api/v1/search/?q=term&category=slug&tags=tag1,tag2&sort=newest|popular|relevant
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        query = request.GET.get('q', '').strip()
        category_slug = request.GET.get('category', '').strip()
        tags_str = request.GET.get('tags', '').strip()
        sort = request.GET.get('sort', 'relevant').strip()
        
        # Start with published articles
        articles = Article.objects.filter(is_published=True, is_deleted=False)
        
        # Fulltext search on title, content, summary
        if query:
            articles = articles.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(summary__icontains=query) |
                Q(meta_keywords__icontains=query)
            )
        
        # Filter by category
        if category_slug:
            articles = articles.filter(category__slug=category_slug)
        
        # Filter by tags
        if tags_str:
            tag_slugs = [t.strip() for t in tags_str.split(',') if t.strip()]
            if tag_slugs:
                articles = articles.filter(tags__slug__in=tag_slugs).distinct()
        
        # Sorting
        if sort == 'newest':
            articles = articles.order_by('-created_at')
        elif sort == 'popular':
            articles = articles.order_by('-views', '-created_at')
        else:  # relevant - default
            # Simple relevance: title matches first, then most views
            if query:
                articles = articles.extra(
                    select={'title_match': f"CASE WHEN LOWER(title) LIKE LOWER('%%{query}%%') THEN 1 ELSE 0 END"}
                ).order_by('-title_match', '-views', '-created_at')
            else:
                articles = articles.order_by('-created_at')
        
        # Pagination
        page_size = 12
        page = int(request.GET.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = articles.count()
        articles_page = articles[start:end]
        
        serializer = ArticleListSerializer(articles_page, many=True, context={'request': request})
        
        return Response({
            'results': serializer.data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        })


class AnalyticsOverviewAPIView(APIView):
    """
    Analytics overview with key metrics
    GET /api/v1/analytics/overview/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Total counts
        total_articles = Article.objects.filter(is_published=True, is_deleted=False).count()
        total_views = Article.objects.filter(is_published=True, is_deleted=False).aggregate(Sum('views'))['views__sum'] or 0
        total_comments = Comment.objects.filter(is_approved=True).count()
        total_subscribers = Subscriber.objects.filter(is_active=True).count()
        
        # Growth comparison (last 30 days vs previous 30 days)
        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        prev_30_days = now - timedelta(days=60)
        
        articles_last_30 = Article.objects.filter(created_at__gte=last_30_days, is_published=True).count()
        articles_prev_30 = Article.objects.filter(created_at__gte=prev_30_days, created_at__lt=last_30_days, is_published=True).count()
        
        articles_growth = 0
        if articles_prev_30 > 0:
            articles_growth = round(((articles_last_30 - articles_prev_30) / articles_prev_30) * 100, 1)
        
        return Response({
            'total_articles': total_articles,
            'total_views': total_views,
            'total_comments': total_comments,
            'total_subscribers': total_subscribers,
            'articles_last_30_days': articles_last_30,
            'articles_growth_percent': articles_growth
        })


class AnalyticsTopArticlesAPIView(APIView):
    """
    Top articles by views
    GET /api/v1/analytics/articles/top/?limit=10
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        limit = int(request.GET.get('limit', 10))
        
        top_articles = Article.objects.filter(
            is_published=True, 
            is_deleted=False
        ).order_by('-views')[:limit]
        
        data = [{
            'id': article.id,
            'title': article.title,
            'slug': article.slug,
            'views': article.views,
            'created_at': article.created_at.isoformat()
        } for article in top_articles]
        
        return Response({'articles': data})


class AnalyticsViewsTimelineAPIView(APIView):
    """
    Views timeline - daily views for last 30 days
    GET /api/v1/analytics/views/timeline/?days=30
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        days = int(request.GET.get('days', 30))
        
        # Get articles from last N days and group by date
        from django.db.models.functions import TruncDate
        now = timezone.now()
        start_date = now - timedelta(days=days)
        
        # Query to get article counts by day
        articles_by_day = Article.objects.filter(
            created_at__gte=start_date,
            is_published=True
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # Create full date range with zeros
        date_map = {item['date']: item['count'] for item in articles_by_day}
        
        labels = []
        data = []
        for i in range(days):
            date = (start_date + timedelta(days=i)).date()
            labels.append(date.strftime('%Y-%m-%d'))
            data.append(date_map.get(date, 0))
        
        return Response({
            'labels': labels,
            'data': data
        })


class AnalyticsCategoriesAPIView(APIView):
    """
    Articles count by category
    GET /api/v1/analytics/categories/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        categories = Category.objects.annotate(
            article_count=Count('articles', filter=Q(articles__is_published=True, articles__is_deleted=False))
        ).filter(article_count__gt=0).order_by('-article_count')
        
        data = {
            'labels': [cat.name for cat in categories],
            'data': [cat.article_count for cat in categories]
        }
        
        return Response(data)
