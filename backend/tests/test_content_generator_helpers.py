"""
Tests for content_generator helper functions.

Tests the extracted helper functions: _auto_add_drivetrain_tag,
_truncate_summary, _inject_inline_image_placeholders.
"""
import pytest
import re
from unittest.mock import patch, MagicMock

# Import the functions under test
from ai_engine.modules.content_generator import (
    _auto_add_drivetrain_tag,
    _truncate_summary,
    _inject_inline_image_placeholders,
)


class TestAutoAddDrivetrainTag:
    """Tests for _auto_add_drivetrain_tag helper."""

    def test_adds_awd_tag(self):
        tags = ['EV', '2026']
        _auto_add_drivetrain_tag({'drivetrain': 'AWD'}, tags)
        assert 'AWD' in tags

    def test_adds_fwd_tag(self):
        tags = []
        _auto_add_drivetrain_tag({'drivetrain': 'FWD'}, tags)
        assert 'FWD' in tags

    def test_adds_rwd_tag(self):
        tags = []
        _auto_add_drivetrain_tag({'drivetrain': 'rwd'}, tags)
        assert 'RWD' in tags

    def test_adds_4wd_tag(self):
        tags = []
        _auto_add_drivetrain_tag({'drivetrain': '4wd'}, tags)
        assert '4WD' in tags

    def test_does_not_duplicate(self):
        tags = ['AWD']
        _auto_add_drivetrain_tag({'drivetrain': 'AWD'}, tags)
        assert tags.count('AWD') == 1

    def test_skips_not_specified(self):
        tags = []
        _auto_add_drivetrain_tag({'drivetrain': 'Not specified'}, tags)
        assert len(tags) == 0

    def test_skips_empty_string(self):
        tags = []
        _auto_add_drivetrain_tag({'drivetrain': ''}, tags)
        assert len(tags) == 0

    def test_skips_none(self):
        tags = []
        _auto_add_drivetrain_tag({'drivetrain': None}, tags)
        assert len(tags) == 0

    def test_skips_missing_key(self):
        tags = []
        _auto_add_drivetrain_tag({}, tags)
        assert len(tags) == 0

    def test_skips_invalid_drivetrain(self):
        tags = []
        _auto_add_drivetrain_tag({'drivetrain': 'CVT'}, tags)
        assert len(tags) == 0

    def test_case_insensitive_existing_check(self):
        """Should not add if a same-value tag exists in different case."""
        tags = ['awd']
        _auto_add_drivetrain_tag({'drivetrain': 'AWD'}, tags)
        # 'awd'.upper() == 'AWD', so should not add duplicate
        assert len(tags) == 1


class TestTruncateSummary:
    """Tests for _truncate_summary helper."""

    def test_short_text_unchanged(self):
        text = "Short text."
        assert _truncate_summary(text, max_len=100) == text

    def test_exact_limit_unchanged(self):
        text = "x" * 100
        assert _truncate_summary(text, max_len=100) == text

    def test_cuts_at_sentence_boundary(self):
        text = "First sentence. Second sentence. Third sentence that is very long."
        result = _truncate_summary(text, max_len=40)
        assert result.endswith('.')
        assert len(result) <= 40

    def test_cuts_at_word_boundary(self):
        # No period in the text — should cut at word boundary
        text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 extra"
        result = _truncate_summary(text, max_len=50)
        assert len(result) <= 50
        assert not result.endswith(' ')  # Should not end mid-word

    def test_default_max_len_is_3000(self):
        short_text = "a" * 2999
        assert _truncate_summary(short_text) == short_text
        long_text = "word " * 700  # 3500 chars
        result = _truncate_summary(long_text)
        assert len(result) <= 3000


