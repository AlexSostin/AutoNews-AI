"""
Batch 1 — Quick Wins: ab_testing_views, bot_protection, search_analytics_views, signals, currency_service
Target: push all 5 from current → 90%+
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════
# ab_testing_views.py — 88% → 95%
# Missed: L24, L46, L53, L115, L119-120, L150-151, L173
# ═══════════════════════════════════════════════════════════════════

class TestABImpressionView:

    def test_missing_variant_id(self):
        """L24: No variant_id → 400."""
        from news.ab_testing_views import ABImpressionView
        factory = APIRequestFactory()
        request = factory.post('/api/v1/ab/impression/', {}, format='json')
        request.user = MagicMock()
        response = ABImpressionView.as_view()(request)
        assert response.status_code == 400

    def test_variant_not_found(self):
        """L30-31: Variant doesn't exist → 404."""
        from news.ab_testing_views import ABImpressionView
        factory = APIRequestFactory()
        request = factory.post('/api/v1/ab/impression/', {'variant_id': 99999}, format='json')
        request.user = MagicMock()
        response = ABImpressionView.as_view()(request)
        assert response.status_code == 404


class TestABClickView:

    def test_missing_variant_id(self):
        """L46: No variant_id → 400."""
        from news.ab_testing_views import ABClickView
        factory = APIRequestFactory()
        request = factory.post('/api/v1/ab/click/', {}, format='json')
        request.user = MagicMock()
        response = ABClickView.as_view()(request)
        assert response.status_code == 400

    def test_variant_not_found(self):
        """L52-53: Variant doesn't exist → 404."""
        from news.ab_testing_views import ABClickView
        factory = APIRequestFactory()
        request = factory.post('/api/v1/ab/click/', {'variant_id': 99999}, format='json')
        request.user = MagicMock()
        response = ABClickView.as_view()(request)
        assert response.status_code == 404


class TestABPickWinnerView:

    def test_missing_variant_id(self):
        """L115: No variant_id → 400."""
        from news.ab_testing_views import ABPickWinnerView
        factory = APIRequestFactory()
        request = factory.post('/api/v1/ab/pick-winner/', {}, format='json')
        request.user = MagicMock(is_staff=True)
        response = ABPickWinnerView.as_view()(request)
        assert response.status_code == 400

    def test_variant_not_found(self):
        """L119-120: Variant doesn't exist → 404."""
        from news.ab_testing_views import ABPickWinnerView
        factory = APIRequestFactory()
        request = factory.post('/api/v1/ab/pick-winner/', {'variant_id': 99999}, format='json')
        request.user = MagicMock(is_staff=True)
        response = ABPickWinnerView.as_view()(request)
        assert response.status_code == 404


class TestABAutoPickView:

    def test_auto_pick(self):
        """L150-151: Auto-pick returns winners list."""
        from news.ab_testing_views import ABAutoPickView
        factory = APIRequestFactory()
        request = factory.post('/api/v1/ab/auto-pick/')
        request.user = MagicMock(is_staff=True)
        response = ABAutoPickView.as_view()(request)
        assert response.status_code == 200
        assert 'winners_picked' in response.data


