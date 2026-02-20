"""
A/B Testing API Views
Handles impression/click tracking for title variants and admin management.
"""
import hashlib
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework import status
from django.db.models import F, Sum
from news.models import ArticleTitleVariant, Article


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

        updated = ArticleTitleVariant.objects.filter(
            id=variant_id, is_active=True
        ).update(clicks=F('clicks') + 1)

        if not updated:
            return Response({'error': 'variant not found or inactive'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'ok': True})


class ABTestsListView(APIView):
    """List all A/B tests (admin only).
    GET /api/v1/ab/tests/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
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

        return Response({'tests': tests, 'count': len(tests)})


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

        # Mark winner and deactivate all variants for this article
        variant.is_winner = True
        variant.save(update_fields=['is_winner'])

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
