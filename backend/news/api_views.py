from rest_framework import viewsets, status, filters
from django.db.models import Avg, Count, Exists, OuterRef, Subquery
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, BasePermission, AllowAny, IsAdminUser
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from .models import (
    Article, Category, Tag, TagGroup, Comment, Rating, CarSpecification, 
    ArticleImage, SiteSettings, Favorite, Subscriber, NewsletterHistory,
    YouTubeChannel, RSSFeed, RSSNewsItem, PendingArticle, AutoPublishSchedule, AdminNotification,
    VehicleSpecs, NewsletterSubscriber
)
from .serializers import (
    ArticleListSerializer, ArticleDetailSerializer, 
    CategorySerializer, TagSerializer, TagGroupSerializer, CommentSerializer, 
    RatingSerializer, CarSpecificationSerializer, ArticleImageSerializer,
    SiteSettingsSerializer, FavoriteSerializer, SubscriberSerializer, NewsletterHistorySerializer,
    YouTubeChannelSerializer, RSSFeedSerializer, RSSNewsItemSerializer, PendingArticleSerializer, AutoPublishScheduleSerializer,
    AdminNotificationSerializer, VehicleSpecsSerializer
)
import os
import sys
import re
import logging

logger = logging.getLogger(__name__)


def invalidate_article_cache(article_id=None, slug=None):
    """
    Selectively invalidate cache keys related to articles.
    Much faster than cache.clear() which deletes EVERYTHING.
    
    Args:
        article_id: Article ID to invalidate specific article cache
        slug: Article slug to invalidate specific article cache
    """
    keys_to_delete = []
    
    # Specific article keys
    if article_id:
        keys_to_delete.append(f'article_{article_id}')
    if slug:
        keys_to_delete.append(f'article_slug_{slug}')
    
    # Pattern-based keys (need to scan Redis)
    patterns_to_delete = [
        'article_list_*',     # Article list pages
        'articles_page_*',    # Paginated lists
        'category_*',         # Category views (article counts changed)
        'homepage_*',         # Homepage caches
        'trending_*',         # Trending articles
        'latest_*',           # Latest articles
        'featured_*',         # Featured articles
        'views.decorators.cache.cache_*',  # Django @cache_page keys
        ':1:views.decorators.cache.cache_page*',  # Django cache_page with prefix
    ]
    
    # Delete simple keys first
    if keys_to_delete:
        cache.delete_many(keys_to_delete)
    
    # Delete pattern-matched keys
    try:
        from django.core.cache.backends.redis import RedisCache
        if isinstance(cache, RedisCache) or hasattr(cache, '_cache'):
            # Use Redis SCAN for pattern matching (safe for large datasets)
            redis_client = cache._cache.get_client() if hasattr(cache._cache, 'get_client') else cache._cache
            
            for pattern in patterns_to_delete:
                cursor = 0
                while True:
                    cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                    if keys:
                        # Decode bytes to strings if needed
                        str_keys = [k.decode('utf-8') if isinstance(k, bytes) else k for k in keys]
                        cache.delete_many(str_keys)
                    if cursor == 0:
                        break
            
            logger.info(f"Selectively invalidated article cache (article_id={article_id}, slug={slug})")
        else:
            # Fallback for non-Redis backends - still better than clearing everything
            logger.warning("Non-Redis cache backend - pattern matching not supported")
            cache.delete_many(keys_to_delete)
    except Exception as e:
        logger.warning(f"Failed to invalidate pattern cache keys: {e}")
        # Still better to continue than fail


