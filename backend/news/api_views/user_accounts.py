from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.models import User
import re
import logging

logger = logging.getLogger(__name__)


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
    @method_decorator(ratelimit(key='ip', rate='1/h', method='POST', block=True))
    def register(self, request):
        """Register a new user with rate limiting to prevent spam"""
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
                    email=email,
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
