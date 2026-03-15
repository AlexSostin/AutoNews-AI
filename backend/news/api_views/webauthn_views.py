"""
WebAuthn (Passkey) API views.
Endpoints:
  POST /api/v1/auth/passkey/register/begin/     — Generate registration challenge
  POST /api/v1/auth/passkey/register/complete/  — Verify & save credential
  GET  /api/v1/auth/passkey/authenticate/       — Get auth challenge
  POST /api/v1/auth/passkey/authenticate/       — Verify assertion → return JWT
  GET  /api/v1/auth/passkey/credentials/        — List passkeys
  DELETE /api/v1/auth/passkey/credentials/<pk>/ — Remove passkey

Works on localhost without HTTPS per WebAuthn spec.
On Railway: set WEBAUTHN_RP_ID and WEBAUTHN_ALLOWED_ORIGINS env vars.
  WEBAUTHN_RP_ID=freshmotors.net
  WEBAUTHN_ALLOWED_ORIGINS=https://www.freshmotors.net,https://freshmotors.net
  (comma-separated — supports both www and non-www in the same deployment)

NOTE: webauthn is imported lazily (inside each method) to avoid oscrypto
      startup errors in WSL environments with non-standard OpenSSL paths.
"""

import base64
import logging
from datetime import datetime, timezone

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

from news.models import WebAuthnCredential

logger = logging.getLogger('news')


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_rp_id() -> str:
    return getattr(settings, 'WEBAUTHN_RP_ID', 'localhost')

def _get_rp_name() -> str:
    return getattr(settings, 'WEBAUTHN_RP_NAME', 'FreshMotors Admin')

def _get_allowed_origins() -> list[str]:
    """
    Returns list of allowed WebAuthn origins.
    Reads WEBAUTHN_ORIGIN and automatically adds the www/non-www counterpart.
    Example: WEBAUTHN_ORIGIN=https://www.freshmotors.net
             → ['https://www.freshmotors.net', 'https://freshmotors.net']
    No extra env vars needed — works out of the box in production.
    """
    origin = getattr(settings, 'WEBAUTHN_ORIGIN', 'http://localhost:3000')
    origins = [origin]

    # Auto-add www ↔ non-www counterpart for production HTTPS domains
    if origin.startswith('https://www.'):
        counterpart = origin.replace('https://www.', 'https://', 1)
        origins.append(counterpart)
    elif origin.startswith('https://') and 'localhost' not in origin:
        counterpart = origin.replace('https://', 'https://www.', 1)
        origins.append(counterpart)

    return origins

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += '=' * padding
    return base64.urlsafe_b64decode(s)


# ─── 1. Register Begin ────────────────────────────────────────────────────────

