"""
Article Feedback ViewSet for admin management of user-submitted feedback.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
import logging

logger = logging.getLogger(__name__)


class ArticleFeedbackViewSet(viewsets.ModelViewSet):
    """Admin ViewSet for managing user-submitted article feedback."""
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        from news.models import ArticleFeedback
        qs = ArticleFeedback.objects.select_related('article').order_by('-created_at')
        
        # Filter by resolved status
        resolved = self.request.query_params.get('resolved')
        if resolved == 'true':
            qs = qs.filter(is_resolved=True)
        elif resolved == 'false':
            qs = qs.filter(is_resolved=False)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        
        return qs
    
    def list(self, request):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        data = []
        for fb in (page if page is not None else qs[:100]):
            data.append({
                'id': fb.id,
                'article_id': fb.article_id,
                'article_title': fb.article.title if fb.article else '',
                'article_slug': fb.article.slug if fb.article else '',
                'category': fb.category,
                'category_display': fb.get_category_display(),
                'message': fb.message,
                'ip_address': fb.ip_address,
                'is_resolved': fb.is_resolved,
                'admin_notes': fb.admin_notes,
                'created_at': fb.created_at.isoformat(),
            })
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        from news.models import ArticleFeedback
        fb = ArticleFeedback.objects.get(pk=pk)
        fb.is_resolved = True
        fb.admin_notes = request.data.get('admin_notes', fb.admin_notes)
        fb.save(update_fields=['is_resolved', 'admin_notes'])
        return Response({'success': True})
    
    @action(detail=True, methods=['post'])
    def unresolve(self, request, pk=None):
        from news.models import ArticleFeedback
        fb = ArticleFeedback.objects.get(pk=pk)
        fb.is_resolved = False
        fb.save(update_fields=['is_resolved'])
        return Response({'success': True})
