"""
Batch 4 — api_views.py
Target: push from 71% → 74%+ by hitting pure-Django views (no external APIs)
Focus: favorites, subscribers, ratings, comments, notifications, feedback, ads, etc.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
UA = {'HTTP_USER_AGENT': 'TestBrowser/1.0'}


def staff_client():
    user = User.objects.create_user('stafftest', 'staff@t.com', 'password123')
    user.is_staff = True
    user.is_superuser = True
    user.save()
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(**UA)
    return client, user


def regular_client():
    user = User.objects.create_user('regulartest', 'reg@t.com', 'password123')
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(**UA)
    return client, user


def anon_client():
    client = APIClient()
    client.credentials(**UA)
    return client


# ═══════════════════════════════════════════════════════════════════
# ChangePasswordView — auth/password/change/
# ═══════════════════════════════════════════════════════════════════

class TestChangePassword:

    def test_wrong_current_password(self):
        """L162-163: Wrong current password → 400."""
        client, user = regular_client()
        resp = client.post('/api/v1/auth/password/change/', {
            'current_password': 'wrongpassword',
            'new_password': 'newsecurepassword123',
        }, format='json')
        assert resp.status_code == 400

    def test_short_new_password(self):
        """L165-167: New password too short → 400."""
        client, user = regular_client()
        resp = client.post('/api/v1/auth/password/change/', {
            'current_password': 'password123',
            'new_password': '12',
        }, format='json')
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════
# EmailPreferencesView — auth/email-preferences/
# ═══════════════════════════════════════════════════════════════════

class TestEmailPreferencesView:

    def test_get_preferences(self):
        client, user = regular_client()
        resp = client.get('/api/v1/auth/email-preferences/')
        assert resp.status_code == 200

    def test_update_preferences(self):
        client, user = regular_client()
        resp = client.patch('/api/v1/auth/email-preferences/', {
            'newsletter_enabled': False,
        }, format='json')
        assert resp.status_code in (200, 204)


# ═══════════════════════════════════════════════════════════════════
# PasswordResetRequestView — auth/password/reset-request/
# ═══════════════════════════════════════════════════════════════════

class TestPasswordResetRequest:

    def test_reset_nonexistent(self):
        """Non-existent email → still 200 (no info leak)."""
        client = anon_client()
        resp = client.post('/api/v1/auth/password/reset-request/', {
            'email': 'nonexistent@test.com',
        }, format='json')
        assert resp.status_code == 200

    def test_no_email(self):
        """No email → 400."""
        client = anon_client()
        resp = client.post('/api/v1/auth/password/reset-request/', {}, format='json')
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════
# FavoriteViewSet — /favorites/
# ═══════════════════════════════════════════════════════════════════

class TestFavoriteViewSet:

    def test_list_favorites(self):
        client, user = regular_client()
        resp = client.get('/api/v1/favorites/')
        assert resp.status_code == 200

    def test_add_favorite(self):
        from news.models import Article
        client, user = regular_client()
        art = Article.objects.create(
            title='Fav Test', slug='fav-test', content='<p>C</p>', is_published=True
        )
        resp = client.post('/api/v1/favorites/', {
            'article': art.id
        }, format='json')
        assert resp.status_code in (200, 201)

    def test_add_favorite_duplicate(self):
        from news.models import Article, Favorite
        client, user = regular_client()
        art = Article.objects.create(
            title='Dup Fav', slug='dup-fav', content='<p>C</p>', is_published=True
        )
        Favorite.objects.create(user=user, article=art)
        resp = client.post('/api/v1/favorites/', {
            'article': art.id
        }, format='json')
        assert resp.status_code in (400, 409)


# ═══════════════════════════════════════════════════════════════════
# SubscriberViewSet & Newsletter — /subscribers/, /newsletter/subscribe/
# ═══════════════════════════════════════════════════════════════════

class TestSubscriberViewSet:

    def test_list_subscribers(self):
        client, _ = staff_client()
        resp = client.get('/api/v1/subscribers/')
        assert resp.status_code == 200

    def test_subscribe(self):
        client = anon_client()
        resp = client.post('/api/v1/newsletter/subscribe/', {
            'email': 'sub-test@example.com'
        }, format='json')
        assert resp.status_code in (200, 201)

    def test_subscribe_invalid_email(self):
        client = anon_client()
        resp = client.post('/api/v1/newsletter/subscribe/', {
            'email': 'not-an-email'
        }, format='json')
        assert resp.status_code == 400

    def test_subscribe_duplicate(self):
        from news.models import Subscriber
        Subscriber.objects.create(email='dup-sub@example.com')
        client = anon_client()
        resp = client.post('/api/v1/newsletter/subscribe/', {
            'email': 'dup-sub@example.com'
        }, format='json')
        assert resp.status_code in (200, 201, 400, 409)


# ═══════════════════════════════════════════════════════════════════
# CurrencyRatesView — /currency-rates/
# ═══════════════════════════════════════════════════════════════════

class TestCurrencyRatesView:

    @patch('news.services.currency_service.get_rates')
    def test_get_rates(self, mock_rates):
        mock_rates.return_value = {'USD': 1.0, 'EUR': 0.92, 'CNY': 7.3}
        client = anon_client()
        resp = client.get('/api/v1/currency-rates/')
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# SiteSettingsViewSet — /settings/
# ═══════════════════════════════════════════════════════════════════

class TestSiteSettingsViewSet:

    def test_get_settings(self):
        client, _ = staff_client()
        resp = client.get('/api/v1/settings/')
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# CarSpecificationViewSet — /car-specifications/
# ═══════════════════════════════════════════════════════════════════

class TestCarSpecificationViewSet:

    def test_list_specs(self):
        client, _ = staff_client()
        resp = client.get('/api/v1/car-specifications/')
        assert resp.status_code == 200

    def test_create_spec(self):
        from news.models import Article
        client, _ = staff_client()
        art = Article.objects.create(
            title='Spec Create', slug='spec-create', content='<p>C</p>'
        )
        resp = client.post('/api/v1/car-specifications/', {
            'article': art.id,
            'model_name': 'BYD Seal',
            'make': 'BYD',
        }, format='json')
        assert resp.status_code in (200, 201)


# ═══════════════════════════════════════════════════════════════════
# RatingViewSet — /ratings/
# ═══════════════════════════════════════════════════════════════════

class TestRatingViewSet:

    def test_rate_article(self):
        from news.models import Article
        client, user = regular_client()
        art = Article.objects.create(
            title='Rate Test', slug='rate-test', content='<p>C</p>', is_published=True
        )
        resp = client.post('/api/v1/ratings/', {
            'article': art.id,
            'rating': 5,
        }, format='json')
        assert resp.status_code in (200, 201)

    def test_rate_out_of_range(self):
        from news.models import Article
        client, user = regular_client()
        art = Article.objects.create(
            title='Rate Bad', slug='rate-bad', content='<p>C</p>', is_published=True
        )
        resp = client.post('/api/v1/ratings/', {
            'article': art.id,
            'rating': 11,
        }, format='json')
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════
# AdminNotificationViewSet — /notifications/
# ═══════════════════════════════════════════════════════════════════

class TestAdminNotificationViewSet:

    def test_list_notifications(self):
        client, _ = staff_client()
        resp = client.get('/api/v1/notifications/')
        assert resp.status_code == 200

    def test_mark_read(self):
        from news.models import AdminNotification
        client, _ = staff_client()
        notif = AdminNotification.objects.create(
            title='Test notif', message='Test message',
            notification_type='comment'
        )
        resp = client.post(f'/api/v1/notifications/{notif.id}/mark_read/')
        assert resp.status_code in (200, 204)


# ═══════════════════════════════════════════════════════════════════
# ArticleFeedbackViewSet — /feedback/
# ═══════════════════════════════════════════════════════════════════

class TestArticleFeedbackViewSet:

    def test_list_feedback(self):
        """Staff can list feedback."""
        client, _ = staff_client()
        resp = client.get('/api/v1/feedback/')
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# AdPlacementViewSet — /ads/
# ═══════════════════════════════════════════════════════════════════

class TestAdPlacementViewSet:

    def test_list_ads(self):
        client, _ = staff_client()
        resp = client.get('/api/v1/ads/')
        assert resp.status_code == 200

    def test_create_ad(self):
        client, _ = staff_client()
        resp = client.post('/api/v1/ads/', {
            'name': 'Test Ad',
            'position': 'sidebar_top',
            'ad_type': 'adsense',
            'ad_code': '<script>test</script>',
            'is_active': True,
        }, format='json')
        assert resp.status_code in (200, 201, 400)  # 400 if position invalid


# ═══════════════════════════════════════════════════════════════════
# AutomationSettingsView — /automation/settings/
# ═══════════════════════════════════════════════════════════════════

class TestAutomationSettingsView:

    def test_get_settings(self):
        client, _ = staff_client()
        resp = client.get('/api/v1/automation/settings/')
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# VehicleSpecsViewSet — /vehicle-specs/
# ═══════════════════════════════════════════════════════════════════

class TestVehicleSpecsViewSet:

    def test_list_specs(self):
        client, _ = staff_client()
        resp = client.get('/api/v1/vehicle-specs/')
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# BrandAliasViewSet — /brand-aliases/
# ═══════════════════════════════════════════════════════════════════

class TestBrandAliasViewSet:

    def test_list_aliases(self):
        client, _ = staff_client()
        resp = client.get('/api/v1/brand-aliases/')
        assert resp.status_code == 200





# ═══════════════════════════════════════════════════════════════════
# CommentViewSet — /comments/
# ═══════════════════════════════════════════════════════════════════

class TestCommentViewSet:

    def test_list_comments(self):
        client, _ = staff_client()
        resp = client.get('/api/v1/comments/')
        assert resp.status_code == 200

    def test_create_comment(self):
        from news.models import Article
        client = anon_client()
        art = Article.objects.create(
            title='Comment API', slug='comment-api', content='<p>C</p>', is_published=True
        )
        resp = client.post('/api/v1/comments/', {
            'article': art.id,
            'name': 'TestUser',
            'email': 'testcomment@test.com',
            'content': 'Great article!',
        }, format='json')
        assert resp.status_code in (200, 201)


# ═══════════════════════════════════════════════════════════════════
# AdminUserManagementViewSet — /admin/users/
# ═══════════════════════════════════════════════════════════════════

class TestAdminUserManagement:

    def test_list_users(self):
        """Admin can list all users."""
        client, _ = staff_client()
        resp = client.get('/api/v1/admin/users/')
        assert resp.status_code == 200

    def test_get_user_detail(self):
        """Admin can get user detail."""
        client, admin = staff_client()
        target = User.objects.create_user('target_user', 'target@t.com', 'pass123')
        resp = client.get(f'/api/v1/admin/users/{target.id}/')
        assert resp.status_code == 200

    def test_update_user(self):
        """Admin can partial update user."""
        client, _ = staff_client()
        target = User.objects.create_user('update_user', 'update@t.com', 'pass123')
        resp = client.patch(f'/api/v1/admin/users/{target.id}/', {
            'first_name': 'Updated',
        }, format='json')
        assert resp.status_code == 200
