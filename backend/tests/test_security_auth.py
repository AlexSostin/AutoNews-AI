"""
Tests for security modules previously at 0% coverage:
- news/api_views/two_factor.py (271 lines, 6 views)
- news/api_views/webauthn_views.py (393 lines, 5 views)
"""
import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def admin_user(db):
    from django.contrib.auth.models import User
    return User.objects.create_superuser(
        username='admin2fa', password='testpass123', email='admin@test.com'
    )


@pytest.fixture
def regular_user(db):
    from django.contrib.auth.models import User
    return User.objects.create_user(
        username='regular2fa', password='testpass123', email='user@test.com'
    )


@pytest.fixture
def auth_admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def auth_user_client(regular_user):
    client = APIClient()
    client.force_authenticate(user=regular_user)
    return client


@pytest.fixture
def totp_device(admin_user):
    """Create a confirmed TOTP device for admin user."""
    from news.models import TOTPDevice
    import pyotp
    secret = pyotp.random_base32()
    device = TOTPDevice.objects.create(
        user=admin_user,
        secret=secret,
        is_confirmed=True,
    )
    return device, secret


@pytest.fixture
def webauthn_credential(admin_user):
    """Create a test WebAuthn credential."""
    from news.models import WebAuthnCredential
    cred = WebAuthnCredential.objects.create(
        user=admin_user,
        credential_id=b'test_cred_id_bytes_123',
        public_key=b'fake_public_key_bytes',
        sign_count=0,
        device_name='Test Key',
    )
    return cred


# ═══════════════════════════════════════════════════════════════════════════
# 2FA Setup — TwoFactorSetupView
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTwoFactorSetup:
    def test_setup_returns_qr_and_secret(self, auth_admin_client):
        """POST /api/v1/auth/2fa/setup/ → QR code + secret."""
        resp = auth_admin_client.post('/api/v1/auth/2fa/setup/')
        assert resp.status_code == 200
        data = resp.json()
        assert 'secret' in data

    def test_non_admin_denied(self, auth_user_client):
        """Non-admin users should be denied access."""
        resp = auth_user_client.post('/api/v1/auth/2fa/setup/')
        assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════
