from rest_framework import viewsets, status, filters as drf_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.utils import timezone
from datetime import timedelta
from ..models import RSSNewsItem, PendingArticle
from ..serializers import RSSNewsItemSerializer
import re
import logging

logger = logging.getLogger(__name__)


class RSSNewsItemViewSet(viewsets.ModelViewSet):
    """
    Browse raw RSS news items and generate articles on demand.
    Staff only.
    """
    queryset = RSSNewsItem.objects.select_related('rss_feed', 'pending_article').all()
    serializer_class = RSSNewsItemSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [drf_filters.OrderingFilter]
    ordering_fields = ['is_favorite', 'published_at', 'created_at']
    ordering = ['-is_favorite', '-created_at']  # default: favorites first, then newest
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by feed
        feed_id = self.request.query_params.get('feed')
        if feed_id:
            queryset = queryset.filter(rss_feed_id=feed_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by brand name (title search — matches all known variants)
        brand_param = self.request.query_params.get('brand')
        if brand_param:
            from django.db.models import Q
            from ..auto_tags import KNOWN_BRANDS, BRAND_DISPLAY_NAMES
            # Collect all raw brand keys whose display name or key matches the param
            brand_lower = brand_param.lower()
            variants = {brand_lower}
            for key in KNOWN_BRANDS:
                display = BRAND_DISPLAY_NAMES.get(key, key)
                if key.lower() == brand_lower or display.lower() == brand_lower:
                    variants.add(key.lower())
                    variants.add(display.lower())
            q = Q()
            for v in variants:
                q |= Q(title__icontains=v)
            queryset = queryset.filter(q)

        # Filter by favorites
        if self.request.query_params.get('favorites') == 'true':
            queryset = queryset.filter(is_favorite=True)

        # By default, exclude dismissed items
        if not self.request.query_params.get('show_dismissed'):
            queryset = queryset.exclude(status='dismissed')
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Generate an AI article from this RSS news item."""
        news_item = self.get_object()
        
        if news_item.status == 'generated':
            return Response(
                {'error': 'Article already generated for this news item'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        news_item.status = 'generating'
        news_item.save(update_fields=['status'])
        
        try:
            from ai_engine.modules.article_generator import expand_press_release
            from ai_engine.main import extract_title, validate_title, _is_generic_header
            
            # Strip HTML tags to get plain text for AI
            plain_text = re.sub(r'<[^>]+>', '', news_item.content).strip()
            if not plain_text:
                plain_text = news_item.excerpt
            
            provider = request.data.get('provider', 'gemini')
            if provider not in ('groq', 'gemini'):
                provider = 'gemini'
            
            # Expand with AI
            expanded_content = expand_press_release(
                press_release_text=plain_text,
                source_url=news_item.source_url,
                provider=provider,
                source_title=news_item.title
            )
            
            # Extract and validate title
            ai_title = extract_title(expanded_content)
            if not ai_title or _is_generic_header(ai_title):
                ai_title = news_item.title
            ai_title = validate_title(ai_title)
            
            # Convert markdown to HTML if needed
            if '###' in expanded_content and '<h2>' not in expanded_content:
                try:
                    import markdown
                    expanded_content = markdown.markdown(expanded_content, extensions=['fenced_code', 'tables'])
                except Exception:
                    pass
            
            # Content quality check
            word_count = len(re.sub(r'<[^>]+>', '', expanded_content).split())
            if word_count < 200:
                news_item.status = 'new'
                news_item.save(update_fields=['status'])
                return Response(
                    {'error': f'AI content too short ({word_count} words), try again'},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )
            
            # Build images list — respect feed's image_policy
            feed = news_item.rss_feed
            image_policy = feed.image_policy if feed else 'pexels_fallback'
            
            if image_policy == 'pexels_only':
                # Media site — don't use their images, search Pexels instead
                images = []
                featured_image = ''
            else:
                # 'original' or 'pexels_fallback' — use source image if available
                images = [news_item.image_url] if news_item.image_url else []
                featured_image = news_item.image_url or ''
            
            # Determine image source
            if image_policy == 'pexels_only':
                img_source = 'pexels'
            elif images:
                img_source = 'rss_original'
            else:
                img_source = 'unknown'
            
            # Create PendingArticle
            pending = PendingArticle.objects.create(
                rss_feed=news_item.rss_feed,
                source_url=news_item.source_url,
                content_hash=news_item.content_hash,
                title=ai_title,
                content=expanded_content,
                excerpt=plain_text[:500],
                images=images,
                featured_image=featured_image,
                image_source=img_source,
                suggested_category=news_item.rss_feed.default_category if news_item.rss_feed else None,
                status='pending'
            )
            
            # Update news item
            news_item.status = 'generated'
            news_item.pending_article = pending
            news_item.save(update_fields=['status', 'pending_article'])
            
            return Response({
                'success': True,
                'message': f'Article generated: {ai_title}',
                'pending_article_id': pending.id
            })
            
        except Exception as e:
            logger.error(f'Error generating article from RSS news item {pk}: {e}', exc_info=True)
            news_item.status = 'new'
            news_item.save(update_fields=['status'])
            return Response(
                {'error': f'Generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Dismiss a news item (hide from feed)."""
        news_item = self.get_object()
        news_item.status = 'dismissed'
        news_item.save(update_fields=['status'])
        return Response({'success': True})
    
    @action(detail=False, methods=['post'])
    def bulk_dismiss(self, request):
        """Dismiss multiple news items."""
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        count = RSSNewsItem.objects.filter(id__in=ids).update(status='dismissed')
        return Response({'success': True, 'count': count})

    @action(detail=False, methods=['post'])
    def cleanup_old(self, request):
        """Delete new/read RSS items older than N days (default 7). Keeps generated/dismissed."""
        days = int(request.data.get('days', 7))
        cutoff = timezone.now() - timedelta(days=days)
        deleted_count, _ = RSSNewsItem.objects.filter(
            status__in=['new', 'read'],
            created_at__lt=cutoff,
        ).delete()
        return Response({'success': True, 'deleted': deleted_count, 'cutoff_days': days})

    @action(detail=False, methods=['post'])
    def bulk_generate(self, request):
        """Generate articles for multiple RSS news items (max 10)."""
        ids = request.data.get('ids', [])
        provider = request.data.get('provider', 'gemini')
        
        if not ids:
            return Response({'error': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        if len(ids) > 10:
            return Response({'error': 'Maximum 10 items per bulk operation'}, status=status.HTTP_400_BAD_REQUEST)
        
        if provider not in ('groq', 'gemini'):
            provider = 'gemini'
        
        items = RSSNewsItem.objects.filter(
            id__in=ids,
            status__in=['new', 'read']
        ).select_related('rss_feed')
        
        if not items.exists():
            return Response({'error': 'No eligible items found (must be new or read status)'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        from ai_engine.modules.article_generator import expand_press_release
        from ai_engine.main import extract_title, validate_title, _is_generic_header
        
        results = []
        success_count = 0
        fail_count = 0
        
        for item in items:
            try:
                item.status = 'generating'
                item.save(update_fields=['status'])
                
                plain_text = re.sub(r'<[^>]+>', '', item.content).strip()
                if not plain_text:
                    plain_text = item.excerpt
                
                expanded_content = expand_press_release(
                    press_release_text=plain_text,
                    source_url=item.source_url,
                    provider=provider,
                    source_title=item.title,
                )
                
                ai_title = extract_title(expanded_content)
                if not ai_title or _is_generic_header(ai_title):
                    ai_title = item.title
                ai_title = validate_title(ai_title)
                
                word_count = len(re.sub(r'<[^>]+>', '', expanded_content).split())
                if word_count < 200:
                    item.status = 'new'
                    item.save(update_fields=['status'])
                    results.append({'id': item.id, 'success': False, 'error': f'Too short ({word_count} words)'})
                    fail_count += 1
                    continue
                
                # Build images based on feed's image policy
                feed = item.rss_feed
                image_policy = feed.image_policy if feed else 'pexels_fallback'
                
                if image_policy == 'pexels_only':
                    images = []
                    featured_image = ''
                    img_source = 'pexels'
                else:
                    images = [item.image_url] if item.image_url else []
                    featured_image = item.image_url or ''
                    img_source = 'rss_original' if images else 'unknown'
                
                pending = PendingArticle.objects.create(
                    rss_feed=item.rss_feed,
                    source_url=item.source_url,
                    content_hash=item.content_hash,
                    title=ai_title,
                    content=expanded_content,
                    excerpt=plain_text[:500],
                    images=images,
                    featured_image=featured_image,
                    image_source=img_source,
                    suggested_category=item.rss_feed.default_category if item.rss_feed else None,
                    status='pending',
                )
                
                item.status = 'generated'
                item.pending_article = pending
                item.save(update_fields=['status', 'pending_article'])
                
                results.append({'id': item.id, 'success': True, 'title': ai_title, 'pending_id': pending.id})
                success_count += 1
                
            except Exception as e:
                logger.error(f'Bulk generate failed for item {item.id}: {e}', exc_info=True)
                item.status = 'new'
                item.save(update_fields=['status'])
                results.append({'id': item.id, 'success': False, 'error': str(e)[:200]})
                fail_count += 1
        
        return Response({
            'success': True,
            'total': len(results),
            'generated': success_count,
            'failed': fail_count,
            'results': results,
        })

    # ================================================================
    # RSS Intelligence Endpoints
    # ================================================================

    @action(detail=False, methods=['get'])
    def trending_brands(self, request):
        """Get trending brands from RSS titles (last N days)."""
        from ..rss_intelligence import get_trending_brands
        days = int(request.query_params.get('days', 7))
        min_mentions = int(request.query_params.get('min', 2))
        trending = get_trending_brands(days=days, min_mentions=min_mentions)
        return Response({'success': True, 'days': days, 'brands': trending})

    @action(detail=False, methods=['get'])
    def trending_topics(self, request):
        """Get trending topics (EV, SUV, recalls, etc.) from RSS titles."""
        from ..rss_intelligence import get_trending_topics
        days = int(request.query_params.get('days', 7))
        topics = get_trending_topics(days=days)
        return Response({'success': True, 'days': days, 'topics': topics})

    @action(detail=False, methods=['post'])
    def run_intelligence(self, request):
        """Run brand detection + model discovery on RSS items.
        Creates Brand(is_visible=False) and VehicleSpecs(article=None) entries."""
        from ..rss_intelligence import process_rss_intelligence
        dry_run = request.data.get('dry_run', False)
        days = int(request.data.get('days', 7))
        
        cutoff = timezone.now() - timedelta(days=days)
        queryset = RSSNewsItem.objects.filter(
            created_at__gte=cutoff,
            status__in=['new', 'read'],
        )
        
        stats = process_rss_intelligence(queryset=queryset, dry_run=dry_run)
        return Response({
            'success': True,
            'dry_run': dry_run,
            'items_scanned': stats['items_scanned'],
            'brands_found': dict(stats['brands_found'].most_common(20)),
            'brands_created': stats['brands_created'],
            'models_found': dict(stats['models_found'].most_common(20)),
            'models_created': stats['models_created'],
        })

    @action(detail=True, methods=['get'])
    def check_duplicates(self, request, pk=None):
        """Check if this RSS item's content is semantically similar to existing articles."""
        from ..rss_intelligence import check_semantic_duplicates
        news_item = self.get_object()
        
        plain_text = re.sub(r'<[^>]+>', '', news_item.content).strip()
        if not plain_text:
            plain_text = news_item.excerpt
        
        threshold = float(request.query_params.get('threshold', 0.85))
        similar = check_semantic_duplicates(plain_text, threshold=threshold)
        
        return Response({
            'success': True,
            'item_id': news_item.id,
            'item_title': news_item.title,
            'similar_articles': similar,
            'has_duplicates': len(similar) > 0,
        })

    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        """Toggle is_favorite on an RSS item. Favorites are kept for 60 days as ML signal."""
        news_item = self.get_object()
        news_item.is_favorite = not news_item.is_favorite
        news_item.save(update_fields=['is_favorite'])
        return Response({
            'success': True,
            'id': news_item.id,
            'is_favorite': news_item.is_favorite,
        })

    # ================================================================
    # Smart RSS Curator Endpoints
    # ================================================================

    @action(detail=False, methods=['post'])
    def curate(self, request):
        """Run Smart RSS Curator pipeline.

        POST /api/v1/rss-news-items/curate/
        Body: { days?: 7, include_ai_summary?: true, provider?: 'gemini' }

        Returns clustered, scored, AI-summarised recommendations.
        """
        import threading

        from ai_engine.modules.rss_curator import curate as run_curator

        days = int(request.data.get('days', 7))
        include_ai = request.data.get('include_ai_summary', True)
        provider = request.data.get('provider', 'gemini')

        if provider not in ('groq', 'gemini'):
            provider = 'gemini'

        result = run_curator(
            days=days,
            include_ai_summary=include_ai,
            provider=provider,
        )
        return Response(result)

    @action(detail=False, methods=['post'])
    def curator_decision(self, request):
        """Log admin decision on a curated item (generate/skip/merge/save_later).

        POST /api/v1/rss-news-items/curator_decision/
        Body: { item_id, decision, cluster_id?, score?, brand? }
        """
        from ..models import CuratorDecisionLog

        item_id = request.data.get('item_id')
        decision = request.data.get('decision')
        cluster_id = request.data.get('cluster_id', '')
        score = int(request.data.get('score', 0))
        brand = request.data.get('brand', '')

        valid_decisions = ('generate', 'skip', 'merge', 'save_later')
        if decision not in valid_decisions:
            return Response(
                {'error': f'Invalid decision. Must be one of: {valid_decisions}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not item_id:
            return Response(
                {'error': 'item_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            news_item = RSSNewsItem.objects.get(id=item_id)
        except RSSNewsItem.DoesNotExist:
            return Response(
                {'error': f'RSSNewsItem {item_id} not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        log = CuratorDecisionLog.objects.create(
            news_item=news_item,
            decision=decision,
            curator_score=score,
            cluster_id=cluster_id,
            brand=brand,
            has_specs_data=request.data.get('has_specs', False),
            source_count=news_item.source_count or 1,
            llm_score=news_item.llm_score,
            title_text=news_item.title[:500],
        )

        # If decision is 'generate', trigger article generation immediately
        generated_article_id = None
        if decision == 'generate':
            try:
                # Re-use existing generate logic
                generate_response = self.generate(request._request, pk=item_id)
                if hasattr(generate_response, 'data') and generate_response.data.get('pending_article_id'):
                    generated_article_id = generate_response.data['pending_article_id']
            except Exception as e:
                logger.error(f'[Curator] Auto-generate failed for item {item_id}: {e}')

        # If decision is 'skip', mark as dismissed
        if decision == 'skip':
            news_item.status = 'dismissed'
            news_item.save(update_fields=['status'])

        return Response({
            'success': True,
            'log_id': log.id,
            'decision': decision,
            'generated_article_id': generated_article_id,
        })

    @action(detail=False, methods=['post'])
    def merge_generate(self, request):
        """Generate a single roundup article from multiple RSS items.

        POST /api/v1/rss-news-items/merge_generate/
        Body: { ids: [1, 2, 3], provider?: 'gemini' }
        """
        ids = request.data.get('ids', [])
        provider = request.data.get('provider', 'gemini')

        if len(ids) < 2:
            return Response(
                {'error': 'At least 2 items required for merge'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(ids) > 5:
            return Response(
                {'error': 'Maximum 5 items per merge'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if provider not in ('groq', 'gemini'):
            provider = 'gemini'

        items = list(
            RSSNewsItem.objects.filter(
                id__in=ids,
                status__in=['new', 'read'],
            ).select_related('rss_feed')
        )

        if len(items) < 2:
            return Response(
                {'error': 'Not enough eligible items (must be new or read status)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark all as generating
        for item in items:
            item.status = 'generating'
            item.save(update_fields=['status'])

        try:
            from ai_engine.modules.article_generator import expand_press_release
            from ai_engine.main import extract_title, validate_title, _is_generic_header

            # Combine content from all items into a roundup prompt
            combined_parts = []
            source_urls = []
            all_images = []

            for item in items:
                plain_text = re.sub(r'<[^>]+>', '', item.content or '').strip()
                if not plain_text:
                    plain_text = item.excerpt or ''
                combined_parts.append(f"### Source: {item.title}\n{plain_text[:800]}")
                if item.source_url:
                    source_urls.append(item.source_url)
                if item.image_url:
                    all_images.append(item.image_url)

            combined_text = (
                "The following are multiple news items about a related topic. "
                "Write a comprehensive roundup article that covers all the key points. "
                "Use a cohesive narrative structure, don't just list the sources.\n\n"
                + "\n\n".join(combined_parts)
            )

            expanded_content = expand_press_release(
                press_release_text=combined_text,
                source_url=source_urls[0] if source_urls else '',
                provider=provider,
                source_title=items[0].title,
            )

            ai_title = extract_title(expanded_content)
            if not ai_title or _is_generic_header(ai_title):
                ai_title = f"Roundup: {items[0].title}"
            ai_title = validate_title(ai_title)

            # Convert markdown to HTML if needed
            if '###' in expanded_content and '<h2>' not in expanded_content:
                try:
                    import markdown
                    expanded_content = markdown.markdown(
                        expanded_content, extensions=['fenced_code', 'tables']
                    )
                except Exception:
                    pass

            word_count = len(re.sub(r'<[^>]+>', '', expanded_content).split())
            if word_count < 200:
                for item in items:
                    item.status = 'new'
                    item.save(update_fields=['status'])
                return Response(
                    {'error': f'Roundup too short ({word_count} words), try again'},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

            # Choose first feed's image policy
            feed = items[0].rss_feed
            image_policy = feed.image_policy if feed else 'pexels_fallback'
            if image_policy == 'pexels_only':
                images = []
                featured_image = ''
                img_source = 'pexels'
            else:
                images = all_images[:3]
                featured_image = all_images[0] if all_images else ''
                img_source = 'rss_original' if images else 'unknown'

            pending = PendingArticle.objects.create(
                rss_feed=items[0].rss_feed,
                source_url=source_urls[0] if source_urls else '',
                content_hash='',
                title=ai_title,
                content=expanded_content,
                excerpt=f"Roundup from {len(items)} sources",
                images=images,
                featured_image=featured_image,
                image_source=img_source,
                suggested_category=(
                    items[0].rss_feed.default_category if items[0].rss_feed else None
                ),
                status='pending',
            )

            # Mark all items as generated
            for item in items:
                item.status = 'generated'
                item.pending_article = pending
                item.save(update_fields=['status', 'pending_article'])

            # Log curator decisions for all merged items
            from ..models import CuratorDecisionLog
            for item in items:
                CuratorDecisionLog.objects.create(
                    news_item=item,
                    decision='merge',
                    curator_score=0,
                    title_text=item.title[:500],
                    source_count=item.source_count or 1,
                    llm_score=item.llm_score,
                )

            return Response({
                'success': True,
                'title': ai_title,
                'pending_article_id': pending.id,
                'items_merged': len(items),
                'word_count': word_count,
            })

        except Exception as e:
            logger.error(f'Merge generate failed: {e}', exc_info=True)
            for item in items:
                item.status = 'new'
                item.save(update_fields=['status'])
            return Response(
                {'error': f'Merge generation failed: {str(e)[:200]}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

