import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock
from news.models import EmailVerification, PasswordResetToken

UA = {'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) TestClient/1.0'}

@pytest.fixture
def auth_client():
    client = APIClient(**UA)
    user = User.objects.create_user(username='normal_user', password='password123', email='user@test.com')
    client.force_authenticate(user=user)
    return client, user

@pytest.fixture
def admin_client():
    client = APIClient(**UA)
    admin = User.objects.create_superuser(username='super_admin', password='password123', email='admin@test.com')
    client.force_authenticate(user=admin)
    return client, admin

@pytest.fixture
def test_client():
    return APIClient(**UA)

@pytest.mark.django_db
class TestCurrentUserView:
    def test_get_current_user(self, auth_client):
        client, user = auth_client
        response = client.get('/api/v1/auth/user/')
        assert response.status_code == 200
        assert response.data['username'] == 'normal_user'
        assert response.data['email'] == 'user@test.com'

    def test_patch_current_user_info(self, auth_client):
        client, user = auth_client
        response = client.patch('/api/v1/auth/user/', {'first_name': 'NewFirst', 'last_name': 'NewLast'}, format='json')
        assert response.status_code == 200
        assert response.data['first_name'] == 'NewFirst'

    def test_patch_email_rejected(self, auth_client):
        client, user = auth_client
        response = client.patch('/api/v1/auth/user/', {'email': 'hacked@test.com'}, format='json')
        assert response.status_code == 400

@pytest.mark.django_db
class TestChangePasswordView:
    @patch('django_ratelimit.core.is_ratelimited', return_value=False)
    def test_change_password_success(self, mock_rate, auth_client):
        client, user = auth_client
        response = client.post('/api/v1/auth/password/change/', {
            'old_password': 'password123',
            'new_password1': 'StrongPass123!',
            'new_password2': 'StrongPass123!'
        }, format='json')
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password('StrongPass123!')

    @patch('django_ratelimit.core.is_ratelimited', return_value=False)
    def test_change_password_mismatch(self, mock_rate, auth_client):
        client, user = auth_client
        response = client.post('/api/v1/auth/password/change/', {
            'old_password': 'password123',
            'new_password1': 'StrongPass123!',
            'new_password2': 'DifferentPass123!'
        }, format='json')
        assert response.status_code == 400

@pytest.mark.django_db
class TestEmailVerificationFlow:
    def test_request_email_change(self, auth_client):
        client, user = auth_client
        response = client.post('/api/v1/auth/email/request-change/', {'new_email': 'new_valid@test.com'}, format='json')
        assert response.status_code == 200
        assert EmailVerification.objects.filter(user=user, new_email='new_valid@test.com').exists()

    def test_verify_email_change_success(self, auth_client):
        client, user = auth_client
        EmailVerification.objects.create(
            user=user, new_email='verified@test.com', code='123456',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        response = client.post('/api/v1/auth/email/verify-code/', {'code': '123456'}, format='json')
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.email == 'verified@test.com'

@pytest.mark.django_db
class TestPasswordResetFlow:
    def test_request_password_reset(self, test_client):
        User.objects.create_user(username='resetuser', email='reset@test.com', password='old')
        response = test_client.post('/api/v1/auth/password/reset-request/', {'email': 'reset@test.com'}, format='json')
        assert response.status_code == 200
        assert PasswordResetToken.objects.filter(user__email='reset@test.com').exists()

    def test_confirm_password_reset_success(self, test_client):
        user = User.objects.create_user(username='reset2', email='reset2@test.com', password='old')
        PasswordResetToken.objects.create(
            user=user, token='fake-uuid-123',
            expires_at=timezone.now() + timedelta(hours=1), ip_address='127.0.0.1'
        )
        response = test_client.post('/api/v1/auth/password/reset-confirm/', {
            'token': 'fake-uuid-123', 'new_password': 'NewStrongPassword123!'
        }, format='json')
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password('NewStrongPassword123!')

@pytest.mark.django_db
class TestUserRegistrationAndOAuth:
    @patch('django_ratelimit.core.is_ratelimited', return_value=False)
    def test_register_success(self, mock_rate, test_client):
        response = test_client.post('/api/v1/users/register/', {
            'username': 'newcoder',
            'email': 'newcoder@test.com',
            'password': 'StrongPassword123!'
        }, format='json')
        assert response.status_code == 201

    @patch('django_ratelimit.core.is_ratelimited', return_value=False)
    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_oauth_creation(self, mock_verify, mock_rate, test_client):
        mock_verify.return_value = {
            'email': 'oauth@google.com', 'name': 'Google User',
            'given_name': 'Google', 'family_name': 'User'
        }
        response = test_client.post('/api/v1/users/google_oauth/', {'credential': 'fake_token'}, format='json')
        assert response.status_code == 200
        assert response.data['created'] is True

@pytest.mark.django_db
class TestAdminUserManagement:
    def test_list_users_authorized(self, admin_client):
        client, admin = admin_client
        response = client.get('/api/v1/admin/users/')
        assert response.status_code == 200
        assert 'stats' in response.data

    def test_update_user_role(self, admin_client):
        client, _ = admin_client
        target = User.objects.create_user(username='target')
        response = client.patch(f'/api/v1/admin/users/{target.id}/', {'role': 'superuser'}, format='json')
        assert response.status_code == 200
        target.refresh_from_db()
        assert target.is_superuser is True

    def test_delete_user(self, admin_client):
        client, _ = admin_client
        target = User.objects.create_user(username='doomed')
        response = client.delete(f'/api/v1/admin/users/{target.id}/')
        assert response.status_code == 200
        assert not User.objects.filter(id=target.id).exists()