# 2FA Confirm — TwoFactorConfirmView 
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTwoFactorConfirm:
    def test_confirm_with_valid_code(self, auth_admin_client, admin_user):
        """Confirm 2FA with valid TOTP code."""
        import pyotp
        setup_resp = auth_admin_client.post('/api/v1/auth/2fa/setup/')
        secret = setup_resp.json()['secret']
        code = pyotp.TOTP(secret).now()
        resp = auth_admin_client.post('/api/v1/auth/2fa/confirm/', {'code': code})
        assert resp.status_code == 200

    def test_confirm_with_invalid_code(self, auth_admin_client):
        """Wrong code → 400."""
        auth_admin_client.post('/api/v1/auth/2fa/setup/')
        resp = auth_admin_client.post('/api/v1/auth/2fa/confirm/', {'code': '000000'})
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# 2FA Verify — TwoFactorVerifyView
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTwoFactorVerify:
    def test_verify_with_valid_credentials(self, totp_device, admin_user):
        """Valid username + password + TOTP → JWT tokens."""
        import pyotp
        device, secret = totp_device
        code = pyotp.TOTP(secret).now()
        client = APIClient()
        resp = client.post('/api/v1/auth/2fa/verify/', {
            'username': 'admin2fa',
            'password': 'testpass123',
            'totp_code': code,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert 'access' in data
        assert 'refresh' in data

    def test_verify_with_bad_code(self, totp_device, admin_user):
        """Invalid TOTP → 400/401."""
        client = APIClient()
        resp = client.post('/api/v1/auth/2fa/verify/', {
            'username': 'admin2fa',
            'password': 'testpass123',
            'totp_code': '000000',
        })
        assert resp.status_code in (400, 401)

    def test_verify_with_wrong_password(self, totp_device):
        """Wrong password → 400/401."""
        import pyotp
        device, secret = totp_device
        code = pyotp.TOTP(secret).now()
        client = APIClient()
        resp = client.post('/api/v1/auth/2fa/verify/', {
            'username': 'admin2fa',
            'password': 'wrongpassword',
            'totp_code': code,
        })
        assert resp.status_code in (400, 401)


# ═══════════════════════════════════════════════════════════════════════════
# 2FA Disable — TwoFactorDisableView
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTwoFactorDisable:
    def test_disable_with_valid_code(self, auth_admin_client, totp_device):
        """Disable 2FA with valid TOTP code."""
        import pyotp
        device, secret = totp_device
        code = pyotp.TOTP(secret).now()
        resp = auth_admin_client.post('/api/v1/auth/2fa/disable/', {'code': code})
        assert resp.status_code == 200

        from news.models import TOTPDevice
        assert not TOTPDevice.objects.filter(user=device.user, is_confirmed=True).exists()

    def test_disable_without_code(self, auth_admin_client, totp_device):
        """No code → 400."""
        resp = auth_admin_client.post('/api/v1/auth/2fa/disable/', {})
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# 2FA Status — TwoFactorStatusView
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestTwoFactorStatus:
    def test_status_enabled(self, auth_admin_client, totp_device):
        """With device → enabled: true."""
        resp = auth_admin_client.get('/api/v1/auth/2fa/status/')
        assert resp.status_code == 200
        assert resp.json()['enabled'] is True

    def test_status_disabled(self, auth_admin_client):
        """No device → enabled: false."""
        resp = auth_admin_client.get('/api/v1/auth/2fa/status/')
        assert resp.status_code == 200
        assert resp.json()['enabled'] is False


# ═══════════════════════════════════════════════════════════════════════════
# WebAuthn — PasskeyListView (credentials CRUD)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def auth_admin_webauthn(db):
    from django.contrib.auth.models import User
    user = User.objects.create_superuser(
        username='adminpasskey', password='testpass123', email='passkey@test.com'
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.mark.django_db
class TestPasskeyList:
    def test_list_empty(self, auth_admin_webauthn):
        """No credentials → empty list."""
        client, user = auth_admin_webauthn
        resp = client.get('/api/v1/auth/passkey/credentials/')
        assert resp.status_code == 200

    def test_list_with_credential(self, auth_admin_webauthn):
        """With credential → list contains it."""
        client, user = auth_admin_webauthn
        from news.models import WebAuthnCredential
        WebAuthnCredential.objects.create(
            user=user,
            credential_id=b'list_test_cred',
            public_key=b'fake_key',
            sign_count=0,
            device_name='Test',
        )
        resp = client.get('/api/v1/auth/passkey/credentials/')
        assert resp.status_code == 200
        data = resp.json()
        creds = data if isinstance(data, list) else data.get('results', data.get('credentials', []))
        assert len(creds) >= 1

    def test_delete_credential(self, auth_admin_webauthn):
        """DELETE removes credential."""
        client, user = auth_admin_webauthn
        from news.models import WebAuthnCredential
        cred = WebAuthnCredential.objects.create(
            user=user,
            credential_id=b'delete_test_cred',
            public_key=b'fake_key',
            sign_count=0,
        )
        resp = client.delete(f'/api/v1/auth/passkey/credentials/{cred.pk}/')
        assert resp.status_code in (200, 204)
        assert not WebAuthnCredential.objects.filter(pk=cred.pk).exists()


# ═══════════════════════════════════════════════════════════════════════════
# WebAuthn — Registration + Authentication (mocked py_webauthn)
# Note: py_webauthn requires libcrypto which may not be available in WSL.
# These tests mock the heavy crypto operations.
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestPasskeyRegisterBegin:
    def test_returns_challenge(self, auth_admin_webauthn):
        """POST → returns registration challenge (with mocked webauthn module)."""
        import sys
        mock_webauthn = MagicMock()
        mock_webauthn.generate_registration_options.return_value = MagicMock(challenge=b'test_challenge')
        mock_webauthn.options_to_json.return_value = '{"challenge": "dGVzdF9jaGFsbGVuZ2U"}'
        # Mock the helpers.structs submodule
        mock_webauthn.helpers.structs.AuthenticatorSelectionCriteria = MagicMock()
        mock_webauthn.helpers.structs.UserVerificationRequirement = MagicMock()
        mock_webauthn.helpers.structs.ResidentKeyRequirement = MagicMock()
        mock_webauthn.helpers.structs.PublicKeyCredentialDescriptor = MagicMock()

        client, user = auth_admin_webauthn
        with patch.dict(sys.modules, {'webauthn': mock_webauthn, 'webauthn.helpers': mock_webauthn.helpers, 'webauthn.helpers.structs': mock_webauthn.helpers.structs}):
            resp = client.post('/api/v1/auth/passkey/register/begin/')
        assert resp.status_code == 200

    def test_unauthenticated_denied(self):
        """Unauthenticated → 401/403."""
        client = APIClient()
        resp = client.post('/api/v1/auth/passkey/register/begin/')
        assert resp.status_code in (401, 403)


@pytest.mark.django_db
class TestPasskeyAuthenticate:
    def test_get_challenge(self, auth_admin_webauthn):
        """GET → returns auth challenge (with mocked webauthn module)."""
        import sys
        mock_webauthn = MagicMock()
        mock_webauthn.generate_authentication_options.return_value = MagicMock(challenge=b'auth_challenge')
        mock_webauthn.options_to_json.return_value = '{"challenge": "YXV0aF9jaGFsbGVuZ2U"}'
        mock_webauthn.helpers.structs.UserVerificationRequirement = MagicMock()

        client, user = auth_admin_webauthn
        from news.models import WebAuthnCredential
        WebAuthnCredential.objects.create(
            user=user, credential_id=b'auth_cred', public_key=b'key', sign_count=0
        )

        with patch.dict(sys.modules, {'webauthn': mock_webauthn, 'webauthn.helpers': mock_webauthn.helpers, 'webauthn.helpers.structs': mock_webauthn.helpers.structs}):
            resp = client.get('/api/v1/auth/passkey/authenticate/')
        assert resp.status_code == 200

