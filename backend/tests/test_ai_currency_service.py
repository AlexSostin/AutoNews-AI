"""
Tests for ai_engine currency_service — fetch, cache, prompt formatting.
All external HTTP and Redis calls are mocked.
"""
import json
import pytest
from unittest.mock import patch, MagicMock


# ═══════════════════════════════════════════════════════════════════════════
# fetch_and_cache_rates — external HTTP fetch + Redis caching
# ═══════════════════════════════════════════════════════════════════════════

class TestFetchAndCacheRates:

    @patch('ai_engine.modules.currency_service.cache')
    @patch('ai_engine.modules.currency_service.requests')
    def test_successful_fetch_and_cache(self, mock_requests, mock_cache):
        """Fetches real rates from API and stores in Redis cache."""
        from ai_engine.modules.currency_service import fetch_and_cache_rates, CACHE_KEY

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'result': 'success',
            'rates': {'CNY': 7.23, 'EUR': 0.93, 'KRW': 1340.0, 'JPY': 149.5}
        }
        mock_requests.get.return_value = mock_response

        result = fetch_and_cache_rates()

        assert result is True
        assert mock_cache.set.called
        call_args = mock_cache.set.call_args[0]
        assert call_args[0] == CACHE_KEY  # First arg is the cache key

    @patch('ai_engine.modules.currency_service.cache')
    @patch('ai_engine.modules.currency_service.requests')
    def test_fetch_failure_returns_false(self, mock_requests, mock_cache):
        """Network failure returns False and doesn't crash."""
        import requests as real_requests
        from ai_engine.modules.currency_service import fetch_and_cache_rates

        mock_requests.RequestException = real_requests.RequestException
        mock_requests.get.side_effect = real_requests.ConnectionError("timeout")

        result = fetch_and_cache_rates()
        assert result is False
        mock_cache.set.assert_not_called()

    @patch('ai_engine.modules.currency_service.cache')
    @patch('ai_engine.modules.currency_service.requests')
    def test_bad_api_result_uses_fallback(self, mock_requests, mock_cache):
        """API returns error result — returns False."""
        from ai_engine.modules.currency_service import fetch_and_cache_rates

        mock_response = MagicMock()
        mock_response.json.return_value = {'result': 'error', 'error-type': 'invalid-key'}
        mock_requests.get.return_value = mock_response

        result = fetch_and_cache_rates()
        assert result is False

    @patch('ai_engine.modules.currency_service.cache')
    @patch('ai_engine.modules.currency_service.requests')
    def test_only_target_currencies_cached(self, mock_requests, mock_cache):
        """Only currencies in TARGET_CURRENCIES are stored in cache."""
        from ai_engine.modules.currency_service import fetch_and_cache_rates, TARGET_CURRENCIES

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'result': 'success',
            'rates': {'CNY': 7.23, 'FAKECOIN': 999.0, 'EUR': 0.93}
        }
        mock_requests.get.return_value = mock_response

        fetch_and_cache_rates()

        call_args = mock_cache.set.call_args[0]
        cached_data = call_args[1]
        stored_rates = cached_data['rates']
        assert 'FAKECOIN' not in stored_rates
        assert all(code in TARGET_CURRENCIES for code in stored_rates)


# ═══════════════════════════════════════════════════════════════════════════
# get_rates_for_prompt — formats cached rates as AI prompt text
# ═══════════════════════════════════════════════════════════════════════════

class TestGetRatesForPrompt:

    @patch('ai_engine.modules.currency_service.cache')
    def test_returns_prompt_string_from_cache(self, mock_cache):
        """Returns a human-readable string when rates are cached."""
        from ai_engine.modules.currency_service import get_rates_for_prompt

        mock_cache.get.return_value = {
            'rates': {'CNY': 7.23, 'EUR': 0.93, 'KRW': 1340.0},
            'updated_at': '2026-03-11 12:00',
            'base': 'USD',
        }

        result = get_rates_for_prompt()
        assert isinstance(result, str)
        assert 'CNY' in result
        assert 'USD' in result

    @patch('ai_engine.modules.currency_service.cache')
    def test_returns_fallback_string_when_no_cache(self, mock_cache):
        """Returns a fallback string with hardcoded rates when cache is empty."""
        from ai_engine.modules.currency_service import get_rates_for_prompt

        mock_cache.get.return_value = None

        result = get_rates_for_prompt()
        assert isinstance(result, str)
        assert len(result) > 30  # Should have some content
        assert 'CNY' in result  # Fallback includes CNY

    @patch('ai_engine.modules.currency_service.cache')
    def test_prompt_says_not_to_guess(self, mock_cache):
        """Prompt instructs AI not to guess exchange rates."""
        from ai_engine.modules.currency_service import get_rates_for_prompt

        mock_cache.get.return_value = {
            'rates': {'CNY': 7.2},
            'updated_at': '2026-03-11 00:00',
            'base': 'USD',
        }

        result = get_rates_for_prompt()
        assert 'NOT' in result.upper() or 'Do NOT' in result or 'not' in result.lower()

    @patch('ai_engine.modules.currency_service.cache')
    def test_prompt_includes_exchange_rate_header(self, mock_cache):
        """Prompt starts with a clear header about exchange rates."""
        from ai_engine.modules.currency_service import get_rates_for_prompt

        mock_cache.get.return_value = {
            'rates': {'CNY': 7.2, 'EUR': 0.93},
            'updated_at': '2026-03-11 12:00',
            'base': 'USD',
        }

        result = get_rates_for_prompt()
        assert 'EXCHANGE' in result.upper() or 'RATES' in result.upper()


# ═══════════════════════════════════════════════════════════════════════════
# get_cached_rates — retrieves cached rates dict
# ═══════════════════════════════════════════════════════════════════════════

class TestGetCachedRates:

    @patch('ai_engine.modules.currency_service.cache')
    def test_returns_dict_from_cache(self, mock_cache):
        """get_cached_rates() returns the cached dict."""
        from ai_engine.modules.currency_service import get_cached_rates

        mock_cache.get.return_value = {
            'rates': {'CNY': 7.1},
            'updated_at': '2026-03-11',
            'base': 'USD',
        }
        result = get_cached_rates()
        assert isinstance(result, dict)
        assert 'rates' in result

    @patch('ai_engine.modules.currency_service.cache')
    def test_returns_none_when_cache_empty(self, mock_cache):
        """Returns None when nothing is cached."""
        from ai_engine.modules.currency_service import get_cached_rates

        mock_cache.get.return_value = None
        result = get_cached_rates()
        assert result is None
