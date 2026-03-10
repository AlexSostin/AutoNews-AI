"""
Tests for the article generation quality pipeline:
- Price format validation
- Duplicate paragraph detection
- Self-consistency checking
- Source typo propagation guard
- Repetition detection (threshold = 3)
"""
import pytest
import re


# ── Import the functions under test ──────────────────────────────────
# We import from the module directly since these are private helpers.
# No Django DB required for these pure-function tests.

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_engine.modules.article_generator import (
    _validate_prices,
    _detect_duplicate_paragraphs,
    _check_self_consistency,
    _clean_source_typos,
    _reduce_repetition,
)


# ═══════════════════════════════════════════════════════════════════════
# 1. Price Validation
# ═══════════════════════════════════════════════════════════════════════

class TestValidatePrices:

    def test_fixes_doubled_approx_conversion(self):
        """CNY 359,800 (approx. $5,000)0 (approximately $49,800 USD) → single conversion."""
        html = '<p>The price is CNY 359,800 (approx. $5,000)0 (approximately $49,800 USD).</p>'
        result = _validate_prices(html)
        assert '(approx. $5,000)' not in result
        assert '(approximately $49,800' in result
        # Should NOT have duplicate conversions
        assert result.count('approx') == 1

    def test_fixes_broken_cny_comma(self):
        """CNY 359,80 → CNY 359,800 (dropped trailing zero)."""
        html = '<p>Starting at CNY 359,80 for the base model.</p>'
        result = _validate_prices(html)
        assert 'CNY 359,800' in result
        # Word boundary — trailing space was a false safety net (misses "359,80." "359,80)")
        assert not re.search(r'CNY 359,80\b', result)

    def test_leaves_valid_cny_alone(self):
        """CNY 359,800 should NOT be modified."""
        html = '<p>Starting at CNY 359,800 for the base model.</p>'
        result = _validate_prices(html)
        assert result == html

    def test_fixes_stray_digit_after_paren(self):
        """(approx. $49,800)0 → (approx. $49,800)."""
        html = '<p>Price is CNY 359,800 (approx. $49,800)0.</p>'
        result = _validate_prices(html)
        assert ')0' not in result
        assert '(approx. $49,800)' in result

    def test_removes_duplicate_usd_annotations(self):
        """Two consecutive (approx. $X) annotations → keep first."""
        html = '<p>CNY 200,000 (approximately $27,500) (approx. $27,500)</p>'
        result = _validate_prices(html)
        assert result.count('approx') == 1

    def test_leaves_different_conversions_alone(self):
        """Two different prices should not be merged."""
        html = '<p>Base: CNY 200,000 (approx. $27,500). Top: CNY 350,000 (approx. $48,000).</p>'
        result = _validate_prices(html)
        assert result.count('approx') == 2


# ═══════════════════════════════════════════════════════════════════════
# 2. Duplicate Paragraph Detection
# ═══════════════════════════════════════════════════════════════════════

class TestDetectDuplicateParagraphs:

    def test_removes_near_duplicate_paragraphs(self):
        """Two paragraphs with >70% similarity → later one removed."""
        html = (
            '<p>The XPeng X9 features a 63.3 kWh battery pack that delivers an impressive '
            'electric range of 450 kilometers, making it ideal for daily commuting and long trips.</p>'
            '<h2>Performance</h2>'
            '<p>Under the hood, the X9 is powered by a sophisticated EREV powertrain system.</p>'
            '<p>The XPeng X9 features a 63.3 kWh battery that delivers a remarkable '
            'electric range of 450 km, making it perfect for daily commuting and longer journeys.</p>'
        )
        result = _detect_duplicate_paragraphs(html)
        # Should have removed the duplicate (3rd para)
        assert result.count('<p>') < html.count('<p>')

    def test_keeps_unique_paragraphs(self):
        """Three completely different paragraphs → all kept."""
        html = (
            '<p>The BYD Seal is a mid-size electric sedan with 313 hp and RWD.</p>'
            '<p>Inside, the cabin features a 15.6-inch rotating display and vegan leather seats.</p>'
            '<p>Pricing starts at CNY 189,800 (approximately $26,000) in the Chinese market.</p>'
        )
        result = _detect_duplicate_paragraphs(html)
        assert result.count('<p>') == 3

    def test_skips_short_paragraphs(self):
        """Paragraphs under 80 chars should not be compared."""
        html = (
            '<p>Great car.</p>'
            '<p>Great car.</p>'
            '<p>The BYD Seal is a mid-size electric sedan with 313 hp and rear-wheel drive.</p>'
        )
        result = _detect_duplicate_paragraphs(html)
        # Short paragraphs ignored, so both "Great car." kept
        assert result.count('Great car') == 2


