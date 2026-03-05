"""
A/B Testing API Views
Handles impression/click tracking for title variants and admin management.
"""
import hashlib
import re
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework import status
from django.db.models import F, Sum
from news.models import ArticleTitleVariant, ArticleImageVariant, Article


def extract_title_pattern(title: str) -> dict:
    """Extract ML-friendly features from a title string.
    Saved alongside winner choice so we can learn what patterns win."""
    words = title.split()
    return {
        'word_count': len(words),
        'char_count': len(title),
        'has_numbers': bool(re.search(r'\d', title)),
        'has_question': title.strip().endswith('?'),
        'has_exclamation': title.strip().endswith('!'),
        'starts_with_number': bool(re.match(r'^\d', title.strip())),
        'has_colon': ':' in title,
        'has_superlative': bool(re.search(r'\b(best|most|top|ultimate|first|new|latest)\b', title, re.IGNORECASE)),
        'has_spec': bool(re.search(r'\b(km|hp|kw|kwh|mph|mpg|bhp|nm|л\.с)\b', title, re.IGNORECASE)),
        'uppercase_ratio': round(sum(1 for c in title if c.isupper()) / max(len(title), 1), 3),
    }


class ABImpressionView(APIView):
    """Track an impression for an A/B test variant.
    POST /api/v1/ab/impression/
    Body: { "variant_id": 123 }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        variant_id = request.data.get('variant_id')
        if not variant_id:
            return Response({'error': 'variant_id required'}, status=status.HTTP_400_BAD_REQUEST)

        variant_type = request.data.get('type', 'title')
        
        if variant_type == 'image':
            updated = ArticleImageVariant.objects.filter(
                id=variant_id, is_active=True
            ).update(impressions=F('impressions') + 1)
        else:
            updated = ArticleTitleVariant.objects.filter(
                id=variant_id, is_active=True
            ).update(impressions=F('impressions') + 1)

        if not updated:
            return Response({'error': 'variant not found or inactive'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'ok': True})


class ABClickView(APIView):
    """Track a click for an A/B test variant.
    POST /api/v1/ab/click/
    Body: { "variant_id": 123 }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        variant_id = request.data.get('variant_id')
        if not variant_id:
            return Response({'error': 'variant_id required'}, status=status.HTTP_400_BAD_REQUEST)

        variant_type = request.data.get('type', 'title')
        
        if variant_type == 'image':
            updated = ArticleImageVariant.objects.filter(
                id=variant_id, is_active=True
            ).update(clicks=F('clicks') + 1)
        else:
            updated = ArticleTitleVariant.objects.filter(
                id=variant_id, is_active=True
            ).update(clicks=F('clicks') + 1)

        if not updated:
            return Response({'error': 'variant not found or inactive'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'ok': True})


