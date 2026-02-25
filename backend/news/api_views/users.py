from rest_framework import viewsets, status, filters
from django.db.models import Avg, Case, Count, Exists, IntegerField, OuterRef, Q, Subquery, Value, When
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
from news.models import (
    Article, Category, Tag, TagGroup, Comment, Rating, CarSpecification, 
    ArticleImage, SiteSettings, Favorite, Subscriber, NewsletterHistory,
    YouTubeChannel, RSSFeed, RSSNewsItem, PendingArticle, AdminNotification,
    VehicleSpecs, NewsletterSubscriber, BrandAlias, AutomationSettings
)
from news.serializers import (
    ArticleListSerializer, ArticleDetailSerializer, 
    CategorySerializer, TagSerializer, TagGroupSerializer, CommentSerializer, 
    RatingSerializer, CarSpecificationSerializer, ArticleImageSerializer,
    SiteSettingsSerializer, FavoriteSerializer, SubscriberSerializer, NewsletterHistorySerializer,
    YouTubeChannelSerializer, RSSFeedSerializer, RSSNewsItemSerializer, PendingArticleSerializer,
    AdminNotificationSerializer, VehicleSpecsSerializer, BrandAliasSerializer,
    AutomationSettingsSerializer
)
import os
import sys
import re
import logging

logger = logging.getLogger(__name__)



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

@method_decorator(ratelimit(key='user', rate='5/h', method='POST'), name='post')
class ChangePasswordView(APIView):
    """Change user password"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from news.validators import validate_password_strength
        from news.security_utils import log_security_event, get_client_ip, get_user_agent
        
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
        from news.models import EmailPreferences
        from news.serializers import EmailPreferencesSerializer
        
        # Get or create preferences for user
        prefs, created = EmailPreferences.objects.get_or_create(user=request.user)
        serializer = EmailPreferencesSerializer(prefs)
        return Response(serializer.data)
    
    def patch(self, request):
        from news.models import EmailPreferences
        from news.serializers import EmailPreferencesSerializer
        
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
        from news.models import EmailVerification
        from news.security_utils import get_client_ip
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
        from news.models import EmailVerification
        from news.security_utils import log_security_event, get_client_ip, get_user_agent
        
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
        from news.models import PasswordResetToken
        from news.security_utils import get_client_ip
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
        from news.models import PasswordResetToken
        from news.validators import validate_password_strength
        from news.security_utils import log_security_event, get_client_ip, get_user_agent
        
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
            
            # Get or create user (case-insensitive)
            user = User.objects.filter(email__iexact=email).first()
            created = False
            
            if not user:
                user = User.objects.create(
                    email=email,  # save the lowercased version
                    username=email.split('@')[0],
                    first_name=given_name,
                    last_name=family_name,
                )
                created = True
            
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

class IsSuperUser(BasePermission):
    """Only allow superusers."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser

