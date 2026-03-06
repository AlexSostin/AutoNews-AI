"""
System Graph API — Obsidian-style entity relationship data.

GET /api/v1/health/graph-data/
Returns nodes (entities with counts), edges (relationships), and health warnings.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class SystemGraphView(APIView):
    """Interactive system graph data — nodes, edges, warnings."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        from news.models import (
            Article, PendingArticle, Category, Tag, TagGroup,
            ArticleImage, Comment, Rating, Favorite, ArticleFeedback,
            Brand, BrandAlias, CarSpecification, VehicleSpecs,
            RSSFeed, RSSNewsItem, YouTubeChannel,
            Subscriber, ArticleEmbedding, ArticleTitleVariant,
            FrontendEventLog, BackendErrorLog,
        )

        nodes = []
        edges = []
        warnings = []

        # ── Sources ──────────────────────────────────────────────
        rss_feeds = RSSFeed.objects.all()
        rss_total = rss_feeds.count()
        rss_active = rss_feeds.filter(is_enabled=True).count()
        now = timezone.now()
        cutoff_48h = now - timedelta(hours=48)

        # Health: count feeds by computed status (health is a @property)
        healthy = 0
        stale = 0
        failing = 0
        for feed in rss_feeds.filter(is_enabled=True):
            h = feed.health
            if h == 'failing':
                failing += 1
            elif h == 'stale':
                stale += 1
            else:
                healthy += 1

        nodes.append({
            'id': 'rss_feeds', 'label': 'RSS Feeds', 'group': 'sources',
            'icon': '📡', 'count': rss_total,
            'breakdown': {'active': rss_active, 'healthy': healthy, 'stale': stale, 'failing': failing},
            'health': 'error' if failing > 0 else ('warning' if stale > 2 else 'healthy'),
        })

        if failing > 0:
            warnings.append({'level': 'error', 'message': f'{failing} RSS feed(s) are failing'})
        if stale > 0:
            warnings.append({'level': 'warning', 'message': f'{stale} RSS feed(s) are stale (no items in 48h)'})

        # RSS Items
        rss_items = RSSNewsItem.objects.all()
        rss_counts = rss_items.aggregate(
            total=Count('id'),
            new=Count('id', filter=Q(status='new')),
            read=Count('id', filter=Q(status='read')),
            generated=Count('id', filter=Q(status='generated')),
            dismissed=Count('id', filter=Q(status='dismissed')),
            favorited=Count('id', filter=Q(is_favorite=True)),
        )
        nodes.append({
            'id': 'rss_items', 'label': 'RSS Items', 'group': 'sources',
            'icon': '📰', 'count': rss_counts['total'],
            'breakdown': {k: v for k, v in rss_counts.items() if k != 'total'},
            'health': 'healthy',
        })
        edges.append({'from': 'rss_feeds', 'to': 'rss_items', 'label': 'produces', 'count': rss_counts['total']})

        # YouTube Channels
        yt_total = YouTubeChannel.objects.count()
        yt_active = YouTubeChannel.objects.filter(is_enabled=True).count()
        nodes.append({
            'id': 'youtube', 'label': 'YouTube', 'group': 'sources',
            'icon': '▶️', 'count': yt_total,
            'breakdown': {'active': yt_active, 'inactive': yt_total - yt_active},
            'health': 'healthy' if yt_active > 0 else 'warning',
        })

        # ── Content ──────────────────────────────────────────────
        pending = PendingArticle.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            approved=Count('id', filter=Q(status='approved')),
            rejected=Count('id', filter=Q(status='rejected')),
            published=Count('id', filter=Q(status='published')),
        )
        nodes.append({
            'id': 'pending_articles', 'label': 'Pending Articles', 'group': 'content',
            'icon': '⏳', 'count': pending['total'],
            'breakdown': {k: v for k, v in pending.items() if k != 'total'},
            'health': 'warning' if pending['pending'] > 20 else 'healthy',
        })
        edges.append({'from': 'rss_items', 'to': 'pending_articles', 'label': 'generates', 'count': rss_counts['generated']})
        edges.append({'from': 'youtube', 'to': 'pending_articles', 'label': 'generates', 'count': 0})

        if pending['pending'] > 20:
            warnings.append({'level': 'warning', 'message': f'{pending["pending"]} pending articles waiting for review'})

        articles = Article.objects.aggregate(
            total=Count('id'),
            published=Count('id', filter=Q(is_published=True, is_deleted=False)),
            draft=Count('id', filter=Q(is_published=False, is_deleted=False)),
            deleted=Count('id', filter=Q(is_deleted=True)),
        )
        nodes.append({
            'id': 'articles', 'label': 'Articles', 'group': 'content',
            'icon': '📝', 'count': articles['total'],
            'breakdown': {k: v for k, v in articles.items() if k != 'total'},
            'health': 'healthy',
        })
        edges.append({'from': 'pending_articles', 'to': 'articles', 'label': 'publishes', 'count': pending['published']})

        # Article Images
        img_total = ArticleImage.objects.count()
        nodes.append({
            'id': 'article_images', 'label': 'Images', 'group': 'content',
            'icon': '🖼️', 'count': img_total,
            'breakdown': {},
            'health': 'healthy',
        })
        edges.append({'from': 'articles', 'to': 'article_images', 'label': 'has', 'count': img_total})

        # ── Vehicles ─────────────────────────────────────────────
        brand_data = Brand.objects.aggregate(
            total=Count('id'),
            visible=Count('id', filter=Q(is_visible=True)),
            hidden=Count('id', filter=Q(is_visible=False)),
        )
        nodes.append({
            'id': 'brands', 'label': 'Brands', 'group': 'vehicles',
            'icon': '🏷️', 'count': brand_data['total'],
            'breakdown': {'visible': brand_data['visible'], 'hidden': brand_data['hidden']},
            'health': 'healthy',
        })
        if brand_data['hidden'] > 10:
            warnings.append({'level': 'info', 'message': f'{brand_data["hidden"]} brands are hidden (discovered but no articles)'})

        alias_total = BrandAlias.objects.count()
        nodes.append({
            'id': 'brand_aliases', 'label': 'Brand Aliases', 'group': 'vehicles',
            'icon': '🔗', 'count': alias_total,
            'breakdown': {},
            'health': 'healthy',
        })
        edges.append({'from': 'brand_aliases', 'to': 'brands', 'label': 'maps to', 'count': alias_total})

        spec_total = CarSpecification.objects.count()
        nodes.append({
            'id': 'car_specs', 'label': 'Car Specs', 'group': 'vehicles',
            'icon': '🚗', 'count': spec_total,
            'breakdown': {},
            'health': 'healthy',
        })
        edges.append({'from': 'articles', 'to': 'car_specs', 'label': '1:1', 'count': spec_total})
        edges.append({'from': 'car_specs', 'to': 'brands', 'label': 'make →', 'count': spec_total})

        vs_data = VehicleSpecs.objects.aggregate(
            total=Count('id'),
            linked=Count('id', filter=Q(article__isnull=False)),
            orphan=Count('id', filter=Q(article__isnull=True)),
        )
        nodes.append({
            'id': 'vehicle_specs', 'label': 'Vehicle Specs', 'group': 'vehicles',
            'icon': '⚙️', 'count': vs_data['total'],
            'breakdown': {'linked': vs_data['linked'], 'orphan': vs_data['orphan']},
            'health': 'warning' if vs_data['orphan'] > vs_data['linked'] else 'healthy',
        })
        edges.append({'from': 'articles', 'to': 'vehicle_specs', 'label': 'FK', 'count': vs_data['linked']})

        if vs_data['orphan'] > 0:
            warnings.append({'level': 'info', 'message': f'{vs_data["orphan"]} vehicle specs have no linked article (discovered from RSS)'})

        # ── Taxonomy ─────────────────────────────────────────────
        cat_data = Category.objects.aggregate(
            total=Count('id'),
            visible=Count('id', filter=Q(is_visible=True)),
        )
        nodes.append({
            'id': 'categories', 'label': 'Categories', 'group': 'taxonomy',
            'icon': '📁', 'count': cat_data['total'],
            'breakdown': {'visible': cat_data['visible'], 'hidden': cat_data['total'] - cat_data['visible']},
            'health': 'healthy',
        })
        edges.append({'from': 'articles', 'to': 'categories', 'label': 'FK', 'count': 0})

        tg_total = TagGroup.objects.count()
        nodes.append({
            'id': 'tag_groups', 'label': 'Tag Groups', 'group': 'taxonomy',
            'icon': '🏷️', 'count': tg_total,
            'breakdown': {},
            'health': 'healthy',
        })

        tag_data = Tag.objects.aggregate(
            total=Count('id'),
            grouped=Count('id', filter=Q(group__isnull=False)),
            ungrouped=Count('id', filter=Q(group__isnull=True)),
        )
        nodes.append({
            'id': 'tags', 'label': 'Tags', 'group': 'taxonomy',
            'icon': '#️⃣', 'count': tag_data['total'],
            'breakdown': {'grouped': tag_data['grouped'], 'ungrouped': tag_data['ungrouped']},
            'health': 'warning' if tag_data['ungrouped'] > 50 else 'healthy',
        })
        edges.append({'from': 'tags', 'to': 'tag_groups', 'label': 'belongs to', 'count': tag_data['grouped']})
        edges.append({'from': 'articles', 'to': 'tags', 'label': 'M2M', 'count': 0})

        # ── Interactions ─────────────────────────────────────────
        comment_data = Comment.objects.aggregate(
            total=Count('id'),
            approved=Count('id', filter=Q(is_approved=True)),
            pending=Count('id', filter=Q(moderation_status='pending')),
        )
        nodes.append({
            'id': 'comments', 'label': 'Comments', 'group': 'interactions',
            'icon': '💬', 'count': comment_data['total'],
            'breakdown': {'approved': comment_data['approved'], 'pending': comment_data['pending']},
            'health': 'warning' if comment_data['pending'] > 10 else 'healthy',
        })
        edges.append({'from': 'articles', 'to': 'comments', 'label': 'has', 'count': comment_data['total']})

        rating_total = Rating.objects.count()
        nodes.append({
            'id': 'ratings', 'label': 'Ratings', 'group': 'interactions',
            'icon': '⭐', 'count': rating_total,
            'breakdown': {},
            'health': 'healthy',
        })
        edges.append({'from': 'articles', 'to': 'ratings', 'label': 'has', 'count': rating_total})

        fav_total = Favorite.objects.count()
        nodes.append({
            'id': 'favorites', 'label': 'Favorites', 'group': 'interactions',
            'icon': '❤️', 'count': fav_total,
            'breakdown': {},
            'health': 'healthy',
        })
        edges.append({'from': 'articles', 'to': 'favorites', 'label': 'has', 'count': fav_total})

        feedback_data = ArticleFeedback.objects.aggregate(
            total=Count('id'),
            unresolved=Count('id', filter=Q(is_resolved=False)),
        )
        nodes.append({
            'id': 'feedback', 'label': 'Feedback', 'group': 'interactions',
            'icon': '🐛', 'count': feedback_data['total'],
            'breakdown': {'unresolved': feedback_data['unresolved'], 'resolved': feedback_data['total'] - feedback_data['unresolved']},
            'health': 'warning' if feedback_data['unresolved'] > 5 else 'healthy',
        })
        edges.append({'from': 'articles', 'to': 'feedback', 'label': 'has', 'count': feedback_data['total']})

        # ── ML/AI ────────────────────────────────────────────────
        emb_total = ArticleEmbedding.objects.count()
        articles_published = articles['published']
        emb_coverage = round(emb_total / articles_published * 100, 1) if articles_published > 0 else 0
        nodes.append({
            'id': 'embeddings', 'label': 'Embeddings', 'group': 'ml',
            'icon': '🧠', 'count': emb_total,
            'breakdown': {
                'indexed': emb_total,
                'total': articles_published,
                'not_indexed': max(0, articles_published - emb_total),
            },
            'health': 'warning' if emb_coverage < 80 else 'healthy',
        })
        edges.append({'from': 'articles', 'to': 'embeddings', 'label': 'indexed', 'count': emb_total})

        if emb_coverage < 80:
            warnings.append({'level': 'warning', 'message': f'Only {emb_coverage}% of articles have embeddings'})

        ab_total = ArticleTitleVariant.objects.count()
        ab_active = ArticleTitleVariant.objects.filter(is_active=True).count()
        nodes.append({
            'id': 'ab_tests', 'label': 'A/B Tests', 'group': 'ml',
            'icon': '🧪', 'count': ab_total,
            'breakdown': {'active': ab_active},
            'health': 'healthy',
        })
        edges.append({'from': 'articles', 'to': 'ab_tests', 'label': 'variants', 'count': ab_total})

        # ── System ───────────────────────────────────────────────
        sub_data = Subscriber.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
        )
        nodes.append({
            'id': 'subscribers', 'label': 'Subscribers', 'group': 'system',
            'icon': '📧', 'count': sub_data['total'],
            'breakdown': {'active': sub_data['active'], 'unsubscribed': sub_data['total'] - sub_data['active']},
            'health': 'healthy',
        })

        # Errors
        be_errors = BackendErrorLog.objects.filter(resolved=False).count()
        fe_errors = FrontendEventLog.objects.filter(resolved=False).count()
        err_total = be_errors + fe_errors
        nodes.append({
            'id': 'errors', 'label': 'Errors', 'group': 'system',
            'icon': '🚨', 'count': err_total,
            'breakdown': {'backend': be_errors, 'frontend': fe_errors},
            'health': 'error' if err_total > 10 else ('warning' if err_total > 0 else 'healthy'),
        })

        if err_total > 0:
            warnings.append({'level': 'error' if err_total > 10 else 'warning', 'message': f'{err_total} unresolved errors ({be_errors} backend, {fe_errors} frontend)'})

        # Sort warnings: error first, then warning, then info
        level_order = {'error': 0, 'warning': 1, 'info': 2}
        warnings.sort(key=lambda w: level_order.get(w['level'], 3))

        return Response({
            'success': True,
            'nodes': nodes,
            'edges': edges,
            'warnings': warnings,
            'generated_at': now.isoformat(),
        })


class EmbeddingStatsView(APIView):
    """Lightweight endpoint for polling embedding index progress.
    GET /api/v1/health/embedding-stats/
    Returns: {indexed, total, not_indexed, pct}
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from news.models import Article, ArticleEmbedding
        total = Article.objects.filter(is_published=True, is_deleted=False).count()
        indexed = ArticleEmbedding.objects.count()
        not_indexed = max(0, total - indexed)
        pct = round(indexed / total * 100, 1) if total > 0 else 0
        return Response({
            'indexed': indexed,
            'total': total,
            'not_indexed': not_indexed,
            'pct': pct,
        })