class CurrentUserView(APIView):
    """Get and update current user information"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
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
    
    def patch(self, request):
        user = request.user
        
        # Update allowed fields (except email)
        if 'first_name' in request.data:
            user.first_name = request.data['first_name'][:30]
        if 'last_name' in request.data:
            user.last_name = request.data['last_name'][:150]
        
        # Email change requires verification (handled by separate endpoint)
        if 'email' in request.data:
            return Response(
                {'email': ['Email change requires verification. Use /api/v1/auth/email/request-change/ endpoint']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.save()
        
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        })


from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator


@method_decorator(ratelimit(key='user', rate='5/h', method='POST'), name='post')
class ChangePasswordView(APIView):
    """Change user password"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from .validators import validate_password_strength
        from .security_utils import log_security_event, get_client_ip, get_user_agent
        
        user = request.user
        old_password = request.data.get('old_password', '')
        new_password1 = request.data.get('new_password1', '')
        new_password2 = request.data.get('new_password2', '')
        
        # Validate old password
        if not check_password(old_password, user.password):
            return Response({'old_password': ['Current password is incorrect']}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate new passwords match
        if new_password1 != new_password2:
            return Response({'new_password1': ['Passwords do not match']}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate password strength
        is_valid, error_message = validate_password_strength(new_password1)
        if not is_valid:
            return Response({'new_password1': [error_message]}, status=status.HTTP_400_BAD_REQUEST)
        
        # Change password
        user.set_password(new_password1)
        user.save()
        
        # Log security event
        log_security_event(
            user=user,
            action='password_changed',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        # TODO: Send email notification
        
        return Response({'detail': 'Password changed successfully'})


class EmailPreferencesView(APIView):
    """Get and update user email preferences"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from .models import EmailPreferences
        from .serializers import EmailPreferencesSerializer
        
        # Get or create preferences for user
        prefs, created = EmailPreferences.objects.get_or_create(user=request.user)
        serializer = EmailPreferencesSerializer(prefs)
        return Response(serializer.data)
    
    def patch(self, request):
        from .models import EmailPreferences
        from .serializers import EmailPreferencesSerializer
        
        prefs, created = EmailPreferences.objects.get_or_create(user=request.user)
        serializer = EmailPreferencesSerializer(prefs, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RequestEmailChangeView(APIView):
    """Request email change - sends verification code to new email"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from .models import EmailVerification
        from .security_utils import get_client_ip
        from django.utils import timezone
        from datetime import timedelta
        import random
        
        new_email = request.data.get('new_email', '').strip().lower()
        
        # Validate email format
        if not new_email:
            return Response({'new_email': ['Email is required']}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if email is taken by another user
        if User.objects.filter(email__iexact=new_email).exclude(id=request.user.id).exists():
            return Response({'new_email': ['This email is already taken']}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if same as current email
        if new_email == request.user.email.lower():
            return Response({'new_email': ['This is your current email']}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate 6-digit code
        code = str(random.randint(100000, 999999))
        
        # Create verification record
        verification = EmailVerification.objects.create(
            user=request.user,
            new_email=new_email,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        # TODO: Send email with code
        # For now, return code in response (DEV ONLY!)
        print(f"🔑 Verification code for {new_email}: {code}")
        
        return Response({
            'detail': f'Verification code sent to {new_email}',
            'code': code,  # DEV ONLY - remove in production
            'expires_in': 900  # 15 minutes in seconds
        })


class VerifyEmailChangeView(APIView):
    """Verify email change with code"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from .models import EmailVerification
        from .security_utils import log_security_event, get_client_ip, get_user_agent
        
        code = request.data.get('code', '').strip()
        
        if not code:
            return Response({'code': ['Verification code is required']}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find valid verification
        try:
            verification = EmailVerification.objects.filter(
                user=request.user,
                code=code,
                is_used=False
            ).latest('created_at')
        except EmailVerification.DoesNotExist:
            return Response({'code': ['Invalid verification code']}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if expired
        if not verification.is_valid():
            return Response({'code': ['Verification code has expired']}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update email
        old_email = request.user.email
        request.user.email = verification.new_email
        request.user.save()
        
        # Mark verification as used
        verification.is_used = True
        verification.save()
        
        # Log security event
        log_security_event(
            user=request.user,
            action='email_changed',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            old_value=old_email,
            new_value=verification.new_email
        )
        
        # TODO: Send notification to old email
        
        return Response({
            'detail': 'Email changed successfully',
            'new_email': verification.new_email
        })


class PasswordResetRequestView(APIView):
    """Request password reset - sends reset link to email"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .models import PasswordResetToken
        from .security_utils import get_client_ip
        from django.utils import timezone
        from datetime import timedelta
        import uuid
        
        email = request.data.get('email', '').strip().lower()
        
        if not email:
            return Response({'email': ['Email is required']}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find user by email
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Don't reveal if email exists or not
            return Response({'detail': 'If email exists, password reset link has been sent'})
        
        # Generate unique token
        token = str(uuid.uuid4())
        
        # Create reset token
        reset = PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=timezone.now() + timedelta(hours=1),
            ip_address=get_client_ip(request)
        )
        
        # TODO: Send email with reset link
        reset_link = f"http://localhost:3000/reset-password?token={token}"
        print(f"🔑 Password reset link for {email}: {reset_link}")
        
        return Response({
            'detail': 'If email exists, password reset link has been sent',
            'reset_link': reset_link  # DEV ONLY - remove in production
        })


class PasswordResetConfirmView(APIView):
    """Confirm password reset with token"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .models import PasswordResetToken
        from .validators import validate_password_strength
        from .security_utils import log_security_event, get_client_ip, get_user_agent
        
        token = request.data.get('token', '').strip()
        new_password = request.data.get('new_password', '')
        
        if not token:
            return Response({'token': ['Reset token is required']}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find token
        try:
            reset = PasswordResetToken.objects.get(token=token, is_used=False)
        except PasswordResetToken.DoesNotExist:
            return Response({'token': ['Invalid or expired reset token']}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if expired
        if not reset.is_valid():
            return Response({'token': ['Reset token has expired']}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate password strength
        is_valid, error_message = validate_password_strength(new_password)
        if not is_valid:
            return Response({'new_password': [error_message]}, status=status.HTTP_400_BAD_REQUEST)
        
        # Change password
        reset.user.set_password(new_password)
        reset.user.save()
        
        # Mark token as used
        reset.is_used = True
        reset.save()
        
        # Log security event
        log_security_event(
            user=reset.user,
            action='password_reset_completed',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        
        # TODO: Send confirmation email
        
        return Response({'detail': 'Password reset successfully'})


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
    pagination_class = None  # Return all categories for dropdowns
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    lookup_field = 'slug'
    
    def get_queryset(self):
        """Filter categories by visibility for non-authenticated users"""
        queryset = super().get_queryset()
        # Admins see all categories, public users only see visible ones
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_visible=True)
        return queryset

    def get_object(self):
        """Support lookup by both slug and ID"""
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]
        
        try:
            if lookup_value.isdigit():
                obj = queryset.get(id=lookup_value)
            else:
                obj = queryset.get(slug=lookup_value)
        except Category.DoesNotExist:
            from django.shortcuts import get_object_or_404
            filter_kwargs = {self.lookup_field: lookup_value}
            obj = get_object_or_404(queryset, **filter_kwargs)
        
        self.check_object_permissions(self.request, obj)
        return obj


class TagGroupViewSet(viewsets.ModelViewSet):
    queryset = TagGroup.objects.all()
    serializer_class = TagGroupSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsStaffOrReadOnly]
    pagination_class = None  # Return all tags
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.filter(is_deleted=False).select_related('specs').prefetch_related('categories', 'tags', 'gallery').annotate(
        avg_rating=Avg('ratings__rating'),
        num_ratings=Count('ratings'),
    )
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
            queryset = queryset.filter(categories__slug=category)
        if tag:
            queryset = queryset.filter(tags__slug=tag)
        if is_published is not None:
            queryset = queryset.filter(is_published=(is_published.lower() == 'true'))
        
        # Annotate is_favorited for authenticated users (avoids N+1 per-article query)
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                _is_favorited=Exists(
                    Favorite.objects.filter(
                        user=self.request.user,
                        article=OuterRef('pk')
                    )
                )
            )
            
        return queryset
    
    def list(self, request, *args, **kwargs):
        # Don't cache for authenticated users (admins need to see fresh data)
        if request.user.is_authenticated:
            return super().list(request, *args, **kwargs)
        # Cache for anonymous users only
        return self._cached_list(request, *args, **kwargs)
    
    @method_decorator(cache_page(30))  # Cache for 30 seconds (was 5 min - too long for fresh content)
    def _cached_list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        # Don't cache for authenticated users
        if request.user.is_authenticated:
            return super().retrieve(request, *args, **kwargs)
        return self._cached_retrieve(request, *args, **kwargs)
    
    @method_decorator(cache_page(60))  # Cache for 1 minute (was 5 min)
    def _cached_retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete article and immediately clear ALL cache (delete is rare, reliability > speed)"""
        instance = self.get_object()
        article_id = instance.id
        slug = instance.slug
        instance.delete()
        cache.clear()  # Full clear for delete - reliable, and delete is rare
        logger.info(f"Article deleted and all cache cleared: id={article_id}, slug={slug}")
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def update(self, request, *args, **kwargs):
        """Handle article update with special handling for FormData (multipart)"""
        import json
        
        # If this is multipart/form-data, we need to process tag_ids specially
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Don't use .copy() on request.data - it tries to deepcopy file objects which fails
            # Instead, create a new QueryDict and manually copy non-file fields
            from django.http import QueryDict
            
            # Parse tag_ids from JSON string to list
            tag_ids_raw = request.data.get('tag_ids')
            if tag_ids_raw and isinstance(tag_ids_raw, str):
                try:
                    parsed_tags = json.loads(tag_ids_raw)
                    if isinstance(parsed_tags, list):
                        # Modify request.data directly (make it mutable first)
                        if hasattr(request.data, '_mutable'):
                            request.data._mutable = True
                        request.data.setlist('tag_ids', [str(t) for t in parsed_tags])
                        if hasattr(request.data, '_mutable'):
                            request.data._mutable = False
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse tag_ids in ArticleViewSet: {e}")
                    pass
        
        # Helper to check for boolean flags in form data (which come as strings 'true'/'false')
        def is_true(key):
            val = request.data.get(key)
            return val and str(val).lower() == 'true'

        # Perform update first
        try:
            response = super().update(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in ArticleViewSet.update super().update: {e}")
            raise
        
        # Then handle deletions if successful
        if response.status_code == 200:
            try:
                instance = self.get_object()
                changed = False
                
                if is_true('delete_image'):
                    instance.image = None
                    changed = True
                if is_true('delete_image_2'):
                    instance.image_2 = None
                    changed = True
                if is_true('delete_image_3'):
                    instance.image_3 = None
                    changed = True
                    
                if changed:
                    instance.save()
                    serializer = self.get_serializer(instance)
                    response = Response(serializer.data)
                
                # Selectively invalidate cache (MUCH faster than cache.clear())
                try:
                    invalidate_article_cache(
                        article_id=instance.id,
                        slug=instance.slug
                    )
                except Exception as cache_err:
                    logger.warning(f"Failed to invalidate article cache: {cache_err}")
                    
            except Exception as inner_err:
                logger.error(f"Error in ArticleViewSet.update post-processing: {inner_err}")
                # Don't return 500 if update was already successful
                
        return response


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
            from ai_engine.modules.youtube_client import YouTubeClient
        except Exception as import_error:
            print(f"Import error: {import_error}")
            print(traceback.format_exc())
            return Response(
                {'error': f'Failed to import AI engine: {str(import_error)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Get AI provider from request (default to 'groq')
        provider = request.data.get('provider', 'groq')
        if provider not in ['groq', 'gemini']:
            return Response(
                {'error': 'Provider must be either "groq" or "gemini"'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Generate article with task_id for WebSocket progress and selected provider
        # Now supporting Draft Safety: is_published=False
        result = generate_article_from_youtube(
            youtube_url, 
            task_id=task_id, 
            provider=provider,
            is_published=False  # Save as Draft!
        )
        
        if result.get('success'):
            article_id = result['article_id']
            print(f"[generate_from_youtube] Draft Article created with ID: {article_id}")
            
            # Invalidate cache so new article appears immediately
            from django.core.cache import cache
            invalidate_article_cache(article_id=article_id)
            
            # Fetch the article to verify
            try:
                article = Article.objects.get(id=article_id)
                serializer = self.get_serializer(article)
                return Response({
                    'success': True,
                    'message': 'Article generated successfully (Draft)',
                    'article': serializer.data
                })
            except Article.DoesNotExist:
                return Response(
                    {'error': f'Article was created but cannot be found (ID: {article_id})'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        else:
            return Response(
                {'error': result.get('error', 'Unknown error')},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='translate-enhance')
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    def translate_enhance(self, request):
        """Translate Russian text to English and generate a formatted HTML article."""
        russian_text = request.data.get('russian_text', '').strip()
        if not russian_text:
            return Response(
                {'error': 'russian_text is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(russian_text) < 20:
            return Response(
                {'error': 'Text is too short. Please provide at least a few sentences.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        category = request.data.get('category', 'News')
        target_length = request.data.get('target_length', 'medium')
        tone = request.data.get('tone', 'professional')
        seo_keywords = request.data.get('seo_keywords', '')
        provider = request.data.get('provider', 'gemini')
        save_as_draft = request.data.get('save_as_draft', False)

        if target_length not in ('short', 'medium', 'long'):
            target_length = 'medium'
        if tone not in ('professional', 'casual', 'technical'):
            tone = 'professional'
        if provider not in ('groq', 'gemini'):
            provider = 'gemini'

        try:
            from ai_engine.modules.translator import translate_and_enhance
            result = translate_and_enhance(
                russian_text=russian_text,
                category=category,
                target_length=target_length,
                tone=tone,
                seo_keywords=seo_keywords,
                provider=provider,
            )
        except Exception as e:
            logger.error(f'Translation error: {e}')
            return Response(
                {'error': f'Translation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Optionally save as draft
        if save_as_draft and result.get('title') and result.get('content'):
            try:
                from django.utils.text import slugify
                slug = slugify(result.get('suggested_slug') or result['title'])[:80]
                
                # Make sure slug is unique
                base_slug = slug
                counter = 1
                while Article.objects.filter(slug=slug).exists():
                    slug = f'{base_slug}-{counter}'
                    counter += 1

                article = Article.objects.create(
                    title=result['title'],
                    slug=slug,
                    content=result['content'],
                    summary=result.get('summary', ''),
                    seo_description=result.get('meta_description', '')[:160],
                    meta_keywords=', '.join(result.get('seo_keywords', [])),
                    is_published=False,
                )

                # Assign categories
                suggested = result.get('suggested_categories', [])
                if suggested:
                    for cat_name in suggested:
                        cat = Category.objects.filter(name__iexact=cat_name).first()
                        if cat:
                            article.categories.add(cat)
                
                # Fall back to the user-selected category
                if article.categories.count() == 0:
                    cat = Category.objects.filter(name__iexact=category).first()
                    if cat:
                        article.categories.add(cat)

                from django.core.cache import cache
                invalidate_article_cache(article_id=article.id, slug=article.slug)

                result['article_id'] = article.id
                result['article_slug'] = article.slug
                result['saved'] = True
                print(f'💾 Draft saved: {article.title} (ID: {article.id})')
            except Exception as save_error:
                logger.error(f'Failed to save draft: {save_error}')
                result['saved'] = False
                result['save_error'] = str(save_error)

        return Response({
            'success': True,
            **result,
        })

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
        # Standards: If user is authenticated, use user ID as primary key for uniqueness
        if request.user.is_authenticated:
            existing_rating = Rating.objects.filter(article=article, user=request.user).first()
        else:
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
                    user=request.user if request.user.is_authenticated else None,
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
        
        # CLEAR CACHE to ensure average rating is updated for anonymous users immediately
        # This fixes the bug where rating resets to 0.0 on refresh
        try:
            from django.core.cache import cache
            invalidate_article_cache(article_id=article.id, slug=article.slug)
            logger.info(f"Cache invalidated after rating article: {article.id}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
        
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
        """Increment article views using Redis atomic counter for better performance"""
        article = self.get_object()
        
        # Try to use Redis for atomic increment (faster, no race conditions)
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            cache_key = f"article_views:{article.id}"
            
            # Atomic increment in Redis
            new_count = redis_conn.incr(cache_key)
            
            # Sync to database every 10 views (reduces DB writes)
            if new_count % 10 == 0:
                Article.objects.filter(id=article.id).update(views=new_count)
                # Invalidate article cache so the new view count is visible
                try:
                    from django.core.cache import cache
                    invalidate_article_cache(article_id=article.id, slug=article.slug)
                except Exception:
                    pass
            
            return Response({'views': new_count})
        except Exception:
            # Fallback to database if Redis unavailable
            article.views += 1
            article.save(update_fields=['views'])
            return Response({'views': article.views})
    
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60 * 15))  # Cache trending for 15 minutes
    def trending(self, request):
        """Get trending articles (most viewed in last 7 days)"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Get articles from last 7 days, sorted by views
        week_ago = timezone.now() - timedelta(days=7)
        trending = Article.objects.filter(
            is_published=True,
            is_deleted=False,
            created_at__gte=week_ago
        ).order_by('-views')[:10]
        
        serializer = ArticleListSerializer(trending, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60 * 60))  # Cache popular for 1 hour
    def popular(self, request):
        """Get most popular articles (all time)"""
        popular = Article.objects.filter(
            is_published=True,
            is_deleted=False
        ).order_by('-views')[:10]
        
        serializer = ArticleListSerializer(popular, many=True, context={'request': request})
        return Response(serializer.data)
    
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
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def extract_specs(self, request, slug=None):
        """
        Extract vehicle specifications from article using AI
        POST /api/v1/articles/{slug}/extract-specs/
        """
        article = self.get_object()
        
        try:
            from ai_engine.modules.specs_extractor import extract_vehicle_specs
            
            # Extract specs using AI
            specs_data = extract_vehicle_specs(
                title=article.title,
                content=article.content,
                summary=article.summary or ""
            )
            
            # Create or update VehicleSpecs
            vehicle_specs, created = VehicleSpecs.objects.update_or_create(
                article=article,
                defaults=specs_data
            )
            
            serializer = VehicleSpecsSerializer(vehicle_specs)
            
            return Response({
                'success': True,
                'created': created,
                'specs': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error extracting specs for article {article.id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def similar_articles(self, request, slug=None):
        """
        Find similar articles using vector search
        GET /api/v1/articles/{slug}/similar-articles/
        """
        article = self.get_object()
        
        try:
            from ai_engine.modules.vector_search import get_vector_engine
            
            engine = get_vector_engine()
            similar = engine.find_similar_articles(article.id, k=15)
            
            # Get Article objects for similar IDs
            similar_ids = [s['article_id'] for s in similar]
            articles = Article.objects.filter(
                id__in=similar_ids,
                is_published=True,
                is_deleted=False
            )
            
            serializer = ArticleListSerializer(articles, many=True, context={'request': request})
            
            return Response({
                'success': True,
                'similar_articles': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error finding similar articles for {article.id}: {e}")
            return Response({
                'success': True,
                'similar_articles': []
            })



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
        """Create comment with rate limiting (10 comments per hour per IP)"""
        # If user is authenticated, save user reference
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if request.user.is_authenticated:
            serializer.save(user=request.user)
        else:
            serializer.save()
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['patch', 'post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        """Approve or reject comment"""
        comment = self.get_object()
        
        # Check if 'approved' is in request data (support both keys)
        is_approved = request.data.get('approved')
        if is_approved is None:
            is_approved = request.data.get('is_approved', True)  # Default to True for backward compat
            
        comment.is_approved = bool(is_approved)
        comment.save(update_fields=['is_approved'])
        serializer = self.get_serializer(comment)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_comments(self, request):
        """Get all comments by the current authenticated user"""
        # Filter by user (for authenticated comments) OR by email (for guest comments)
        user_comments = self.get_queryset().filter(user=request.user)
        email_comments = self.get_queryset().filter(email=request.user.email, user__isnull=True)
        
        # Combine both querysets
        from django.db.models import Q
        comments = self.get_queryset().filter(
            Q(user=request.user) | Q(email=request.user.email, user__isnull=True)
        ).distinct()
        
        serializer = self.get_serializer(comments, many=True)
        return Response({
            'count': comments.count(),
            'results': serializer.data
        })


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


class CarSpecificationViewSet(viewsets.ModelViewSet):
    queryset = CarSpecification.objects.select_related('article').all()
    serializer_class = CarSpecificationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = None  # Return all specs (no global PAGE_SIZE limit)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['make', 'model', 'trim', 'model_name', 'engine', 'article__title']
    ordering_fields = ['make', 'model', 'price', 'horsepower']
    ordering = ['make', 'model']

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def re_extract(self, request, pk=None):
        """Re-run AI/regex spec extraction for an existing CarSpecification.
        POST /api/v1/car-specifications/{id}/re_extract/
        """
        spec = self.get_object()
        article = spec.article

        try:
            from news.spec_extractor import extract_specs_from_content, save_specs_for_article
            specs = extract_specs_from_content(article)
            if specs and specs.get('make') and specs['make'] != 'Not specified':
                result = save_specs_for_article(article, specs)
                if result:
                    serializer = self.get_serializer(result)
                    return Response({
                        'success': True,
                        'message': f'Re-extracted: {result.make} {result.model}',
                        'spec': serializer.data,
                    })
            return Response({
                'success': False,
                'message': 'Could not extract specs from article content',
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Re-extract failed for spec {pk}: {e}')
            return Response({
                'success': False,
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def extract_for_article(self, request):
        """Create/update CarSpecification from an article ID.
        POST /api/v1/car-specifications/extract_for_article/
        Body: { "article_id": 86 }
        """
        article_id = request.data.get('article_id')
        if not article_id:
            return Response({'success': False, 'message': 'article_id is required'},
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            article = Article.objects.get(id=article_id, is_published=True)
        except Article.DoesNotExist:
            return Response({'success': False, 'message': 'Article not found or not published'},
                          status=status.HTTP_404_NOT_FOUND)

        try:
            from news.spec_extractor import extract_specs_from_content, save_specs_for_article
            specs = extract_specs_from_content(article)
            if specs and specs.get('make') and specs['make'] != 'Not specified':
                result = save_specs_for_article(article, specs)
                if result:
                    serializer = self.get_serializer(result)
                    return Response({
                        'success': True,
                        'created': not CarSpecification.objects.filter(
                            article=article).exclude(id=result.id).exists(),
                        'message': f'Extracted: {result.make} {result.model}',
                        'spec': serializer.data,
                    })
            return Response({
                'success': False,
                'message': 'Could not extract specs from article content',
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Extract specs failed for article {article_id}: {e}')
            return Response({
                'success': False,
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

    def update(self, request, *args, **kwargs):
        """Always update the single settings instance"""
        settings = SiteSettings.load()
        serializer = self.get_serializer(settings, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        serializer.save()
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
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    def google_oauth(self, request):
        """
        Verify Google ID token and create/login user
        Expects: { "credential": "google_id_token" }
        Returns: { "access": "jwt_token", "refresh": "jwt_refresh", "user": {...} }
        """
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        from rest_framework_simplejwt.tokens import RefreshToken
        
        credential = request.data.get('credential')
        
        if not credential:
            return Response(
                {'detail': 'Google credential is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Verify the Google ID token
            # We don't need to specify CLIENT_ID - Google's public keys work without it
            idinfo = id_token.verify_oauth2_token(
                credential, 
                google_requests.Request()
            )
            
            # Extract user information from the token
            email = idinfo.get('email')
            if not email:
                return Response(
                    {'detail': 'Email not provided by Google'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            email = email.lower().strip()
            name = idinfo.get('name', '')
            given_name = idinfo.get('given_name', '')
            family_name = idinfo.get('family_name', '')
            picture = idinfo.get('picture', '')
            
            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],  # Use email prefix as username
                    'first_name': given_name,
                    'last_name': family_name,
                }
            )
            
            # If username collision, append number
            if created and User.objects.filter(username=user.username).exclude(id=user.id).exists():
                base_username = user.username
                counter = 1
                while User.objects.filter(username=f"{base_username}{counter}").exists():
                    counter += 1
                user.username = f"{base_username}{counter}"
                user.save()
            
            # Update user info if changed
            if not created:
                updated = False
                if user.first_name != given_name:
                    user.first_name = given_name
                    updated = True
                if user.last_name != family_name:
                    user.last_name = family_name
                    updated = True
                if updated:
                    user.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            logger.info(f"Google OAuth {'registration' if created else 'login'}: {email}")
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff,
                    'date_joined': user.date_joined.isoformat(),
                },
                'created': created,
            }, status=status.HTTP_200_OK)
        
        except ValueError as e:
            # Invalid token
            logger.warning(f"Invalid Google token: {str(e)}")
            return Response(
                {'detail': 'Invalid Google credential'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            logger.error(f"Google OAuth failed: {str(e)}")
            return Response(
                {'detail': 'Authentication failed. Please try again.'},
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


class SubscriberViewSet(viewsets.ModelViewSet):
    """
    Newsletter subscription management.
    - Anyone can subscribe (rate limited)
    - Staff can view/manage subscribers
    """
    serializer_class = SubscriberSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Show all subscribers for admins, only active for others"""
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return NewsletterSubscriber.objects.all()
        return NewsletterSubscriber.objects.filter(is_active=True)
    
    def get_permissions(self):
        if self.action in ['list', 'destroy', 'send_newsletter', 'export_csv', 'import_csv', 'bulk_delete', 'newsletter_history']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    @method_decorator(ratelimit(key='ip', rate='5/h', method='POST', block=True))
    def create(self, request, *args, **kwargs):
        """Subscribe to newsletter"""
        email = request.data.get('email', '').lower().strip()
        
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already subscribed
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email,
            defaults={'is_active': True}
        )
        
        if not created and subscriber.is_active:
            return Response({'message': 'Already subscribed!'}, status=status.HTTP_200_OK)
        
        # Reactivate if previously unsubscribed
        if not subscriber.is_active:
            subscriber.is_active = True
            subscriber.unsubscribed_at = None
            subscriber.save()
        
        # Send welcome email
        try:
            from django.core.mail import send_mail
            send_mail(
                subject='Welcome to Fresh Motors! 🚗',
                message='Thank you for subscribing to Fresh Motors newsletter!\n\nYou will receive the latest automotive news and reviews.',
                from_email=None,  # Uses DEFAULT_FROM_EMAIL
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception as e:
            logger.warning(f"Failed to send welcome email: {e}")
        
        return Response({
            'message': 'Successfully subscribed!',
            'email': email
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def unsubscribe(self, request):
        """Unsubscribe from newsletter"""
        from django.utils import timezone
        
        email = request.data.get('email', '').lower().strip()
        
        try:
            subscriber = NewsletterSubscriber.objects.get(email=email)
            subscriber.is_active = False
            subscriber.unsubscribed_at = timezone.now()
            subscriber.save()
            return Response({'message': 'Successfully unsubscribed'})
        except NewsletterSubscriber.DoesNotExist:
            return Response({'error': 'Email not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def send_newsletter(self, request):
        """Send newsletter to all active subscribers (admin only)"""
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        subject = request.data.get('subject')
        message = request.data.get('message')
        
        if not subject or not message:
            return Response({'error': 'Subject and message required'}, status=status.HTTP_400_BAD_REQUEST)
        
        subscribers = NewsletterSubscriber.objects.filter(is_active=True).values_list('email', flat=True)
        
        if not subscribers:
            return Response({'error': 'No active subscribers'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from django.core.mail import send_mass_mail
            
            messages = [
                (subject, message, None, [email])
                for email in subscribers
            ]
            
            sent = send_mass_mail(messages, fail_silently=False)
            
            # Save to history
            NewsletterHistory.objects.create(
                subject=subject,
                message=message,
                sent_to_count=sent,
                sent_by=request.user
            )
            
            return Response({
                'message': f'Newsletter sent to {sent} subscribers',
                'count': sent
            })
        except Exception as e:
            logger.error(f"Failed to send newsletter: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def export_csv(self, request):
        """Export all subscribers as CSV"""
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="subscribers.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Email', 'Status', 'Subscribed Date', 'Unsubscribed Date'])
        
        subscribers = NewsletterSubscriber.objects.all()
        for sub in subscribers:
            writer.writerow([
                sub.email,
                'Active' if sub.is_active else 'Unsubscribed',
                sub.subscribed_at.strftime('%Y-%m-%d %H:%M:%S'),
                sub.unsubscribed_at.strftime('%Y-%m-%d %H:%M:%S') if sub.unsubscribed_at else ''
            ])
        
        return response
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def import_csv(self, request):
        """Import subscribers from CSV file"""
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not csv_file.name.endswith('.csv'):
            return Response({'error': 'File must be CSV format'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            import csv
            import io
            
            decoded_file = csv_file.read().decode('utf-8')
            csv_data = csv.DictReader(io.StringIO(decoded_file))
            
            added = 0
            skipped = 0
            
            for row in csv_data:
                email = row.get('email', '').lower().strip()
                if not email:
                    continue
                
                # Check if email is valid
                from django.core.validators import validate_email
                try:
                    validate_email(email)
                except:
                    skipped += 1
                    continue
                
                # Create or update subscriber
                _, created = NewsletterSubscriber.objects.get_or_create(
                    email=email,
                    defaults={'is_active': True}
                )
                
                if created:
                    added += 1
                else:
                    skipped += 1
            
            return Response({
                'message': f'Import complete',
                'added': added,
                'skipped': skipped
            })
        except Exception as e:
            logger.error(f"CSV import failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def bulk_delete(self, request):
        """Delete multiple subscribers"""
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        deleted_count = NewsletterSubscriber.objects.filter(id__in=ids).delete()[0]
        
        return Response({
            'message': f'Deleted {deleted_count} subscribers',
            'count': deleted_count
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def newsletter_history(self, request):
        """Get newsletter history"""
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        history = NewsletterHistory.objects.all()
        serializer = NewsletterHistorySerializer(history, many=True)
        return Response(serializer.data)



class YouTubeChannelViewSet(viewsets.ModelViewSet):
    """
    Manage YouTube channels for automatic article generation.
    Staff only.
    """
    queryset = YouTubeChannel.objects.all()
    serializer_class = YouTubeChannelSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        # Extract channel ID from URL if possible
        channel_url = serializer.validated_data.get('channel_url', '')
        channel_id = self._extract_channel_id(channel_url)
        serializer.save(channel_id=channel_id)
    
    def _extract_channel_id(self, url):
        """Try to extract channel ID from YouTube URL"""
        import re
        patterns = [
            r'youtube\.com/channel/([a-zA-Z0-9_-]+)',
            r'youtube\.com/@([a-zA-Z0-9_-]+)',
            r'youtube\.com/c/([a-zA-Z0-9_-]+)',
            r'youtube\.com/user/([a-zA-Z0-9_-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return ''
    
    @action(detail=True, methods=['post'])
    def scan_now(self, request, pk=None):
        """Manually trigger scan for a specific channel (Background Process)"""
        channel = self.get_object()
        
        import subprocess
        import sys
        from django.conf import settings  # <--- Added import
        
        try:
            # In Docker, manage.py is in the current working directory usually, 
            # or rely on relative path from api_views location
            # BASE_DIR is .../backend/auto_news_site (usually) or .../backend
            
            # Try to find manage.py reliably
            manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
            if not os.path.exists(manage_py):
                # Try one level up if settings is in a subdir
                manage_py = os.path.join(os.path.dirname(settings.BASE_DIR), 'manage.py')
            
            if not os.path.exists(manage_py):
                 # Fallback to simple 'manage.py' assuming CWD is correct root
                 manage_py = 'manage.py'

            print(f"🚀 Launching scan for {channel.name} using {manage_py}")
            
            subprocess.Popen(
                [sys.executable, manage_py, 'scan_youtube', '--channel_id', str(channel.id)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            message = f'Background scan started for {channel.name}'
        except Exception as e:
            print(f"❌ Error starting scan: {e}")
            import traceback
            print(traceback.format_exc())
            message = f'Failed to start scan: {str(e)}'
            
        return Response({
            'message': message,
            'channel_id': channel.id
        })
    
    @action(detail=True, methods=['get'])
    def fetch_videos(self, request, pk=None):
        """Fetch latest videos from channel without generating"""
        channel = self.get_object()
        
        try:
            # Add both backend and ai_engine paths for proper imports
            import os
            import sys
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ai_engine_dir = os.path.join(backend_dir, 'ai_engine')
            
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            if ai_engine_dir not in sys.path:
                sys.path.insert(0, ai_engine_dir)
                
            from ai_engine.modules.youtube_client import YouTubeClient
            client = YouTubeClient()
            
            # Use channel_id if available, otherwise url
            identifier = channel.channel_id if channel.channel_id else channel.channel_url
            
            # Fetch latest 10 videos
            videos = client.get_latest_videos(identifier, max_results=10)
            
            return Response({
                'channel': channel.name,
                'videos': videos
            })
        except Exception as e:
            logger.error(f"Error fetching videos: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def generate_pending(self, request, pk=None):
        """Generate a PendingArticle from a specific video"""
        channel = self.get_object()
        video_url = request.data.get('video_url')
        video_id = request.data.get('video_id')
        video_title = request.data.get('video_title')
        provider = request.data.get('provider', 'gemini')
        
        if not video_url:
            return Response({'error': 'video_url is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Add both backend and ai_engine paths for proper imports
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ai_engine_dir = os.path.join(backend_dir, 'ai_engine')
            
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            if ai_engine_dir not in sys.path:
                sys.path.insert(0, ai_engine_dir)
                
            from ai_engine.main import create_pending_article
            
            result = create_pending_article(
                youtube_url=video_url,
                channel_id=channel.id,
                video_title=video_title,
                video_id=video_id,
                provider=provider
            )
            
            if result.get('success'):
                # Invalidate cache to ensure pending counts are updated
                invalidate_article_cache()
                logger.info(f"Cache invalidated after manual generation for channel {channel.name}")
                return Response(result)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error generating pending article: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def scan_all(self, request):
        """Trigger scan for all enabled channels (Background Process)"""
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        import subprocess
        import sys
        from django.conf import settings  # <--- Added import
        
        try:
            manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
            subprocess.Popen(
                [sys.executable, manage_py, 'scan_youtube'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            count = YouTubeChannel.objects.filter(is_enabled=True).count()
            message = f'Background scan started for {count} channels'
        except Exception as e:
            print(f"❌ Error starting scan: {e}")
            message = f'Failed to start scan: {str(e)}'
            count = 0
            
        return Response({
            'message': message,
            'count': count
        })


class RSSFeedViewSet(viewsets.ModelViewSet):
    """
    Manage RSS feeds for automatic article generation.
    Staff only.
    """
    queryset = RSSFeed.objects.all()
    serializer_class = RSSFeedSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['get'])
    def with_pending_counts(self, request):
        """Get RSS feeds with count of pending articles for each"""
        from django.db.models import Count, Q
        
        feeds = RSSFeed.objects.filter(is_enabled=True).annotate(
            pending_count=Count(
                'pending_articles',
                filter=Q(pending_articles__status='pending')
            )
        ).order_by('name')
        
        serializer = self.get_serializer(feeds, many=True)
        data = serializer.data
        
        # Add pending_count to each feed
        for i, feed in enumerate(feeds):
            data[i]['pending_count'] = feed.pending_count
        
        return Response(data)
    @action(detail=True, methods=['post'])
    def scan_now(self, request, pk=None):
        """Manually trigger scan for a specific RSS feed (Background Process)"""
        feed = self.get_object()
        
        import subprocess
        import sys
        from django.conf import settings
        
        try:
            manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
            if not os.path.exists(manage_py):
                manage_py = os.path.join(os.path.dirname(settings.BASE_DIR), 'manage.py')
            
            if not os.path.exists(manage_py):
                manage_py = 'manage.py'

            print(f"🚀 Launching RSS scan for {feed.name} using {manage_py}")
            
            subprocess.Popen(
                [sys.executable, manage_py, 'scan_rss_feeds', '--feed-id', str(feed.id)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            message = f'Background scan started for {feed.name}'
        except Exception as e:
            print(f"❌ Error starting RSS scan: {e}")
            import traceback
            print(traceback.format_exc())
            message = f'Failed to start scan: {str(e)}'
            
        return Response({
            'message': message,
            'feed_id': feed.id
        })
    
    @action(detail=False, methods=['post'])
    def scan_all(self, request):
        """Scan all enabled RSS feeds (Background Process)"""
        import subprocess
        import sys
        from django.conf import settings
        
        try:
            manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
            subprocess.Popen(
                [sys.executable, manage_py, 'scan_rss_feeds', '--all'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            count = RSSFeed.objects.filter(is_enabled=True).count()
            message = f'Background scan started for {count} RSS feeds'
        except Exception as e:
            print(f"❌ Error starting RSS scan: {e}")
            message = f'Failed to start scan: {str(e)}'
            count = 0
            
        return Response({
            'message': message,
            'count': count
        })


    @action(detail=False, methods=['post'])
    def test_feed(self, request):
        """Test an RSS feed URL by fetching and parsing it server-side"""
        import requests as http_requests
        import xml.etree.ElementTree as ET
        
        feed_url = request.data.get('feed_url', '').strip()
        if not feed_url:
            return Response({'error': 'feed_url is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            resp = http_requests.get(feed_url, timeout=15, headers={
                'User-Agent': 'FreshMotors RSS Reader/1.0',
                'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            })
            resp.raise_for_status()
            
            content = resp.text.strip()
            
            # Check if response is HTML instead of XML/RSS
            if content.startswith('<!DOCTYPE') or content.startswith('<html'):
                return Response({
                    'error': 'URL returned an HTML page, not an RSS/XML feed. Check the feed URL.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Try feedparser first (handles more formats)
            try:
                import feedparser
                parsed = feedparser.parse(content)
                if parsed.entries:
                    feed_meta = {
                        'title': parsed.feed.get('title', ''),
                        'link': parsed.feed.get('link', ''),
                        'description': parsed.feed.get('subtitle', '') or parsed.feed.get('description', ''),
                    }
                    entries = []
                    for entry in parsed.entries[:5]:
                        entries.append({
                            'title': entry.get('title', 'No title'),
                            'link': entry.get('link', ''),
                            'published': entry.get('published', ''),
                        })
                    return Response({
                        'success': True,
                        'entries_count': len(parsed.entries),
                        'entries': entries,
                        'feed_meta': feed_meta
                    })
            except ImportError:
                pass
            
            # Fallback to XML parsing
            root = ET.fromstring(content)
            
            entries = []
            items = root.findall('.//item')
            if not items:
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                items = root.findall('.//atom:entry', ns)
            
            for item in items[:5]:
                title = item.findtext('title') or item.findtext('{http://www.w3.org/2005/Atom}title') or 'No title'
                link = item.findtext('link') or ''
                if not link:
                    link_el = item.find('{http://www.w3.org/2005/Atom}link')
                    if link_el is not None:
                        link = link_el.get('href', '')
                published = item.findtext('pubDate') or item.findtext('{http://www.w3.org/2005/Atom}published') or ''
                entries.append({'title': title, 'link': link, 'published': published})
            
            total = len(root.findall('.//item')) or len(root.findall('.//{http://www.w3.org/2005/Atom}entry'))
            
            # Extract feed metadata
            channel = root.find('.//channel') or root
            ns_atom = '{http://www.w3.org/2005/Atom}'
            feed_meta = {
                'title': channel.findtext('title') or root.findtext(f'{ns_atom}title') or '',
                'link': channel.findtext('link') or '',
                'description': channel.findtext('description') or root.findtext(f'{ns_atom}subtitle') or '',
            }
            if not feed_meta['link']:
                link_el = root.find(f'{ns_atom}link')
                if link_el is not None:
                    feed_meta['link'] = link_el.get('href', '')
            
            return Response({
                'success': True,
                'entries_count': total,
                'entries': entries,
                'feed_meta': feed_meta
            })
        except http_requests.exceptions.Timeout:
            return Response({'error': 'Connection timed out. The server may be slow or blocking requests.'}, status=status.HTTP_408_REQUEST_TIMEOUT)
        except http_requests.exceptions.RequestException as e:
            return Response({'error': f'Failed to fetch feed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except ET.ParseError:
            return Response({'error': 'Response is not valid XML/RSS. The URL may not point to an RSS feed.'}, status=status.HTTP_400_BAD_REQUEST)


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
            import re
            
            # Strip HTML tags to get plain text for AI
            plain_text = re.sub(r'<[^>]+>', '', news_item.content).strip()
            if not plain_text:
                plain_text = news_item.excerpt
            
            provider = request.data.get('provider', 'groq')
            if provider not in ('groq', 'gemini'):
                provider = 'groq'
            
            # Expand with AI
            expanded_content = expand_press_release(
                press_release_text=plain_text,
                source_url=news_item.source_url,
                provider=provider
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
            
            # Build images list
            images = [news_item.image_url] if news_item.image_url else []
            
            # Create PendingArticle
            pending = PendingArticle.objects.create(
                rss_feed=news_item.rss_feed,
                source_url=news_item.source_url,
                content_hash=news_item.content_hash,
                title=ai_title,
                content=expanded_content,
                excerpt=plain_text[:500],
                images=images,
                featured_image=news_item.image_url or '',
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


class PendingArticleViewSet(viewsets.ModelViewSet):
    """
    Manage pending articles waiting for review.
    Staff only.
    """
    queryset = PendingArticle.objects.select_related(
        'youtube_channel',
        'rss_feed',
        'suggested_category'
    ).all()
    serializer_class = PendingArticleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'video_title']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = PendingArticle.objects.select_related(
            'youtube_channel',
            'rss_feed',
            'suggested_category'
        ).all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(categories__slug=category)
        
        # Filter by RSS feed ID
        rss_feed_id = self.request.query_params.get('rss_feed')
        if rss_feed_id:
            queryset = queryset.filter(rss_feed_id=rss_feed_id)
        
        # Filter only RSS articles (exclude YouTube)
        only_rss = self.request.query_params.get('only_rss')
        if only_rss == 'true':
            queryset = queryset.filter(rss_feed__isnull=False)
        
        # Filter only YouTube articles (exclude RSS)
        only_youtube = self.request.query_params.get('only_youtube')
        exclude_rss = self.request.query_params.get('exclude_rss')
        if only_youtube == 'true' or exclude_rss == 'true':
            queryset = queryset.filter(youtube_channel__isnull=False)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve and publish a pending article"""
        pending = self.get_object()
        
        if pending.status != 'pending':
            return Response({'error': 'Article is not pending'}, status=status.HTTP_400_BAD_REQUEST)
        
        
        # Create the actual article
        try:
            from django.utils.text import slugify
            import uuid
            
            # Generate unique slug
            base_slug = slugify(pending.title)[:80]
            slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
            
            is_published = request.data.get('publish', True)
            
            # Extract author info from channel if available
            author_name = ""
            author_channel_url = ""
            if pending.youtube_channel:
                author_name = pending.youtube_channel.name
                author_channel_url = pending.youtube_channel.channel_url
            elif pending.rss_feed:
                # For RSS articles, use feed name and source URL
                author_name = pending.rss_feed.name
                author_channel_url = pending.source_url or pending.rss_feed.feed_url

            article = Article.objects.create(
                title=pending.title,
                slug=slug,
                content=pending.content,
                summary=pending.excerpt or pending.content[:200],
                is_published=is_published,
                youtube_url=pending.video_url,
                author_name=author_name,
                author_channel_url=author_channel_url
            )
            
            # Add category (ManyToMany field)
            # For RSS articles, use suggested_category or fallback to "News"
            if pending.rss_feed:
                if pending.suggested_category:
                    article.categories.add(pending.suggested_category)
                else:
                    # Fallback to "News" category for RSS articles
                    from news.models import Category
                    news_category, _ = Category.objects.get_or_create(
                        slug='news',
                        defaults={'name': 'News', 'description': 'General automotive news'}
                    )
                    article.categories.add(news_category)
            elif pending.suggested_category:
                # For non-RSS articles (YouTube), only add if exists
                article.categories.add(pending.suggested_category)
            
            
            # Handle Images (Upload local files or save Cloudinary URLs)
            logger.info(f"[APPROVE] Processing images for article '{article.title[:50]}'")
            logger.info(f"[APPROVE] pending.images = {pending.images}")
            logger.info(f"[APPROVE] pending.featured_image = {pending.featured_image}")
            
            image_sources = []
            if pending.images and isinstance(pending.images, list):
                image_sources = pending.images[:3]
            elif pending.featured_image:
                image_sources = [pending.featured_image]
            
            if image_sources:
                from django.core.files import File
                from django.core.files.base import ContentFile
                import os
                import requests as img_requests
                for i, image_path in enumerate(image_sources):
                    if not image_path: continue
                    
                    try:
                        file_name = f"{slug}_{i+1}.jpg"
                        content_file = None
                        cloudinary_url = None
                        
                        # Case A: It's already a Cloudinary URL - reuse it directly
                        if 'cloudinary.com' in image_path:
                            logger.info(f"[APPROVE] Reusing existing Cloudinary URL for image {i+1}: {image_path[:100]}")
                            cloudinary_url = image_path
                        
                        # Case B: It's a non-Cloudinary URL (Pexels, etc) - download and upload
                        elif image_path.startswith('http'):
                            logger.info(f"[APPROVE] Downloading image {i+1} from URL: {image_path[:100]}")
                            resp = img_requests.get(image_path, timeout=15)
                            logger.info(f"[APPROVE] Download status: {resp.status_code}, size: {len(resp.content)} bytes")
                            if resp.status_code == 200 and len(resp.content) > 0:
                                content_file = ContentFile(resp.content, name=file_name)
                            else:
                                logger.warning(f"[APPROVE] Failed to download image: status={resp.status_code}")
                        
                        # Case C: It's a local file relative path
                        elif image_path.startswith('/media/'):
                             from django.conf import settings
                             full_path = os.path.join(settings.BASE_DIR, image_path.lstrip('/'))
                             logger.info(f"[APPROVE] Reading relative image: {full_path}")
                             if os.path.exists(full_path):
                                 with open(full_path, 'rb') as f:
                                     content = f.read()
                                     content_file = ContentFile(content, name=file_name)
                             else:
                                 logger.warning(f"[APPROVE] Local file not found: {full_path}")
                        
                        # Case D: It's a legacy absolute local path
                        elif os.path.exists(image_path):
                            logger.info(f"[APPROVE] Reading local image: {image_path}")
                            with open(image_path, 'rb') as f:
                                content = f.read()
                                content_file = ContentFile(content, name=file_name)
                        else:
                            logger.warning(f"[APPROVE] Image path not recognized/found: {image_path}")
                                
                        # Save to Article
                        if cloudinary_url:
                            # Direct assignment for Cloudinary URLs
                            if i == 0:
                                article.image = cloudinary_url
                                logger.info(f"[APPROVE] ✓ Image 1 reused from Cloudinary: {cloudinary_url}")
                            elif i == 1:
                                article.image_2 = cloudinary_url
                                logger.info(f"[APPROVE] ✓ Image 2 reused from Cloudinary: {cloudinary_url}")
                            elif i == 2:
                                article.image_3 = cloudinary_url
                                logger.info(f"[APPROVE] ✓ Image 3 reused from Cloudinary: {cloudinary_url}")
                            article.save()
                        elif content_file:
                            # Upload new file
                            logger.info(f"[APPROVE] Saving image {i+1} ({file_name}, {len(content_file)} bytes) to article...")
                            if i == 0:
                                article.image.save(file_name, content_file, save=True)
                                logger.info(f"[APPROVE] ✓ Image 1 saved. article.image.url = {article.image.url if article.image else 'NONE'}")
                            elif i == 1:
                                article.image_2.save(file_name, content_file, save=True)
                                logger.info(f"[APPROVE] ✓ Image 2 saved. article.image_2.url = {article.image_2.url if article.image_2 else 'NONE'}")
                            elif i == 2:
                                article.image_3.save(file_name, content_file, save=True)
                                logger.info(f"[APPROVE] ✓ Image 3 saved. article.image_3.url = {article.image_3.url if article.image_3 else 'NONE'}")
                        else:
                            logger.warning(f"[APPROVE] No content_file or cloudinary_url for image {i+1}")
                                
                    except Exception as img_err:
                        logger.error(f"[APPROVE] Error saving image {image_path}: {img_err}", exc_info=True)
            else:
                logger.warning(f"[APPROVE] No images found in pending article")
            
            # Restore Tags from PendingArticle
            if pending.tags and isinstance(pending.tags, list):
                try:
                    for tag_name in pending.tags:
                        tag_slug = slugify(tag_name)
                        tag, _ = Tag.objects.get_or_create(
                            slug=tag_slug, 
                            defaults={'name': tag_name}
                        )
                        article.tags.add(tag)
                    print(f"  Restored {len(pending.tags)} tags")
                except Exception as e:
                    print(f"  Error restoring tags: {e}")

            # Restore Specs from PendingArticle
            if pending.specs and isinstance(pending.specs, dict):
                try:
                    specs = pending.specs
                    if specs.get('make') != 'Not specified':
                        CarSpecification.objects.update_or_create(
                            article=article,
                            defaults={
                                'model_name': f"{specs.get('make', '')} {specs.get('model', '')}",
                                'engine': specs.get('engine', ''),
                                'horsepower': str(specs.get('horsepower', '')),
                                'torque': specs.get('torque', ''),
                                'zero_to_sixty': specs.get('acceleration', ''),
                                'top_speed': specs.get('top_speed', ''),
                                'price': specs.get('price', ''),
                            }
                        )
                        print("  Restored CarSpecification")
                except Exception as e:
                    print(f"  Error restoring specs: {e}")
            
            # Update pending article
            pending.status = 'published'
            pending.published_article = article
            pending.reviewed_by = request.user
            pending.reviewed_at = timezone.now()
            pending.save()
            
            # Clear cache so the new article appears on homepage immediately
            # The ArticleViewSet list uses @cache_page(300) for anonymous users
            try:
                from django.core.cache import cache
                invalidate_article_cache(article_id=article.id, slug=article.slug)
                logger.info(f"Cache invalidated after publishing article: {article.slug}")
            except Exception as cache_err:
                logger.warning(f"Failed to invalidate cache: {cache_err}")
            
            return Response({
                'message': 'Article approved successfully' if not is_published else 'Article published successfully',
                'article_id': article.id,
                'article_slug': article.slug
            })
        except Exception as e:
            logger.error(f"Failed to publish article: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a pending article"""
        pending = self.get_object()
        
        if pending.status != 'pending':
            return Response({'error': 'Article is not pending'}, status=status.HTTP_400_BAD_REQUEST)
        
        pending.status = 'rejected'
        pending.reviewed_by = request.user
        pending.reviewed_at = timezone.now()
        pending.review_notes = request.data.get('reason', '')
        pending.save()
        
        return Response({'message': 'Article rejected'})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get statistics about pending articles"""
        # Get base queryset
        queryset = PendingArticle.objects.all()
        
        # Apply source filters
        only_rss = request.query_params.get('only_rss')
        if only_rss == 'true':
            queryset = queryset.filter(rss_feed__isnull=False)
        
        only_youtube = request.query_params.get('only_youtube')
        exclude_rss = request.query_params.get('exclude_rss')
        if only_youtube == 'true' or exclude_rss == 'true':
            queryset = queryset.filter(youtube_channel__isnull=False)
        
        return Response({
            'pending': queryset.filter(status='pending').count(),
            'approved': queryset.filter(status='approved').count(),
            'rejected': queryset.filter(status='rejected').count(),
            'published': queryset.filter(status='published').count(),
            'total': queryset.count()
        })


class AutoPublishScheduleViewSet(viewsets.ModelViewSet):
    """
    Manage auto-publish schedule settings.
    Only one schedule object exists (singleton pattern).
    """
    queryset = AutoPublishSchedule.objects.all()
    serializer_class = AutoPublishScheduleSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        # Return single schedule object, create if not exists
        schedule, _ = AutoPublishSchedule.objects.get_or_create(pk=1)
        serializer = self.get_serializer(schedule)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        # Always return the single schedule object
        schedule, _ = AutoPublishSchedule.objects.get_or_create(pk=1)
        serializer = self.get_serializer(schedule)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        schedule, _ = AutoPublishSchedule.objects.get_or_create(pk=1)
        serializer = self.get_serializer(schedule, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def trigger_scan(self, request, pk=None):
        """Manually trigger a scan now"""
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        schedule = self.get_object()
        schedule.last_scan = timezone.now()
        schedule.total_scans += 1
        schedule.save()
        
        # Trigger the actual scan process in background
        import subprocess
        import sys
        from django.conf import settings
        
        try:
            manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
            if not os.path.exists(manage_py):
                # Try one level up if settings is in a subdir
                manage_py = os.path.join(os.path.dirname(settings.BASE_DIR), 'manage.py')
            
            if not os.path.exists(manage_py):
                 manage_py = 'manage.py'

            subprocess.Popen(
                [sys.executable, manage_py, 'scan_youtube'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            message = 'Auto-scan triggered for all enabled channels'
        except Exception as e:
            logger.error(f"Error triggering auto-scan: {e}")
            message = f'Failed to trigger scan: {str(e)}'
        
        return Response({
            'message': message,
            'timestamp': schedule.last_scan
        })


class AdminNotificationViewSet(viewsets.ModelViewSet):
    """
    Admin notifications management.
    Shows notifications for comments, subscribers, errors, etc.
    """
    queryset = AdminNotification.objects.all()
    serializer_class = AdminNotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter notifications for admin users only"""
        if not self.request.user.is_staff:
            return AdminNotification.objects.none()
        return AdminNotification.objects.all().order_by('-created_at')
    
    def list(self, request):
        """Get all notifications with unread count"""
        queryset = self.get_queryset()
        
        # Optional filters
        is_unread = request.query_params.get('unread', None)
        notification_type = request.query_params.get('type', None)
        limit = request.query_params.get('limit', None)
        
        if is_unread == 'true':
            queryset = queryset.filter(is_read=False)
        
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        # Get counts before limiting
        unread_count = self.get_queryset().filter(is_read=False).count()
        total_count = self.get_queryset().count()
        
        if limit:
            queryset = queryset[:int(limit)]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'notifications': serializer.data,
            'unread_count': unread_count,
            'total_count': total_count
        })
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a single notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        count = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({
            'status': 'all marked as read',
            'count': count
        })
    
    @action(detail=False, methods=['post'])
    def clear_all(self, request):
        """Delete all read notifications"""
        count, _ = self.get_queryset().filter(is_read=True).delete()
        return Response({
            'status': 'cleared read notifications',
            'count': count
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get just the unread count (for polling)"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})
    
    @action(detail=False, methods=['post'])
    def create_test(self, request):
        """Create a test notification (for development)"""
        if not request.user.is_superuser:
            return Response({'error': 'Superuser required'}, status=status.HTTP_403_FORBIDDEN)
        
        notification = AdminNotification.create_notification(
            notification_type=request.data.get('type', 'info'),
            title=request.data.get('title', 'Test Notification'),
            message=request.data.get('message', 'This is a test notification.'),
            link=request.data.get('link', ''),
            priority=request.data.get('priority', 'normal')
        )
        serializer = self.get_serializer(notification)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@method_decorator(ratelimit(key='ip', rate='5/h', method='POST', block=True), name='post')
class NewsletterSubscribeView(APIView):
    """Newsletter subscription endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .models import NewsletterSubscriber
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        from .email_service import email_service
        
        email = request.data.get('email', '').strip().lower()
        
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            return Response({'error': 'Invalid email format'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get IP address for tracking
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()
        
        # Create or update subscriber
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email,
            defaults={'is_active': True, 'ip_address': ip_address}
        )
        
        if not created:
            if not subscriber.is_active:
                # Reactivate subscription
                subscriber.is_active = True
                subscriber.unsubscribed_at = None
                subscriber.ip_address = ip_address
                subscriber.save()
                
                # Send welcome email for resubscription
                email_service.send_newsletter_welcome(email)
                
                return Response({'message': 'Successfully resubscribed!'}, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'Already subscribed!'}, status=status.HTTP_200_OK)
        
        # Send welcome email to new subscriber
        email_sent = email_service.send_newsletter_welcome(email)
        if email_sent:
            logger.info(f"New newsletter subscriber: {email} - welcome email sent")
        else:
            logger.warning(f"New newsletter subscriber: {email} - welcome email failed")
        
        return Response({'message': 'Successfully subscribed!'}, status=status.HTTP_201_CREATED)
