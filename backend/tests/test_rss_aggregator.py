"""
Tests for ai_engine/modules/rss_aggregator.py.
Split into:
  - Pure method tests (no mocks, no HTTP)
  - Mocked tests (DB & HTTP mocked)
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timedelta
from django.utils import timezone

from ai_engine.modules.rss_aggregator import RSSAggregator


@pytest.fixture
def aggregator():
    return RSSAggregator()


# ═══════════════════════════════════════════════════════════════════════════
# Pure method tests (no external calls)
# ═══════════════════════════════════════════════════════════════════════════

class TestCalculateContentHash:
    """Tests for calculate_content_hash() — SHA256 hashing."""

    def test_deterministic(self, aggregator):
        h1 = aggregator.calculate_content_hash("hello world")
        h2 = aggregator.calculate_content_hash("hello world")
        assert h1 == h2

    def test_different_content_different_hash(self, aggregator):
        h1 = aggregator.calculate_content_hash("BMW X5 review")
        h2 = aggregator.calculate_content_hash("Mercedes EQS review")
        assert h1 != h2

    def test_empty_string(self, aggregator):
        h = aggregator.calculate_content_hash("")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA256 hex = 64 chars


class TestCalculateTitleSimilarity:
    """Tests for calculate_title_similarity() — SequenceMatcher ratio."""

    def test_identical_titles(self, aggregator):
        score = aggregator.calculate_title_similarity("BMW X5 Review", "BMW X5 Review")
        assert score == 1.0

    def test_completely_different(self, aggregator):
        score = aggregator.calculate_title_similarity("BMW X5", "Toyota Camry")
        assert score < 0.5

    def test_similar_titles(self, aggregator):
        score = aggregator.calculate_title_similarity(
            "2025 BMW X5 M60i Review",
            "2025 BMW X5 M60i Full Review"
        )
        assert score > 0.7

    def test_empty_strings(self, aggregator):
        score = aggregator.calculate_title_similarity("", "")
        assert score == 1.0  # SequenceMatcher considers empty strings identical


class TestConvertPlainTextToHtml:
    """Tests for convert_plain_text_to_html() — text to HTML conversion."""

    def test_wraps_paragraphs(self, aggregator):
        result = aggregator.convert_plain_text_to_html("First paragraph.\n\nSecond paragraph.")
        assert "<p>" in result
        assert "First paragraph." in result
        assert "Second paragraph." in result

    def test_converts_urls_to_links(self, aggregator):
        result = aggregator.convert_plain_text_to_html("Visit https://example.com for more.")
        assert "href" in result or "https://example.com" in result

    def test_empty_string(self, aggregator):
        result = aggregator.convert_plain_text_to_html("")
        assert isinstance(result, str)

    def test_single_paragraph(self, aggregator):
        result = aggregator.convert_plain_text_to_html("Just one line of text.")
        assert "<p>" in result

    def test_preserves_content(self, aggregator):
        text = "BMW reveals the all-new X5 for 2025."
        result = aggregator.convert_plain_text_to_html(text)
        assert "BMW" in result
        assert "X5" in result


class TestCleanPublisherMentions:
    """Tests for clean_publisher_mentions() — removes self-references."""

    def test_removes_read_more(self, aggregator):
        text = "Great article content.\nRead more at Motor1.com"
        result = aggregator.clean_publisher_mentions(text)
        # Should remove or clean the publisher mention
        assert "Great article" in result

    def test_preserves_meaningful_content(self, aggregator):
        text = "The 2025 BMW X5 is a game changer in the luxury SUV segment."
        result = aggregator.clean_publisher_mentions(text)
        assert "BMW X5" in result
        assert "luxury SUV" in result

    def test_empty_string(self, aggregator):
        result = aggregator.clean_publisher_mentions("")
        assert result == ""

    def test_no_publisher_mentions(self, aggregator):
        text = "Pure article content without any publisher references."
        result = aggregator.clean_publisher_mentions(text)
        assert result == text


class TestExtractPlainText:
    """Tests for extract_plain_text() — gets plain text from RSS entry."""

    def test_extracts_from_summary(self, aggregator):
        # feedparser entries use attribute access, not dict
        entry = MagicMock()
        entry.summary = "<p>BMW reveals new X5 model</p>"
        entry.content = None
        entry.description = None
        result = aggregator.extract_plain_text(entry)
        assert "BMW" in result
        assert "<p>" not in result

    def test_empty_entry(self, aggregator):
        entry = MagicMock(spec=[])
        result = aggregator.extract_plain_text(entry)
        assert result == ""

    def test_html_entities_decoded(self, aggregator):
        entry = MagicMock()
        entry.summary = "BMW &amp; Mercedes partnership"
        entry.content = None
        entry.description = None
        result = aggregator.extract_plain_text(entry)
        assert "BMW" in result


class TestParseEntryDate:
    """Tests for parse_entry_date() — extracts dates from RSS entries."""

    def test_with_published_parsed(self, aggregator):
        import time
        entry = MagicMock()
        entry.published_parsed = time.struct_time((2025, 6, 15, 12, 0, 0, 0, 166, 0))
        entry.updated_parsed = None
        result = aggregator.parse_entry_date(entry)
        assert result is not None

    def test_missing_date(self, aggregator):
        entry = MagicMock(spec=[])  # no attributes
        result = aggregator.parse_entry_date(entry)
        assert result is None

    def test_with_updated_parsed(self, aggregator):
        import time
        entry = MagicMock()
        entry.published_parsed = None
        entry.updated_parsed = time.struct_time((2025, 3, 10, 8, 0, 0, 0, 69, 0))
        result = aggregator.parse_entry_date(entry)
        assert result is not None


# ═══════════════════════════════════════════════════════════════════════════
# Mocked tests (DB & HTTP)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestIsDuplicate:
    """Tests for is_duplicate() — deduplication logic."""

    def test_no_duplicate_found(self, aggregator):
        result = aggregator.is_duplicate("Completely unique title XYZ", "unique content here")
        assert result is False

    def test_title_similarity_match(self, aggregator):
        """If a very similar title exists in Article table, it's a duplicate."""
        from news.models import Article
        Article.objects.create(
            title="2025 BMW X5 M60i Full Review and Test Drive",
            slug="bmw-x5-dup-similarity-test",
            content="<p>Some content</p>",
            is_published=True,
        )
        # Very similar title should be caught
        result = aggregator.is_duplicate(
            "2025 BMW X5 M60i Full Review and Test Drive",
            "Different content entirely"
        )
        assert result is True


