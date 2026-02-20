"""
Tests for specs_enricher module regex extraction.
"""
import pytest
from ai_engine.modules.specs_enricher import _extract_values_from_text, _most_common


class TestSpecsEnricherRegex:
    """Tests for regex-based spec extraction"""

    def test_extract_horsepower(self):
        """Should extract horsepower values from text"""
        text = "The 2025 BMW M3 produces 473 hp and impressive acceleration"
        values = _extract_values_from_text(text, 'horsepower')
        assert '473' in values

    def test_extract_acceleration(self):
        """Should extract 0-60 times"""
        text = "The car accelerates from 0-60 in 3.1 seconds flat"
        values = _extract_values_from_text(text, 'acceleration')
        assert '3.1' in values

    def test_most_common_returns_top(self):
        """_most_common should return the most frequent value"""
        assert _most_common(['AWD', 'AWD', 'FWD']) == 'AWD'
        assert _most_common(['RWD']) == 'RWD'

    def test_most_common_empty(self):
        """_most_common should return None for empty list"""
        assert _most_common([]) is None


class TestSpecsEnricherPatterns:
    """Tests for additional SPEC_PATTERNS regex keys"""

    def test_extract_torque_nm(self):
        text = "The motor delivers 450 Nm of peak torque"
        values = _extract_values_from_text(text, 'torque')
        assert '450' in values

    def test_extract_torque_lbft(self):
        text = "Output is rated at 295 lb-ft of torque"
        values = _extract_values_from_text(text, 'torque')
        assert '295' in values

    def test_extract_battery_kwh(self):
        text = "Equipped with a 75 kWh battery pack"
        values = _extract_values_from_text(text, 'battery')
        assert '75' in values

    def test_extract_top_speed(self):
        text = "It has a top speed of 210 km/h"
        values = _extract_values_from_text(text, 'top_speed')
        assert '210' in values

    def test_extract_range_km(self):
        text = "WLTP range: 550 km on a single charge"
        values = _extract_values_from_text(text, 'range_km')
        assert '550' in values

    def test_extract_drivetrain(self):
        text = "Standard all-wheel drive for confident handling"
        values = _extract_values_from_text(text, 'drivetrain')
        assert len(values) > 0

    def test_extract_price_usd(self):
        text = "Starting at $35,990 in the US market"
        values = _extract_values_from_text(text, 'price_usd')
        assert '35990' in values

    def test_no_match_returns_empty(self):
        text = "This text has nothing useful in it"
        values = _extract_values_from_text(text, 'horsepower')
        assert values == []


class TestEnrichSpecsFromWeb:
    """Tests for enrich_specs_from_web function"""

    def test_enriches_missing_hp(self):
        from ai_engine.modules.specs_enricher import enrich_specs_from_web
        specs = {'make': 'BYD', 'model': 'Seal'}
        web_text = "The BYD Seal produces 313 hp with its dual motor setup. " * 3
        result = enrich_specs_from_web(specs, web_text)
        assert result.get('horsepower') is not None

    def test_skips_short_context(self):
        from ai_engine.modules.specs_enricher import enrich_specs_from_web
        specs = {'make': 'Test'}
        result = enrich_specs_from_web(specs, "short")
        assert result == specs

    def test_enriches_torque(self):
        from ai_engine.modules.specs_enricher import enrich_specs_from_web
        specs = {'make': 'NIO', 'model': 'ET5'}
        web_text = "The NIO ET5 delivers 700 Nm of torque for instant acceleration. " * 3
        result = enrich_specs_from_web(specs, web_text)
        assert 'torque' in result
        assert '700' in result['torque']

    def test_build_enriched_analysis(self):
        from ai_engine.modules.specs_enricher import build_enriched_analysis
        specs = {'make': 'Tesla', 'model': 'Model 3', 'horsepower': 350}
        text, enriched = build_enriched_analysis(specs, "")
        assert 'Tesla' in text
        assert 'Model 3' in text

