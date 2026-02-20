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
            articles = articles.filter(categories__slug=category_slug)
        
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
        published_articles = Article.objects.filter(is_published=True, is_deleted=False)
        total_articles = published_articles.count()
        total_views = published_articles.aggregate(Sum('views'))['views__sum'] or 0
        total_comments = Comment.objects.filter(is_approved=True).count()
        total_subscribers = Subscriber.objects.filter(is_active=True).count()
        
        # Growth comparison (last 30 days vs previous 30 days)
        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        prev_30_days = now - timedelta(days=60)
        
        # 1. Articles Growth
        articles_last_30 = Article.objects.filter(created_at__gte=last_30_days, is_published=True).count()
        articles_prev_30 = Article.objects.filter(created_at__gte=prev_30_days, created_at__lt=last_30_days, is_published=True).count()
        articles_growth = 0
        if articles_prev_30 > 0:
            articles_growth = round(((articles_last_30 - articles_prev_30) / articles_prev_30) * 100, 1)
        elif articles_last_30 > 0:
            articles_growth = 100.0

        # 2. Views Growth
        views_last_30 = Article.objects.filter(created_at__gte=last_30_days, is_published=True).aggregate(Sum('views'))['views__sum'] or 0
        views_prev_30 = Article.objects.filter(created_at__gte=prev_30_days, created_at__lt=last_30_days, is_published=True).aggregate(Sum('views'))['views__sum'] or 0
        views_growth = 0
        if views_prev_30 > 0:
            views_growth = round(((views_last_30 - views_prev_30) / views_prev_30) * 100, 1)
        elif views_last_30 > 0:
            views_growth = 100.0

        # 3. Comments Growth
        comments_last_30 = Comment.objects.filter(created_at__gte=last_30_days, is_approved=True).count()
        comments_prev_30 = Comment.objects.filter(created_at__gte=prev_30_days, created_at__lt=last_30_days, is_approved=True).count()
        comments_growth = 0
        if comments_prev_30 > 0:
            comments_growth = round(((comments_last_30 - comments_prev_30) / comments_prev_30) * 100, 1)
        elif comments_last_30 > 0:
            comments_growth = 100.0

        # 4. Subscribers Growth
        subs_last_30 = Subscriber.objects.filter(created_at__gte=last_30_days, is_active=True).count()
        subs_prev_30 = Subscriber.objects.filter(created_at__gte=prev_30_days, created_at__lt=last_30_days, is_active=True).count()
        subs_growth = 0
        if subs_prev_30 > 0:
            subs_growth = round(((subs_last_30 - subs_prev_30) / subs_prev_30) * 100, 1)
        elif subs_last_30 > 0:
            subs_growth = 100.0
        
        return Response({
            'total_articles': total_articles,
            'total_views': total_views,
            'total_comments': total_comments,
            'total_subscribers': total_subscribers,
            'articles_growth': articles_growth,
            'views_growth': views_growth,
            'comments_growth': comments_growth,
            'subscribers_growth': subs_growth,
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

class GSCAnalyticsAPIView(APIView):
    """
    Search Console analytics for the dashboard
    GET /api/v1/analytics/gsc/?days=30
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from news.models import GSCReport, ArticleGSCStats
        days = int(request.GET.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # 1. Site-wide timeline
        reports = GSCReport.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')

        labels = []
        clicks_data = []
        impressions_data = []
        
        # Create full range
        date_map = {r.date: r for r in reports}
        for i in range(days + 1):
            curr_date = start_date + timedelta(days=i)
            labels.append(curr_date.strftime('%Y-%m-%d'))
            report = date_map.get(curr_date)
            clicks_data.append(report.clicks if report else 0)
            impressions_data.append(report.impressions if report else 0)

        # 2. Key Metrics Summary (Last 7 days vs previous 7 days)
        last_7_end = end_date - timedelta(days=2) # Latest data
        last_7_start = last_7_end - timedelta(days=7)
        prev_7_end = last_7_start
        prev_7_start = prev_7_end - timedelta(days=7)

        def get_summary(start, end):
            stats = GSCReport.objects.filter(date__gte=start, date__lte=end).aggregate(
                Sum('clicks'), Sum('impressions'), Sum('position')
            )
            count = GSCReport.objects.filter(date__gte=start, date__lte=end).count()
            
            clicks = stats['clicks__sum'] or 0
            impressions = stats['impressions__sum'] or 0
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            avg_pos = (stats['position__sum'] / count) if count > 0 else 0
            
            return {
                'clicks': clicks,
                'impressions': impressions,
                'ctr': round(ctr, 2),
                'position': round(avg_pos, 1)
            }

        current_summary = get_summary(last_7_start, last_7_end)
        previous_summary = get_summary(prev_7_start, prev_7_end)

        last_report = GSCReport.objects.order_by('-updated_at').first()
        
        return Response({
            'timeline': {
                'labels': labels,
                'clicks': clicks_data,
                'impressions': impressions_data,
            },
            'summary': current_summary,
            'previous_summary': previous_summary,
            'last_sync': last_report.updated_at.isoformat() if last_report else None
        })


class AnalyticsAIStatsAPIView(APIView):
    """
    AI & Enrichment analytics
    GET /api/v1/analytics/ai-stats/
    Returns: enrichment coverage, top tags by views, source breakdown
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from news.models import (
            VehicleSpecs, ArticleTitleVariant, CarSpecification,
            PendingArticle
        )

        published = Article.objects.filter(is_published=True, is_deleted=False)
        total = published.count()

        # --- 1. Enrichment Coverage ---
        with_vehicle_specs = VehicleSpecs.objects.filter(
            article__in=published
        ).values('article').distinct().count()

        with_ab_titles = ArticleTitleVariant.objects.filter(
            article__in=published
        ).values('article').distinct().count()

        with_tags = published.filter(tags__isnull=False).distinct().count()

        with_car_specs = CarSpecification.objects.filter(
            article__in=published
        ).values('article').distinct().count()

        with_images = published.exclude(
            Q(image='') | Q(image__isnull=True)
        ).count()

        enrichment = {
            'total_articles': total,
            'vehicle_specs': with_vehicle_specs,
            'ab_titles': with_ab_titles,
            'tags': with_tags,
            'car_specs': with_car_specs,
            'images': with_images,
        }

        # --- 2. Top Tags by Views ---
        top_tags = Tag.objects.filter(
            article__is_published=True,
            article__is_deleted=False
        ).annotate(
            article_count=Count('article', distinct=True),
            total_views=Sum('article__views')
        ).order_by('-total_views')[:15]

        tags_data = [{
            'name': tag.name,
            'slug': tag.slug,
            'article_count': tag.article_count,
            'total_views': tag.total_views or 0,
        } for tag in top_tags]

        # --- 3. AI Source Breakdown ---
        # YouTube articles (have youtube_url)
        youtube_count = published.exclude(
            Q(youtube_url='') | Q(youtube_url__isnull=True)
        ).count()

        # RSS articles (approved from PendingArticle with rss_feed)
        rss_published_ids = PendingArticle.objects.filter(
            status='published',
            rss_feed__isnull=False,
            published_article__isnull=False
        ).values_list('published_article_id', flat=True)
        rss_count = published.filter(id__in=rss_published_ids).count()

        # Translated/manual (no youtube URL and not from RSS)
        translated_count = total - youtube_count - rss_count

        sources = {
            'youtube': youtube_count,
            'rss': rss_count,
            'translated': max(translated_count, 0),
        }

        return Response({
            'enrichment': enrichment,
            'top_tags': tags_data,
            'sources': sources,
        })


class AnalyticsAIGenerationAPIView(APIView):
    """
    AI Generation Quality Metrics
    GET /api/v1/analytics/ai-generation/

    Returns:
    - spec_coverage: per-field fill rates for CarSpecification
    - generation_time: avg/median/max seconds from generation to publication
    - edit_rates: % of content changed between AI original and published version
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import re
        from django.db.models import Avg, Max
        from news.models import CarSpecification

        published = Article.objects.filter(is_published=True, is_deleted=False)
        total = published.count()

        # ── 1. Spec Field Coverage ──────────────────────────────────
        spec_fields = [
            'make', 'model', 'engine', 'horsepower', 'torque',
            'zero_to_sixty', 'top_speed', 'drivetrain', 'price', 'release_date',
        ]
        specs_qs = CarSpecification.objects.filter(article__in=published)
        total_specs = specs_qs.count()

        field_coverage = {}
        if total_specs > 0:
            for field in spec_fields:
                filled = specs_qs.exclude(**{field: ''}).exclude(**{f'{field}__isnull': True}).count()
                field_coverage[field] = round(filled / total_specs * 100, 1)
        overall_spec_coverage = round(
            sum(field_coverage.values()) / len(spec_fields), 1
        ) if field_coverage else 0

        # ── 2. Generation → Publication Time ────────────────────────
        gen_times = []
        articles_with_meta = published.filter(
            generation_metadata__isnull=False,
        ).values_list('generation_metadata', 'created_at')

        for meta, created_at in articles_with_meta:
            if isinstance(meta, dict):
                ts = meta.get('timestamp') or meta.get('generated_at')
                if ts:
                    try:
                        from django.utils.dateparse import parse_datetime
                        gen_dt = parse_datetime(str(ts))
                        if gen_dt and created_at:
                            diff = (created_at - gen_dt).total_seconds()
                            if 0 < diff < 86400 * 7:  # sanity: <7 days
                                gen_times.append(diff)
                    except (ValueError, TypeError):
                        pass

        gen_time_stats = {}
        if gen_times:
            gen_times.sort()
            gen_time_stats = {
                'avg_seconds': round(sum(gen_times) / len(gen_times), 1),
                'median_seconds': round(gen_times[len(gen_times) // 2], 1),
                'max_seconds': round(max(gen_times), 1),
                'sample_size': len(gen_times),
            }

        # ── 3. Content Edit Percentage ──────────────────────────────
        strip_html = re.compile(r'<[^>]+>')
        edit_samples = []
        edited_articles = published.exclude(
            content_original=''
        ).exclude(
            content_original__isnull=True
        ).values_list('id', 'content', 'content_original')[:200]

        for article_id, content, original in edited_articles:
            clean_c = strip_html.sub('', content or '').strip()
            clean_o = strip_html.sub('', original or '').strip()
            if not clean_o:
                continue
            # Simple char-level diff ratio
            from difflib import SequenceMatcher
            ratio = SequenceMatcher(None, clean_o, clean_c).ratio()
            edit_pct = round((1 - ratio) * 100, 1)
            edit_samples.append(edit_pct)

        edit_stats = {}
        if edit_samples:
            edit_samples.sort()
            edit_stats = {
                'avg_edit_pct': round(sum(edit_samples) / len(edit_samples), 1),
                'median_edit_pct': round(edit_samples[len(edit_samples) // 2], 1),
                'max_edit_pct': round(max(edit_samples), 1),
                'unedited_count': sum(1 for p in edit_samples if p < 1),
                'sample_size': len(edit_samples),
            }

        return Response({
            'spec_coverage': {
                'total_with_specs': total_specs,
                'total_articles': total,
                'overall_pct': overall_spec_coverage,
                'per_field': field_coverage,
            },
            'generation_time': gen_time_stats,
            'edit_rates': edit_stats,
        })


class AnalyticsPopularModelsAPIView(APIView):
    """
    Popular Car Models by Views
    GET /api/v1/analytics/popular-models/

    Returns top car make+model combinations ranked by total article views.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from news.models import CarSpecification

        # Aggregate views by make + model
        models_qs = CarSpecification.objects.filter(
            article__is_published=True,
            article__is_deleted=False,
        ).exclude(
            make=''
        ).exclude(
            model=''
        ).values(
            'make', 'model'
        ).annotate(
            total_views=Sum('article__views'),
            article_count=Count('article', distinct=True),
        ).order_by('-total_views')[:15]

        models_data = [{
            'make': m['make'],
            'model': m['model'],
            'label': f"{m['make']} {m['model']}",
            'total_views': m['total_views'] or 0,
            'article_count': m['article_count'],
        } for m in models_qs]

        return Response({
            'models': models_data,
            'count': len(models_data),
        })


class AnalyticsProviderStatsAPIView(APIView):
    """
    AI Provider Performance Stats
    GET /api/v1/analytics/provider-stats/

    Returns per-provider quality averages and per-brand breakdown.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            from ai_engine.modules.provider_tracker import get_provider_summary
            summary = get_provider_summary()
            return Response(summary)
        except Exception as e:
            return Response({
                'providers': {},
                'by_brand': {},
                'total_records': 0,
                'error': str(e),
            })
