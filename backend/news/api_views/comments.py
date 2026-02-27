"""
Comments API ViewSet with rate limiting, spam protection, and moderation.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from ..models import Comment
from ..serializers import CommentSerializer
from ._shared import IsStaffOrReadOnly
import logging

logger = logging.getLogger(__name__)


class CommentViewSet(viewsets.ModelViewSet):
    """
    Comments API with rate limiting to prevent spam.
    - Anyone can create comments (rate limited to 10/hour per IP)
    - Staff can approve/delete comments
    - Authenticated users can see their own comment history
    """
    queryset = Comment.objects.select_related('article', 'user')
    serializer_class = CommentSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'content']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """
        Allow anyone to create comments (guests can comment),
        but require staff for approve/delete actions
        """
        if self.action in ['create', 'list', 'retrieve']:
            return [AllowAny()]
        elif self.action in ['approve', 'my_comments']:
            return [IsAuthenticated()]
        return [IsStaffOrReadOnly()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        article_id = self.request.query_params.get('article', None)
        is_approved = self.request.query_params.get('is_approved', None)
        # Support 'approved' alias from frontend
        if is_approved is None:
            is_approved = self.request.query_params.get('approved', None)
        
        # Filter by article
        if article_id:
            queryset = queryset.filter(article_id=article_id)
            
        # Filter by approval status
        if is_approved is not None:
            queryset = queryset.filter(is_approved=(str(is_approved).lower() == 'true'))
        
        # Only filter out replies for list actions, not for detail actions (approve, delete, etc.)
        if self.action == 'list':
            include_replies = self.request.query_params.get('include_replies', 'false')
            if include_replies.lower() != 'true':
                queryset = queryset.filter(parent__isnull=True)
            
        return queryset
    
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    def create(self, request, *args, **kwargs):
        """Create comment with rate limiting and honeypot spam protection."""
        # Honeypot: hidden 'website' field — real users never fill it,
        # but spam bots auto-fill every field. Silently reject.
        honeypot = request.data.get('website', '')
        if honeypot:
            logger.warning(
                f"🍯 Honeypot caught spam bot: website='{honeypot}' | "
                f"IP: {request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))}"
            )
            # Return fake success so bot doesn't retry
            return Response({'id': 0, 'status': 'created'}, status=status.HTTP_201_CREATED)
        
        # If user is authenticated, save user reference
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if request.user.is_authenticated:
            comment = serializer.save(user=request.user)
        else:
            comment = serializer.save()
        
        # Run comment through moderation engine
        try:
            from news.comment_moderator import moderate_comment
            result = moderate_comment(
                content=comment.content,
                name=comment.name,
                email=comment.email,
                user=request.user if request.user.is_authenticated else None,
                article_id=comment.article_id,
            )
            comment.moderation_status = result.status
            comment.moderation_reason = result.reason[:255]
            comment.is_approved = result.is_approved
            comment.save(update_fields=['moderation_status', 'moderation_reason', 'is_approved'])
            logger.info(
                f"💬 Comment moderation: {result.status} | "
                f"reason: {result.reason} | name: {comment.name}"
            )
        except Exception as e:
            logger.warning(f"Comment moderation error: {e}")
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['patch', 'post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        """Approve or reject comment — also logs decision for ML training."""
        comment = self.get_object()
        
        # Check if 'approved' is in request data (support both keys)
        is_approved = request.data.get('approved')
        if is_approved is None:
            is_approved = request.data.get('is_approved', True)
            
        comment.is_approved = bool(is_approved)
        comment.moderation_status = 'admin_approved' if comment.is_approved else 'admin_rejected'
        comment.moderation_reason = f"{'Approved' if comment.is_approved else 'Rejected'} by {request.user.username}"
        comment.save(update_fields=['is_approved', 'moderation_status', 'moderation_reason'])
        
        # Log decision for ML training
        try:
            from news.models import CommentModerationLog
            CommentModerationLog.objects.create(
                comment=comment,
                admin_user=request.user,
                decision='approved' if comment.is_approved else 'rejected',
            )
        except Exception as e:
            logger.warning(f"Failed to log moderation decision: {e}")
        
        serializer = self.get_serializer(comment)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_comments(self, request):
        """Get all comments by the current authenticated user"""
        comments = self.get_queryset().filter(
            Q(user=request.user) | Q(email=request.user.email, user__isnull=True)
        ).distinct()
        
        serializer = self.get_serializer(comments, many=True)
        return Response({
            'count': comments.count(),
            'results': serializer.data
        })