class ABTestsListView(APIView):
    """List all A/B tests (admin only).
    GET /api/v1/ab/tests/?limit=20
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        limit = int(request.query_params.get('limit', 20))

        # Get articles with active or past variants
        articles_with_tests = Article.objects.filter(
            title_variants__isnull=False
        ).distinct().prefetch_related('title_variants')

        tests = []
        for article in articles_with_tests:
            variants = article.title_variants.all()
            total_impressions = sum(v.impressions for v in variants)
            is_active = any(v.is_active and not v.is_winner for v in variants)
            winner = next((v for v in variants if v.is_winner), None)

            tests.append({
                'article_id': article.id,
                'article_title': article.title,
                'article_slug': article.slug,
                'is_active': is_active,
                'total_impressions': total_impressions,
                'winner': winner.variant if winner else None,
                'variants': [
                    {
                        'id': v.id,
                        'variant': v.variant,
                        'title': v.title,
                        'impressions': v.impressions,
                        'clicks': v.clicks,
                        'ctr': v.ctr,
                        'is_winner': v.is_winner,
                        'is_active': v.is_active,
                    }
                    for v in variants
                ],
            })

        # Sort: active tests first, then by total impressions
        tests.sort(key=lambda t: (not t['is_active'], -t['total_impressions']))

        total_count = len(tests)
        active_count = sum(1 for t in tests if t['is_active'])
        winners_count = sum(1 for t in tests if t['winner'])

        return Response({
            'tests': tests[:limit],
            'count': total_count,
            'active_count': active_count,
            'winners_count': winners_count,
            'showing': min(limit, total_count),
        })


class ABPickWinnerView(APIView):
    """Manually pick a winner for an A/B test (admin only).
    POST /api/v1/ab/pick-winner/
    Body: { "variant_id": 123 }
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        variant_id = request.data.get('variant_id')
        if not variant_id:
            return Response({'error': 'variant_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            variant = ArticleTitleVariant.objects.get(id=variant_id)
        except ArticleTitleVariant.DoesNotExist:
            return Response({'error': 'variant not found'}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()

        # Mark winner with full selection metadata
        variant.is_winner = True
        variant.selected_at = now
        variant.selection_source = 'admin'
        variant.title_pattern = extract_title_pattern(variant.title)
        variant.save(update_fields=['is_winner', 'selected_at', 'selection_source', 'title_pattern'])

        # Log patterns for ALL variants (losers too — contrast is ML gold)
        for other in ArticleTitleVariant.objects.filter(article=variant.article).exclude(id=variant.id):
            if other.title_pattern is None:
                other.title_pattern = extract_title_pattern(other.title)
                other.save(update_fields=['title_pattern'])

        ArticleTitleVariant.objects.filter(
            article=variant.article
        ).update(is_active=False)

        # Apply winning title to article
        article = variant.article
        article.title = variant.title
        article.save(update_fields=['title'])

        return Response({
            'ok': True,
            'article_id': article.id,
            'winning_variant': variant.variant,
            'winning_title': variant.title,
            'selected_at': now.isoformat(),
            'selection_source': 'admin',
        })


class ABAutoPickView(APIView):
    """Trigger auto-pick for all eligible tests (admin only).
    POST /api/v1/ab/auto-pick/
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        winners = ArticleTitleVariant.check_and_pick_winners()
        return Response({
            'ok': True,
            'winners_picked': len(winners),
            'details': [
                {'article_id': aid, 'variant': v}
                for aid, v in winners
            ],
        })


def get_variant_for_request(article, request):
    """Determine which title variant to show for a given request.
    Uses a cookie-based seed for consistent assignment per visitor.
    Returns (display_title, variant_id) or (article.title, None) if no active test.
    """
    variants = list(article.title_variants.filter(is_active=True, is_winner=False))
    if len(variants) < 2:
        return article.title, None

    # Use cookie or IP for consistent variant assignment
    seed = request.COOKIES.get('ab_seed', '')
    if not seed:
        seed = request.META.get('REMOTE_ADDR', 'unknown')

    # Deterministic hash → variant index
    hash_val = int(hashlib.md5(
        f"{seed}:{article.id}".encode()
    ).hexdigest(), 16)
    chosen = variants[hash_val % len(variants)]

    return chosen.title, chosen.id

def get_image_variant_for_request(article, request):
    """Determine which image variant to show for a given request.
    Uses a cookie-based seed for consistent assignment per visitor.
    Returns (image_url, variant_id) or (article.image, None) if no active test.
    """
    variants = list(article.image_variants.filter(is_active=True, is_winner=False))
    if len(variants) < 2:
        return article.image, None

    # Use cookie or IP for consistent variant assignment
    seed = request.COOKIES.get('ab_seed', '')
    if not seed:
        seed = request.META.get('REMOTE_ADDR', 'unknown')

    # Deterministic hash → variant index
    hash_val = int(hashlib.md5(
        f"image:{seed}:{article.id}".encode()
    ).hexdigest(), 16)
    chosen = variants[hash_val % len(variants)]

    return chosen.image_url, chosen.id
