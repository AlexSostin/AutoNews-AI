"""
Tests for api_views.py — Batch 1: User Authentication & Profile
Covers: CurrentUserView, ChangePasswordView, EmailPreferencesView,
        RequestEmailChangeView, VerifyEmailChangeView,
        PasswordResetRequestView, PasswordResetConfirmView,
        UserViewSet.me, UserViewSet.register
"""
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User

pytestmark = pytest.mark.django_db

API = '/api/v1'


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser', email='test@example.com',
        password='OldPass123!', first_name='Test', last_name='User',
    )


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username='staffuser', email='staff@example.com',
        password='Staff123!', is_staff=True,
    )


@pytest.fixture
def auth_client(user):
    client = APIClient(HTTP_USER_AGENT='TestBrowser/1.0')
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def anon_client():
    return APIClient(HTTP_USER_AGENT='TestBrowser/1.0')


# ═══════════════════════════════════════════════════════════════════════════
# CurrentUserView — GET /api/v1/auth/user/
# ═══════════════════════════════════════════════════════════════════════════

class TestCurrentUserView:

    def test_get_current_user(self, auth_client, user):
        resp = auth_client.get(f'{API}/auth/user/')
        assert resp.status_code == 200
        assert resp.data['username'] == 'testuser'
        assert resp.data['email'] == 'test@example.com'
        assert resp.data['first_name'] == 'Test'
        assert 'is_staff' in resp.data
        assert 'date_joined' in resp.data

    def test_get_current_user_anonymous_forbidden(self, anon_client):
        resp = anon_client.get(f'{API}/auth/user/')
        assert resp.status_code == 401

    def test_patch_name(self, auth_client, user):
        resp = auth_client.patch(f'{API}/auth/user/', {
            'first_name': 'Updated', 'last_name': 'Name',
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['first_name'] == 'Updated'
        assert resp.data['last_name'] == 'Name'
        user.refresh_from_db()
        assert user.first_name == 'Updated'

    def test_patch_email_rejected(self, auth_client):
        resp = auth_client.patch(f'{API}/auth/user/', {
            'email': 'new@mail.com',
        }, format='json')
        assert resp.status_code == 400
        assert 'email' in resp.data


# ═══════════════════════════════════════════════════════════════════════════
# ChangePasswordView — POST /api/v1/auth/password/change/
# ═══════════════════════════════════════════════════════════════════════════

class TestChangePasswordView:

    def test_change_password_success(self, auth_client, user):
        resp = auth_client.post(f'{API}/auth/password/change/', {
            'old_password': 'OldPass123!',
            'new_password1': 'NewSecure456!',
            'new_password2': 'NewSecure456!',
        }, format='json')
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.check_password('NewSecure456!')

    def test_change_password_wrong_old(self, auth_client):
        resp = auth_client.post(f'{API}/auth/password/change/', {
            'old_password': 'WrongPassword!',
            'new_password1': 'NewPass123!',
            'new_password2': 'NewPass123!',
        }, format='json')
        assert resp.status_code == 400
        assert 'old_password' in resp.data

    def test_change_password_mismatch(self, auth_client):
        resp = auth_client.post(f'{API}/auth/password/change/', {
            'old_password': 'OldPass123!',
            'new_password1': 'NewPass123!',
            'new_password2': 'Different456!',
        }, format='json')
        assert resp.status_code == 400

    def test_change_password_anonymous_forbidden(self, anon_client):
        resp = anon_client.post(f'{API}/auth/password/change/', {
            'old_password': 'x', 'new_password1': 'y', 'new_password2': 'y',
        }, format='json')
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# EmailPreferencesView — GET/PATCH /api/v1/auth/email-preferences/
# ═══════════════════════════════════════════════════════════════════════════

class TestEmailPreferencesView:

    def test_get_preferences(self, auth_client):
        resp = auth_client.get(f'{API}/auth/email-preferences/')
        assert resp.status_code == 200

    def test_patch_preferences(self, auth_client):
        resp = auth_client.patch(f'{API}/auth/email-preferences/', {},
                                 format='json')
        assert resp.status_code == 200

    def test_anonymous_forbidden(self, anon_client):
        resp = anon_client.get(f'{API}/auth/email-preferences/')
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# RequestEmailChangeView — POST /api/v1/auth/email/request-change/
# ═══════════════════════════════════════════════════════════════════════════

class TestRequestEmailChangeView:

    def test_request_email_change(self, auth_client):
        resp = auth_client.post(f'{API}/auth/email/request-change/', {
            'new_email': 'newemail@test.com',
        }, format='json')
        assert resp.status_code == 200
        assert 'code' in resp.data  # DEV mode returns code
        assert resp.data['expires_in'] == 900

    def test_request_email_change_empty(self, auth_client):
        resp = auth_client.post(f'{API}/auth/email/request-change/', {
            'new_email': '',
        }, format='json')
        assert resp.status_code == 400

    def test_request_email_change_same_email(self, auth_client, user):
        resp = auth_client.post(f'{API}/auth/email/request-change/', {
            'new_email': user.email,
        }, format='json')
        assert resp.status_code == 400

    def test_request_email_change_taken(self, auth_client, staff_user):
        resp = auth_client.post(f'{API}/auth/email/request-change/', {
            'new_email': staff_user.email,
        }, format='json')
        assert resp.status_code == 400
        assert 'already taken' in str(resp.data)


# ═══════════════════════════════════════════════════════════════════════════
# VerifyEmailChangeView — POST /api/v1/auth/email/verify-code/
# ═══════════════════════════════════════════════════════════════════════════

class TestVerifyEmailChangeView:

    def test_verify_code_success(self, auth_client, user):
        # First request a change to get a code
        resp = auth_client.post(f'{API}/auth/email/request-change/', {
            'new_email': 'verified@test.com',
        }, format='json')
        code = resp.data['code']

        # Verify
        resp = auth_client.post(f'{API}/auth/email/verify-code/', {
            'code': code,
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['new_email'] == 'verified@test.com'
        user.refresh_from_db()
        assert user.email == 'verified@test.com'

    def test_verify_code_empty(self, auth_client):
        resp = auth_client.post(f'{API}/auth/email/verify-code/', {
            'code': '',
        }, format='json')
        assert resp.status_code == 400

    def test_verify_code_invalid(self, auth_client):
        resp = auth_client.post(f'{API}/auth/email/verify-code/', {
            'code': '000000',
        }, format='json')
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# PasswordResetRequestView — POST /api/v1/auth/password/reset-request/
# ═══════════════════════════════════════════════════════════════════════════

class TestPasswordResetRequestView:

    def test_request_reset_existing_user(self, anon_client, user):
        resp = anon_client.post(f'{API}/auth/password/reset-request/', {
            'email': user.email,
        }, format='json')
        assert resp.status_code == 200
        assert 'reset_link' in resp.data  # DEV mode

    def test_request_reset_nonexistent_email(self, anon_client):
        resp = anon_client.post(f'{API}/auth/password/reset-request/', {
            'email': 'nobody@nowhere.com',
        }, format='json')
        # Should not reveal whether email exists
        assert resp.status_code == 200
        assert 'If email exists' in resp.data.get('detail', '')

    def test_request_reset_empty_email(self, anon_client):
        resp = anon_client.post(f'{API}/auth/password/reset-request/', {
            'email': '',
        }, format='json')
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# PasswordResetConfirmView — POST /api/v1/auth/password/reset-confirm/
# ═══════════════════════════════════════════════════════════════════════════

class TestPasswordResetConfirmView:

    def test_reset_confirm_success(self, anon_client, user):
        # First request reset to get a token
        resp = anon_client.post(f'{API}/auth/password/reset-request/', {
            'email': user.email,
        }, format='json')
        # Extract token from reset_link
        reset_link = resp.data['reset_link']
        token = reset_link.split('token=')[1]

        # Confirm reset
        resp = anon_client.post(f'{API}/auth/password/reset-confirm/', {
            'token': token,
            'new_password': 'ResetSecure789!',
        }, format='json')
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.check_password('ResetSecure789!')

    def test_reset_confirm_invalid_token(self, anon_client):
        resp = anon_client.post(f'{API}/auth/password/reset-confirm/', {
            'token': 'invalid-token-123',
            'new_password': 'SomePass123!',
        }, format='json')
        assert resp.status_code == 400

    def test_reset_confirm_empty_token(self, anon_client):
        resp = anon_client.post(f'{API}/auth/password/reset-confirm/', {
            'token': '',
            'new_password': 'SomePass123!',
        }, format='json')
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# UserViewSet.me — GET /api/v1/users/me/
# ═══════════════════════════════════════════════════════════════════════════

class TestUserViewSetMe:

    def test_get_me(self, auth_client, user):
        resp = auth_client.get(f'{API}/users/me/')
        assert resp.status_code == 200
        assert resp.data['username'] == 'testuser'
        assert resp.data['email'] == 'test@example.com'

    def test_get_me_anonymous_forbidden(self, anon_client):
        resp = anon_client.get(f'{API}/users/me/')
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# UserViewSet.register — POST /api/v1/users/register/
# ═══════════════════════════════════════════════════════════════════════════

class TestUserViewSetRegister:

    def test_register_success(self, anon_client):
        resp = anon_client.post(f'{API}/users/register/', {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'StrongPass123!',
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['username'] == 'newuser'
        assert User.objects.filter(username='newuser').exists()

    def test_register_missing_fields(self, anon_client):
        resp = anon_client.post(f'{API}/users/register/', {
            'username': 'newuser',
        }, format='json')
        assert resp.status_code == 400

    def test_register_short_username(self, anon_client):
        resp = anon_client.post(f'{API}/users/register/', {
            'username': 'ab',
            'email': 'short@example.com',
            'password': 'StrongPass123!',
        }, format='json')
        assert resp.status_code == 400

    def test_register_invalid_username_chars(self, anon_client):
        resp = anon_client.post(f'{API}/users/register/', {
            'username': 'bad user!',
            'email': 'bad@example.com',
            'password': 'StrongPass123!',
        }, format='json')
        assert resp.status_code == 400

    def test_register_invalid_email(self, anon_client):
        resp = anon_client.post(f'{API}/users/register/', {
            'username': 'gooduser',
            'email': 'not-an-email',
            'password': 'StrongPass123!',
        }, format='json')
        assert resp.status_code == 400

    def test_register_duplicate_username(self, anon_client, user):
        resp = anon_client.post(f'{API}/users/register/', {
            'username': user.username,
            'email': 'new@example.com',
            'password': 'StrongPass123!',
        }, format='json')
        assert resp.status_code == 400
        assert 'username' in resp.data

    def test_register_duplicate_email(self, anon_client, user):
        resp = anon_client.post(f'{API}/users/register/', {
            'username': 'newuser2',
            'email': user.email,
            'password': 'StrongPass123!',
        }, format='json')
        assert resp.status_code == 400
        assert 'email' in resp.data

    def test_register_weak_password(self, anon_client):
        resp = anon_client.post(f'{API}/users/register/', {
            'username': 'passuser',
            'email': 'pass@example.com',
            'password': '123',
        }, format='json')
        assert resp.status_code == 400