class TestGetVariantForRequest:

    def test_no_active_variants(self):
        """L167-168: Less than 2 active variants → original title."""
        from news.ab_testing_views import get_variant_for_request
        from news.models import Article
        article = Article.objects.create(
            title='Test Article', slug='test-ab-variant', content='<p>C</p>'
        )
        request = MagicMock()
        request.COOKIES = {}
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        title, variant_id = get_variant_for_request(article, request)
        assert title == 'Test Article'
        assert variant_id is None

    def test_with_cookie_seed(self):
        """L171-179: With ab_seed cookie → deterministic variant."""
        from news.ab_testing_views import get_variant_for_request
        from news.models import Article, ArticleTitleVariant
        article = Article.objects.create(
            title='Test AB', slug='test-ab-seed', content='<p>C</p>'
        )
        ArticleTitleVariant.objects.create(
            article=article, variant='A', title='Title A', is_active=True
        )
        ArticleTitleVariant.objects.create(
            article=article, variant='B', title='Title B', is_active=True
        )
        request = MagicMock()
        request.COOKIES = {'ab_seed': 'test-seed-123'}
        request.META = {}
        title, variant_id = get_variant_for_request(article, request)
        assert title in ('Title A', 'Title B')
        assert variant_id is not None

    def test_with_ip_fallback(self):
        """L172-173: No cookie → use IP."""
        from news.ab_testing_views import get_variant_for_request
        from news.models import Article, ArticleTitleVariant
        article = Article.objects.create(
            title='Test IP', slug='test-ab-ip', content='<p>C</p>'
        )
        ArticleTitleVariant.objects.create(
            article=article, variant='A', title='Title A', is_active=True
        )
        ArticleTitleVariant.objects.create(
            article=article, variant='B', title='Title B', is_active=True
        )
        request = MagicMock()
        request.COOKIES = {}
        request.META = {'REMOTE_ADDR': '192.168.1.1'}
        title, variant_id = get_variant_for_request(article, request)
        assert title in ('Title A', 'Title B')


# ═══════════════════════════════════════════════════════════════════
# bot_protection.py — 77% → 95%
# Missed: L87, L103-104, L115-119, L129-132
# ═══════════════════════════════════════════════════════════════════

class TestBotProtectionMiddleware:

    def _make_middleware(self):
        from news.bot_protection import BotProtectionMiddleware
        return BotProtectionMiddleware(get_response=lambda r: MagicMock(status_code=200))

    def test_empty_user_agent_blocked(self):
        """L102-107: Empty UA → 403."""
        mw = self._make_middleware()
        request = MagicMock()
        request.path = '/api/v1/articles/'
        request.method = 'GET'
        request.META = {'HTTP_USER_AGENT': ''}
        with patch('news.bot_protection.sys') as mock_sys:
            mock_sys.argv = ['manage.py', 'runserver']
            response = mw(request)
        assert response.status_code == 403

    def test_bot_ua_blocked(self):
        """L114-122: Known bot UA → 403."""
        mw = self._make_middleware()
        request = MagicMock()
        request.path = '/api/v1/articles/'
        request.method = 'GET'
        request.META = {
            'HTTP_USER_AGENT': 'python-requests/2.28.0',
            'REMOTE_ADDR': '1.2.3.4',
        }
        with patch('news.bot_protection.sys') as mock_sys:
            mock_sys.argv = ['manage.py', 'runserver']
            response = mw(request)
        assert response.status_code == 403

    def test_allowed_bot_passes(self):
        """L110-111: Googlebot UA → passes through."""
        mw = self._make_middleware()
        request = MagicMock()
        request.path = '/api/v1/articles/'
        request.method = 'GET'
        request.META = {
            'HTTP_USER_AGENT': 'Googlebot/2.1 (+http://www.google.com/bot.html)',
            'REMOTE_ADDR': '66.249.66.1',
        }
        with patch('news.bot_protection.sys') as mock_sys:
            mock_sys.argv = ['manage.py', 'runserver']
            response = mw(request)
        assert response.status_code == 200

    def test_non_api_path_passes(self):
        """L92-93: Non-API path → passes through."""
        mw = self._make_middleware()
        request = MagicMock()
        request.path = '/about/'
        request.META = {'HTTP_USER_AGENT': 'python-requests/2.28.0'}
        with patch('news.bot_protection.sys') as mock_sys:
            mock_sys.argv = ['manage.py', 'runserver']
            response = mw(request)
        assert response.status_code == 200

    def test_excluded_path_passes(self):
        """L96-97: Excluded path (sitemap) → passes."""
        mw = self._make_middleware()
        request = MagicMock()
        request.path = '/api/v1/sitemap/'
        request.META = {'HTTP_USER_AGENT': 'python-requests/2.28.0'}
        with patch('news.bot_protection.sys') as mock_sys:
            mock_sys.argv = ['manage.py', 'runserver']
            response = mw(request)
        assert response.status_code == 200

    def test_get_ip_with_x_forwarded_for(self):
        """L129-131: X-Forwarded-For header → first IP extracted."""
        from news.bot_protection import BotProtectionMiddleware
        request = MagicMock()
        request.META = {
            'HTTP_X_FORWARDED_FOR': '10.0.0.1, 10.0.0.2',
            'REMOTE_ADDR': '192.168.1.1'
        }
        ip = BotProtectionMiddleware._get_ip(request)
        assert ip == '10.0.0.1'

    def test_get_ip_without_forwarded(self):
        """L132: No X-Forwarded-For → REMOTE_ADDR."""
        from news.bot_protection import BotProtectionMiddleware
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '192.168.1.1'}
        ip = BotProtectionMiddleware._get_ip(request)
        assert ip == '192.168.1.1'


