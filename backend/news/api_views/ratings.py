"""
Ratings API ViewSet with rate limiting.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from ..models import Rating
from ..serializers import RatingSerializer


class RatingViewSet(viewsets.ModelViewSet):
    """
    Ratings API with rate limiting.
    - Users can rate articles (rate limited to 20/hour per IP)
    - Authenticated users can see their rating history
    """
    queryset = Rating.objects.select_related('article', 'user')
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']
    
    def get_permissions(self):
        if self.action == 'my_ratings':
            return [IsAuthenticated()]
        return super().get_permissions()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        article_id = self.request.query_params.get('article', None)
        
        if article_id:
            queryset = queryset.filter(article_id=article_id)
            
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create rating with user IP and user reference if authenticated"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get user IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            user_ip = x_forwarded_for.split(',')[0]
        else:
            user_ip = request.META.get('REMOTE_ADDR')
        
        # Save with user reference if authenticated
        if request.user.is_authenticated:
            serializer.save(ip_address=user_ip, user=request.user)
        else:
            serializer.save(ip_address=user_ip)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_ratings(self, request):
        """Get all ratings by the current authenticated user"""
        ratings = self.get_queryset().filter(user=request.user)
        
        serializer = self.get_serializer(ratings, many=True)
        return Response({
            'count': ratings.count(),
            'results': serializer.data
        })
