"""
Tests for api_views.py — Batch 4: Newsletter, Currency, Ads, BrandAlias
Covers: NewsletterSubscribeView, SubscriberViewSet (send/export/bulk_delete),
        CurrencyRatesView, AdPlacementViewSet, BrandAliasViewSet
"""
import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from django.contrib.auth.models import User

pytestmark = pytest.mark.django_db

API = '/api/v1'
UA = {'HTTP_USER_AGENT': 'TestBrowser/1.0'}


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username='staffnl', email='staffnl@test.com',
        password='Pass123!', is_staff=True,
    )


@pytest.fixture
def staff_client(staff_user):
    client = APIClient(**UA)
    client.force_authenticate(user=staff_user)
    return client


@pytest.fixture
def anon_client():
    return APIClient(**UA)


@pytest.fixture
def newsletter_subscriber(db):
    from news.models import NewsletterSubscriber
    return NewsletterSubscriber.objects.create(
        email='sub@test.com', is_active=True,
    )


@pytest.fixture
def ad_placement(db):
    from news.models import AdPlacement
    return AdPlacement.objects.create(
        name='Header Ad', position='header', ad_type='banner',
        link='https://example.com', is_active=True, priority=10,
    )


@pytest.fixture
def brand_alias(db):
    from news.models import BrandAlias
    return BrandAlias.objects.create(
        canonical_name='BMW', alias='Bayerische Motoren Werke',
    )


# ═══════════════════════════════════════════════════════════════════════════
# NewsletterSubscribeView — POST /api/v1/newsletter/subscribe/
# ═══════════════════════════════════════════════════════════════════════════

class TestNewsletterSubscribeView:

    @patch('news.email_service.email_service.send_newsletter_welcome', return_value=True)
    def test_subscribe_new(self, mock_email, anon_client):
        resp = anon_client.post(f'{API}/newsletter/subscribe/', {
            'email': 'new@newsletter.com',
        }, format='json')
        assert resp.status_code == 201
        assert 'subscribed' in resp.data['message'].lower()

    @patch('news.email_service.email_service.send_newsletter_welcome', return_value=True)
    def test_subscribe_duplicate(self, mock_email, anon_client, newsletter_subscriber):
        resp = anon_client.post(f'{API}/newsletter/subscribe/', {
            'email': newsletter_subscriber.email,
        }, format='json')
        assert resp.status_code == 200
        assert 'already' in resp.data['message'].lower()

    def test_subscribe_empty_email(self, anon_client):
        resp = anon_client.post(f'{API}/newsletter/subscribe/', {
            'email': '',
        }, format='json')
        assert resp.status_code == 400

    def test_subscribe_invalid_email(self, anon_client):
        resp = anon_client.post(f'{API}/newsletter/subscribe/', {
            'email': 'not-email',
        }, format='json')
        assert resp.status_code == 400

    @patch('news.email_service.email_service.send_newsletter_welcome', return_value=True)
    def test_resubscribe_inactive(self, mock_email, anon_client, newsletter_subscriber):
        newsletter_subscriber.is_active = False
        newsletter_subscriber.save()
        resp = anon_client.post(f'{API}/newsletter/subscribe/', {
            'email': newsletter_subscriber.email,
        }, format='json')
        assert resp.status_code == 200
        assert 'resubscribed' in resp.data['message'].lower()
        newsletter_subscriber.refresh_from_db()
        assert newsletter_subscriber.is_active is True


# ═══════════════════════════════════════════════════════════════════════════
# SubscriberViewSet Extended — send_newsletter, export_csv, bulk_delete
# ═══════════════════════════════════════════════════════════════════════════