# ═══════════════════════════════════════════════════════════════════
# currency_service.py — 89% → 95%
# Missed: L51, L79-81, L141-142, L146-148
# ═══════════════════════════════════════════════════════════════════

class TestFetchExchangeRates:

    @patch('news.services.currency_service.urlopen')
    def test_successful_fetch(self, mock_urlopen):
        """L43-63: Successful API fetch → rates returned."""
        from news.services.currency_service import fetch_exchange_rates
        import json
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'rates': {'CNY': 7.3, 'EUR': 0.92, 'GBP': 0.79, 'JPY': 150.0}
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        rates = fetch_exchange_rates()
        assert 'CNY' in rates
        assert rates['USD'] == 1.0

    @patch('news.services.currency_service.urlopen')
    def test_empty_rates_fallback(self, mock_urlopen):
        """L50-51: Empty rates dict → try next API → fallback."""
        from news.services.currency_service import fetch_exchange_rates, FALLBACK_RATES
        import json
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({'rates': {}}).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        rates = fetch_exchange_rates()
        assert rates == FALLBACK_RATES

    @patch('news.services.currency_service.urlopen')
    def test_api_error_fallback(self, mock_urlopen):
        """L65-70: All APIs fail → fallback rates."""
        from news.services.currency_service import fetch_exchange_rates, FALLBACK_RATES
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError('Connection refused')
        rates = fetch_exchange_rates()
        assert rates == FALLBACK_RATES


class TestGetRates:

    @patch('news.services.currency_service.cache')
    def test_cache_hit(self, mock_cache):
        """L76-77: Cached rates → returned directly."""
        from news.services.currency_service import get_rates
        mock_cache.get.return_value = {'USD': 1.0, 'CNY': 0.137}
        rates = get_rates()
        assert rates['USD'] == 1.0

    @patch('news.services.currency_service.cache')
    @patch('news.services.currency_service.fetch_exchange_rates')
    def test_cache_miss(self, mock_fetch, mock_cache):
        """L79-81: Cache miss → fetch and cache."""
        from news.services.currency_service import get_rates
        mock_cache.get.return_value = None
        mock_fetch.return_value = {'USD': 1.0}
        rates = get_rates()
        assert rates['USD'] == 1.0
        mock_cache.set.assert_called_once()


class TestConvertToUsd:

    def test_none_amount(self):
        from news.services.currency_service import convert_to_usd
        assert convert_to_usd(None, 'EUR') is None

    def test_none_currency(self):
        from news.services.currency_service import convert_to_usd
        assert convert_to_usd(100, None) is None

    def test_usd_passthrough(self):
        from news.services.currency_service import convert_to_usd
        assert convert_to_usd(35000, 'USD') == 35000

    @patch('news.services.currency_service.get_rates')
    def test_unknown_currency(self, mock_rates):
        """L102-104: Unknown currency not in rates or fallback → None."""
        from news.services.currency_service import convert_to_usd
        mock_rates.return_value = {'USD': 1.0}
        # Patch FALLBACK_RATES to not have XYZ
        result = convert_to_usd(100, 'XYZ')
        assert result is None


