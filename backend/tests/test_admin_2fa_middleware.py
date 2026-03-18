"""
Tests for Admin 2FA Middleware — ensures Django admin /admin/ enforces TOTP
verification when user has 2FA enabled.

Test matrix:
- Exempt paths (login/logout) → pass through
- Anonymous users → pass through (Django handles login redirect)
- Staff without 2FA → pass through (with warning log)
- Staff with 2FA, not verified → redirect to /admin/verify-2fa/
- Staff with 2FA, verified session → pass through
- POST valid TOTP code → sets session flag, redirects to /admin/
- POST invalid code → stays on verification page with error
- POST backup code → works as alternative to TOTP
- Logout clears 2FA verification state
"""
import pytest
import pyotp
from django.test import Client
from django.contrib.auth.models import User


@pytest.fixture
def staff_user(db):
    """Staff user without 2FA."""
    return User.objects.create_user(
        username='staff_no2fa', password='testpass123',
        email='staff@test.com', is_staff=True,
    )


@pytest.fixture
def staff_user_with_2fa(db):
    """Staff user WITH confirmed 2FA device."""
    user = User.objects.create_user(
        username='staff_2fa', password='testpass123',
        email='staff2fa@test.com', is_staff=True,
    )
    from news.models import TOTPDevice
    secret = pyotp.random_base32()
    TOTPDevice.objects.create(user=user, secret=secret, is_confirmed=True)
    return user, secret


@pytest.fixture
def logged_in_client_no2fa(staff_user):
    """Django test client logged in as staff WITHOUT 2FA."""
    client = Client()
    client.login(username='staff_no2fa', password='testpass123')
    return client


@pytest.fixture
def logged_in_client_with_2fa(staff_user_with_2fa):
    """Django test client logged in as staff WITH 2FA (not yet verified)."""
    user, secret = staff_user_with_2fa
    client = Client()
    client.login(username='staff_2fa', password='testpass123')
    return client, secret


# ═══════════════════════════════════════════════════════════════════════════
# Exempt Paths — should NEVER require 2FA
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAdmin2FAExemptPaths:
    def test_login_page_accessible(self):
        """GET /admin/login/ → login form (no 2FA redirect)."""
        client = Client()
        resp = client.get('/admin/login/')
        assert resp.status_code == 200

    def test_logout_accessible(self, logged_in_client_with_2fa):
        """GET /admin/logout/ → not redirected to 2FA."""
        client, _ = logged_in_client_with_2fa
        resp = client.get('/admin/logout/', follow=False)
        # Should NOT redirect to /admin/verify-2fa/
        assert '/verify-2fa/' not in (resp.get('Location', '') or '')

    def test_non_admin_paths_unaffected(self):
        """Non-admin paths are not intercepted by middleware."""
        client = Client()
        resp = client.get('/api/v1/health/')
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# Staff WITHOUT 2FA — should pass through
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAdmin2FANoDevice:
    def test_staff_without_2fa_can_access_admin(self, logged_in_client_no2fa):
        """Staff without TOTP device → admin index accessible."""
        resp = logged_in_client_no2fa.get('/admin/', follow=False)
        # Should get 200 (admin index) or 302 to /admin/ (not to verify-2fa)
        if resp.status_code == 302:
            assert '/verify-2fa/' not in resp['Location']
        else:
            assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# Staff WITH 2FA — redirect to verify page
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAdmin2FARedirect:
    def test_admin_index_redirects_to_verify(self, logged_in_client_with_2fa):
        """Staff with 2FA, not verified → redirect to /admin/verify-2fa/."""
        client, _ = logged_in_client_with_2fa
        resp = client.get('/admin/', follow=False)
        assert resp.status_code == 302
        assert '/admin/verify-2fa/' in resp['Location']

    def test_admin_changelist_redirects(self, logged_in_client_with_2fa):
        """Any admin page redirects to verify-2fa."""
        client, _ = logged_in_client_with_2fa
        resp = client.get('/admin/news/article/', follow=False)
        assert resp.status_code == 302
        assert '/admin/verify-2fa/' in resp['Location']

    def test_verify_page_shows_form(self, logged_in_client_with_2fa):
        """GET /admin/verify-2fa/ → renders the verification form."""
        client, _ = logged_in_client_with_2fa
        resp = client.get('/admin/verify-2fa/')
        assert resp.status_code == 200
        assert b'totp_code' in resp.content
        assert b'2FA Verification' in resp.content


# ═══════════════════════════════════════════════════════════════════════════
# TOTP Verification — valid/invalid codes
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAdmin2FAVerification:
    def test_valid_totp_code_grants_access(self, logged_in_client_with_2fa):
        """POST valid TOTP code → sets session flag → redirects to admin."""
        client, secret = logged_in_client_with_2fa
        code = pyotp.TOTP(secret).now()
        resp = client.post('/admin/verify-2fa/', {'totp_code': code})
        assert resp.status_code == 302
        assert '/admin/' in resp['Location']
        # Session should now be verified
        assert client.session.get('admin_2fa_verified') is True

    def test_verified_session_passes_through(self, logged_in_client_with_2fa):
        """After verification, admin pages are accessible without redirect."""
        client, secret = logged_in_client_with_2fa
        code = pyotp.TOTP(secret).now()
        client.post('/admin/verify-2fa/', {'totp_code': code})
        # Now admin should work
        resp = client.get('/admin/', follow=False)
        # Should NOT redirect to verify-2fa anymore
        if resp.status_code == 302:
            assert '/verify-2fa/' not in resp['Location']
        else:
            assert resp.status_code == 200

    def test_invalid_code_stays_on_page(self, logged_in_client_with_2fa):
        """POST invalid code → stays on verify page with error."""
        client, _ = logged_in_client_with_2fa
        resp = client.post('/admin/verify-2fa/', {'totp_code': '000000'})
        assert resp.status_code == 200  # Re-renders the page
        assert b'Invalid 2FA code' in resp.content
        assert client.session.get('admin_2fa_verified') is not True

    def test_empty_code_shows_error(self, logged_in_client_with_2fa):
        """POST empty code → error message."""
        client, _ = logged_in_client_with_2fa
        resp = client.post('/admin/verify-2fa/', {'totp_code': ''})
        assert resp.status_code == 200
        assert b'enter your 2FA code' in resp.content

    def test_backup_code_works(self, logged_in_client_with_2fa):
        """POST valid backup code → session verified."""
        client, secret = logged_in_client_with_2fa
        from news.models import TOTPDevice
        user = User.objects.get(username='staff_2fa')
        device = TOTPDevice.objects.get(user=user)
        # Generate backup codes
        plaintext_codes, hashed_codes = TOTPDevice.generate_backup_codes()
        device.backup_codes = hashed_codes
        device.save()
        resp = client.post('/admin/verify-2fa/', {'totp_code': plaintext_codes[0]})
        assert resp.status_code == 302
        assert client.session.get('admin_2fa_verified') is True


# ═══════════════════════════════════════════════════════════════════════════
# Anonymous users — should not be affected
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAdmin2FAAnonymous:
    def test_anonymous_user_not_redirected_to_2fa(self):
        """Anonymous user → Django login redirect, NOT 2FA page."""
        client = Client()
        resp = client.get('/admin/', follow=False)
        assert resp.status_code in (302, 301)
        location = resp.get('Location', '')
        assert 'login' in location or '/admin/login/' in location
        assert '/verify-2fa/' not in location
