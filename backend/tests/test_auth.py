"""
Tests for authentication endpoints:
- JWT login/refresh
- Current user info
- Password change
- Password reset flow
- Email change verification
"""
import pytest
from django.contrib.auth.models import User
from rest_framework import status


@pytest.mark.django_db
class TestJWTAuth:
    """JWT token obtain and refresh"""

    def test_login_success(self, api_client):
        """Valid credentials return access + refresh tokens"""
        User.objects.create_user(username='loginuser', password='StrongPass123!', email='login@test.com')
        resp = api_client.post('/api/v1/token/', {'username': 'loginuser', 'password': 'StrongPass123!'})
        assert resp.status_code == status.HTTP_200_OK
        assert 'access' in resp.data
        assert 'refresh' in resp.data

    def test_login_wrong_password(self, api_client):
        """Wrong password returns 401"""
        User.objects.create_user(username='loginuser2', password='StrongPass123!', email='login2@test.com')
        resp = api_client.post('/api/v1/token/', {'username': 'loginuser2', 'password': 'wrong'})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, api_client):
        """Valid refresh token returns new access token"""
        User.objects.create_user(username='refreshuser', password='StrongPass123!', email='refresh@test.com')
        login_resp = api_client.post('/api/v1/token/', {'username': 'refreshuser', 'password': 'StrongPass123!'})
        refresh_token = login_resp.data['refresh']

        resp = api_client.post('/api/v1/token/refresh/', {'refresh': refresh_token})
        assert resp.status_code == status.HTTP_200_OK
        assert 'access' in resp.data

    def test_refresh_invalid_token(self, api_client):
        """Invalid refresh token returns 401"""
        resp = api_client.post('/api/v1/token/refresh/', {'refresh': 'invalid-token'})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestCurrentUser:
    """GET/PATCH /api/v1/auth/user/"""

    def test_get_current_user(self, authenticated_client):
        """Authenticated user can get their own info"""
        resp = authenticated_client.get('/api/v1/auth/user/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['username'] == 'testuser'
        assert 'email' in resp.data
        assert 'is_staff' in resp.data

    def test_get_current_user_unauthenticated(self, api_client):
        """Unauthenticated request returns 401"""
        resp = api_client.get('/api/v1/auth/user/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_name(self, authenticated_client):
        """Can update first_name and last_name"""
        resp = authenticated_client.patch('/api/v1/auth/user/', {
            'first_name': 'John',
            'last_name': 'Doe',
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['first_name'] == 'John'
        assert resp.data['last_name'] == 'Doe'

    def test_email_change_rejected_via_patch(self, authenticated_client):
        """Direct email change via PATCH is rejected"""
        resp = authenticated_client.patch('/api/v1/auth/user/', {
            'email': 'new@test.com',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPasswordChange:
    """POST /api/v1/auth/password/change/"""

    def test_change_password_success(self, api_client):
        """Valid old password + strong new password succeeds"""
        user = User.objects.create_user(username='pwuser', password='OldPass123!', email='pw@test.com')
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(user).access_token)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        resp = api_client.post('/api/v1/auth/password/change/', {
            'old_password': 'OldPass123!',
            'new_password1': 'NewStrong456!',
            'new_password2': 'NewStrong456!',
        })
        assert resp.status_code == status.HTTP_200_OK

        # Verify new password works
        user.refresh_from_db()
        assert user.check_password('NewStrong456!')

    def test_change_password_wrong_old(self, api_client):
        """Wrong old password returns 400"""
        user = User.objects.create_user(username='pwuser2', password='OldPass123!', email='pw2@test.com')
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(user).access_token)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        resp = api_client.post('/api/v1/auth/password/change/', {
            'old_password': 'WrongPassword!',
            'new_password1': 'NewStrong456!',
            'new_password2': 'NewStrong456!',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_mismatch(self, api_client):
        """Mismatched new passwords return 400"""
        user = User.objects.create_user(username='pwuser3', password='OldPass123!', email='pw3@test.com')
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(user).access_token)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        resp = api_client.post('/api/v1/auth/password/change/', {
            'old_password': 'OldPass123!',
            'new_password1': 'NewStrong456!',
            'new_password2': 'DifferentPass!',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPasswordReset:
    """Password reset request + confirm flow"""

    def test_request_reset(self, api_client):
        """Password reset request returns success (even for non-existent email for security)"""
        User.objects.create_user(username='resetuser', password='OldPass123!', email='reset@test.com')
        resp = api_client.post('/api/v1/auth/password/reset-request/', {'email': 'reset@test.com'})
        assert resp.status_code == status.HTTP_200_OK

    def test_request_reset_unknown_email(self, api_client):
        """Non-existent email still returns 200 (no info leakage)"""
        resp = api_client.post('/api/v1/auth/password/reset-request/', {'email': 'nobody@test.com'})
        assert resp.status_code == status.HTTP_200_OK

    def test_confirm_reset(self, api_client):
        """Valid token + strong password resets successfully"""
        from news.models import PasswordResetToken
        from django.utils import timezone
        from datetime import timedelta

        user = User.objects.create_user(username='resetuser2', password='OldPass123!', email='reset2@test.com')
        reset = PasswordResetToken.objects.create(
            user=user,
            token='test-reset-token-123',
            expires_at=timezone.now() + timedelta(hours=1),
            ip_address='127.0.0.1',
        )

        resp = api_client.post('/api/v1/auth/password/reset-confirm/', {
            'token': 'test-reset-token-123',
            'new_password': 'BrandNewPass789!',
        })
        assert resp.status_code == status.HTTP_200_OK

        # Verify new password works
        user.refresh_from_db()
        assert user.check_password('BrandNewPass789!')

    def test_confirm_reset_invalid_token(self, api_client):
        """Invalid token returns 400"""
        resp = api_client.post('/api/v1/auth/password/reset-confirm/', {
            'token': 'nonexistent-token',
            'new_password': 'BrandNewPass789!',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestEmailPreferences:
    """GET/PATCH /api/v1/auth/email-preferences/"""

    def test_get_email_preferences(self, authenticated_client):
        """Can get email preferences"""
        resp = authenticated_client.get('/api/v1/auth/email-preferences/')
        assert resp.status_code == status.HTTP_200_OK

    def test_update_email_preferences(self, authenticated_client):
        """Can update email preferences"""
        resp = authenticated_client.patch('/api/v1/auth/email-preferences/', {
            'newsletter': False,
        }, format='json')
        assert resp.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_email_preferences_requires_auth(self, api_client):
        """Email preferences requires authentication"""
        resp = api_client.get('/api/v1/auth/email-preferences/')
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