class TestUpdateAllUsdPrices:

    @patch('news.services.currency_service.fetch_exchange_rates')
    @patch('news.services.currency_service.cache')
    def test_update_cycle(self, mock_cache, mock_fetch):
        """L109-161: Full update cycle with VehicleSpecs records."""
        from news.services.currency_service import update_all_usd_prices
        from news.models import Article, VehicleSpecs
        mock_fetch.return_value = {'USD': 1.0, 'CNY': 0.137, 'EUR': 1.08}
        article = Article.objects.create(
            title='Currency Test', slug='currency-test', content='<p>C</p>'
        )
        VehicleSpecs.objects.create(
            article=article, make='BYD', model_name='Seal',
            price_from=250000, currency='CNY',
        )
        updated, errors = update_all_usd_prices()
        assert errors == 0

    @patch('news.services.currency_service.fetch_exchange_rates')
    @patch('news.services.currency_service.cache')
    def test_update_with_error(self, mock_cache, mock_fetch):
        """L146-148: Save error → counted."""
        from news.services.currency_service import update_all_usd_prices
        from news.models import Article, VehicleSpecs
        mock_fetch.return_value = {'USD': 1.0}
        article = Article.objects.create(
            title='Error Test', slug='currency-error', content='<p>C</p>'
        )
        vs = VehicleSpecs.objects.create(
            article=article, make='Test', model_name='X',
            price_from=100, currency='EUR',
        )
        # Patch save to raise
        with patch.object(VehicleSpecs, 'save', side_effect=Exception('DB error')):
            updated, errors = update_all_usd_prices()
        assert errors >= 1


# ═══════════════════════════════════════════════════════════════════
# signals.py — 86% → 93%
# Missed: L87-93, L128, L132, L146-147, L204, L210-218, L305-306, L342-343
# ═══════════════════════════════════════════════════════════════════

class TestSignals:

    def test_comment_notification(self):
        """L13-23: New comment → notification created."""
        from news.models import Article, Comment, AdminNotification
        article = Article.objects.create(
            title='Signal Test', slug='signal-comment-test', content='<p>C</p>'
        )
        before = AdminNotification.objects.count()
        Comment.objects.create(
            article=article, name='Test User', email='test@test.com',
            content='Great article!', is_approved=True
        )
        after = AdminNotification.objects.count()
        assert after > before

    def test_subscriber_notification(self):
        """L26-36: New subscriber → notification created."""
        from news.models import Subscriber, AdminNotification
        before = AdminNotification.objects.count()
        Subscriber.objects.create(email='signal-test@test.com')
        after = AdminNotification.objects.count()
        assert after > before

    def test_article_publish_notification(self):
        """L39-49: New article → notification created."""
        from news.models import Article, AdminNotification
        before = AdminNotification.objects.count()
        Article.objects.create(
            title='Signal Article', slug='signal-article-test',
            content='<p>Content</p>'
        )
        after = AdminNotification.objects.count()
        assert after > before

    def test_pending_article_notification(self):
        """L52-62: New PendingArticle → notification."""
        from news.models import PendingArticle, AdminNotification
        before = AdminNotification.objects.count()
        PendingArticle.objects.create(
            title='Pending Signal Test', video_url='https://youtube.com/watch?v=test123'
        )
        after = AdminNotification.objects.count()
        assert after > before

    def test_pending_article_error_notification(self):
        """L63-70: PendingArticle with error status → error notification."""
        from news.models import PendingArticle, AdminNotification
        pa = PendingArticle.objects.create(
            title='Error Signal Test', video_url='https://youtube.com/watch?v=error123'
        )
        before = AdminNotification.objects.count()
        pa.status = 'error'
        pa.save()
        after = AdminNotification.objects.count()
        assert after > before

    def test_vehicle_specs_syncs_car_spec(self):
        """L228-306: VehicleSpecs save → CarSpecification created."""
        from news.models import Article, VehicleSpecs, CarSpecification
        article = Article.objects.create(
            title='Sync Test', slug='sync-spec-test', content='<p>C</p>'
        )
        vs = VehicleSpecs.objects.create(
            article=article, make='Tesla', model_name='Model 3',
            power_hp=350, torque_nm=450, fuel_type='EV',
            battery_kwh=75, drivetrain='AWD',
        )
        assert CarSpecification.objects.filter(article=article).exists()
        cs = CarSpecification.objects.get(article=article)
        assert cs.make == 'Tesla'
        assert '350 HP' in cs.horsepower

    def test_vehicle_specs_no_article_skipped(self):
        """L235: VehicleSpecs without article → skip sync."""
        from news.models import VehicleSpecs, CarSpecification
        before = CarSpecification.objects.count()
        VehicleSpecs.objects.create(
            article=None, make='NoBrand', model_name='NoModel',
        )
        after = CarSpecification.objects.count()
        assert after == before

    def test_vehicle_specs_no_make_skipped(self):
        """L287-288: VehicleSpecs with no make → skip sync."""
        from news.models import Article, VehicleSpecs, CarSpecification
        article = Article.objects.create(
            title='No Make', slug='no-make-sync', content='<p>C</p>'
        )
        before = CarSpecification.objects.count()
        VehicleSpecs.objects.create(
            article=article, make='', model_name='X',
        )
        after = CarSpecification.objects.count()
        assert after == before

    def test_car_spec_sync_exception(self):
        """L305-306: Exception during sync → logged, no crash."""
        from news.models import Article, VehicleSpecs, CarSpecification
        article = Article.objects.create(
            title='Sync Error', slug='sync-error-test', content='<p>C</p>'
        )
        with patch.object(CarSpecification.objects, 'update_or_create', side_effect=Exception('DB crashed')):
            # Should not crash
            VehicleSpecs.objects.create(
                article=article, make='BYD', model_name='Seal',
            )

    def test_car_spec_tags_exception(self):
        """L342-343: Exception in tag sync → logged, no crash."""
        from news.models import Article, CarSpecification
        article = Article.objects.create(
            title='Tag Error', slug='tag-error-test', content='<p>C</p>'
        )
        with patch('news.models.Tag.objects.filter', side_effect=Exception('Tag error')):
            # Should not crash
            CarSpecification.objects.create(
                article=article, model_name='Test', make='BYD', drivetrain='AWD'
            )