# ═══════════════════════════════════════════════════════════════════════
# 3. Self-Consistency
# ═══════════════════════════════════════════════════════════════════════

class TestCheckSelfConsistency:

    def test_fixes_rounding_inconsistency(self):
        """63.3 kWh vs 63 kWh → keeps 63.3 kWh everywhere."""
        html = (
            '<p>The battery is a 63.3 kWh lithium iron phosphate unit.</p>'
            '<p>With its 63 kWh battery, range reaches 450 km.</p>'
        )
        result = _check_self_consistency(html)
        # Bare "63 kWh" must be gone; precise "63.3 kWh" must be present everywhere
        assert not re.search(r'\b63 kWh\b', result), "Rounded value was not replaced"
        assert result.count('63.3 kWh') >= 2, "Both occurrences should now say 63.3 kWh"

    def test_accepts_different_specs(self):
        """63.3 kWh battery and 60 liters fuel → no conflict (different units)."""
        html = (
            '<p>The battery is a 63.3 kWh unit.</p>'
            '<p>The fuel tank holds 60 liters.</p>'
        )
        result = _check_self_consistency(html)
        assert '63.3 kWh' in result
        assert '60 liters' in result

    def test_ignores_very_different_values(self):
        """200 km vs 450 km → no fix (these are genuinely different specs)."""
        html = (
            '<p>Pure electric range is 450 km.</p>'
            '<p>The competitors offer only 200 km of electric range.</p>'
        )
        result = _check_self_consistency(html)
        assert '450 km' in result
        assert '200 km' in result

    def test_skips_headings(self):
        """Specs in headings should not be counted."""
        html = (
            '<h2>63.3 kWh Battery and 450 km Range</h2>'
            '<p>The 63 kWh pack delivers solid range.</p>'
        )
        result = _check_self_consistency(html)
        # Heading must be preserved unchanged
        assert '<h2>63.3 kWh Battery and 450 km Range</h2>' in result
        # With only one body occurrence of kWh, no consistency fix should apply
        # so the body text stays as-is ("63 kWh" not changed since nothing to compare to)
        assert '63 kWh' in result, "Single body occurrence should not be altered"


# ═══════════════════════════════════════════════════════════════════════
# 4. Source Typo Guard
# ═══════════════════════════════════════════════════════════════════════

class TestCleanSourceTypos:

    def test_fixes_staring_price(self):
        """'staring price' → 'starting price'."""
        html = '<p>The staring price is CNY 359,800.</p>'
        result = _clean_source_typos(html)
        assert 'starting price' in result
        assert 'staring price' not in result

    def test_fixes_staring_at(self):
        """'staring at' → 'starting at'."""
        html = '<p>Prices are staring at $49,800.</p>'
        result = _clean_source_typos(html)
        assert 'starting at' in result

    def test_fixes_model_name_staring(self):
        """'X9 staring' (trim name) → 'X9 Starting'."""
        html = '<p>The XPeng X9 staring EREV comes with a 63.3 kWh battery.</p>'
        result = _clean_source_typos(html)
        # Function converts "X9 staring EREV" → "X9 starting EREV" (lowercase s)
        # or "X9 Starting" (capital S) via the trim-name regex — either is correct
        assert 'staring' not in result, f"'staring' was not corrected; got: {result}"
        assert 'starting' in result.lower(), "Expected 'starting' to appear after correction"

    def test_fixes_luxary(self):
        """'luxary' → 'luxury'."""
        html = '<p>The luxary interior features premium leather.</p>'
        result = _clean_source_typos(html)
        assert 'luxury' in result
        assert 'luxary' not in result

    def test_fixes_electirc(self):
        """'electirc' → 'electric'."""
        html = '<p>This is a fully electirc vehicle with impressive range.</p>'
        result = _clean_source_typos(html)
        assert 'electric' in result
        assert 'electirc' not in result

    def test_leaves_correct_text_alone(self):
        """Correctly spelled text should not be modified."""
        html = '<p>The starting price for this luxury electric vehicle is very competitive.</p>'
        result = _clean_source_typos(html)
        assert result == html


