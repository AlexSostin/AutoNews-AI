from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, BasePermission, AllowAny
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.models import User
from .models import Article, Category, Tag, Comment, Rating, CarSpecification, ArticleImage, SiteSettings, Favorite
from .serializers import (
    ArticleListSerializer, ArticleDetailSerializer, 
    CategorySerializer, TagSerializer, CommentSerializer, 
    RatingSerializer, CarSpecificationSerializer, ArticleImageSerializer,
    SiteSettingsSerializer, FavoriteSerializer
)
import os
import sys
import re
import logging

logger = logging.getLogger(__name__)


class IsStaffOrReadOnly(BasePermission):
    """
    Custom permission to only allow staff users to edit objects.
    Read-only for everyone else. Logs unauthorized access attempts.
    """
    def has_permission(self, request, view):
        # Read permissions are allowed to any request
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        # Write permissions only for staff
        is_allowed = request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)
        
        # Log unauthorized write attempts
        if not is_allowed and request.user and request.user.is_authenticated:
            logger.warning(
                f"Unauthorized write attempt: user={request.user.username}, "
                f"method={request.method}, path={request.path}"
            )
        
        return is_allowed


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
    permission_classes = [IsStaffOrReadOnly]
    lookup_field = 'slug'
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
    queryset = Article.objects.filter(is_deleted=False).select_related('category', 'specs').prefetch_related('tags', 'gallery')
    permission_classes = [IsStaffOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content', 'summary']
    ordering_fields = ['created_at', 'views', 'title']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """
        Allow anyone to rate articles and check their rating,
        but require staff for other write operations
        """
        if self.action in ['rate', 'get_user_rating', 'increment_views']:
            return [AllowAny()]
        return super().get_permissions()
    
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
    
    def list(self, request, *args, **kwargs):
        # Don't cache for authenticated users (admins need to see fresh data)
        if request.user.is_authenticated:
            return super().list(request, *args, **kwargs)
        # Cache for anonymous users only
        return self._cached_list(request, *args, **kwargs)
    
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def _cached_list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        # Don't cache for authenticated users
        if request.user.is_authenticated:
            return super().retrieve(request, *args, **kwargs)
        return self._cached_retrieve(request, *args, **kwargs)
    
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def _cached_retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Handle article update with special handling for FormData (multipart)"""
        import json
        
        # If this is multipart/form-data, we need to process tag_ids specially
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Make request.data mutable if needed
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            
            # Parse tag_ids from JSON string to list
            tag_ids = data.get('tag_ids')
            if tag_ids and isinstance(tag_ids, str):
                try:
                    parsed_tags = json.loads(tag_ids)
                    # Replace the string with actual list in request data
                    if hasattr(request.data, '_mutable'):
                        request.data._mutable = True
                    request.data.setlist('tag_ids', [str(t) for t in parsed_tags])
                    if hasattr(request.data, '_mutable'):
                        request.data._mutable = False
                except json.JSONDecodeError:
                    pass
        
        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def generate_from_youtube(self, request):
        """Generate article from YouTube URL with WebSocket progress"""
        import uuid
        
        youtube_url = request.data.get('youtube_url')
        task_id = request.data.get('task_id') or str(uuid.uuid4())[:8]
        
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
            
            # Add both backend and ai_engine paths for proper imports
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ai_engine_dir = os.path.join(backend_dir, 'ai_engine')
            
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            if ai_engine_dir not in sys.path:
                sys.path.insert(0, ai_engine_dir)
            
            try:
                from ai_engine.main import generate_article_from_youtube
            except Exception as import_error:
                print(f"Import error: {import_error}")
                print(traceback.format_exc())
                return Response(
                    {'error': f'Failed to import AI engine: {str(import_error)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Generate article with task_id for WebSocket progress
            result = generate_article_from_youtube(youtube_url, task_id=task_id)
            
            if result.get('success'):
                article_id = result['article_id']
                print(f"[generate_from_youtube] Article created with ID: {article_id}")
                
                # Clear cache so new article appears immediately
                from django.core.cache import cache
                cache.clear()
                print(f"[generate_from_youtube] Cache cleared")
                
                # Fetch the article (even if soft-deleted, to debug)
                try:
                    article = Article.objects.get(id=article_id)
                    print(f"[generate_from_youtube] Article found: {article.title}, is_published={article.is_published}, is_deleted={article.is_deleted}")
                    
                    # Force publish and un-delete in case something went wrong
                    if not article.is_published or article.is_deleted:
                        article.is_published = True
                        article.is_deleted = False
                        article.save()
                        print(f"[generate_from_youtube] Article status updated to published")
                    
                except Article.DoesNotExist:
                    print(f"[generate_from_youtube] Article with ID {article_id} not found!")
                    return Response(
                        {'error': f'Article was created but cannot be found (ID: {article_id})'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
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
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    def rate(self, request, slug=None):
        """Rate an article"""
        article = self.get_object()
        rating_value = request.data.get('rating')
        
        logger.debug(f"Received rating_value: {rating_value}, type: {type(rating_value)}")
        
        if not rating_value:
            return Response(
                {'error': 'Rating value is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            rating_int = int(rating_value)
            if not (1 <= rating_int <= 5):
                return Response(
                    {'error': 'Rating must be between 1 and 5'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Rating must be a valid number'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get user IP and user agent for better fingerprinting (harder to bypass with VPN)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Create fingerprint (IP + User Agent hash for better uniqueness)
        import hashlib
        fingerprint = hashlib.md5(f"{ip_address}_{user_agent[:100]}".encode()).hexdigest()
        
        logger.debug(f"Rating attempt - Article: {article.id}, Fingerprint hash: {fingerprint[:8]}...")
        
        # Check if user already rated (by fingerprint)
        existing_rating = Rating.objects.filter(article=article, ip_address=fingerprint).first()
        
        if existing_rating:
            # Update existing rating
            logger.info(f"Updated rating for article {article.id}")
            existing_rating.rating = rating_int
            existing_rating.save()
        else:
            # Create new rating
            logger.info(f"Created new rating for article {article.id}")
            try:
                rating_obj = Rating.objects.create(
                    article=article,
                    rating=rating_int,
                    ip_address=fingerprint
                )
            except Exception as e:
                logger.error(f"Failed to create rating: {str(e)}")
                return Response(
                    {'error': f'Failed to create rating: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Recalculate average
        article.refresh_from_db()
        
        return Response({
            'average_rating': article.average_rating(),
            'rating_count': article.rating_count()
        })
    
    @action(detail=True, methods=['get'], url_path='my-rating')
    def get_user_rating(self, request, slug=None):
        """Get current user's rating for this article"""
        article = self.get_object()
        
        # Get user IP and user agent for fingerprinting
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Create fingerprint
        import hashlib
        fingerprint = hashlib.md5(f"{ip_address}_{user_agent[:100]}".encode()).hexdigest()
        
        # Get user's rating
        user_rating = Rating.objects.filter(article=article, ip_address=fingerprint).first()
        
        if user_rating:
            return Response({
                'user_rating': user_rating.rating,
                'has_rated': True
            })
        else:
            return Response({
                'user_rating': 0,
                'has_rated': False
            })
    
    @action(detail=True, methods=['post'])
    def increment_views(self, request, slug=None):
        """Increment article views"""
        article = self.get_object()
        article.views += 1
        article.save(update_fields=['views'])
        return Response({'views': article.views})
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def reset_all_views(self, request):
        """Reset all article views to 0 (admin only)"""
        if not request.user.is_staff:
            return Response({'detail': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        count = Article.objects.all().update(views=0)
        return Response({
            'detail': f'Reset views to 0 for {count} articles',
            'articles_updated': count
        })


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.select_related('article')
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
        elif self.action == 'approve':
            return [IsAuthenticated()]
        return [IsStaffOrReadOnly()]
    
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
    permission_classes = [IsStaffOrReadOnly]
    
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


class UserViewSet(viewsets.ViewSet):
    """
    ViewSet for user operations
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user information"""
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'date_joined': user.date_joined.isoformat(),
        })
    
    @action(detail=False, methods=['post'], permission_classes=[])
    @method_decorator(ratelimit(key='ip', rate='5/h', method='POST', block=True))
    def register(self, request):
        """Register a new user with rate limiting to prevent spam"""
        import re
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        username = request.data.get('username', '').strip()
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        
        # Input sanitization
        if not username or not email or not password:
            return Response(
                {'detail': 'Username, email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Username validation
        if len(username) < 3 or len(username) > 30:
            return Response(
                {'detail': 'Username must be between 3 and 30 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return Response(
                {'detail': 'Username can only contain letters, numbers and underscores'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Email validation
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return Response(
                {'detail': 'Invalid email format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Password validation using Django validators
        try:
            validate_password(password)
        except DjangoValidationError as e:
            return Response(
                {'detail': ' '.join(e.messages)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user exists (case-insensitive)
        if User.objects.filter(username__iexact=username).exists():
            return Response(
                {'username': ['User with this username already exists']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {'email': ['User with this email already exists']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            logger.info(f"New user registered: {username} ({email})")
            
            return Response({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'message': 'User registered successfully'
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Registration failed: {str(e)}")
            return Response(
                {'detail': 'Registration failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FavoriteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user favorites
    """
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return favorites for current user"""
        return Favorite.objects.filter(user=self.request.user).select_related('article', 'article__category')
    
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


from rest_framework.views import APIView
import requests as http_requests

class CurrencyRatesView(APIView):
    """
    Get current exchange rates for USD to EUR and CNY.
    Cached for 1 hour to avoid excessive API calls.
    """
    permission_classes = [AllowAny]
    
    @method_decorator(cache_page(60 * 60))  # Cache for 1 hour
    def get(self, request):
        cache_key = 'currency_rates_usd'
        rates = cache.get(cache_key)
        
        if not rates:
            try:
                # Using free exchangerate-api.com
                response = http_requests.get(
                    'https://open.er-api.com/v6/latest/USD',
                    timeout=10
                )
                data = response.json()
                
                if data.get('result') == 'success':
                    all_rates = data.get('rates', {})
                    rates = {
                        'USD': 1.0,
                        'EUR': all_rates.get('EUR', 0.92),
                        'CNY': all_rates.get('CNY', 7.25),
                        'GBP': all_rates.get('GBP', 0.79),
                        'JPY': all_rates.get('JPY', 148.5),
                        'updated_at': data.get('time_last_update_utc', '')
                    }
                    cache.set(cache_key, rates, 60 * 60)  # Cache for 1 hour
                else:
                    # Fallback rates
                    rates = {
                        'USD': 1.0,
                        'EUR': 0.92,
                        'CNY': 7.25,
                        'GBP': 0.79,
                        'JPY': 148.5,
                        'updated_at': 'fallback'
                    }
            except Exception as e:
                logger.warning(f"Failed to fetch currency rates: {e}")
                rates = {
                    'USD': 1.0,
                    'EUR': 0.92,
                    'CNY': 7.25,
                    'GBP': 0.79,
                    'JPY': 148.5,
                    'updated_at': 'fallback'
                }
        
        return Response(rates)
