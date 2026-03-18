"""
Admin 2FA Middleware — enforces TOTP verification for Django admin access.

When a staff user with 2FA enabled logs into /admin/, this middleware
intercepts the request and requires TOTP verification before granting
access to any admin page. The verification state is stored in the
Django session as 'admin_2fa_verified'.

Flow:
1. User logs into Django admin with username/password (standard admin login)
2. Middleware detects the user has a confirmed TOTPDevice
3. Redirects to /admin/verify-2fa/ for TOTP code entry
4. On valid code → sets session['admin_2fa_verified'] = True
5. All subsequent admin requests pass through
"""
import logging
from django.shortcuts import render, redirect
from django.contrib import messages

logger = logging.getLogger('news')

# Paths that should NOT require 2FA (login/logout flow)
EXEMPT_PATHS = [
    '/admin/login/',
    '/admin/logout/',
    '/admin/jsi18n/',
]


class Admin2FAMiddleware:
    """Require TOTP verification for Django admin when user has 2FA enabled."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only intercept /admin/ requests
        if not request.path.startswith('/admin/'):
            return self.get_response(request)

        # Skip exempt paths (login/logout)
        if any(request.path.startswith(p) for p in EXEMPT_PATHS):
            return self.get_response(request)

        # Skip if user is not authenticated (will be redirected to login)
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return self.get_response(request)

        # Check if user has 2FA configured
        from news.models import TOTPDevice
        try:
            device = TOTPDevice.objects.get(user=request.user, is_confirmed=True)
        except TOTPDevice.DoesNotExist:
            # No 2FA configured — allow through (but log warning for staff)
            if request.user.is_staff:
                logger.warning(
                    f"⚠️ Admin access WITHOUT 2FA: user={request.user.username} "
                    f"path={request.path}"
                )
            return self.get_response(request)

        # User has 2FA — check if already verified this session
        if request.session.get('admin_2fa_verified'):
            return self.get_response(request)

        # Handle the verification page — serve it directly from middleware
        # (no Django URL pattern needed, avoids 404)
        if request.path == '/admin/verify-2fa/':
            return self._handle_verify_page(request, device)

        # Not verified — redirect to verification page
        logger.info(
            f"🔐 Admin 2FA required: user={request.user.username} "
            f"redirecting to verify-2fa"
        )
        return redirect('/admin/verify-2fa/')

    def _handle_verify_page(self, request, device):
        """Handle the 2FA verification form."""
        if request.method == 'POST':
            code = request.POST.get('totp_code', '').strip()

            if not code:
                messages.error(request, 'Please enter your 2FA code.')
                return render(request, 'admin/verify_2fa.html')

            # Verify TOTP or backup code
            if device.verify_code(code) or device.verify_backup_code(code):
                request.session['admin_2fa_verified'] = True
                logger.info(
                    f"🔑 Admin 2FA verified: user={request.user.username}"
                )
                messages.success(request, '✅ 2FA verified successfully!')
                # Redirect to admin index
                next_url = request.GET.get('next', '/admin/')
                return redirect(next_url)
            else:
                logger.warning(
                    f"🔒 Admin 2FA FAILED: user={request.user.username}"
                )
                messages.error(request, '❌ Invalid 2FA code. Please try again.')
                return render(request, 'admin/verify_2fa.html')

        # GET — show the form
        return render(request, 'admin/verify_2fa.html')
