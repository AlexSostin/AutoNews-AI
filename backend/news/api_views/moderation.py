"""
Content Moderation Queue — human-in-the-loop review between AI generation and publish.

Provides endpoints to:
- List articles pending moderation
- Approve / reject articles with notes
- Bulk approve / reject
- Get moderation stats
"""
import logging
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status

logger = logging.getLogger(__name__)


class ModerationQueueView(APIView):
    """
    GET  /api/v1/admin/moderation/ — list articles pending review
    POST /api/v1/admin/moderation/ — approve/reject articles
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """List articles pending moderation with quality metrics."""
        from news.models import Article
        
        status_filter = request.query_params.get('status', 'pending_review')
        
        articles = Article.objects.filter(
            is_deleted=False,
            moderation_status=status_filter,
        ).select_related('specs', 'moderation_reviewed_by').prefetch_related(
            'categories', 'tags'
        ).order_by('-created_at')[:50]
        
        data = []
        for a in articles:
            # Get quality score from generation metadata
            quality_score = None
            provider = None
            if a.generation_metadata:
                quality_score = a.generation_metadata.get('quality_score')
                provider = a.generation_metadata.get('provider')
            
            specs_info = None
            if hasattr(a, 'specs') and a.specs:
                specs_info = {
                    'make': a.specs.make,
                    'model': a.specs.model,
                    'has_price': bool(a.specs.price),
                }
            
            img_url = ''
            if a.image:
                try:
                    raw = str(a.image)
                    img_url = raw if raw.startswith('http') else ''
                except Exception:
                    pass
            
            data.append({
                'id': a.id,
                'title': a.title,
                'slug': a.slug,
                'summary': (a.summary or '')[:200],
                'image': img_url,
                'categories': [{'id': c.id, 'name': c.name} for c in a.categories.all()],
                'tags': [{'id': t.id, 'name': t.name} for t in a.tags.all()[:5]],
                'specs': specs_info,
                'quality_score': quality_score,
                'provider': provider,
                'content_length': len(a.content or ''),
                'has_images': bool(a.image),
                'moderation_status': a.moderation_status,
                'moderation_notes': a.moderation_notes,
                'moderation_reviewed_at': a.moderation_reviewed_at.isoformat() if a.moderation_reviewed_at else None,
                'moderation_reviewed_by': a.moderation_reviewed_by.username if a.moderation_reviewed_by else None,
                'created_at': a.created_at.isoformat(),
                'is_published': a.is_published,
            })
        
        # Stats
        total_pending = Article.objects.filter(is_deleted=False, moderation_status='pending_review').count()
        total_approved = Article.objects.filter(is_deleted=False, moderation_status='approved').count()
        total_rejected = Article.objects.filter(is_deleted=False, moderation_status='rejected').count()
        
        return Response({
            'articles': data,
            'stats': {
                'pending': total_pending,
                'approved_today': Article.objects.filter(
                    is_deleted=False,
                    moderation_status='approved',
                    moderation_reviewed_at__date=timezone.now().date(),
                ).count(),
                'rejected_today': Article.objects.filter(
                    is_deleted=False,
                    moderation_status='rejected',
                    moderation_reviewed_at__date=timezone.now().date(),
                ).count(),
                'total_pending': total_pending,
                'total_approved': total_approved,
                'total_rejected': total_rejected,
            },
        })
    
    def post(self, request):
        """
        Approve or reject articles.
        
        Body:
        {
            "action": "approve" | "reject",
            "article_ids": [1, 2, 3],
            "notes": "Optional reviewer notes",
            "auto_publish": false  // If true, also set is_published=True on approve
        }
        """
        from news.models import Article
        
        action = request.data.get('action')
        article_ids = request.data.get('article_ids', [])
        notes = request.data.get('notes', '')
        auto_publish = request.data.get('auto_publish', False)
        
        if action not in ('approve', 'reject'):
            return Response(
                {'error': 'action must be "approve" or "reject"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not article_ids:
            return Response(
                {'error': 'article_ids required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        articles = Article.objects.filter(id__in=article_ids, is_deleted=False)
        updated_ids = []
        
        for article in articles:
            article.moderation_status = 'approved' if action == 'approve' else 'rejected'
            article.moderation_notes = notes
            article.moderation_reviewed_at = timezone.now()
            article.moderation_reviewed_by = request.user
            
            update_fields = [
                'moderation_status', 'moderation_notes',
                'moderation_reviewed_at', 'moderation_reviewed_by',
            ]
            
            # Optionally auto-publish on approve
            if action == 'approve' and auto_publish:
                article.is_published = True
                update_fields.append('is_published')
            
            article.save(update_fields=update_fields)
            updated_ids.append(article.id)
            
            logger.info(
                f"[MODERATION] {action.upper()}: '{article.title[:50]}' "
                f"by {request.user.username}"
            )
        
        return Response({
            'success': True,
            'action': action,
            'updated_count': len(updated_ids),
            'article_ids': updated_ids,
        })