class TestInjectInlineImagePlaceholders:
    """Tests for _inject_inline_image_placeholders."""

    def _make_article(self, n_sections=5, text_len=300):
        """Generate test HTML with n_sections of h2 + p."""
        parts = []
        for i in range(n_sections):
            parts.append(f'<h2>Section {i}</h2>')
            parts.append(f'<p>{"x" * text_len}</p>')
        return ''.join(parts)

    def test_inserts_placeholders_in_long_article(self):
        html = self._make_article(n_sections=5)
        result = _inject_inline_image_placeholders(html, max_images=2)
        assert '{{IMAGE_2}}' in result
        # IMAGE_3 may or may not be present depending on logic
        count = result.count('{{IMAGE_')
        assert count >= 1

    def test_skips_short_article(self):
        html = '<h2>Title</h2><p>short</p><h2>End</h2><p>end</p>'
        result = _inject_inline_image_placeholders(html, max_images=2)
        assert '{{IMAGE_2}}' not in result  # Too few sections

    def test_skips_sections_with_custom_blocks(self):
        html = (
            '<h2>Title</h2><p>' + 'x' * 300 + '</p>'
            '<h2>Specs</h2><div class="spec-bar">...</div><p>' + 'a' * 300 + '</p>'
            '<h2>Pros</h2><div class="pros-cons">...</div><p>' + 'b' * 300 + '</p>'
            '<h2>Content</h2><p>' + 'y' * 300 + '</p>'
            '<h2>More</h2><p>' + 'z' * 300 + '</p>'
        )
        result = _inject_inline_image_placeholders(html, max_images=2)
        # Placeholders should exist somewhere in the result
        has_any = '{{IMAGE_2}}' in result or '{{IMAGE_3}}' in result
        assert has_any, "At least one placeholder should be inserted"
        # Verify no placeholder is between "Specs" h2 and its custom block
        specs_h2_pos = result.find('<h2>Specs</h2>')
        specs_block_pos = result.find('spec-bar')
        if specs_h2_pos >= 0 and specs_block_pos >= 0:
            between = result[specs_h2_pos:specs_block_pos]
            assert '{{IMAGE_' not in between, "No placeholder should be inside a custom block section"

    def test_max_images_1(self):
        html = self._make_article(n_sections=5)
        result = _inject_inline_image_placeholders(html, max_images=1)
        assert '{{IMAGE_2}}' in result
        assert '{{IMAGE_3}}' not in result

    def test_does_not_modify_first_h2(self):
        html = self._make_article(n_sections=5)
        result = _inject_inline_image_placeholders(html, max_images=2)
        # First h2 should still be at the very start
        assert result.startswith('<h2>Section 0</h2>')


# ═══════════════════════════════════════════════════════════════════════════
# NEW FEATURE TESTS
# ═══════════════════════════════════════════════════════════════════════════

from ai_engine.modules.content_generator import (
    _auto_add_tech_tags,
    _inject_tech_highlights,
)
from ai_engine.modules.article_post_processor import (
    _strip_hallucinated_compare_cards,
)


