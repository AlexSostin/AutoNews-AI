from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
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
