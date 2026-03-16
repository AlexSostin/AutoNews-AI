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