# ═══════════════════════════════════════════════════════════════════════
# 5. Repetition Detector (threshold lowered to 3)
# ═══════════════════════════════════════════════════════════════════════

class TestReduceRepetitionThreshold:

    def test_catches_spec_in_3_blocks(self):
        """A spec appearing in 4+ blocks should trigger cleanup (threshold=3 marks overused, removes after 3 seen)."""
        html = (
            '<p>The car has 450 km of range and advanced technology.</p>'
            '<p>With 450 km range, long trips are easy and stress-free.</p>'
            '<p>Daily driving benefits from the 450 km electric range capability.</p>'
            '<p>The 450 km range is competitive against rivals in this segment.</p>'
            '<p>The interior is spacious with premium materials.</p>'
        )
        result = _reduce_repetition(html)
        # The spec "450 km" appeared in 4 blocks — the 4th should be removed
        count_450 = len(re.findall(r'450\s*km', result))
        original_count = len(re.findall(r'450\s*km', html))
        # Should have removed at least one occurrence
        assert count_450 < original_count

    def test_does_not_remove_when_under_threshold(self):
        """Spec in only 2 blocks → no removal."""
        html = (
            '<p>The car has 450 km of range.</p>'
            '<p>With 450 km range, long trips are easy.</p>'
            '<p>The interior is spacious.</p>'
        )
        result = _reduce_repetition(html)
        assert result.count('450 km') == 2  # Both kept


# ═══════════════════════════════════════════════════════════════════════
# 6. Edge Cases — empty/None/no-tags/Unicode
# ═══════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_validate_prices_empty_string(self):
        """Empty string should not crash and return empty string."""
        assert _validate_prices('') == ''

    def test_clean_source_typos_empty_string(self):
        """Empty string should not crash."""
        assert _clean_source_typos('') == ''

    def test_check_self_consistency_empty_string(self):
        """Empty string should not crash."""
        assert _check_self_consistency('') == ''

    def test_detect_duplicate_paragraphs_no_p_tags(self):
        """HTML without <p> tags (e.g. only headings) returns unchanged."""
        html = '<h2>Performance</h2><h2>Design</h2>'
        assert _detect_duplicate_paragraphs(html) == html

    def test_detect_duplicate_paragraphs_single_para(self):
        """A single paragraph (>80 chars) — nothing to compare, should pass through."""
        html = '<p>The BYD Seal is an impressive mid-size electric sedan with 313 horsepower, rear-wheel drive, and a competitive price.</p>'
        assert _detect_duplicate_paragraphs(html) == html

    def test_validate_prices_unicode_content(self):
        """Unicode text (Chinese/Arabic) alongside prices should not corrupt content."""
        html = '<p>价格从 CNY 359,800 (approximately $49,800) 开始。</p>'
        result = _validate_prices(html)
        assert '开始' in result  # Chinese chars preserved
        assert 'CNY 359,800' in result

    def test_clean_source_typos_correct_text_unicode(self):
        """Hebrew/Arabic text should pass through the typo guard cleanly."""
        html = '<p>السيارة الكهربائية ممتازة — starting price is $49,800.</p>'
        result = _clean_source_typos(html)
        assert 'starting price' in result
        assert 'السيارة' in result  # Arabic chars preserved
