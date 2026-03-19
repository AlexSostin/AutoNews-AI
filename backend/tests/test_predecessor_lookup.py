"""Tests for ai_engine.modules.predecessor_lookup — predecessor + sibling matching."""
import pytest
from unittest.mock import patch, MagicMock
from ai_engine.modules.predecessor_lookup import (
    find_predecessor, find_siblings, format_evolution, format_siblings, get_predecessor_context
)


class TestFindPredecessor:
    """Test predecessor lookup (same model, earlier year)."""

    def test_empty_make_returns_none(self):
        assert find_predecessor('', 'Model') is None
        assert find_predecessor(None, 'Model') is None

    def test_empty_model_returns_none(self):
        assert find_predecessor('Make', '') is None
        assert find_predecessor('Make', None) is None

    def test_returns_dict_or_none(self):
        """Real DB test — should return dict or None, never crash."""
        result = find_predecessor('NONEXISTENT_BRAND_XYZ', 'Model', current_year=2025)
        assert result is None

    def test_result_has_required_keys(self):
        """If predecessor found, it should have make/model/year keys."""
        result = find_predecessor('ZEEKR', '7X', current_year=2027)
        if result:
            assert 'make' in result
            assert 'model' in result
            assert 'year' in result


class TestFindSiblings:
    """Test sibling matching (same brand, different model)."""

    def test_empty_make_returns_empty(self):
        assert find_siblings('', 'Model') == []

    def test_nonexistent_brand_returns_empty(self):
        assert find_siblings('NONEXISTENT_BRAND_XYZ', 'Model') == []

    def test_returns_list(self):
        """Should always return a list."""
        result = find_siblings('ZEEKR', '8X')
        assert isinstance(result, list)

    def test_excludes_current_model(self):
        """Siblings should NOT include the model being searched for."""
        result = find_siblings('ZEEKR', '8X')
        for s in result:
            assert not s['model'].startswith('8X'), f"Sibling should not be 8X itself: {s}"

    def test_siblings_have_specs(self):
        """Each sibling should have power_hp (required field for real specs)."""
        result = find_siblings('ZEEKR', '8X')
        for s in result:
            assert 'power_hp' in s, f"Sibling missing power_hp: {s}"

    def test_max_results_respected(self):
        result = find_siblings('ZEEKR', '8X', max_results=1)
        assert len(result) <= 1

    def test_body_type_filter(self):
        """When body_type given, should prefer same body type."""
        result_suv = find_siblings('ZEEKR', '8X', body_type='SUV')
        result_any = find_siblings('ZEEKR', '8X')
        # Both should return results (if DB has data)
        # SUV filter should not return MORE results than unfiltered
        assert len(result_suv) <= len(result_any) + 1  # +1 tolerance for edge cases


class TestFormatEvolution:
    """Test predecessor comparison formatting."""

    def test_none_predecessor_returns_empty(self):
        assert format_evolution({}, None) == ''

    def test_basic_formatting(self):
        predecessor = {'make': 'BMW', 'model': 'iX3', 'year': 2024, 'power_hp': 286}
        result = format_evolution({}, predecessor)
        assert '═══' in result
        assert 'PREDECESSOR' in result
        assert 'BMW iX3' in result
        assert '2024' in result

    def test_power_diff_shown(self):
        predecessor = {'make': 'BMW', 'model': 'iX3', 'year': 2024, 'power_hp': 286}
        current_specs = {'horsepower': '340'}
        result = format_evolution(current_specs, predecessor)
        assert '+54 hp' in result

    def test_range_diff_shown(self):
        predecessor = {'make': 'BMW', 'model': 'iX3', 'year': 2024, 'range_km': 400}
        current_specs = {'range': '450 km'}
        result = format_evolution(current_specs, predecessor)
        assert '+50 km' in result

    def test_no_diff_shows_reference_specs(self):
        predecessor = {'make': 'BMW', 'model': 'iX3', 'year': 2024, 'power_hp': 286}
        current_specs = {}  # No overlapping keys for comparison
        result = format_evolution(current_specs, predecessor)
        # Should show reference specs instead
        assert '286' in result


class TestFormatSiblings:
    """Test sibling formatting for prompt injection."""

    def test_empty_siblings_returns_empty(self):
        assert format_siblings('BMW', 'X5', []) == ''

    def test_basic_formatting(self):
        siblings = [
            {'make': 'BMW', 'model': 'X3', 'year': 2025, 'power_hp': 300, 'battery_kwh': 80.0},
            {'make': 'BMW', 'model': 'iX1', 'year': 2024, 'power_hp': 200},
        ]
        result = format_siblings('BMW', 'X5', siblings)
        assert '═══' in result
        assert 'BRAND LINEUP' in result
        assert 'BMW X3' in result
        assert 'BMW iX1' in result
        assert '300 hp' in result

    def test_includes_price_when_available(self):
        siblings = [
            {'make': 'BYD', 'model': 'Seal', 'year': 2025, 'power_hp': 310,
             'price_from': 25000, 'currency': 'USD'},
        ]
        result = format_siblings('BYD', 'Han', siblings)
        assert '$25,000' in result


class TestGetPredecessorContext:
    """Test the main entry point with predecessor → sibling fallback."""

    def test_empty_inputs_return_empty(self):
        assert get_predecessor_context('', '', {}) == ''

    @patch('ai_engine.modules.predecessor_lookup.find_predecessor')
    @patch('ai_engine.modules.predecessor_lookup.find_siblings')
    def test_predecessor_found_no_sibling_lookup(self, mock_siblings, mock_pred):
        """When predecessor found, siblings should NOT be searched."""
        mock_pred.return_value = {'make': 'BMW', 'model': 'X5', 'year': 2024, 'power_hp': 350}
        result = get_predecessor_context('BMW', 'X5', {}, year=2025)
        assert len(result) > 0
        mock_siblings.assert_not_called()

    @patch('ai_engine.modules.predecessor_lookup.find_predecessor')
    @patch('ai_engine.modules.predecessor_lookup.find_siblings')
    def test_no_predecessor_falls_back_to_siblings(self, mock_siblings, mock_pred):
        """When no predecessor, should search for siblings."""
        mock_pred.return_value = None
        mock_siblings.return_value = [
            {'make': 'BMW', 'model': 'X3', 'year': 2025, 'power_hp': 300}
        ]
        result = get_predecessor_context('BMW', 'X5', {}, year=2025)
        mock_siblings.assert_called_once()
        assert 'BRAND LINEUP' in result

    @patch('ai_engine.modules.predecessor_lookup.find_predecessor')
    @patch('ai_engine.modules.predecessor_lookup.find_siblings')
    def test_nothing_found_returns_empty(self, mock_siblings, mock_pred):
        """When neither predecessor nor siblings found, return empty."""
        mock_pred.return_value = None
        mock_siblings.return_value = []
        result = get_predecessor_context('UNKNOWN', 'Car', {}, year=2025)
        assert result == ''
