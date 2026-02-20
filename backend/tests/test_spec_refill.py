"""
Tests for spec_refill module.
"""
import pytest
from ai_engine.modules.spec_refill import compute_coverage, _is_filled, KEY_SPEC_FIELDS


class TestSpecCoverage:
    """Tests for compute_coverage() and _is_filled()"""

    def test_is_filled_positive(self):
        """Real values should be considered filled"""
        assert _is_filled('BMW') is True
        assert _is_filled('350') is True
        assert _is_filled('AWD') is True
        assert _is_filled(2025) is True

    def test_is_filled_negative(self):
        """Empty and placeholder values should not be filled"""
        assert _is_filled('') is False
        assert _is_filled(None) is False
        assert _is_filled('Not specified') is False
        assert _is_filled('None') is False
        assert _is_filled('0') is False

    def test_coverage_full(self):
        """All fields filled should give 100%"""
        specs = {f: 'value' for f in KEY_SPEC_FIELDS}
        filled, total, pct, missing = compute_coverage(specs)
        assert filled == 10
        assert pct == 100.0
        assert missing == []

    def test_coverage_empty(self):
        """No specs should give 0%"""
        filled, total, pct, missing = compute_coverage({})
        assert filled == 0
        assert pct == 0.0
        assert len(missing) == 10

    def test_coverage_partial(self):
        """Some fields filled should give partial coverage"""
        specs = {'make': 'BMW', 'model': 'X5', 'year': '2025'}
        filled, total, pct, missing = compute_coverage(specs)
        assert filled == 3
        assert pct == 30.0
        assert 'make' not in missing
        assert 'engine' in missing
