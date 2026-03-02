"""
Article engagement mixin — handles ratings, views, recommendations, trending,
feedback, A/B title & image testing, and similar articles.
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit
import logging

from news.api_views._shared import invalidate_article_cache

logger = logging.getLogger(__name__)


class ArticleEngagementMixin:
    """Mixin for article engagement actions on ArticleViewSet."""

    @action(detail=True, methods=['post'])
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    def rate(self, request, slug=None):
        """Rate an article"""
        from news.models import Rating
        article = self.get_object()
        rating_value = request.data.get('rating')
        logger.debug(f"Received rating_value: {rating_value}, type: {type(rating_value)}")
        if not rating_value:
            return Response({'error': 'Rating value is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            rating_int = int(rating_value)
            if not (1 <= rating_int <= 5):
                return Response({'error': 'Rating must be between 1 and 5'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({'error': 'Rating must be a valid number'}, status=status.HTTP_400_BAD_REQUEST)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip_address = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        import hashlib
        fingerprint = hashlib.md5(f"{ip_address}_{user_agent[:100]}".encode()).hexdigest()
        logger.debug(f"Rating attempt - Article: {article.id}, Fingerprint hash: {fingerprint[:8]}...")
        if request.user.is_authenticated:
            existing_rating = Rating.objects.filter(article=article, user=request.user).first()
        else:
            existing_rating = Rating.objects.filter(article=article, ip_address=fingerprint).first()
        if existing_rating:
            logger.info(f"Updated rating for article {article.id}")
            existing_rating.rating = rating_int
            existing_rating.save()
        else:
            logger.info(f"Created new rating for article {article.id}")
            try:
                Rating.objects.create(
                    article=article,
                    user=request.user if request.user.is_authenticated else None,
                    rating=rating_int,
                    ip_address=fingerprint
                )
            except Exception as e:
                logger.error(f"Failed to create rating: {str(e)}")
                return Response({'error': f'Failed to create rating: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        article.refresh_from_db()
        try:
            from django.core.cache import cache
            invalidate_article_cache(article_id=article.id, slug=article.slug)
            logger.info(f"Cache invalidated after rating article: {article.id}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
        return Response({'average_rating': article.average_rating(), 'rating_count': article.rating_count()})

    @action(detail=True, methods=['get'], url_path='my-rating')
    def get_user_rating(self, request, slug=None):
        """Get current user's rating for this article"""
        from news.models import Rating
        article = self.get_object()
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip_address = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        import hashlib
        fingerprint = hashlib.md5(f"{ip_address}_{user_agent[:100]}".encode()).hexdigest()
        user_rating = Rating.objects.filter(article=article, ip_address=fingerprint).first()
        if user_rating:
            return Response({'user_rating': user_rating.rating, 'has_rated': True})
        return Response({'user_rating': 0, 'has_rated': False})

    @action(detail=True, methods=['post'])
    def increment_views(self, request, slug=None):
        """Increment article views using Redis atomic counter"""
        from news.models import Article
        article = self.get_object()
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            cache_key = f"article_views:{article.id}"
            user_identifier = None
            if request.user.is_authenticated:
                user_identifier = f"user_{request.user.id}"
            else:
                session_key = request.session.session_key
                if session_key:
                    user_identifier = f"session_{session_key}"
                else:
                    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                    ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
                    user_identifier = f"ip_{ip}"
            if user_identifier:
                tags = article.tags.all()
                tag_names = [t.name for t in tags]
                if tag_names:
                    pref_key = f"user_prefs:{user_identifier}"
                    try:
                        for tag_name in tag_names:
                            redis_conn.zincrby(pref_key, 1, tag_name)
                        redis_conn.expire(pref_key, 60 * 60 * 24 * 30)
                    except Exception:
                        pass
                # Track reading history for ML recommendations
                try:
                    history_key = f"user_history:{user_identifier}"
                    redis_conn.lrem(history_key, 0, str(article.id))  # Remove if exists
                    redis_conn.lpush(history_key, str(article.id))     # Add to front
                    redis_conn.ltrim(history_key, 0, 19)               # Keep last 20
                    redis_conn.expire(history_key, 60 * 60 * 24 * 30)  # 30 days
                except Exception:
                    pass
            new_count = redis_conn.incr(cache_key)
            if new_count % 10 == 0:
                Article.objects.filter(id=article.id).update(views=new_count)
                try:
                    from django.core.cache import cache
                    invalidate_article_cache(article_id=article.id, slug=article.slug)
                except Exception:
                    pass
            return Response({'status': 'success', 'views': new_count})
        except Exception:
            from django.db import models
            Article.objects.filter(id=article.id).update(views=models.F('views') + 1)
            return Response({'status': 'fallback_success'})

    @action(detail=False, methods=['get'])
    def recommended(self, request):
        """User Personalization Engine: Returns articles based on ML reading history analysis."""
        from news.serializers import ArticleListSerializer
        user_identifier = None
        if request.user.is_authenticated:
            user_identifier = f"user_{request.user.id}"
        else:
            session_key = getattr(request, 'session', None)
            session_key = session_key.session_key if session_key else None
            if session_key:
                user_identifier = f"session_{session_key}"
            else:
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
                user_identifier = f"ip_{ip}"

        ml_article_ids = []
        # Try ML-based recommendations from reading history
        try:
            from django_redis import get_redis_connection
            from ai_engine.modules.content_recommender import find_similar, is_available
            redis_conn = get_redis_connection("default")
            
            # Get recently viewed article IDs from Redis
            history_key = f"user_history:{user_identifier}"
            recent_ids_bytes = redis_conn.lrange(history_key, 0, 4)  # Last 5 viewed
            recent_ids = [int(aid.decode('utf-8')) for aid in recent_ids_bytes] if recent_ids_bytes else []
            
            if recent_ids and is_available():
                # Find articles similar to what user has read
                seen = set(recent_ids)
                for article_id in recent_ids[:3]:  # Use top 3 most recent
                    try:
                        similar = find_similar(article_id, top_n=5)
                        for s in similar:
                            if s['id'] not in seen:
                                ml_article_ids.append(s['id'])
                                seen.add(s['id'])
                    except Exception:
                        continue
                if ml_article_ids:
                    logger.info(f"ML recommended {len(ml_article_ids)} articles for {user_identifier}")
        except Exception as e:
            logger.debug(f"ML recommendations failed: {e}")

        queryset = self.get_queryset().filter(is_published=True)

        if ml_article_ids:
            # ML-based: order by similarity (preserve order from find_similar)
            from django.db.models import Case, When, Value, IntegerField
            preserved_order = Case(
                *[When(id=pk, then=Value(i)) for i, pk in enumerate(ml_article_ids)],
                default=Value(999),
                output_field=IntegerField(),
            )
            ml_qs = queryset.filter(id__in=ml_article_ids).annotate(
                ml_rank=preserved_order
            ).order_by('ml_rank')
            # Fill remaining slots with popular articles
            remaining = queryset.exclude(id__in=ml_article_ids).order_by('-views', '-created_at')
            from itertools import chain
            combined_ids = list(ml_qs.values_list('id', flat=True)) + list(remaining.values_list('id', flat=True)[:20])
            preserved_full = Case(
                *[When(id=pk, then=Value(i)) for i, pk in enumerate(combined_ids)],
                default=Value(999),
                output_field=IntegerField(),
            )
            queryset = queryset.filter(id__in=combined_ids).annotate(
                final_rank=preserved_full
            ).order_by('final_rank')
        else:
            # Fallback: tag-based preferences from Redis
            top_tags = []
            try:
                from django_redis import get_redis_connection
                redis_conn = get_redis_connection("default")
                pref_key = f"user_prefs:{user_identifier}"
                top_tags_bytes = redis_conn.zrevrange(pref_key, 0, 2)
                top_tags = [t.decode('utf-8') for t in top_tags_bytes]
            except Exception:
                pass
            if top_tags:
                from django.db.models import Case, When, Value, IntegerField
                queryset = queryset.annotate(
                    has_matching_tag=Case(
                        When(tags__name__in=top_tags, then=Value(1)),
                        default=Value(0),
                        output_field=IntegerField(),
                    ),
                ).distinct().order_by('-views', '-has_matching_tag', '-created_at')
            else:
                queryset = queryset.order_by('-views', '-created_at')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ArticleListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = ArticleListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='feedback', permission_classes=[AllowAny])
    def submit_feedback(self, request, slug=None):
        """Submit user feedback about article issues"""
        article = self.get_object()
        category = request.data.get('category', 'other')
        message = request.data.get('message', '').strip()
        if not message or len(message) < 5:
            return Response({'error': 'Message must be at least 5 characters'}, status=400)
        if len(message) > 1000:
            return Response({'error': 'Message too long (max 1000 characters)'}, status=400)
        valid_categories = ['factual_error', 'typo', 'outdated', 'hallucination', 'other']
        if category not in valid_categories:
            category = 'other'
        ip = self._get_client_ip(request)
        from django.utils import timezone
        from datetime import timedelta
        from news.models import ArticleFeedback
        if ip:
            recent = ArticleFeedback.objects.filter(
                article=article, ip_address=ip,
                created_at__gte=timezone.now() - timedelta(days=1)
            ).exists()
            if recent:
                return Response({'error': 'You already submitted feedback for this article today'}, status=429)
        feedback = ArticleFeedback.objects.create(
            article=article, category=category, message=message[:1000],
            ip_address=ip, user_agent=request.META.get('HTTP_USER_AGENT', '')[:300]
        )
        return Response({'success': True, 'id': feedback.id, 'message': 'Thank you for your feedback!'}, status=201)

    def _get_client_ip(self, request):
        """Extract client IP from request headers"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    @action(detail=True, methods=['post'], url_path='toggle-publish', permission_classes=[IsAdminUser])
    def toggle_publish(self, request, slug=None):
        """Toggle article published/draft status."""
        article = self.get_object()
        article.is_published = not article.is_published
        article.save(update_fields=['is_published'])
        
        try:
            invalidate_article_cache(article_id=article.id, slug=article.slug)
        except Exception:
            pass
        
        new_status = 'published' if article.is_published else 'draft'
        logger.info(f"[TOGGLE-PUBLISH] Article {article.id} '{article.title[:50]}' → {new_status}")
        
        return Response({
            'success': True,
            'is_published': article.is_published,
            'status': new_status,
        })

    @action(detail=True, methods=['get'], url_path='ab-title', permission_classes=[AllowAny])
    def ab_title(self, request, slug=None):
        """Get the A/B test title variant for this visitor."""
        import random
        from news.models import ArticleTitleVariant
        article = self.get_object()
        variants = list(ArticleTitleVariant.objects.filter(article=article))
        if not variants:
            return Response({'title': article.title, 'variant': None, 'ab_active': False})
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_bot = any(bot in user_agent for bot in ['googlebot', 'bingbot', 'yandex', 'spider', 'crawler'])
        cookie_key = f'ab_{article.id}'
        assigned_variant = request.COOKIES.get(cookie_key)
        if is_bot:
            assigned_variant = 'A'
        if assigned_variant and assigned_variant in [v.variant for v in variants]:
            chosen = next(v for v in variants if v.variant == assigned_variant)
        else:
            chosen = random.choice(variants)
            assigned_variant = chosen.variant
        if not is_bot:
            from django.db.models import F
            ArticleTitleVariant.objects.filter(id=chosen.id).update(impressions=F('impressions') + 1)
        response = Response({'title': chosen.title, 'variant': chosen.variant, 'ab_active': True})
        if not is_bot:
            response.set_cookie(cookie_key, assigned_variant, max_age=30*24*60*60, httponly=False, samesite='Lax')
        return response

    @action(detail=True, methods=['post'], url_path='ab-click', permission_classes=[AllowAny])
    def ab_click(self, request, slug=None):
        """Record a click for an A/B test variant."""
        from news.models import ArticleTitleVariant
        from django.db.models import F
        article = self.get_object()
        variant_letter = request.data.get('variant') or request.COOKIES.get(f'ab_{article.id}')
        if not variant_letter:
            return Response({'success': False, 'error': 'No variant specified'}, status=400)
        updated = ArticleTitleVariant.objects.filter(article=article, variant=variant_letter).update(clicks=F('clicks') + 1)
        return Response({'success': updated > 0})

    @action(detail=True, methods=['get'], url_path='ab-stats', permission_classes=[IsAdminUser])
    def ab_stats(self, request, slug=None):
        """Get A/B test statistics for an article (admin only)."""
        from news.models import ArticleTitleVariant
        article = self.get_object()
        variants = ArticleTitleVariant.objects.filter(article=article)
        data = [{'id': v.id, 'variant': v.variant, 'title': v.title, 'impressions': v.impressions,
                 'clicks': v.clicks, 'ctr': v.ctr, 'is_winner': v.is_winner} for v in variants]
        return Response({
            'article_id': article.id, 'article_slug': article.slug, 'original_title': article.title,
            'variants': data, 'total_impressions': sum(v.impressions for v in variants),
            'total_clicks': sum(v.clicks for v in variants),
        })

    @action(detail=True, methods=['post'], url_path='ab-pick-winner', permission_classes=[IsAdminUser])
    def ab_pick_winner(self, request, slug=None):
        """Pick the winning A/B variant and apply it as the article title."""
        from news.models import ArticleTitleVariant
        article = self.get_object()
        variant_letter = request.data.get('variant')
        if not variant_letter:
            return Response({'error': 'Specify variant (A, B, or C)'}, status=400)
        try:
            winner = ArticleTitleVariant.objects.get(article=article, variant=variant_letter)
        except ArticleTitleVariant.DoesNotExist:
            return Response({'error': f'Variant {variant_letter} not found'}, status=404)
        ArticleTitleVariant.objects.filter(article=article).update(is_winner=False)
        winner.is_winner = True
        winner.save(update_fields=['is_winner'])
        article.title = winner.title
        article.save(update_fields=['title'])
        return Response({'success': True, 'new_title': winner.title, 'variant': winner.variant, 'ctr': winner.ctr})

    @action(detail=True, methods=['get'], url_path='ab-image', permission_classes=[AllowAny])
    def ab_image(self, request, slug=None):
        """Get the A/B test image variant for this visitor."""
        import random
        from news.models.system import ArticleImageVariant
        from django.db.models import F
        article = self.get_object()
        variants = list(ArticleImageVariant.objects.filter(article=article))
        if not variants:
            return Response({'image_source': article.image_source, 'variant': None, 'ab_active': False})
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_bot = any(bot in user_agent for bot in ['googlebot', 'bingbot', 'yandex', 'spider', 'crawler'])
        cookie_key = f'ab_img_{article.id}'
        assigned_variant = request.COOKIES.get(cookie_key)
        if is_bot:
            assigned_variant = 'A'
        if assigned_variant and assigned_variant in [v.variant for v in variants]:
            chosen = next(v for v in variants if v.variant == assigned_variant)
        else:
            chosen = random.choice(variants)
            assigned_variant = chosen.variant
        if not is_bot:
            ArticleImageVariant.objects.filter(id=chosen.id).update(impressions=F('impressions') + 1)
        response = Response({'image_url': chosen.image_url, 'image_source': chosen.image_source,
                             'variant': chosen.variant, 'ab_active': True})
        if not is_bot:
            response.set_cookie(cookie_key, assigned_variant, max_age=30*24*60*60, httponly=False, samesite='Lax')
        return response

    @action(detail=True, methods=['post'], url_path='ab-image-click', permission_classes=[AllowAny])
    def ab_image_click(self, request, slug=None):
        """Record a click for an A/B test image variant."""
        from news.models.system import ArticleImageVariant
        from django.db.models import F
        article = self.get_object()
        variant_letter = request.data.get('variant') or request.COOKIES.get(f'ab_img_{article.id}')
        if not variant_letter:
            return Response({'success': False, 'error': 'No variant specified'}, status=400)
        updated = ArticleImageVariant.objects.filter(article=article, variant=variant_letter).update(clicks=F('clicks') + 1)
        return Response({'success': updated > 0})

    @action(detail=True, methods=['get'], url_path='ab-image-stats', permission_classes=[IsAdminUser])
    def ab_image_stats(self, request, slug=None):
        """Get A/B test statistics for article image (admin only)."""
        from news.models.system import ArticleImageVariant
        article = self.get_object()
        variants = ArticleImageVariant.objects.filter(article=article)
        data = [{'id': v.id, 'variant': v.variant, 'image_url': v.image_url, 'image_source': v.image_source,
                 'impressions': v.impressions, 'clicks': v.clicks, 'ctr': v.ctr, 'is_winner': v.is_winner} for v in variants]
        return Response({
            'article_id': article.id, 'original_image_source': article.image_source,
            'variants': data, 'total_impressions': sum(v.impressions for v in variants),
            'total_clicks': sum(v.clicks for v in variants),
        })

    @action(detail=True, methods=['post'], url_path='ab-image-pick-winner', permission_classes=[IsAdminUser])
    def ab_image_pick_winner(self, request, slug=None):
        """Pick the winning A/B image variant."""
        from news.models.system import ArticleImageVariant
        article = self.get_object()
        variant_letter = request.data.get('variant')
        if not variant_letter:
            return Response({'error': 'Specify variant (A, B, or C)'}, status=400)
        try:
            winner = ArticleImageVariant.objects.get(article=article, variant=variant_letter)
        except ArticleImageVariant.DoesNotExist:
            return Response({'error': f'Variant {variant_letter} not found'}, status=404)
        ArticleImageVariant.objects.filter(article=article).update(is_winner=False, is_active=False)
        winner.is_winner = True
        winner.save(update_fields=['is_winner'])
        article.image_source = winner.image_source
        article.save(update_fields=['image_source'])
        return Response({'success': True, 'new_image_source': winner.image_source, 'variant': winner.variant, 'ctr': winner.ctr})

    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60 * 15))
    def trending(self, request):
        """Get trending articles (most viewed in last 7 days, fallback to all-time)"""
        from django.utils import timezone
        from datetime import timedelta
        from news.models import Article
        from news.serializers import ArticleListSerializer
        week_ago = timezone.now() - timedelta(days=7)
        trending = Article.objects.defer('engagement_score', 'engagement_updated_at').filter(
            is_published=True, is_deleted=False, created_at__gte=week_ago, views__gt=0,
        ).order_by('-views')[:10]
        if not trending.exists():
            trending = Article.objects.defer('engagement_score', 'engagement_updated_at').filter(
                is_published=True, is_deleted=False,
            ).order_by('-views')[:10]
        serializer = ArticleListSerializer(trending, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60 * 60))
    def popular(self, request):
        """Get most popular articles (all time)"""
        from news.models import Article
        from news.serializers import ArticleListSerializer
        popular = Article.objects.defer('engagement_score', 'engagement_updated_at').filter(
            is_published=True, is_deleted=False
        ).order_by('-views')[:10]
        serializer = ArticleListSerializer(popular, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def reset_all_views(self, request):
        """Reset all article views to 0 (admin only)"""
        from news.models import Article
        if not request.user.is_staff:
            return Response({'detail': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        count = Article.objects.all().update(views=0)
        return Response({'detail': f'Reset views to 0 for {count} articles', 'articles_updated': count})

    @action(detail=True, methods=['get'])
    def similar_articles(self, request, slug=None):
        """Find similar articles using TF-IDF ML model + make/model fallback."""
        from news.models import Article, CarSpecification
        from news.serializers import ArticleListSerializer
        article = self.get_object()
        result_ids = []
        # Try local ML model first (free, instant, no API calls)
        try:
            from ai_engine.modules.content_recommender import find_similar, is_available
            if is_available():
                similar = find_similar(article.id, top_n=15)
                result_ids = [s['id'] for s in similar]
                logger.info(f"ML found {len(result_ids)} similar articles for {article.id}")
        except Exception as e:
            logger.warning(f"ML similar search failed for {article.id}: {e}")
        # Fallback to vector search engine if ML didn't find enough
        if len(result_ids) < 6:
            try:
                from ai_engine.modules.vector_search import get_vector_engine
                engine = get_vector_engine()
                similar = engine.find_similar_articles(article.id, k=15)
                for s in similar:
                    aid = s['article_id']
                    if aid not in result_ids and aid != article.id:
                        result_ids.append(aid)
            except Exception as e:
                logger.warning(f"Vector search fallback failed for {article.id}: {e}")
        if len(result_ids) < 6:
            try:
                car_spec = CarSpecification.objects.filter(article=article).first()
                if car_spec and car_spec.make and car_spec.make != 'Not specified':
                    existing_ids = set(result_ids) | {article.id}
                    if car_spec.model and car_spec.model != 'Not specified':
                        same_model = CarSpecification.objects.filter(
                            make__iexact=car_spec.make, model__iexact=car_spec.model,
                            article__is_published=True, article__is_deleted=False
                        ).exclude(article_id__in=existing_ids).values_list('article_id', flat=True)[:5]
                        result_ids.extend(same_model)
                        existing_ids.update(same_model)
                    same_make = CarSpecification.objects.filter(
                        make__iexact=car_spec.make, article__is_published=True, article__is_deleted=False
                    ).exclude(article_id__in=existing_ids).values_list('article_id', flat=True)[:8]
                    result_ids.extend(same_make)
            except Exception as e:
                logger.warning(f"Make/model fallback failed: {e}")
        if len(result_ids) < 6:
            try:
                existing_ids = set(result_ids) | {article.id}
                cat_ids = article.categories.values_list('id', flat=True)
                if cat_ids:
                    same_cat = Article.objects.filter(
                        categories__id__in=cat_ids, is_published=True, is_deleted=False
                    ).exclude(id__in=existing_ids).order_by('-views').values_list('id', flat=True)[:10]
                    result_ids.extend(same_cat)
            except Exception:
                pass
        seen = set()
        unique_ids = []
        for aid in result_ids:
            if aid not in seen and aid != article.id:
                seen.add(aid)
                unique_ids.append(aid)
        articles = Article.objects.filter(id__in=unique_ids[:15], is_published=True, is_deleted=False)
        id_order = {aid: i for i, aid in enumerate(unique_ids)}
        sorted_articles = sorted(articles, key=lambda a: id_order.get(a.id, 999))
        serializer = ArticleListSerializer(sorted_articles, many=True, context={'request': request})
        return Response({'success': True, 'similar_articles': serializer.data})

    @action(detail=False, methods=['get'], url_path='semantic-search')
    def semantic_search(self, request):
        """Search articles by meaning using TF-IDF ML model.
        GET /api/v1/articles/semantic-search/?q=electric SUV review
        """
        from news.serializers import ArticleListSerializer
        from news.models import Article
        
        query = request.query_params.get('q', '').strip()
        if not query or len(query) < 2:
            return Response({'results': [], 'query': query})
        
        try:
            from ai_engine.modules.content_recommender import semantic_search as ml_search, is_available
            if not is_available():
                return Response({'results': [], 'query': query, 'ml_available': False})
            
            results = ml_search(query, top_n=12)
            article_ids = [r['id'] for r in results]
            
            if article_ids:
                from django.db.models import Case, When, Value, IntegerField
                preserved = Case(
                    *[When(id=pk, then=Value(i)) for i, pk in enumerate(article_ids)],
                    default=Value(999),
                    output_field=IntegerField(),
                )
                articles = Article.objects.filter(
                    id__in=article_ids, is_published=True, is_deleted=False
                ).annotate(ml_rank=preserved).order_by('ml_rank')
                serializer = ArticleListSerializer(articles, many=True, context={'request': request})
                return Response({
                    'results': serializer.data,
                    'query': query,
                    'ml_available': True,
                    'count': len(serializer.data),
                })
            
            return Response({'results': [], 'query': query, 'ml_available': True})
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return Response({'results': [], 'query': query, 'error': str(e)})

    @action(detail=False, methods=['get'], url_path='ml-info')
    def ml_info(self, request):
        """Get ML Content Recommender model info."""
        try:
            from ai_engine.modules.content_recommender import get_model_info
            return Response(get_model_info())
        except Exception as e:
            return Response({'error': str(e)})

