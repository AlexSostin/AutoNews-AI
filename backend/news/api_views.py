from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from .models import Article, Category, Tag, Comment, Rating, CarSpecification, ArticleImage, SiteSettings
from .serializers import (
    ArticleListSerializer, ArticleDetailSerializer, 
    CategorySerializer, TagSerializer, CommentSerializer, 
    RatingSerializer, CarSpecificationSerializer, ArticleImageSerializer,
    SiteSettingsSerializer
)
import os
import sys
import re


def is_valid_youtube_url(url):
    """Validate YouTube URL to prevent malicious input"""
    if not url or not isinstance(url, str):
        return False
    youtube_regex = r'^(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([a-zA-Z0-9_-]{11})(&.*)?$'
    return bool(re.match(youtube_regex, url))


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @method_decorator(cache_page(60 * 60))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @method_decorator(cache_page(60 * 60))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.select_related('category', 'specs').prefetch_related('tags', 'gallery')
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content', 'excerpt']
    ordering_fields = ['created_at', 'views', 'title']
    ordering = ['-created_at']
    
    def get_object(self):
        """Support lookup by both slug and ID"""
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]
        
        # Try to get by slug first, then by ID if slug fails
        try:
            if lookup_value.isdigit():
                # If it's a number, try ID lookup
                obj = queryset.get(id=lookup_value)
            else:
                # Otherwise use slug
                obj = queryset.get(slug=lookup_value)
        except Article.DoesNotExist:
            # Fallback to original lookup
            filter_kwargs = {self.lookup_field: lookup_value}
            obj = get_object_or_404(queryset, **filter_kwargs)
        
        self.check_object_permissions(self.request, obj)
        return obj
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ArticleListSerializer
        return ArticleDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category', None)
        tag = self.request.query_params.get('tag', None)
        is_published = self.request.query_params.get('is_published', None)
        # Support both 'published' and 'is_published' for backward compatibility
        if is_published is None:
            is_published = self.request.query_params.get('published', None)
        
        # For non-authenticated users, show only published articles
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_published=True)
        
        if category:
            queryset = queryset.filter(category__slug=category)
        if tag:
            queryset = queryset.filter(tags__slug=tag)
        if is_published is not None:
            queryset = queryset.filter(is_published=(is_published.lower() == 'true'))
            
        return queryset
    
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def generate_from_youtube(self, request):
        """Generate article from YouTube URL"""
        youtube_url = request.data.get('youtube_url')
        
        if not youtube_url:
            return Response(
                {'error': 'youtube_url is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate YouTube URL
        if not is_valid_youtube_url(youtube_url):
            return Response(
                {'error': 'Invalid YouTube URL format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Import AI engine
            import traceback
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            try:
                from ai_engine.main import generate_article_from_youtube
            except Exception as import_error:
                print(f"Import error: {import_error}")
                print(traceback.format_exc())
                return Response(
                    {'error': f'Failed to import AI engine: {str(import_error)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Generate article
            result = generate_article_from_youtube(youtube_url)
            
            if result.get('success'):
                article = Article.objects.get(id=result['article_id'])
                serializer = self.get_serializer(article)
                return Response({
                    'success': True,
                    'message': 'Article generated successfully',
                    'article': serializer.data
                })
            else:
                return Response(
                    {'error': result.get('error', 'Unknown error')},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            import traceback
            print(f"Error generating article: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """Rate an article"""
        article = self.get_object()
        rating_value = request.data.get('rating')
        
        if not rating_value or not (1 <= int(rating_value) <= 5):
            return Response(
                {'error': 'Rating must be between 1 and 5'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get user IP for preventing duplicate votes
        user_ip = request.META.get('REMOTE_ADDR', 'unknown')
        
        # Check if user already rated
        existing_rating = Rating.objects.filter(article=article, user_ip=user_ip).first()
        
        if existing_rating:
            return Response(
                {'error': 'You have already rated this article'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create new rating
        Rating.objects.create(
            article=article,
            rating=int(rating_value),
            user_ip=user_ip
        )
        
        # Recalculate average
        article.refresh_from_db()
        
        return Response({
            'average_rating': article.average_rating,
            'rating_count': article.rating_count
        })
    
    @action(detail=True, methods=['post'])
    def increment_views(self, request, pk=None):
        """Increment article views"""
        article = self.get_object()
        article.views += 1
        article.save(update_fields=['views'])
        return Response({'views': article.views})


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.select_related('article')
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'content']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        article_id = self.request.query_params.get('article', None)
        is_approved = self.request.query_params.get('is_approved', None)
        
        if article_id:
            queryset = queryset.filter(article_id=article_id)
        if is_approved is not None:
            queryset = queryset.filter(is_approved=(is_approved.lower() == 'true'))
            
        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        """Approve comment"""
        comment = self.get_object()
        comment.is_approved = True
        comment.save(update_fields=['is_approved'])
        serializer = self.get_serializer(comment)
        return Response(serializer.data)


class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.select_related('article')
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        article_id = self.request.query_params.get('article', None)
        
        if article_id:
            queryset = queryset.filter(article_id=article_id)
            
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create rating with user IP"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get user IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            user_ip = x_forwarded_for.split(',')[0]
        else:
            user_ip = request.META.get('REMOTE_ADDR')
        
        serializer.save(user_ip=user_ip)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class CarSpecificationViewSet(viewsets.ModelViewSet):
    queryset = CarSpecification.objects.all()
    serializer_class = CarSpecificationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['make', 'model', 'year']
    ordering_fields = ['make', 'model', 'year', 'created_at']
    ordering = ['-created_at']


class ArticleImageViewSet(viewsets.ModelViewSet):
    queryset = ArticleImage.objects.select_related('article')
    serializer_class = ArticleImageSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['order', 'created_at']
    ordering = ['order']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        article_id = self.request.query_params.get('article', None)
        
        if article_id:
            queryset = queryset.filter(article_id=article_id)
            
        return queryset


class SiteSettingsViewSet(viewsets.ModelViewSet):
    queryset = SiteSettings.objects.all()
    serializer_class = SiteSettingsSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def list(self, request):
        """Return the single settings instance"""
        settings = SiteSettings.load()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Always return the single settings instance"""
        settings = SiteSettings.load()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)
