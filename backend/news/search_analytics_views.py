"""
Search and Analytics API Views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q, Count, Sum, Case, When, Value, IntegerField
from django.utils import timezone
from datetime import timedelta
from news.models import Article, Category, Tag, Comment, Subscriber
from news.serializers import ArticleListSerializer


class SearchAPIView(APIView):
    """
    Smart search with hybrid BM25 + vector ranking.
    GET /api/v1/search/?q=term&category=slug&tags=tag1,tag2&sort=newest|popular|relevant

    When `q` is provided:
      1. Tries hybrid_search() (BM25 + FAISS via RRF) — best relevance.
      2. Falls back to ORM icontains if vector engine not ready.
    When no `q`: returns articles filtered/sorted by category, tags, sort.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.GET.get('q', '').strip()
        category_slug = request.GET.get('category', '').strip()
        tags_str = request.GET.get('tags', '').strip()
        sort = request.GET.get('sort', 'relevant').strip()
        page_size = 12
        page = int(request.GET.get('page', 1))

        if query:
            # ── Hybrid search path ──────────────────────────────────
            article_ids_ordered = self._hybrid_article_ids(query)

            if article_ids_ordered:
                # Fetch matching articles, preserving RRF order
                articles_qs = Article.objects.filter(
                    id__in=article_ids_ordered,
                    is_published=True,
                    is_deleted=False,
                )

                # Optional filters
                if category_slug:
                    articles_qs = articles_qs.filter(categories__slug=category_slug)
                if tags_str:
                    tag_slugs = [t.strip() for t in tags_str.split(',') if t.strip()]
                    if tag_slugs:
                        articles_qs = articles_qs.filter(tags__slug__in=tag_slugs).distinct()

                # Materialise and re-sort by RRF rank
                articles_map = {a.id: a for a in articles_qs}
                articles_ordered = [
                    articles_map[aid]
                    for aid in article_ids_ordered
                    if aid in articles_map
                ]

                total = len(articles_ordered)
                start = (page - 1) * page_size
                articles_page = articles_ordered[start:start + page_size]

                serializer = ArticleListSerializer(
                    articles_page, many=True, context={'request': request}
                )
                return Response({
                    'results': serializer.data,
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total + page_size - 1) // page_size,
                    'search_mode': 'hybrid',
                })

            # ── Fallback: ORM icontains ──────────────────────────────
            articles = Article.objects.filter(is_published=True, is_deleted=False).filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(summary__icontains=query) |
                Q(meta_keywords__icontains=query)
            )
        else:
            articles = Article.objects.filter(is_published=True, is_deleted=False)

        # ── Non-hybrid path: filters + sorting ──────────────────────
        if category_slug:
            articles = articles.filter(categories__slug=category_slug)
        if tags_str:
            tag_slugs = [t.strip() for t in tags_str.split(',') if t.strip()]
            if tag_slugs:
                articles = articles.filter(tags__slug__in=tag_slugs).distinct()

        if sort == 'newest':
            articles = articles.order_by('-created_at')
        elif sort == 'popular':
            articles = articles.order_by('-views', '-created_at')
        else:  # relevant
            if query:
                articles = articles.annotate(
                    relevance=Case(
                        When(title__icontains=query, then=Value(3)),
                        When(summary__icontains=query, then=Value(2)),
                        When(Q(meta_keywords__icontains=query) | Q(tags__name__icontains=query), then=Value(1)),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                ).order_by('-relevance', '-views', '-created_at').distinct()
            else:
                articles = articles.order_by('-created_at')

        total = articles.count()
        start = (page - 1) * page_size
        articles_page = articles[start:start + page_size]

        serializer = ArticleListSerializer(articles_page, many=True, context={'request': request})
        return Response({
            'results': serializer.data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
            'search_mode': 'orm',
        })

    def _hybrid_article_ids(self, query: str) -> list:
        """
        Run hybrid_search and return article IDs ordered by RRF score.
        Returns empty list if engine not available or no embeddings indexed.
        """
        try:
            from ai_engine.modules.vector_search import get_vector_engine
            engine = get_vector_engine()
            results = engine.hybrid_search(query, k=50)
            return [r['article_id'] for r in results if r.get('article_id')]
        except Exception:
            return []




class AnalyticsOverviewAPIView(APIView):
    """
    Analytics overview with key metrics
    GET /api/v1/analytics/overview/
    """
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _get_total_views_from_redis(db_total: int) -> int:
        """
        Try to get total views from live Redis counters.
        If Redis is unavailable or has 0 keys, fall back to DB sum.
        """
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            keys = redis_conn.keys("article_views:*")
            if not keys:
                return db_total  # Redis cold / empty → use DB
            redis_total = sum(int(redis_conn.get(k) or 0) for k in keys)
            # Use Redis if it's higher (source of truth for live counts)
            return max(db_total, redis_total)
        except Exception:
            return db_total  # Redis unavailable → fall back silently

    def get(self, request):
        # Total counts
        published_articles = Article.objects.filter(is_published=True, is_deleted=False)
        total_articles = published_articles.count()
        db_total_views = published_articles.aggregate(Sum('views'))['views__sum'] or 0
        # Use Redis live counters when available (fixes "0 views" after Redis restart)
        total_views = self._get_total_views_from_redis(db_total_views)
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

        # 2. Key Metrics Summary — same period as timeline
        # Split into current half vs previous half for trend arrows
        mid_date = end_date - timedelta(days=days // 2)
        # GSC data lags ~2 days, offset end accordingly
        gsc_end = end_date - timedelta(days=2)
        gsc_start = gsc_end - timedelta(days=days)
        prev_end = gsc_start
        prev_start = prev_end - timedelta(days=days)

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

        current_summary = get_summary(gsc_start, gsc_end)
        previous_summary = get_summary(prev_start, prev_end)

        last_report = GSCReport.objects.order_by('-updated_at').first()
        
        return Response({
            'timeline': {
                'labels': labels,
                'clicks': clicks_data,
                'impressions': impressions_data,
            },
            'summary': current_summary,
            'previous_summary': previous_summary,
            'last_sync': last_report.updated_at.isoformat() if last_report else None,
            'days': days,
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

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status

class TrackReadMetricView(APIView):
    """
    Endpoint to receive Dwell Time and Scroll Depth signals from the frontend.
    These metrics are recorded when the user leaves an article page.
    """
    permission_classes = [AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='30/m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        article_id = request.data.get('article_id')
        dwell_time = request.data.get('dwell_time_seconds', 0)
        scroll_depth = request.data.get('max_scroll_depth_pct', 0)
        
        if not article_id:
            return Response({'error': 'article_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Cap values to prevent malicious data pollution
        try:
            dwell_time = min(int(dwell_time), 3600)  # Cap at 1 hour
            scroll_depth = min(int(scroll_depth), 100) # Cap at 100%
        except (ValueError, TypeError):
            return Response({'error': 'Invalid metric values'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Don't save useless bouncing sessions for ML
        if dwell_time < 2 and scroll_depth < 10:
            return Response({'status': 'ignored_bounce'}, status=status.HTTP_200_OK)
            
        from news.models import Article
        from news.models.interactions import ReadMetric
        
        try:
            article = Article.objects.get(id=article_id, is_published=True)
            
            # Fetch user / session info
            user = request.user if request.user.is_authenticated else None
            session_key = request.session.session_key if hasattr(request, 'session') and request.session.session_key else ''
            
            # Get real IP (considering Cloudflare headers)
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')
            
            # Save the metric
            ReadMetric.objects.create(
                article=article,
                user=user,
                session_key=session_key,
                ip_address=ip,
                dwell_time_seconds=dwell_time,
                max_scroll_depth_pct=scroll_depth
            )
            
            return Response({'status': 'success'}, status=status.HTTP_201_CREATED)
            
        except Article.DoesNotExist:
            return Response({'error': 'Article not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TrackLinkClickView(APIView):
    """
    Endpoint to receive internal link click events from the frontend.
    """
    permission_classes = [AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='60/m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        article_id = request.data.get('source_article_id')
        destination_url = request.data.get('destination_url')
        link_type = request.data.get('link_type', 'other')
        
        if not article_id or not destination_url:
            return Response({'error': 'source_article_id and destination_url are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from news.models import Article
        from news.models.interactions import InternalLinkClick
        
        try:
            article = Article.objects.get(id=article_id, is_published=True)
            
            # Fetch user / session info
            user = request.user if request.user.is_authenticated else None
            session_key = request.session.session_key if hasattr(request, 'session') and request.session.session_key else ''
            
            # Get real IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')
            
            # Save the metric
            InternalLinkClick.objects.create(
                source_article=article,
                destination_url=destination_url[:500],
                link_type=link_type,
                user=user,
                session_key=session_key,
                ip_address=ip
            )
            
            return Response({'status': 'success'}, status=status.HTTP_201_CREATED)
            
        except Article.DoesNotExist:
            return Response({'error': 'Article not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TrackMicroFeedbackView(APIView):
    """
    Endpoint to receive granular RLHF feedback (Thumbs Up / Down) on specific AI components like Vehicle Specs.
    """
    permission_classes = [AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='20/m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        article_id = request.data.get('article_id')
        component_type = request.data.get('component_type')
        is_helpful = request.data.get('is_helpful')
        
        if not article_id or not component_type or is_helpful is None:
            return Response({'error': 'article_id, component_type, and is_helpful are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from news.models import Article
        from news.models.interactions import ArticleMicroFeedback
        
        try:
            article = Article.objects.get(id=article_id, is_published=True)
            
            # Fetch user / session info
            user = request.user if request.user.is_authenticated else None
            session_key = request.session.session_key if hasattr(request, 'session') and request.session.session_key else ''
            
            # Get real IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')
            
            ArticleMicroFeedback.objects.create(
                article=article,
                user=user,
                session_key=session_key,
                ip_address=ip,
                component_type=component_type,
                is_helpful=bool(is_helpful)
            )
            
            return Response({'status': 'success'}, status=status.HTTP_201_CREATED)
            
        except Article.DoesNotExist:
            return Response({'error': 'Article not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrackPageAnalyticsView(APIView):
    """
    Universal page analytics event endpoint.
    Accepts a single event or batch of events (up to 10).
    
    POST /api/v1/analytics/page-events/
    {
        "events": [
            {
                "event_type": "page_leave",
                "page_type": "articles",
                "page_url": "/articles",
                "metrics": {"dwell_seconds": 45, "scroll_depth_pct": 78},
                "referrer_page": "home",
                "device_type": "desktop",
                "viewport_width": 1920,
                "session_hash": "abc123"
            }
        ]
    }
    """
    permission_classes = [AllowAny]
    
    VALID_EVENT_TYPES = {
        'page_view', 'page_leave', 'card_click', 'search', 'filter_use',
        'recommended_impression', 'recommended_click', 'compare_use',
        'infinite_scroll', 'ad_impression', 'ad_click',
    }
    VALID_PAGE_TYPES = {
        'home', 'articles', 'article_detail', 'trending', 'cars',
        'car_detail', 'compare', 'categories', 'category_detail', 'other',
    }
    
    @method_decorator(ratelimit(key='ip', rate='60/m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        from news.models.system import PageAnalyticsEvent
        
        # Support single event or batch
        events_data = request.data.get('events', [])
        if not events_data:
            # Single event mode
            events_data = [request.data]
        
        # Cap batch size
        events_data = events_data[:10]
        
        # Get IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR')
        
        created_count = 0
        for event in events_data:
            event_type = event.get('event_type', '')
            page_type = event.get('page_type', 'other')
            
            if not event_type:
                continue
                
            # Clamp to valid values
            if event_type not in self.VALID_EVENT_TYPES:
                continue
            if page_type not in self.VALID_PAGE_TYPES:
                page_type = 'other'
            
            try:
                vw = event.get('viewport_width', 0)
                vw_int = min(int(vw or 0), 9999)
                
                PageAnalyticsEvent.objects.create(
                    event_type=event_type,
                    page_type=page_type,
                    page_url=str(event.get('page_url', ''))[:500],
                    metrics=event.get('metrics') or {},
                    referrer_page=str(event.get('referrer_page', ''))[:200],
                    device_type=str(event.get('device_type', ''))[:10],
                    viewport_width=vw_int if vw_int > 0 else None,
                    ip_address=ip,
                    session_hash=str(event.get('session_hash', ''))[:64],
                )
                created_count += 1
            except Exception:
                continue
        
        return Response({'status': 'ok', 'created': created_count}, status=status.HTTP_201_CREATED)


class ReadingNowView(APIView):
    """
    Real-time "currently reading" counter using Redis.
    
    GET /api/v1/analytics/reading-now/<article_id>/
    → {"reading_now": 5}
    
    POST /api/v1/analytics/reading-now/<article_id>/
    {"action": "join"} or {"action": "leave"}
    """
    permission_classes = [AllowAny]
    
    def _get_redis(self):
        try:
            import redis
            return redis.Redis(host='redis', port=6379, db=0)
        except Exception:
            return None
    
    def get(self, request, article_id):
        r = self._get_redis()
        if not r:
            return Response({'reading_now': 0})
        
        key = f"reading_now:{article_id}"
        count = r.get(key)
        return Response({'reading_now': int(count) if count else 0})
    
    @method_decorator(ratelimit(key='ip', rate='30/m', method='POST', block=True))
    def post(self, request, article_id):
        action = request.data.get('action', 'join')
        
        r = self._get_redis()
        if not r:
            return Response({'reading_now': 0})
        
        key = f"reading_now:{article_id}"
        
        if action == 'join':
            count = r.incr(key)
            r.expire(key, 300)  # Auto-expire after 5 min (safety net)
        elif action == 'leave':
            count = r.decr(key)
            # Don't go below 0
            if int(count) < 0:
                r.set(key, 0)
                count = 0
        else:
            count = r.get(key) or 0
        
        return Response({'reading_now': max(int(count), 0)})


class AnalyticsExtraStatsAPIView(APIView):
    """
    Extra analytics for dashboard widgets: subscribers, RSS feeds, error logs.
    GET /api/v1/analytics/extra-stats/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import logging
        from news.models import Subscriber, FrontendEventLog, BackendErrorLog
        from news.models.sources import RSSFeed
        from django.db.models.functions import TruncMonth

        logger = logging.getLogger(__name__)
        now = timezone.now()

        # ── 1. Subscriber growth ──
        subscribers_data = {}
        try:
            subscribers = Subscriber.objects.filter(is_active=True)
            total_subscribers = subscribers.count()

            monthly_growth = (
                subscribers
                .filter(created_at__gte=now - timedelta(days=365))
                .annotate(month=TruncMonth('created_at'))
                .values('month')
                .annotate(count=Count('id'))
                .order_by('month')
            )
            sub_labels = [m['month'].strftime('%b %Y') for m in monthly_growth]
            sub_data = [m['count'] for m in monthly_growth]
            # Cumulative
            cumulative = []
            running = total_subscribers - sum(sub_data)
            for d in sub_data:
                running += d
                cumulative.append(running)

            subscribers_data = {
                'total': total_subscribers,
                'labels': sub_labels,
                'data': sub_data,
                'cumulative': cumulative,
            }
        except Exception as e:
            logger.exception("extra-stats: subscribers section failed")
            subscribers_data = {'total': 0, 'labels': [], 'data': [], 'cumulative': [], 'error': str(e)}

        # ── 2. RSS Feed stats ──
        rss_data = {}
        try:
            feeds = RSSFeed.objects.all()
            total_feeds = feeds.count()
            active_feeds = feeds.filter(is_enabled=True).count()
            total_entries = sum(feeds.values_list('entries_processed', flat=True))
            by_type = dict(feeds.values('source_type').annotate(c=Count('id')).values_list('source_type', 'c'))
            recently_active = feeds.filter(last_checked__gte=now - timedelta(hours=24)).count()
            top_feeds = list(
                feeds.filter(is_enabled=True)
                .order_by('-entries_processed')[:5]
                .values('name', 'entries_processed', 'source_type')
            )
            rss_data = {
                'total_feeds': total_feeds,
                'active_feeds': active_feeds,
                'total_entries': total_entries,
                'recently_active': recently_active,
                'by_type': by_type,
                'top_feeds': top_feeds,
            }
        except Exception as e:
            logger.exception("extra-stats: rss section failed")
            rss_data = {'total_feeds': 0, 'active_feeds': 0, 'total_entries': 0,
                        'recently_active': 0, 'by_type': {}, 'top_feeds': [], 'error': str(e)}

        # ── 3. Error log summary ──
        errors_data = {}
        try:
            frontend_total = FrontendEventLog.objects.count()
            frontend_unresolved = FrontendEventLog.objects.filter(resolved=False).count()
            frontend_last_24h = FrontendEventLog.objects.filter(last_seen__gte=now - timedelta(hours=24)).count()
            top_errors = list(
                FrontendEventLog.objects.filter(resolved=False)
                .order_by('-occurrence_count')[:5]
                .values('error_type', 'message', 'occurrence_count', 'last_seen')
            )
            backend_total = BackendErrorLog.objects.count()
            backend_last_24h = BackendErrorLog.objects.filter(last_seen__gte=now - timedelta(hours=24)).count()
            errors_data = {
                'frontend_total': frontend_total,
                'frontend_unresolved': frontend_unresolved,
                'frontend_last_24h': frontend_last_24h,
                'top_errors': top_errors,
                'backend_total': backend_total,
                'backend_last_24h': backend_last_24h,
            }
        except Exception as e:
            logger.exception("extra-stats: errors section failed")
            errors_data = {'frontend_total': 0, 'frontend_unresolved': 0, 'frontend_last_24h': 0,
                           'top_errors': [], 'backend_total': 0, 'backend_last_24h': 0, 'error': str(e)}

        return Response({
            'subscribers': subscribers_data,
            'rss': rss_data,
            'errors': errors_data,
        })



class ReaderEngagementView(APIView):
    """
    Reader quality metrics from ReadMetric.
    GET /api/v1/analytics/reader-engagement/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Avg, Count, Q
        from news.models.interactions import ReadMetric

        sessions = ReadMetric.objects.all()
        total = sessions.count()

        if total == 0:
            return Response({
                'top_articles': [],
                'scroll_funnel': {'25': 0, '50': 0, '75': 0, '100': 0},
                'overall': {'avg_dwell_seconds': 0, 'avg_scroll_depth': 0,
                             'bounce_rate_pct': 0, 'total_sessions': 0},
            })

        top_articles_qs = (
            ReadMetric.objects
            .values('article__id', 'article__title', 'article__slug')
            .annotate(avg_dwell=Avg('dwell_time_seconds'), avg_scroll=Avg('max_scroll_depth_pct'), session_count=Count('id'))
            .order_by('-avg_dwell')[:10]
        )
        top_articles = [{
            'article_id': r['article__id'], 'title': r['article__title'], 'slug': r['article__slug'],
            'avg_dwell_seconds': round(r['avg_dwell'] or 0, 1),
            'avg_scroll_depth': round(r['avg_scroll'] or 0, 1),
            'session_count': r['session_count'],
        } for r in top_articles_qs]

        funnel = {str(m): round(sessions.filter(max_scroll_depth_pct__gte=m).count() / total * 100, 1) for m in [25, 50, 75, 100]}

        agg = sessions.aggregate(avg_dwell=Avg('dwell_time_seconds'), avg_scroll=Avg('max_scroll_depth_pct'))
        bounces = sessions.filter(dwell_time_seconds__lt=10, max_scroll_depth_pct__lt=25).count()

        return Response({
            'top_articles': top_articles,
            'scroll_funnel': funnel,
            'overall': {
                'avg_dwell_seconds': round(agg['avg_dwell'] or 0, 1),
                'avg_scroll_depth': round(agg['avg_scroll'] or 0, 1),
                'bounce_rate_pct': round(bounces / total * 100, 1),
                'total_sessions': total,
            },
        })


class CapsuleFeedbackSummaryView(APIView):
    """
    Summary of capsule feedback votes from ArticleCapsuleFeedback.
    GET /api/v1/analytics/capsule-feedback-summary/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count
        from news.models.interactions import ArticleCapsuleFeedback

        total = ArticleCapsuleFeedback.objects.count()
        positive_total = ArticleCapsuleFeedback.objects.filter(is_positive=True).count()
        negative_total = ArticleCapsuleFeedback.objects.filter(is_positive=False).count()

        by_type = [{'type': r['feedback_type'], 'is_positive': r['is_positive'], 'count': r['count']}
                   for r in ArticleCapsuleFeedback.objects.values('feedback_type', 'is_positive').annotate(count=Count('id')).order_by('-count')]

        def top_articles_for(is_pos):
            return [{'article_id': r['article__id'], 'title': r['article__title'], 'slug': r['article__slug'], 'votes': r['votes']}
                    for r in ArticleCapsuleFeedback.objects.filter(is_positive=is_pos)
                    .values('article__id', 'article__title', 'article__slug').annotate(votes=Count('id')).order_by('-votes')[:5]]

        return Response({
            'total': total, 'positive_total': positive_total, 'negative_total': negative_total,
            'by_type': by_type,
            'top_positive_articles': top_articles_for(True),
            'top_negative_articles': top_articles_for(False),
        })


class ArticleComplaintsView(APIView):
    """
    Articles with user-reported problems from ArticleFeedback.
    GET /api/v1/analytics/article-complaints/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count, Q
        from news.models.interactions import ArticleFeedback  # type: ignore

        total = ArticleFeedback.objects.count()
        unresolved = ArticleFeedback.objects.filter(is_resolved=False).count()

        most_complained = [{'article_id': r['article__id'], 'title': r['article__title'], 'slug': r['article__slug'],
                             'total_reports': r['total_reports'], 'unresolved_reports': r['unresolved_reports']}
                           for r in ArticleFeedback.objects.values('article__id', 'article__title', 'article__slug')
                           .annotate(total_reports=Count('id'), unresolved_reports=Count('id', filter=Q(is_resolved=False)))
                           .order_by('-total_reports')[:10]]

        by_category = [{'category': r['category'], 'count': r['count']}
                       for r in ArticleFeedback.objects.values('category').annotate(count=Count('id')).order_by('-count')]

        return Response({
            'total': total, 'unresolved_total': unresolved, 'resolved_total': total - unresolved,
            'most_complained': most_complained, 'by_category': by_category,
        })
