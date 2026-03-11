"""
Currency Exchange Rate Service
Fetches daily rates from open.er-api.com (free, no key needed).
Caches in Django cache (Redis) with 48h TTL as safety buffer.
"""
import logging
import requests
from datetime import datetime
from django.core.cache import cache

logger = logging.getLogger('news')

CACHE_KEY = 'currency_exchange_rates'
CACHE_TTL = 48 * 60 * 60  # 48 hours (safety buffer; refresh is daily)

# Currencies relevant to automotive markets worldwide
TARGET_CURRENCIES = [
    'CNY', 'JPY', 'KRW', 'MXN', 'EUR', 'GBP', 'AUD',
    'THB', 'INR', 'ILS', 'BRL', 'CAD', 'SEK', 'NOK',
    'IDR', 'MYR', 'SAR', 'AED', 'TRY', 'PLN', 'CZK',
]

API_URL = 'https://open.er-api.com/v6/latest/USD'


def fetch_and_cache_rates():
    """
    Fetch latest USD-based exchange rates and cache them.
    Returns True on success, False on failure.
    """
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('result') != 'success':
            logger.warning(f"Currency API returned non-success: {data.get('result')}")
            return False

        all_rates = data.get('rates', {})
        # Filter to only currencies we care about
        rates = {
            code: all_rates[code]
            for code in TARGET_CURRENCIES
            if code in all_rates
        }

        cache_data = {
            'rates': rates,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'base': 'USD',
        }

        cache.set(CACHE_KEY, cache_data, CACHE_TTL)
        logger.info(f"💱 Currency rates updated: {len(rates)} currencies cached")
        return True

    except requests.RequestException as e:
        logger.error(f"💱 Currency fetch failed: {e}")
        return False
    except Exception as e:
        logger.error(f"💱 Currency service error: {e}")
        return False


def get_cached_rates():
    """Get cached rates dict, or None if not cached."""
    return cache.get(CACHE_KEY)


def get_rates_for_prompt():
    """
    Returns a formatted string of exchange rates for injection into AI prompts.
    Falls back to hardcoded approximate rates if cache is empty.
    """
    cached = get_cached_rates()

    if cached and cached.get('rates'):
        rates = cached['rates']
        updated = cached.get('updated_at', 'unknown')
    else:
        # Hardcoded fallback (approximate March 2026 rates)
        rates = {
            'CNY': 7.25, 'JPY': 149.0, 'KRW': 1340, 'MXN': 17.8,
            'EUR': 0.92, 'GBP': 0.79, 'AUD': 1.55, 'THB': 34.0,
            'INR': 83.5, 'ILS': 3.65, 'BRL': 5.0, 'CAD': 1.36,
        }
        updated = 'approximate (fallback)'

    # Format into a compact string
    parts = []
    for code, rate in sorted(rates.items()):
        if rate >= 100:
            parts.append(f"{rate:,.0f} {code}")
        elif rate >= 10:
            parts.append(f"{rate:.1f} {code}")
        else:
            parts.append(f"{rate:.2f} {code}")

    rates_line = " | ".join(parts)

    return (
        f"CURRENT EXCHANGE RATES (updated {updated}):\n"
        f"1 USD = {rates_line}\n"
        f"Use these rates for ALL currency conversions. Do NOT guess exchange rates."
    )
