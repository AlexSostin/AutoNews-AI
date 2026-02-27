"""
Article Image ViewSet for managing article gallery images.
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from ..models import ArticleImage
from ..serializers import ArticleImageSerializer


class ArticleImageViewSet(viewsets.ModelViewSet):
    queryset = ArticleImage.objects.select_related('article')
    serializer_class = ArticleImageSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['order', 'created_at']
    ordering = ['order']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        article_param = self.request.query_params.get('article', None)
        
        if article_param:
            # Support both numeric ID and slug
            if article_param.isdigit():
                queryset = queryset.filter(article_id=article_param)
            else:
                queryset = queryset.filter(article__slug=article_param)
            
        return queryset