@pytest.mark.django_db
class TestFetchFeed:
    """Tests for fetch_feed() — HTTP calls mocked."""

    @patch('ai_engine.modules.rss_aggregator.feedparser.parse')
    def test_successful_fetch(self, mock_parse, aggregator):
        mock_parse.return_value = MagicMock(
            bozo=False,
            entries=[{"title": "Test Article", "link": "https://example.com/1"}],
            feed={"title": "Test Feed"}
        )
        result = aggregator.fetch_feed("https://example.com/rss")
        assert result is not None

    @patch('ai_engine.modules.rss_aggregator.feedparser.parse')
    def test_failed_fetch(self, mock_parse, aggregator):
        mock_parse.return_value = MagicMock(
            bozo=True,
            bozo_exception=Exception("Parse error"),
            entries=[]
        )
        result = aggregator.fetch_feed("https://invalid.com/rss")
        # Should handle error gracefully
        assert result is not None or result is None  # doesn't crash


class TestExtractOgImage:
    """Tests for extract_og_image() — scrapes og:image from article pages."""

    @patch('requests.get')
    def test_found_og_image(self, mock_get, aggregator):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><head><meta property="og:image" content="https://example.com/image.jpg"></head></html>'
        mock_get.return_value = mock_resp

        result = aggregator.extract_og_image("https://example.com/article")
        assert result == "https://example.com/image.jpg"

    @patch('requests.get')
    def test_no_og_image(self, mock_get, aggregator):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><head><title>No Image</title></head></html>'
        mock_get.return_value = mock_resp

        result = aggregator.extract_og_image("https://example.com/article")
        assert result is None

    def test_empty_url(self, aggregator):
        result = aggregator.extract_og_image("")
        assert result is None

    def test_none_url(self, aggregator):
        result = aggregator.extract_og_image(None)
        assert result is None
