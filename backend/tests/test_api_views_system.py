import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from unittest.mock import patch

from news.models import SiteSettings, AdminNotification, AdPlacement, ThemeAnalytics, AutomationSettings

UA = {'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) TestClient/1.0'}

@pytest.fixture
def admin_client():
    client = APIClient(**UA)
    admin = User.objects.create_superuser(username='super_admin', email='admin@test.com', password='pass')
    client.force_authenticate(user=admin)
    return client, admin

@pytest.fixture
def test_client():
    return APIClient(**UA)

@pytest.mark.django_db
class TestSiteSettingsViewSet:
    def test_list_site_settings(self, test_client):
        response = test_client.get('/api/v1/settings/')
        assert response.status_code == 200

    def test_update_site_settings_unauthorized(self, test_client):
        response = test_client.patch('/api/v1/settings/1/', {'site_name': 'Hacked'})
        assert response.status_code in [401, 403, 404, 405]

@pytest.mark.django_db
class TestCurrencyRatesView:
    @patch('news.api_views.system.http_requests.get')
    def test_get_currency_rates_fallback(self, mock_get, test_client):
        mock_get.side_effect = Exception("API Offline")
        from django.core.cache import cache
        cache.delete('currency_rates_usd')
        
        response = test_client.get('/api/v1/currency-rates/')
        assert response.status_code == 200

@pytest.mark.django_db
class TestAdminNotificationViewSet:
    def test_list_notifications_admin(self, admin_client):
        client, _ = admin_client
        response = client.get('/api/v1/notifications/')
        assert response.status_code == 200

@pytest.mark.django_db
class TestAdPlacementViewSet:
    def test_active_ads_public(self, test_client):
        response = test_client.get('/api/v1/ads/active/?position=header')
        assert response.status_code == 200

    def test_track_click(self, test_client):
        ad = AdPlacement.objects.create(position='sidebar', is_active=True, link='https://google.com')
        response = test_client.post(f'/api/v1/ads/{ad.id}/track-click/')
        assert response.status_code == 200

@pytest.mark.django_db
class TestThemeAnalyticsView:
    @patch('django_ratelimit.core.is_ratelimited', return_value=False)
    def test_post_theme_anonymous(self, mock_rate, test_client):
        response = test_client.post('/api/v1/site/theme-analytics/', {'theme': 'dark'}, format='json')
        assert response.status_code == 200
        assert ThemeAnalytics.objects.filter(theme='dark').exists()

@pytest.mark.django_db
class TestAutomationTriggerView:
    @patch('threading.Thread.start')
    def test_trigger_rss(self, mock_start, admin_client):
        client, _ = admin_client
        response = client.post('/api/v1/automation/trigger/rss/')
        assert response.status_code == 200
        mock_start.assert_called_once()
