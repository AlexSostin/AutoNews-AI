"""
Favorites ViewSet for managing user article favorites.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import Article, Favorite
from ..serializers import FavoriteSerializer


class FavoriteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user favorites
    """
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return favorites for current user"""
        return Favorite.objects.filter(user=self.request.user).select_related('article').prefetch_related('article__categories')
    
    def create(self, request, *args, **kwargs):
        """Add article to favorites"""
        article_id = request.data.get('article')
        
        if not article_id:
            return Response(
                {'detail': 'Article ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if article exists
        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            return Response(
                {'detail': 'Article not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already favorited
        if Favorite.objects.filter(user=request.user, article=article).exists():
            return Response(
                {'detail': 'Article already in favorites'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create favorite
        favorite = Favorite.objects.create(user=request.user, article=article)
        serializer = self.get_serializer(favorite)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        """Remove article from favorites"""
        favorite = self.get_object()
        favorite.delete()
        return Response({'detail': 'Removed from favorites'}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'])
    def toggle(self, request):
        """Toggle favorite status for an article"""
        article_id = request.data.get('article')
        
        if not article_id:
            return Response(
                {'detail': 'Article ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if article exists
        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            return Response(
                {'detail': 'Article not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Toggle favorite
        favorite, created = Favorite.objects.get_or_create(user=request.user, article=article)
        
        if not created:
            # Already exists - remove it
            favorite.delete()
            return Response({
                'detail': 'Removed from favorites',
                'is_favorited': False
            })
        else:
            # Created new favorite
            serializer = self.get_serializer(favorite)
            return Response({
                'detail': 'Added to favorites',
                'is_favorited': True,
                'favorite': serializer.data
            }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def check(self, request):
        """Check if article is favorited"""
        article_id = request.query_params.get('article')
        
        if not article_id:
            return Response(
                {'detail': 'Article ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        is_favorited = Favorite.objects.filter(
            user=request.user,
            article_id=article_id
        ).exists()
        
        return Response({'is_favorited': is_favorited})