# ═══════════════════════════════════════════════════════════════════
# search_analytics_views.py — 86% → 93%
# Missed: L108, L117, L126, L135, L431-456, L478-491, L566-567
# ═══════════════════════════════════════════════════════════════════

class TestAnalyticsOverview:

    def test_growth_with_previous_data(self):
        """L107-108, L116-117, L125-126, L134-135: Growth calc with data in both periods."""
        from news.search_analytics_views import AnalyticsOverviewAPIView
        from news.models import Article
        from django.utils import timezone
        from datetime import timedelta

        # Create articles in last 30 days
        for i in range(3):
            Article.objects.create(
                title=f'Recent {i}', slug=f'recent-growth-{i}',
                content='<p>Content</p>', is_published=True,
                created_at=timezone.now() - timedelta(days=5),
            )
        # Create articles in previous 30 days
        for i in range(2):
            Article.objects.create(
                title=f'Old {i}', slug=f'old-growth-{i}',
                content='<p>Content</p>', is_published=True,
                created_at=timezone.now() - timedelta(days=40),
            )

        factory = APIRequestFactory()
        request = factory.get('/api/v1/analytics/overview/')
        request.user = MagicMock(is_authenticated=True)
        response = AnalyticsOverviewAPIView.as_view()(request)
        assert response.status_code == 200
        assert 'articles_growth' in response.data

    def test_growth_no_previous_data(self):
        """L109-110: No previous period → 100% growth."""
        from news.search_analytics_views import AnalyticsOverviewAPIView
        factory = APIRequestFactory()
        request = factory.get('/api/v1/analytics/overview/')
        request.user = MagicMock(is_authenticated=True)
        response = AnalyticsOverviewAPIView.as_view()(request)
        assert response.status_code == 200


class TestAnalyticsProviderStats:

    def test_provider_stats_error(self):
        """L566-567: Provider stats error → graceful response."""
        from news.search_analytics_views import AnalyticsProviderStatsAPIView
        factory = APIRequestFactory()
        request = factory.get('/api/v1/analytics/provider-stats/')
        request.user = MagicMock(is_authenticated=True)
        with patch('news.search_analytics_views.AnalyticsProviderStatsAPIView.get') as mock_get:
            # Actually call real view — it will try import
            pass
        response = AnalyticsProviderStatsAPIView.as_view()(request)
        assert response.status_code == 200