class TestSubscriberExtendedActions:

    @patch('django.core.mail.send_mass_mail', return_value=1)
    def test_send_newsletter(self, mock_mail, staff_client, newsletter_subscriber):
        resp = staff_client.post(f'{API}/subscribers/send_newsletter/', {
            'subject': 'Test Newsletter',
            'message': 'Hello subscribers!',
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['count'] == 1

    def test_send_newsletter_missing_subject(self, staff_client, newsletter_subscriber):
        resp = staff_client.post(f'{API}/subscribers/send_newsletter/', {
            'message': 'No subject',
        }, format='json')
        assert resp.status_code == 400

    def test_export_csv(self, staff_client, newsletter_subscriber):
        resp = staff_client.get(f'{API}/subscribers/export_csv/')
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'text/csv'
        assert b'Email' in resp.content

    def test_bulk_delete(self, staff_client, newsletter_subscriber):
        resp = staff_client.post(f'{API}/subscribers/bulk_delete/', {
            'ids': [newsletter_subscriber.id],
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['count'] == 1

    def test_bulk_delete_no_ids(self, staff_client):
        resp = staff_client.post(f'{API}/subscribers/bulk_delete/', {
            'ids': [],
        }, format='json')
        assert resp.status_code == 400

    def test_newsletter_history(self, staff_client):
        resp = staff_client.get(f'{API}/subscribers/newsletter_history/')
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# CurrencyRatesView — GET /api/v1/currency-rates/
# ═══════════════════════════════════════════════════════════════════════════

class TestCurrencyRatesView:

    @patch('news.api_views.http_requests.get')
    def test_get_rates_success(self, mock_get, anon_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'result': 'success',
            'rates': {'EUR': 0.91, 'CNY': 7.3, 'GBP': 0.78, 'JPY': 150.0},
            'time_last_update_utc': '2026-02-21'
        }
        mock_get.return_value = mock_resp

        resp = anon_client.get(f'{API}/currency-rates/')
        assert resp.status_code == 200
        assert 'EUR' in resp.data

    @patch('news.api_views.http_requests.get', side_effect=Exception('Timeout'))
    def test_get_rates_fallback(self, mock_get, anon_client):
        from django.core.cache import cache
        cache.clear()  # Clear cache_page cached response
        resp = anon_client.get(f'{API}/currency-rates/')
        assert resp.status_code == 200
        assert resp.data['updated_at'] == 'fallback'
        assert resp.data['EUR'] == 0.92


# ═══════════════════════════════════════════════════════════════════════════
# AdPlacementViewSet — CRUD + actions
# ═══════════════════════════════════════════════════════════════════════════

class TestAdPlacementViewSet:

    def test_list_ads_admin(self, staff_client, ad_placement):
        resp = staff_client.get(f'{API}/ads/')
        assert resp.status_code == 200

    def test_create_ad(self, staff_client):
        resp = staff_client.post(f'{API}/ads/', {
            'name': 'Sidebar Ad', 'position': 'sidebar',
            'ad_type': 'banner', 'link': 'https://ad.com',
        }, format='json')
        assert resp.status_code == 201

    def test_active_ads(self, anon_client, ad_placement):
        resp = anon_client.get(f'{API}/ads/active/', {'position': 'header'})
        assert resp.status_code == 200
        assert len(resp.data['results']) >= 1

    def test_active_ads_no_position(self, anon_client):
        resp = anon_client.get(f'{API}/ads/active/')
        assert resp.status_code == 200
        assert resp.data['results'] == []

    def test_track_click(self, anon_client, ad_placement):
        resp = anon_client.post(f'{API}/ads/{ad_placement.id}/track-click/')
        assert resp.status_code == 200

    def test_delete_ad(self, staff_client, ad_placement):
        resp = staff_client.delete(f'{API}/ads/{ad_placement.id}/')
        assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════
# BrandAliasViewSet — CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestBrandAliasViewSet:

    def test_list_aliases(self, staff_client, brand_alias):
        resp = staff_client.get(f'{API}/brand-aliases/')
        assert resp.status_code == 200

    def test_create_alias(self, staff_client):
        resp = staff_client.post(f'{API}/brand-aliases/', {
            'canonical_name': 'Mercedes-Benz', 'alias': 'MB',
        }, format='json')
        assert resp.status_code == 201

    def test_delete_alias(self, staff_client, brand_alias):
        resp = staff_client.delete(f'{API}/brand-aliases/{brand_alias.id}/')
        assert resp.status_code == 204

    def test_anonymous_forbidden(self, anon_client):
        resp = anon_client.get(f'{API}/brand-aliases/')
        assert resp.status_code in (401, 403)
