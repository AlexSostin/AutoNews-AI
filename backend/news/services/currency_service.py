"""
Currency conversion service for VehicleSpecs price normalization.
Fetches exchange rates weekly and converts all prices to USD equivalents.
"""
import logging
import json
from datetime import timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError

from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger('news')

# Cache key for exchange rates
RATES_CACHE_KEY = 'currency_exchange_rates'
RATES_CACHE_TTL = 7 * 24 * 60 * 60  # 7 days in seconds

# Fallback rates (updated Feb 2026) — used if API is down
FALLBACK_RATES = {
    'CNY': 0.137,   # 1 CNY = 0.137 USD
    'EUR': 1.08,    # 1 EUR = 1.08 USD
    'GBP': 1.26,    # 1 GBP = 1.26 USD
    'JPY': 0.0067,  # 1 JPY = 0.0067 USD
    'RUB': 0.011,   # 1 RUB = 0.011 USD
    'USD': 1.0,
}


def fetch_exchange_rates():
    """
    Fetch current exchange rates from a free API.
    Returns dict of {currency_code: rate_to_usd}.
    Falls back to hardcoded rates if API fails.
    """
    # Try free exchangerate API (no key needed for USD base)
    apis = [
        'https://open.er-api.com/v6/latest/USD',
        'https://api.exchangerate-api.com/v4/latest/USD',
    ]
    
    for api_url in apis:
        try:
            req = Request(api_url, headers={'User-Agent': 'FreshMotors/1.0'})
            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            rates_from_usd = data.get('rates', {})
            if not rates_from_usd:
                continue
            
            # Convert from "1 USD = X CNY" to "1 CNY = Y USD"
            rates_to_usd = {}
            for currency, rate in rates_from_usd.items():
                if rate and rate > 0:
                    rates_to_usd[currency] = 1.0 / rate
            rates_to_usd['USD'] = 1.0
            
            logger.info(f"✅ Fetched exchange rates from {api_url}: "
                        f"CNY={rates_to_usd.get('CNY', 'N/A'):.4f}, "
                        f"EUR={rates_to_usd.get('EUR', 'N/A'):.4f}")
            return rates_to_usd
            
        except (URLError, json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"⚠️ Failed to fetch rates from {api_url}: {e}")
            continue
    
    logger.warning("⚠️ All exchange rate APIs failed — using fallback rates")
    return FALLBACK_RATES


def get_rates():
    """Get cached exchange rates, fetching if needed."""
    rates = cache.get(RATES_CACHE_KEY)
    if rates:
        return rates
    
    rates = fetch_exchange_rates()
    cache.set(RATES_CACHE_KEY, rates, RATES_CACHE_TTL)
    return rates


def convert_to_usd(amount, currency):
    """
    Convert an amount from the given currency to USD.
    Returns rounded integer or None if conversion fails.
    """
    if not amount or not currency:
        return None
    
    if currency == 'USD':
        return int(amount)
    
    rates = get_rates()
    rate = rates.get(currency)
    
    if not rate:
        # Try fallback
        rate = FALLBACK_RATES.get(currency)
    
    if not rate:
        logger.warning(f"⚠️ No exchange rate for {currency}")
        return None
    
    return int(round(amount * rate))


def update_all_usd_prices():
    """
    Update USD price equivalents for all VehicleSpecs records.
    Called weekly by the scheduler.
    """
    from news.models import VehicleSpecs
    
    # Force fresh rates
    rates = fetch_exchange_rates()
    cache.set(RATES_CACHE_KEY, rates, RATES_CACHE_TTL)
    
    now = timezone.now()
    updated = 0
    errors = 0
    
    # Only process records with prices that aren't already in USD
    specs_to_update = VehicleSpecs.objects.filter(
        price_from__isnull=False,
    ).exclude(currency='USD')
    
    for vs in specs_to_update:
        try:
            usd_from = convert_to_usd(vs.price_from, vs.currency)
            usd_to = convert_to_usd(vs.price_to, vs.currency) if vs.price_to else None
            
            update_fields = ['price_updated_at']
            vs.price_updated_at = now
            
            if usd_from != vs.price_usd_from:
                vs.price_usd_from = usd_from
                update_fields.append('price_usd_from')
            if usd_to != vs.price_usd_to:
                vs.price_usd_to = usd_to
                update_fields.append('price_usd_to')
            
            vs.save(update_fields=update_fields)
            updated += 1
        except Exception as e:
            errors += 1
            logger.error(f"❌ Failed to update USD price for {vs.make} {vs.model_name}: {e}")
    
    # Also update USD records (just set updated_at)
    VehicleSpecs.objects.filter(
        price_from__isnull=False,
        currency='USD',
    ).update(
        price_usd_from=None,  # No conversion needed
        price_usd_to=None,
        price_updated_at=now,
    )
    
    logger.info(f"💱 USD price update complete: {updated} converted, {errors} errors")
    return updated, errors
