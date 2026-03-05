"""
Two-Factor Authentication (TOTP) API Views.

Endpoints:
- POST /api/v1/auth/2fa/setup/     — Generate QR code + secret for authenticator app
- POST /api/v1/auth/2fa/confirm/   — Confirm 2FA setup with first valid code
- POST /api/v1/auth/2fa/verify/    — Verify 2FA code during login (returns JWT tokens)
- POST /api/v1/auth/2fa/disable/   — Disable 2FA (requires valid code)
- GET  /api/v1/auth/2fa/status/    — Check if 2FA is enabled for current user
"""
import pyotp
import qrcode
import base64
import io
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework import status
from django.contrib.auth import authenticate  # kept for potential future use

from news.models import TOTPDevice

logger = logging.getLogger(__name__)


class TwoFactorSetupView(APIView):
    """Generate TOTP secret and QR code for authenticator app setup."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        user = request.user

        # If already has confirmed 2FA, require disable first
        existing = TOTPDevice.objects.filter(user=user, is_confirmed=True).first()
        if existing:
            return Response({
                'detail': '2FA is already enabled. Disable it first to reconfigure.',
            }, status=status.HTTP_400_BAD_REQUEST)

        # Generate new secret
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email or user.username,
            issuer_name='FreshMotors Admin'
        )

        # Generate QR code as base64
        qr = qrcode.make(provisioning_uri)
        buffer = io.BytesIO()
        qr.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        # Save unconfirmed device (overwrite any pending)
        TOTPDevice.objects.update_or_create(
            user=user,
            defaults={
                'secret': secret,
                'is_confirmed': False,
                'backup_codes': [],
            }
        )

        logger.info(f"🔐 2FA setup initiated: user={user.username}")

        return Response({
            'secret': secret,
            'qr_code': f'data:image/png;base64,{qr_base64}',
            'provisioning_uri': provisioning_uri,
            'message': 'Scan QR code with Google Authenticator or similar app, then confirm with a code.',
        })


class TwoFactorConfirmView(APIView):
    """Confirm 2FA setup by verifying the first code from authenticator app."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        code = request.data.get('code', '').strip()
        if not code or len(code) != 6:
            return Response({'detail': 'Valid 6-digit code is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = TOTPDevice.objects.get(user=request.user)
        except TOTPDevice.DoesNotExist:
            return Response({'detail': 'No 2FA setup found. Run setup first.'}, status=status.HTTP_404_NOT_FOUND)

        if device.is_confirmed:
            return Response({'detail': '2FA is already confirmed.'}, status=status.HTTP_400_BAD_REQUEST)

        if not device.verify_code(code):
            return Response({'detail': 'Invalid code. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)

        # Generate backup codes
        plaintext_codes, hashed_codes = TOTPDevice.generate_backup_codes()

        device.is_confirmed = True
        device.backup_codes = hashed_codes
        device.save(update_fields=['is_confirmed', 'backup_codes'])

        logger.info(f"🔐 2FA confirmed: user={request.user.username}")

        return Response({
            'success': True,
            'message': '2FA is now enabled! Save your backup codes securely.',
            'backup_codes': plaintext_codes,
        })


class TwoFactorVerifyView(APIView):
    """Verify 2FA code during login flow (step 2 of two-step auth).

    Client sends username, password, and totp_code.
    Returns JWT tokens if everything is valid.
    """
    # AllowAny required — this endpoint is called BEFORE login is complete
    # (DRF default IsAuthenticatedOrReadOnly blocks POST from unauthenticated users)
    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth.models import User

        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        totp_code = request.data.get('totp_code', '').strip()

        logger.info(f"🔐 2FA verify attempt: username={username!r} totp_len={len(totp_code)}")

        if not username or not password or not totp_code:
            return Response(
                {'detail': 'username, password, and totp_code are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Lookup user — bypass django-axes by using check_password directly
        # (axes would block after multiple /token/ failures, causing 2FA verify to silently fail)
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            logger.warning(f"🔒 2FA verify: user not found username={username!r}")
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            logger.warning(f"🔒 2FA verify: wrong password for user={user.username}")
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            logger.warning(f"🔒 2FA verify: user is inactive username={user.username}")
            return Response({'detail': 'Account is disabled.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Verify TOTP code
        try:
            device = TOTPDevice.objects.get(user=user, is_confirmed=True)
        except TOTPDevice.DoesNotExist:
            logger.error(f"🔒 2FA verify: no confirmed device for user={user.username}")
            return Response({'detail': '2FA is not enabled for this account.'}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"🔐 2FA verify: checking code for user={user.username}")

        # Try TOTP code first, then backup code
        if not device.verify_code(totp_code) and not device.verify_backup_code(totp_code):
            logger.warning(f"🔒 2FA verification FAILED: user={user.username}")
            return Response({'detail': 'Invalid 2FA code.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Issue JWT tokens
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        logger.info(f"🔑 2FA login SUCCESS: user={user.username}")

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })



class TwoFactorGoogleVerifyView(APIView):
    """Verify 2FA code for users who signed in via Google OAuth.

    Client sends google_user_id and totp_code (no password needed since
    Google already authenticated the user).
    Returns JWT tokens if TOTP is valid.
    """
    # AllowAny required — called before login is complete
    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth.models import User
        from rest_framework_simplejwt.tokens import RefreshToken

        google_user_id = request.data.get('google_user_id', '').strip()
        totp_code = request.data.get('totp_code', '').strip()

        if not google_user_id or not totp_code:
            return Response(
                {'detail': 'google_user_id and totp_code are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(pk=google_user_id)
        except (User.DoesNotExist, ValueError):
            return Response({'detail': 'Invalid user.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Verify TOTP code
        try:
            device = TOTPDevice.objects.get(user=user, is_confirmed=True)
        except TOTPDevice.DoesNotExist:
            return Response({'detail': '2FA is not enabled for this account.'}, status=status.HTTP_400_BAD_REQUEST)

        if not device.verify_code(totp_code) and not device.verify_backup_code(totp_code):
            logger.warning(f"🔒 Google 2FA verification FAILED: user={user.username}")
            return Response({'detail': 'Invalid 2FA code.'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        logger.info(f"🔑 Google OAuth 2FA login SUCCESS: user={user.username}")

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
        })


class TwoFactorDisableView(APIView):
    """Disable 2FA (requires valid TOTP code to confirm identity)."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        code = request.data.get('code', '').strip()
        if not code:
            return Response({'detail': 'Provide your 2FA code to disable.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = TOTPDevice.objects.get(user=request.user, is_confirmed=True)
        except TOTPDevice.DoesNotExist:
            return Response({'detail': '2FA is not enabled.'}, status=status.HTTP_404_NOT_FOUND)

        if not device.verify_code(code):
            return Response({'detail': 'Invalid code.'}, status=status.HTTP_400_BAD_REQUEST)

        device.delete()
        logger.info(f"🔓 2FA disabled: user={request.user.username}")

        return Response({'success': True, 'message': '2FA has been disabled.'})


class TwoFactorStatusView(APIView):
    """Check if current user has 2FA enabled."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        has_2fa = TOTPDevice.objects.filter(
            user=request.user, is_confirmed=True
        ).exists()

        return Response({
            'enabled': has_2fa,
            'user': request.user.username,
        })
