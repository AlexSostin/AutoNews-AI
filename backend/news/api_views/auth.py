from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
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
        
        # Create reset token (Valid for 15 minutes)
        reset = PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=timezone.now() + timedelta(minutes=15),
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