class TestStripHallucinatedCompareCards:
    """Tests for _strip_hallucinated_compare_cards — hallucination guard."""

    COMPARE_HTML = '''
    <div class="compare-grid">
      <div class="compare-card featured">
        <div class="compare-badge">This Vehicle</div>
        <div class="compare-card-name">2026 BYD SEAL 07 DM-i</div>
        <div class="compare-row"><span class="k">Power</span><span class="v">268 hp</span></div>
      </div>
      <div class="compare-card">
        <div class="compare-card-name">2024 Aito M7 REV</div>
        <div class="compare-row"><span class="k">Power</span><span class="v">200 hp</span></div>
      </div>
      <div class="compare-card">
        <div class="compare-card-name">2024 BYD Han DM-i</div>
        <div class="compare-row"><span class="k">Power</span><span class="v">194 hp</span></div>
      </div>
    </div>
    '''

    def test_removes_hallucinated_brand(self):
        result = _strip_hallucinated_compare_cards(self.COMPARE_HTML, ['BYD'])
        assert 'Aito' not in result
        assert 'BYD Han DM-i' in result

    def test_keeps_allowed_brand(self):
        """Featured card uses class='compare-card featured', regex only targets
        non-featured cards (class='compare-card'), so featured is always kept.
        BYD Han DM-i is a non-featured card and should remain because BYD is allowed."""
        result = _strip_hallucinated_compare_cards(self.COMPARE_HTML, ['BYD'])
        assert 'BYD Han DM-i' in result
        assert 'Aito' not in result

    def test_empty_allowed_disables_guard(self):
        """Empty allowed_makes = guard disabled, returns HTML unchanged."""
        result = _strip_hallucinated_compare_cards(self.COMPARE_HTML, [])
        assert result == self.COMPARE_HTML
        assert 'Aito' in result  # All cards preserved

    def test_all_allowed_keeps_all(self):
        result = _strip_hallucinated_compare_cards(self.COMPARE_HTML, ['BYD', 'Aito'])
        assert 'Aito M7' in result
        assert 'BYD Han DM-i' in result

    def test_case_insensitive_match(self):
        result = _strip_hallucinated_compare_cards(self.COMPARE_HTML, ['byd'])
        assert 'BYD Han DM-i' in result

    def test_no_compare_grid_returns_unchanged(self):
        html = '<p>Normal article content</p>'
        result = _strip_hallucinated_compare_cards(html, ['BYD'])
        assert result == html

    def test_none_allowed_makes_removes_all(self):
        result = _strip_hallucinated_compare_cards(self.COMPARE_HTML, None)
        # Should return unchanged (guard disabled)
        assert 'Aito' in result


class TestAutoAddTechTags:
    """Tests for _auto_add_tech_tags — keyword-based tech tag auto-detection."""

    def test_detects_lidar(self):
        html = '<p>The roof-mounted LiDAR sensor provides 3D mapping.</p>'
        tags = []
        _auto_add_tech_tags(html, tags, {})
        assert 'LiDAR' in tags

    def test_detects_adas_keywords(self):
        html = '<p>Advanced driver assistance systems are standard.</p>'
        tags = []
        _auto_add_tech_tags(html, tags, {})
        assert 'ADAS' in tags

    def test_detects_fast_charging(self):
        html = '<p>DC fast charging at 200 kW replenishes in 30 minutes.</p>'
        tags = []
        _auto_add_tech_tags(html, tags, {})
        assert 'Fast Charging' in tags

    def test_detects_battery_from_specs(self):
        html = '<p>Simple text without battery mention.</p>'
        tags = []
        _auto_add_tech_tags(html, tags, {'battery': '75 kWh'})
        assert 'Battery' in tags

    def test_does_not_duplicate_existing_tag(self):
        html = '<p>This car has LiDAR sensors.</p>'
        tags = ['LiDAR']
        _auto_add_tech_tags(html, tags, {})
        assert tags.count('LiDAR') == 1

    def test_no_false_positive_on_clean_text(self):
        html = '<p>This is a nice car with leather seats and a big trunk.</p>'
        tags = []
        _auto_add_tech_tags(html, tags, {})
        # Should NOT add ADAS, LiDAR, etc. from generic text
        assert 'ADAS' not in tags
        assert 'LiDAR' not in tags

    def test_multiple_techs_detected(self):
        html = '''
        <p>Features LiDAR, adaptive cruise control, and lane keeping assist.</p>
        <p>Emergency braking with pedestrian detection is standard.</p>
        <p>The infotainment system supports Apple CarPlay.</p>
        '''
        tags = []
        _auto_add_tech_tags(html, tags, {})
        assert 'LiDAR' in tags
        assert 'Adaptive Cruise' in tags
        assert 'Lane Assist' in tags
        assert 'Safety' in tags
        assert 'CarPlay' in tags
        assert len(tags) >= 5

    def test_case_insensitive_matching(self):
        html = '<p>The LIDAR sensor and ADAS suite work together.</p>'
        tags = []
        _auto_add_tech_tags(html, tags, {})
        assert 'LiDAR' in tags
        assert 'ADAS' in tags

    def test_turbo_detection(self):
        html = '<p>1.5L Turbocharged 4-cylinder engine.</p>'
        tags = []
        _auto_add_tech_tags(html, tags, {})
        assert 'Turbo' in tags

    def test_aerodynamics_detection(self):
        html = '<p>The drag coefficient is an impressive 0.23 Cd.</p>'
        tags = []
        _auto_add_tech_tags(html, tags, {})
        assert 'Aerodynamics' in tags