class PasskeyRegisterBeginView(APIView):
    """Generate registration options (staff only)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import webauthn  # lazy — avoids oscrypto startup crash in WSL
        from webauthn.helpers.structs import (
            AuthenticatorSelectionCriteria,
            UserVerificationRequirement,
            ResidentKeyRequirement,
        )

        if not request.user.is_staff:
            return Response({'detail': 'Staff only.'}, status=status.HTTP_403_FORBIDDEN)

        user = request.user
        user_id = str(user.pk).encode()

        existing = WebAuthnCredential.objects.filter(user=user).values_list('credential_id', flat=True)

        from webauthn.helpers.structs import PublicKeyCredentialDescriptor
        exclude_credentials = [
            PublicKeyCredentialDescriptor(id=bytes(cred_id))
            for cred_id in existing
        ]

        options = webauthn.generate_registration_options(
            rp_id=_get_rp_id(),
            rp_name=_get_rp_name(),
            user_id=user_id,
            user_name=user.username,
            user_display_name=user.get_full_name() or user.username,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.PREFERRED,
                resident_key=ResidentKeyRequirement.PREFERRED,
            ),
            exclude_credentials=exclude_credentials,
        )

        request.session['webauthn_register_challenge'] = _b64url_encode(options.challenge)
        request.session.modified = True

        # options_to_json() returns a JSON string — parse it first so DRF
        # doesn't double-serialize it into a quoted string.
        import json as _json
        return Response(_json.loads(webauthn.options_to_json(options)))


# ─── 2. Register Complete ─────────────────────────────────────────────────────

class PasskeyRegisterCompleteView(APIView):
    """Verify registration response and save credential."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import webauthn  # lazy

        if not request.user.is_staff:
            return Response({'detail': 'Staff only.'}, status=status.HTTP_403_FORBIDDEN)

        challenge_b64 = request.session.get('webauthn_register_challenge')
        if not challenge_b64:
            return Response({'detail': 'No registration challenge in session.'}, status=status.HTTP_400_BAD_REQUEST)

        challenge = _b64url_decode(challenge_b64)

        try:
            verification = webauthn.verify_registration_response(
                credential=request.data,
                expected_challenge=challenge,
                expected_rp_id=_get_rp_id(),
                expected_origin=_get_allowed_origins(),
                require_user_verification=False,
            )
        except Exception as e:
            logger.warning(f'WebAuthn registration failed for {request.user}: {e}')
            return Response({'detail': f'Registration failed: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        device_name = request.data.get('device_name', 'Passkey')
        cred = WebAuthnCredential.objects.create(
            user=request.user,
            credential_id=bytes(verification.credential_id),
            public_key=bytes(verification.credential_public_key),
            sign_count=verification.sign_count,
            transports=request.data.get('response', {}).get('transports', []),
            device_name=device_name[:100],
        )

        del request.session['webauthn_register_challenge']
        request.session.modified = True

        logger.info(f'✅ Passkey registered: user={request.user.username} device="{device_name}" id={cred.pk}')
        return Response({
            'status': 'ok',
            'id': cred.pk,
            'device_name': cred.device_name,
            'created_at': cred.created_at.isoformat(),
        })


# ─── 3. Authenticate ──────────────────────────────────────────────────────────

class PasskeyAuthenticateView(APIView):
    """
    GET  → returns challenge options
    POST → verifies assertion → returns JWT tokens
    """
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='10/5m', method='GET', block=True))
    def get(self, request):
        import webauthn  # lazy
        import secrets
        from webauthn.helpers.structs import UserVerificationRequirement
        from django.core.cache import cache

        options = webauthn.generate_authentication_options(
            rp_id=_get_rp_id(),
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        # Store challenge in cache with a one-time token (cross-domain safe).
        # Session cookies are lost on cross-domain POST (SameSite=Lax), so
        # session storage breaks on Vercel+Railway. Cache avoids this.
        auth_token = secrets.token_urlsafe(32)
        cache.set(
            f'passkey_auth:{auth_token}',
            {'challenge': _b64url_encode(options.challenge)},
            timeout=120,  # 2 minutes to complete the flow
        )

        import json as _json
        response_data = _json.loads(webauthn.options_to_json(options))
        response_data['auth_token'] = auth_token  # client must echo this in POST
        return Response(response_data)

    @method_decorator(ratelimit(key='ip', rate='10/5m', method='POST', block=True))
    def post(self, request):
        import webauthn  # lazy
        from django.core.cache import cache

        # Retrieve challenge from cache using the one-time auth_token
        auth_token = request.data.get('auth_token', '')
        cached = cache.get(f'passkey_auth:{auth_token}')
        if not cached:
            return Response(
                {'detail': 'Challenge expired or missing. Please try again.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        challenge = _b64url_decode(cached['challenge'])
        cache.delete(f'passkey_auth:{auth_token}')  # One-time use

        raw_id_b64 = request.data.get('rawId') or request.data.get('id', '')
        try:
            raw_id_bytes = _b64url_decode(raw_id_b64)
        except Exception:
            return Response({'detail': 'Invalid rawId.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cred = WebAuthnCredential.objects.select_related('user').get(credential_id=raw_id_bytes)
        except WebAuthnCredential.DoesNotExist:
            logger.warning(f'WebAuthn: credential not found rawId={raw_id_b64[:20]}...')
            return Response({'detail': 'Unknown credential.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            verification = webauthn.verify_authentication_response(
                credential=request.data,
                expected_challenge=challenge,
                expected_rp_id=_get_rp_id(),
                expected_origin=_get_allowed_origins(),
                credential_public_key=bytes(cred.public_key),
                credential_current_sign_count=cred.sign_count,
                require_user_verification=False,
            )
        except Exception as e:
            logger.warning(f'WebAuthn auth failed: {e}')
            return Response({'detail': f'Authentication failed: {e}'}, status=status.HTTP_401_UNAUTHORIZED)

        cred.sign_count = verification.new_sign_count
        cred.last_used = datetime.now(timezone.utc)
        cred.save(update_fields=['sign_count', 'last_used'])

        user = cred.user
        if not user.is_active:
            return Response({'detail': 'Account is disabled.'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        logger.info(f'🔑 Passkey login: user={user.username} device="{cred.device_name}"')

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


# ─── 4. List / Delete credentials ─────────────────────────────────────────────

class PasskeyListView(APIView):
    """List and delete registered passkeys."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        creds = WebAuthnCredential.objects.filter(user=request.user).order_by('-created_at')
        return Response([{
            'id': c.pk,
            'device_name': c.device_name,
            'created_at': c.created_at.isoformat(),
            'last_used': c.last_used.isoformat() if c.last_used else None,
            'transports': c.transports,
        } for c in creds])

    def delete(self, request, pk):
        try:
            cred = WebAuthnCredential.objects.get(pk=pk, user=request.user)
            cred.delete()
            logger.info(f'🗑️ Passkey deleted: user={request.user.username} id={pk}')
            return Response({'status': 'deleted'})
        except WebAuthnCredential.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)


# ─── 5. Verify passkey after password login (pending tokens) ───────────────────

class PasskeyVerifyPendingView(APIView):
    """
    Called after password login when requires_passkey=True was returned.
    Flow:
      1. User enters username+password → backend stores JWT in session, returns requires_passkey=True
      2. GET /auth/passkey/verify-pending/?token=<pending_token> → returns auth options (challenge)
      3. Browser asks for biometric
      4. POST /auth/passkey/verify-pending/ {pending_token, ...assertion} → verifies + returns JWT
    Uses Django cache (Redis) — no session cookies needed (stateless, cross-origin safe).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """Return authentication options for pending passkey verification."""
        import webauthn
        from webauthn.helpers.structs import UserVerificationRequirement
        from django.core.cache import cache
        import json as _json

        pending_token = request.GET.get('token', '')
        cache_key = f'passkey_pending:{pending_token}'
        pending = cache.get(cache_key)
        if not pending:
            return Response({'detail': 'No pending login or token expired. Please login again.'}, status=status.HTTP_400_BAD_REQUEST)

        options = webauthn.generate_authentication_options(
            rp_id=_get_rp_id(),
            user_verification=UserVerificationRequirement.PREFERRED,
        )
        challenge_b64 = _b64url_encode(options.challenge)
        # Store challenge alongside pending tokens, keyed by same token
        pending['challenge'] = challenge_b64
        cache.set(cache_key, pending, timeout=120)
        return Response(_json.loads(webauthn.options_to_json(options)))

    @method_decorator(ratelimit(key='ip', rate='10/5m', method='POST', block=True))
    def post(self, request):
        """Verify biometric assertion and return pending JWT tokens."""
        import webauthn
        from django.core.cache import cache
        from datetime import datetime, timezone

        pending_token = request.data.get('pending_token', '')
        cache_key = f'passkey_pending:{pending_token}'
        pending = cache.get(cache_key)
        if not pending:
            return Response({'detail': 'No pending login or token expired. Please login again.'}, status=status.HTTP_400_BAD_REQUEST)

        challenge_b64 = pending.get('challenge')
        if not challenge_b64:
            return Response({'detail': 'No passkey challenge found. Call GET first.'}, status=status.HTTP_400_BAD_REQUEST)

        challenge = _b64url_decode(challenge_b64)

        # Remove pending_token from assertion data before passing to webauthn
        assertion_data = {k: v for k, v in request.data.items() if k != 'pending_token'}

        raw_id_b64 = assertion_data.get('rawId') or assertion_data.get('id', '')
        try:
            raw_id_bytes = _b64url_decode(raw_id_b64)
        except Exception:
            return Response({'detail': 'Invalid rawId.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cred = WebAuthnCredential.objects.select_related('user').get(credential_id=raw_id_bytes)
        except WebAuthnCredential.DoesNotExist:
            return Response({'detail': 'Unknown credential.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            verification = webauthn.verify_authentication_response(
                credential=assertion_data,
                expected_challenge=challenge,
                expected_rp_id=_get_rp_id(),
                expected_origin=_get_allowed_origins(),
                credential_public_key=bytes(cred.public_key),
                credential_current_sign_count=cred.sign_count,
                require_user_verification=False,
            )
        except Exception as e:
            logger.warning(f'PasskeyVerifyPending failed: {e}')
            return Response({'detail': f'Passkey verification failed: {e}'}, status=status.HTTP_401_UNAUTHORIZED)

        # Update credential
        cred.sign_count = verification.new_sign_count
        cred.last_used = datetime.now(timezone.utc)
        cred.save(update_fields=['sign_count', 'last_used'])

        # Invalidate one-time token
        cache.delete(cache_key)

        logger.info(f'🔑 Passkey verified post-login: user={cred.user.username} device="{cred.device_name}"')

        return Response({
            'access': pending['access'],
            'refresh': pending['refresh'],
        })
