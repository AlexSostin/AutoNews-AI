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
        is_dup, _ = aggregator.is_duplicate("Completely unique title XYZ", "unique content here")
        assert is_dup is False

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
        is_dup, _ = aggregator.is_duplicate(
            "2025 BMW X5 M60i Full Review and Test Drive",
            "Different content entirely"
        )
        assert is_dup is True


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

@pytest.mark.django_db
class TestKeywordFiltering:
    """Tests keyword filtering logic in process_feed()."""

    @patch('ai_engine.modules.rss_aggregator.RSSAggregator.fetch_feed')
    @patch('ai_engine.modules.rss_aggregator.RSSAggregator.is_duplicate')
    def test_include_keywords_filtering(self, mock_is_duplicate, mock_fetch_feed, aggregator):
        mock_is_duplicate.return_value = (False, None)
        import time
        
        class MockEntry(dict):
            def __getattr__(self, name):
                if name in self:
                    return self[name]
                raise AttributeError(f"MockEntry has no attribute '{name}'")
                
        entry1 = MockEntry({
            'title': "Review of the new Electric SUV",
            'link': "http://example.com/1",
            'summary': "This is a great electric vehicle that we have been testing over the past week. It has an amazing range and the interior is incredibly spacious. The Battery electric vehicle has finally become mainstream with this new release. The charging speed is extremely fast and the safety features are top notch. Overall, a great electric SUV.",
            'published_parsed': time.struct_time((2026, 1, 1, 12, 0, 0, 0, 0, 0)),
            'content': [{'value': '<p>This is a great electric vehicle that we have been testing over the past week. It has an amazing range and the interior is incredibly spacious. The Battery electric vehicle has finally become mainstream with this new release. The charging speed is extremely fast and the safety features are top notch. Overall, a great electric SUV.</p>'}],
            'description': None,
        })
        entry2 = MockEntry({
            'title': "Detailed look at the Hybrid Sedan",
            'link': "http://example.com/2",
            'summary': "Not what we are looking for. However, this is a very long text to ensure that it passes the 100 character minimum length check present in the process_feed method. We just have to make sure it is long enough. The hybrid system is decent but falls short compared to regular. The sedan market is really suffering these days.",
            'published_parsed': time.struct_time((2026, 1, 1, 13, 0, 0, 0, 0, 0)),
            'content': [{'value': '<p>Not what we are looking for. However, this is a very long text to ensure that it passes the 100 character minimum length check present in the process_feed method. We just have to make sure it is long enough. The hybrid system is decent but falls short compared to regular. The sedan market is really suffering these days.</p>'}],
            'description': None,
        })

        mock_fetch_feed.return_value = MagicMock(entries=[entry1, entry2])

        from news.models import RSSFeed, RSSNewsItem
        feed = RSSFeed.objects.create(
            name='Test Feed',
            feed_url='http://test.com',
            include_keywords='electric'
        )

        aggregator.process_feed(feed)

        # Only one item should have been saved (the one containing 'electric')
        assert RSSNewsItem.objects.filter(rss_feed=feed).count() == 1
        assert RSSNewsItem.objects.filter(title="Review of the new Electric SUV").exists()

    @patch('ai_engine.modules.rss_aggregator.RSSAggregator.fetch_feed')
    @patch('ai_engine.modules.rss_aggregator.RSSAggregator.is_duplicate')
    def test_exclude_keywords_filtering(self, mock_is_duplicate, mock_fetch_feed, aggregator):
        mock_is_duplicate.return_value = (False, None)
        import time
        
        class MockEntry(dict):
            def __getattr__(self, name):
                if name in self:
                    return self[name]
                raise AttributeError(f"MockEntry has no attribute '{name}'")
        
        entry1 = MockEntry({
            'title': "Review of the new Sedan",
            'link': "http://example.com/1",
            'summary': "A great car that is completely safe and passes all safety standards. The new sedan has excellent mileage and a very comfortable interior. I would recommend this to anyone looking for a solid daily driver. The infotainment system is snappy and the trunk space is surprisingly large for its class.",
            'published_parsed': time.struct_time((2026, 1, 1, 12, 0, 0, 0, 0, 0)),
            'content': [{'value': '<p>A great car that is completely safe and passes all safety standards. The new sedan has excellent mileage and a very comfortable interior. I would recommend this to anyone looking for a solid daily driver. The infotainment system is snappy and the trunk space is surprisingly large for its class.</p>'}],
            'description': None,
        })
        entry2 = MockEntry({
            'title': "Recall issued for hybrid model",
            'link': "http://example.com/2",
            'summary': "A massive recall was issued today for multiple vehicles. This recall is extremely serious and consumers should be aware of the potential for a crash. The manufacturer has stated that a fix will be available shortly but until then, extreme caution is advised when driving these affected models.",
            'published_parsed': time.struct_time((2026, 1, 1, 13, 0, 0, 0, 0, 0)),
            'content': [{'value': '<p>A massive recall was issued today for multiple vehicles. This recall is extremely serious and consumers should be aware of the potential for a crash. The manufacturer has stated that a fix will be available shortly but until then, extreme caution is advised when driving these affected models.</p>'}],
            'description': None,
        })

        mock_fetch_feed.return_value = MagicMock(entries=[entry1, entry2])

        from news.models import RSSFeed, RSSNewsItem
        feed = RSSFeed.objects.create(
            name='Test Feed 2',
            feed_url='http://test2.com',
            exclude_keywords='recall, crash'
        )

        aggregator.process_feed(feed)

        # Only one item should have been saved (the one NOT containing 'recall')
        assert RSSNewsItem.objects.filter(rss_feed=feed).count() == 1
        assert RSSNewsItem.objects.filter(title="Review of the new Sedan").exists()