class TestInjectTechHighlights:
    """Tests for _inject_tech_highlights — visual tech block injection."""

    # Minimum ~800 chars of plain text required by the length guard.
    # Build reusable snippets that are always long enough.
    _LONG_PARA = '<p>' + 'x' * 120 + '</p>\n'  # 120 plain chars per paragraph

    def _make_tech_html(self, extra_heading='', suffix=''):
        """Return an article HTML stub with Technology & Features and enough filler content."""
        filler = self._LONG_PARA * 7  # 840 plain chars
        return (
            f'<h2>Performance & Specs</h2>\n{filler}'
            f'<h2>Technology &amp; Features</h2>\n{self._LONG_PARA * 2}'
            f'{extra_heading}'
            + suffix
        )

    def _make_no_tech_html(self, suffix=''):
        """Return an article HTML stub WITHOUT Technology heading."""
        filler = self._LONG_PARA * 7
        return (
            f'<h2>Design</h2>\n{filler}'
            + suffix
        )

    def test_injects_after_technology_heading(self):
        html = self._make_tech_html(suffix='<h2>Pricing</h2><p>From $30k.</p>')
        result = _inject_tech_highlights(html, ['ADAS', 'LiDAR'])
        assert 'tech-highlights' in result
        assert 'KEY TECHNOLOGIES' in result
        # Should be between Technology and Pricing
        tech_pos = result.find('tech-highlights')
        pricing_pos = result.find('Pricing')
        assert tech_pos < pricing_pos

    def test_injects_correct_items(self):
        html = self._make_tech_html()
        result = _inject_tech_highlights(html, ['ADAS', 'Fast Charging'])
        assert 'ADAS' in result
        assert 'Fast Charging' in result
        assert 'tech-item' in result

    def test_limits_to_8_items(self):
        html = self._make_tech_html()
        many_tags = ['ADAS', 'LiDAR', 'Adaptive Cruise', 'Lane Assist',
                     'Fast Charging', 'Battery', 'Turbo', 'Infotainment',
                     'Safety', 'CarPlay']  # 10 tags
        result = _inject_tech_highlights(html, many_tags)
        assert result.count('tech-item') == 8

    def test_empty_tags_returns_unchanged(self):
        # Empty tags check happens before length guard — HTML size doesn't matter
        html = '<h2>Technology &amp; Features</h2><p>Text.</p>'
        result = _inject_tech_highlights(html, [])
        assert result == html

    def test_unknown_tags_skipped(self):
        html = self._make_tech_html()
        result = _inject_tech_highlights(html, ['UnknownTag123'])
        assert result == html

    def test_fallback_before_pricing(self):
        """When no Technology heading exists, inject before Pricing."""
        html = self._make_no_tech_html(
            suffix='<h2>Pricing &amp; Availability</h2><p>From $30k.</p>'
        )
        result = _inject_tech_highlights(html, ['ADAS'])
        assert 'tech-highlights' in result
        assert 'Key Technologies' in result

    def test_includes_descriptions(self):
        html = self._make_tech_html()
        result = _inject_tech_highlights(html, ['LiDAR'])
        assert 'tech-desc' in result
        assert 'Laser-based' in result

    def test_short_article_skipped(self):
        """Stub/fallback articles (< 800 plain chars) must NOT get the tech block."""
        html = '<h2>Technology &amp; Features</h2><p>Short.</p>'
        result = _inject_tech_highlights(html, ['ADAS', 'LiDAR'])
        assert result == html  # Unchanged
        assert 'tech-highlights' not in result