class AdminUserManagementViewSet(viewsets.ViewSet):
    """
    Admin-only ViewSet for managing users and their permissions.
    Only superusers can access these endpoints.
    """
    permission_classes = [IsSuperUser]

    def list(self, request):
        """List all users with optional search, filters, and pagination."""
        users = User.objects.all().annotate(
            role_order=Case(
                When(is_superuser=True, then=Value(0)),
                When(is_staff=True, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        ).order_by('role_order', '-date_joined')

        # Search by username or email
        search = request.query_params.get('search', '').strip()
        if search:
            users = users.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        # Filter by role
        role = request.query_params.get('role', '').strip()
        if role == 'superuser':
            users = users.filter(is_superuser=True)
        elif role == 'staff':
            users = users.filter(is_staff=True, is_superuser=False)
        elif role == 'user':
            users = users.filter(is_staff=False, is_superuser=False)

        # Filter by active status
        is_active = request.query_params.get('is_active', '').strip()
        if is_active == 'true':
            users = users.filter(is_active=True)
        elif is_active == 'false':
            users = users.filter(is_active=False)

        # Pagination
        total_filtered = users.count()
        try:
            page = max(1, int(request.query_params.get('page', 1)))
            page_size = min(100, max(1, int(request.query_params.get('page_size', 25))))
        except (ValueError, TypeError):
            page = 1
            page_size = 25

        import math
        total_pages = max(1, math.ceil(total_filtered / page_size))
        page = min(page, total_pages)
        offset = (page - 1) * page_size
        paginated_users = users[offset:offset + page_size]

        # Build response
        user_list = []
        for u in paginated_users:
            role_label = 'Superuser' if u.is_superuser else ('Staff' if u.is_staff else 'User')
            user_list.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'role': role_label,
                'is_superuser': u.is_superuser,
                'is_staff': u.is_staff,
                'is_active': u.is_active,
                'date_joined': u.date_joined.isoformat(),
                'last_login': u.last_login.isoformat() if u.last_login else None,
            })

        # Stats (always over all users, not filtered)
        all_users = User.objects.all()
        stats = {
            'total': all_users.count(),
            'active': all_users.filter(is_active=True).count(),
            'staff': all_users.filter(is_staff=True).count(),
            'superusers': all_users.filter(is_superuser=True).count(),
        }

        return Response({
            'results': user_list,
            'stats': stats,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_filtered,
                'total_pages': total_pages,
            }
        })

    def create(self, request):
        """Create a new user."""
        username = request.data.get('username', '').strip()
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '').strip()
        role = request.data.get('role', 'user').strip()
        first_name = request.data.get('first_name', '').strip()
        last_name = request.data.get('last_name', '').strip()

        # Validation
        if not username:
            return Response({'error': 'Username is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not password or len(password) < 8:
            return Response({'error': 'Password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)
        if email and User.objects.filter(email=email).exists():
            return Response({'error': 'Email already in use.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        # Set role
        if role == 'superuser':
            user.is_staff = True
            user.is_superuser = True
        elif role == 'staff':
            user.is_staff = True
            user.is_superuser = False
        else:
            user.is_staff = False
            user.is_superuser = False
        user.save()

        role_label = 'Superuser' if user.is_superuser else ('Staff' if user.is_staff else 'User')
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': role_label,
            'message': f'User "{username}" created successfully.',
        }, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        """Get a single user's details."""
        user = get_object_or_404(User, pk=pk)
        role_label = 'Superuser' if user.is_superuser else ('Staff' if user.is_staff else 'User')
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': role_label,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
        })

    def partial_update(self, request, pk=None):
        """Update a user's role, active status, or profile info."""
        user = get_object_or_404(User, pk=pk)

        # Self-protection: cannot demote or deactivate yourself
        if user.id == request.user.id:
            changing_role = 'is_superuser' in request.data or 'is_staff' in request.data or 'role' in request.data
            changing_active = 'is_active' in request.data and not request.data['is_active']
            if changing_role or changing_active:
                return Response(
                    {'detail': 'You cannot change your own role or deactivate yourself.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Handle role changes via 'role' field
        role = request.data.get('role')
        if role:
            if role == 'superuser':
                user.is_superuser = True
                user.is_staff = True
            elif role == 'staff':
                user.is_superuser = False
                user.is_staff = True
            elif role == 'user':
                user.is_superuser = False
                user.is_staff = False

        # Handle direct field updates
        if 'is_active' in request.data:
            user.is_active = request.data['is_active']
        if 'first_name' in request.data:
            user.first_name = request.data['first_name']
        if 'last_name' in request.data:
            user.last_name = request.data['last_name']
        if 'email' in request.data:
            new_email = request.data['email'].strip().lower()
            # Check uniqueness
            if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
                return Response(
                    {'detail': 'A user with this email already exists.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.email = new_email

        user.save()
        logger.info(f"Admin {request.user.username} updated user {user.username} (id={user.id})")

        role_label = 'Superuser' if user.is_superuser else ('Staff' if user.is_staff else 'User')
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': role_label,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
        })

    def destroy(self, request, pk=None):
        """Delete a user. Cannot delete yourself."""
        user = get_object_or_404(User, pk=pk)

        if user.id == request.user.id:
            return Response(
                {'detail': 'You cannot delete your own account.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        username = user.username
        user.delete()
        logger.info(f"Admin {request.user.username} deleted user {username} (id={pk})")
        return Response({'detail': f'User {username} has been deleted.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Reset a user's password to a random one. Returns the new password once."""
        import secrets
        import string

        user = get_object_or_404(User, pk=pk)

        # Generate a secure random password
        alphabet = string.ascii_letters + string.digits + '!@#$%'
        new_password = ''.join(secrets.choice(alphabet) for _ in range(16))

        user.set_password(new_password)
        user.save()
        logger.info(f"Admin {request.user.username} reset password for user {user.username} (id={pk})")

        return Response({
            'detail': f'Password for {user.username} has been reset.',
            'new_password': new_password,
        })

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

@method_decorator(ratelimit(key='ip', rate='5/h', method='POST', block=True), name='post')
class NewsletterSubscribeView(APIView):
    """Newsletter subscription endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        from news.models import NewsletterSubscriber
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        from news.email_service import email_service
        
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

