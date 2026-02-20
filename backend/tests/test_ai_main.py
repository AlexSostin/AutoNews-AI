"""
Tests for ai_engine/main.py — pure logic functions.
No external API calls — tests title validation, extraction, and duplicate checking.
"""
import pytest
from unittest.mock import patch, MagicMock

from ai_engine.main import (
    _is_generic_header,
    _contains_non_latin,
    validate_title,
    extract_title,
    check_duplicate,
)


# ─── _is_generic_header ─────────────────────────────────────────────────────

class TestIsGenericHeader:
    """Tests for _is_generic_header() — detects section headers that shouldn't be titles."""

    def test_exact_match(self):
        assert _is_generic_header("performance & specs") is True

    def test_case_insensitive(self):
        assert _is_generic_header("Performance & Specifications") is True

    def test_with_whitespace(self):
        assert _is_generic_header("  performance and specs  ") is True

    def test_substring_match_short(self):
        assert _is_generic_header("The performance & specs") is True

    def test_valid_title_not_generic(self):
        assert _is_generic_header("2025 BMW X5 M60i Review") is False

    def test_long_valid_title(self):
        assert _is_generic_header("The All-New 2025 Mercedes-Benz EQS 580 Sedan Review") is False

    def test_regex_pattern_verdict(self):
        assert _is_generic_header("Final Verdict") is True

    def test_regex_pattern_conclusion(self):
        assert _is_generic_header("Conclusion") is True


# ─── _contains_non_latin ────────────────────────────────────────────────────

class TestContainsNonLatin:
    """Tests for _contains_non_latin() — detects non-English characters."""

    def test_english_only(self):
        assert _contains_non_latin("2025 BMW X5 Review") is False

    def test_cyrillic(self):
        assert _contains_non_latin("Обзор нового BMW X5") is True

    def test_chinese(self):
        assert _contains_non_latin("全新宝马X5评测") is True

    def test_accented_latin(self):
        # Accented Latin chars (like French/German) should be allowed
        assert _contains_non_latin("Citroën ë-C4 électrique") is False

    def test_many_non_latin_chars(self):
        # 4 Cyrillic chars (> 2 threshold) → True
        assert _contains_non_latin("BMW X5 тест") is True

    def test_few_non_latin_allowed(self):
        # 2 or fewer non-Latin chars → allowed
        assert _contains_non_latin("BMW X5 тт") is False


# ─── validate_title ─────────────────────────────────────────────────────────

class TestValidateTitle:
    """Tests for validate_title() — title validation with fallback chain."""

    def test_valid_title_returned_as_is(self):
        result = validate_title("2025 BMW X5 M60i Full Review and Test Drive")
        assert result == "2025 BMW X5 M60i Full Review and Test Drive"

    def test_strips_whitespace(self):
        result = validate_title("  2025 BMW X5 Review  ")
        assert result == "2025 BMW X5 Review"

    def test_generic_title_falls_back(self):
        # Short generic titles (< 15 chars) should fall through to last-resort
        result = validate_title("Conclusion")
        # "Conclusion" is <15 chars, so validate_title treats it as short
        # and falls to the last-resort which accepts anything >5 chars
        assert result == "Conclusion"  # returned as last-resort

    def test_generic_long_title_uses_fallback(self):
        # With fallback data available, a generic title should be overridden
        result = validate_title(
            "Performance and Specifications",
            video_title="2025 BMW X5 M60i Review"
        )
        assert "BMW" in result

    def test_short_title_rejected(self):
        result = validate_title("BMW")
        assert result != "BMW"

    def test_fallback_to_video_title(self):
        result = validate_title("Short", video_title="Amazing 2025 BMW X5 Full Test Drive")
        assert "BMW" in result or "Amazing" in result

    def test_fallback_to_specs(self):
        specs = {"make": "BMW", "model": "X5", "year": "2025"}
        result = validate_title("X", video_title=None, specs=specs)
        assert "BMW" in result
        assert "X5" in result

    def test_specs_with_trim(self):
        specs = {"make": "Mercedes", "model": "EQS", "year": "2025", "trim": "580"}
        result = validate_title("", video_title=None, specs=specs)
        assert "Mercedes" in result
        assert "580" in result

    def test_last_resort_fallback(self):
        result = validate_title("", video_title="", specs={})
        assert result == "New Car Review"

    def test_non_latin_title_rejected(self):
        result = validate_title("Обзор нового автомобиля BMW X5 2025")
        assert result != "Обзор нового автомобиля BMW X5 2025"

    def test_video_title_cleaned(self):
        result = validate_title("Bad", video_title="Great BMW Review | Some Channel Name")
        assert "Some Channel Name" not in result


# ─── extract_title ──────────────────────────────────────────────────────────

class TestExtractTitle:
    """Tests for extract_title() — extracts title from HTML h2 tags."""

    def test_extracts_first_valid_h2(self):
        html = "<h2>2025 BMW X5 Review</h2><p>Content here</p>"
        assert extract_title(html) == "2025 BMW X5 Review"

    def test_skips_generic_h2(self):
        html = "<h2>Performance & Specs</h2><h2>2025 BMW X5 Review</h2>"
        assert extract_title(html) == "2025 BMW X5 Review"

    def test_strips_inner_html_tags(self):
        html = "<h2><strong>2025 BMW X5 Review</strong></h2>"
        assert extract_title(html) == "2025 BMW X5 Review"

    def test_no_h2_returns_none(self):
        html = "<h1>Title</h1><p>Content</p>"
        assert extract_title(html) is None

    def test_only_generic_h2_returns_none(self):
        html = "<h2>Performance & Specs</h2><h2>Conclusion</h2>"
        assert extract_title(html) is None

    def test_h2_with_attributes(self):
        html = '<h2 class="title" id="main">2025 BMW X5 Review</h2>'
        assert extract_title(html) == "2025 BMW X5 Review"


# ─── check_duplicate ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCheckDuplicate:
    """Tests for check_duplicate() — checks if YouTube URL already processed."""

    def test_no_duplicate_returns_none(self):
        # No article with this URL exists → returns None
        result = check_duplicate("https://www.youtube.com/watch?v=UNIQUE_NONEXISTENT")
        assert result is None

    def test_duplicate_returns_article(self):
        from news.models import Article
        article = Article.objects.create(
            title='Dup Test', slug='dup-test',
            content='<p>Content</p>', is_published=True,
            youtube_url='https://www.youtube.com/watch?v=EXISTING_DUP'
        )
        result = check_duplicate("https://www.youtube.com/watch?v=EXISTING_DUP")
        assert result is not None
        assert result.id == article.id
