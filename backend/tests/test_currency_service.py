import pytest
from unittest.mock import patch, MagicMock
from urllib.error import URLError
from news.services.currency_service import fetch_exchange_rates, get_rates, convert_to_usd, update_all_usd_prices, FALLBACK_RATES
from news.models import VehicleSpecs

@patch('news.services.currency_service.urlopen')
def test_fetch_exchange_rates_success(mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"result": "success", "rates": {"EUR": 0.85, "CNY": 7.0}}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    rates = fetch_exchange_rates()
    
    assert rates['USD'] == 1.0
    assert rates['EUR'] == 1.0 / 0.85
    assert rates['CNY'] == 1.0 / 7.0

@patch('news.services.currency_service.urlopen')
def test_fetch_exchange_rates_fallback(mock_urlopen):
    mock_urlopen.side_effect = URLError("Network offline")
    
    rates = fetch_exchange_rates()
    assert rates == FALLBACK_RATES

def test_convert_to_usd():
    with patch('news.services.currency_service.get_rates', return_value={'CNY': 0.14}):
        result = convert_to_usd(100000, 'CNY')
        assert result == 14000

@pytest.mark.django_db
@patch('news.services.currency_service.fetch_exchange_rates', return_value={'CNY': 0.14, 'EUR': 1.1, 'USD': 1.0})
def test_update_all_usd_prices(mock_fetch):
    specs_cny = VehicleSpecs.objects.create(make='NIO', model_name='ET5', currency='CNY', price_from=298000)
    specs_usd = VehicleSpecs.objects.create(make='Tesla', model_name='Model 3', currency='USD', price_from=38000)
    
    updated, errors = update_all_usd_prices()
    
    assert updated == 1
    assert errors == 0
    
    specs_cny.refresh_from_db()
    specs_usd.refresh_from_db()
    
    assert specs_cny.price_usd_from == int(298000 * 0.14)
    assert specs_usd.price_usd_from is None # USD values aren't converted, kept blank to avoid redundancy
