"""
Batch 3 — searcher.py, rss_aggregator.py, auto_publisher.py
Target: searcher 72→85%, rss_aggregator 64→80%, auto_publisher 69→85%
"""
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from types import SimpleNamespace

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════
# searcher.py — 72% → 85%
# Focus: _is_blocked, _is_trusted, _classify_license, _is_automotive_result,
#        _scrape_page_content edge cases, _search_ddgs, get_web_context
# ═══════════════════════════════════════════════════════════════════

class TestSearcherHelpers:

    def test_is_blocked_youtube(self):
        from ai_engine.modules.searcher import _is_blocked
        assert _is_blocked('https://youtube.com/watch?v=1') is True

    def test_is_blocked_normal(self):
        from ai_engine.modules.searcher import _is_blocked
        assert _is_blocked('https://caranddriver.com/reviews') is False

    def test_is_trusted_known(self):
        from ai_engine.modules.searcher import _is_trusted
        assert _is_trusted('https://caranddriver.com/reviews/bmw') is True

    def test_is_trusted_unknown(self):
        from ai_engine.modules.searcher import _is_trusted
        assert _is_trusted('https://randomsite.com/page') is False

    def test_is_automotive_trusted(self):
        """L209-210: Trusted → always automotive."""
        from ai_engine.modules.searcher import _is_automotive_result
        assert _is_automotive_result({'trusted': True, 'title': '', 'desc': ''}) is True

    def test_is_automotive_keyword_match(self):
        """L211-212: Has automotive keyword."""
        from ai_engine.modules.searcher import _is_automotive_result
        assert _is_automotive_result({
            'trusted': False, 'title': 'BYD Seal EV review',
            'desc': 'horsepower and torque specs'
        }) is True

    def test_is_automotive_no_match(self):
        """L212: No automotive keywords → False."""
        from ai_engine.modules.searcher import _is_automotive_result
        assert _is_automotive_result({
            'trusted': False, 'title': 'Xiaomi 15 Pro',
            'desc': 'smartphone camera quality'
        }) is False


class TestClassifyLicense:

    def test_cc_domain(self):
        from ai_engine.modules.searcher import _classify_license
        assert _classify_license('https://upload.wikimedia.org/img.jpg', '') == 'cc'

    def test_editorial_domain(self):
        from ai_engine.modules.searcher import _classify_license
        assert _classify_license('https://cdn.motor1.com/img.jpg', '') == 'editorial'

    def test_unknown_domain(self):
        from ai_engine.modules.searcher import _classify_license
        assert _classify_license('https://random.com/img.jpg', '') == 'unknown'

    def test_editorial_from_source(self):
        from ai_engine.modules.searcher import _classify_license
        assert _classify_license('https://cdn.example.com/x.jpg', 'newsroom.byd.com') == 'editorial'


class TestScrapePageContent:

    @patch('ai_engine.modules.searcher.requests.get')
    def test_timeout(self, mock_get):
        """L129-131: Timeout → empty string."""
        import requests as req
        from ai_engine.modules.searcher import _scrape_page_content
        mock_get.side_effect = req.exceptions.Timeout()
        assert _scrape_page_content('https://example.com') == ""

    @patch('ai_engine.modules.searcher.requests.get')
    def test_non_html_content(self, mock_get):
        """L76-77: Non-HTML → empty string."""
        from ai_engine.modules.searcher import _scrape_page_content
        mock_resp = MagicMock()
        mock_resp.headers = {'content-type': 'application/pdf'}
        mock_get.return_value = mock_resp
        assert _scrape_page_content('https://example.com/doc.pdf') == ""

    @patch('ai_engine.modules.searcher.requests.get')
    def test_no_body(self, mock_get):
        """L105-106: No body tag → empty string."""
        from ai_engine.modules.searcher import _scrape_page_content
        mock_resp = MagicMock()
        mock_resp.headers = {'content-type': 'text/html'}
        mock_resp.text = ''
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        assert _scrape_page_content('https://example.com') == ""

    @patch('ai_engine.modules.searcher.requests.get')
    def test_successful_scrape(self, mock_get):
        """L94-127: Successful scrape with article content."""
        from ai_engine.modules.searcher import _scrape_page_content
        html = """<html><body><article>
            <p>The BYD Seal is an impressive electric sedan with 530 horsepower and AWD.</p>
        </article></body></html>"""
        mock_resp = MagicMock()
        mock_resp.headers = {'content-type': 'text/html'}
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        result = _scrape_page_content('https://example.com')
        assert 'BYD Seal' in result

    @patch('ai_engine.modules.searcher.requests.get')
    def test_truncation_at_sentence(self, mock_get):
        """L119-125: Content > max_chars → truncated at sentence boundary."""
        from ai_engine.modules.searcher import _scrape_page_content
        long_text = ('This is a sentence about electric cars. ' * 100)
        html = f"<html><body><p>{long_text}</p></body></html>"
        mock_resp = MagicMock()
        mock_resp.headers = {'content-type': 'text/html'}
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        result = _scrape_page_content('https://example.com', max_chars=200)
        assert len(result) <= 210  # ~200 + small margin


class TestSearchDDGS:

    @patch('ai_engine.modules.searcher.HAS_DDGS', False)
    def test_no_ddgs(self):
        """L145-146: No DDGS → empty list."""
        from ai_engine.modules.searcher import _search_ddgs
        assert _search_ddgs('test') == []

    @patch('ai_engine.modules.searcher.DDGS')
    @patch('ai_engine.modules.searcher.HAS_DDGS', True)
    def test_successful_search(self, mock_ddgs_cls):
        """L148-163: Successful DDGS search."""
        from ai_engine.modules.searcher import _search_ddgs
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text.return_value = [
            {'title': 'BYD Seal Review', 'body': 'Electric sedan', 'href': 'https://caranddriver.com/byd'},
            {'title': 'YouTube BYD', 'body': 'Video', 'href': 'https://youtube.com/123'},
        ]
        mock_ddgs_cls.return_value = mock_ddgs
        results = _search_ddgs('BYD Seal')
        assert len(results) == 1  # YouTube blocked
        assert results[0]['trusted'] is True

    @patch('ai_engine.modules.searcher.DDGS')
    @patch('ai_engine.modules.searcher.HAS_DDGS', True)
    def test_ddgs_exception(self, mock_ddgs_cls):
        """L164-166: DDGS exception → empty list."""
        from ai_engine.modules.searcher import _search_ddgs
        mock_ddgs_cls.side_effect = Exception('Rate limited')
        assert _search_ddgs('test') == []


class TestSearchGoogle:

    @patch('ai_engine.modules.searcher.HAS_GOOGLE', False)
    def test_no_google(self):
        """L174-175: No google → empty list."""
        from ai_engine.modules.searcher import _search_google
        assert _search_google('test') == []


class TestGetWebContext:

    def test_not_specified_make(self):
        """L419-420: Make='Not specified' → empty string."""
        from ai_engine.modules.searcher import get_web_context
        assert get_web_context({'make': 'Not specified', 'model': 'X'}) == ""

    def test_not_specified_model(self):
        from ai_engine.modules.searcher import get_web_context
        assert get_web_context({'make': 'BYD', 'model': 'Not specified'}) == ""


class TestSearchBingImages:

    @patch('ai_engine.modules.searcher.requests.get')
    def test_bing_non_200(self, mock_get):
        """L498-500: Non-200 → empty list."""
        from ai_engine.modules.searcher import _search_bing_images
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_get.return_value = mock_resp
        assert _search_bing_images('test') == []

    @patch('ai_engine.modules.searcher.requests.get')
    def test_bing_exception(self, mock_get):
        """L545-547: Exception → empty list."""
        from ai_engine.modules.searcher import _search_bing_images
        mock_get.side_effect = Exception('Connection error')
        assert _search_bing_images('test') == []


class TestSearchCarImages:

    @patch('ai_engine.modules.searcher.HAS_DDGS', False)
    @patch('ai_engine.modules.searcher._search_bing_images')
    @patch('ai_engine.modules.searcher._search_google_images')
    def test_all_fail_empty(self, mock_google, mock_bing):
        """L686-696: All providers fail → empty."""
        from ai_engine.modules.searcher import search_car_images
        mock_bing.return_value = []
        mock_google.return_value = []
        result = search_car_images('test')
        assert result == []

    @patch('ai_engine.modules.searcher.HAS_DDGS', False)
    @patch('ai_engine.modules.searcher._search_bing_images')
    def test_bing_fallback(self, mock_bing):
        """L682-684: DDGS fails → Bing fallback."""
        from ai_engine.modules.searcher import search_car_images
        mock_bing.return_value = [
            {'title': 'BYD', 'url': 'https://cdn.motor1.com/img.jpg',
             'thumbnail': '', 'source': '', 'width': 1920, 'height': 1080,
             'is_press': True, 'license': 'editorial'}
        ]
        result = search_car_images('BYD Seal')
        assert len(result) == 1


# ═══════════════════════════════════════════════════════════════════
# rss_aggregator.py — 64% → 80%
# Focus: fetch_feed error/empty, is_duplicate title similarity,
#        extract_images, extract_og_image, extract_content,
#        parse_entry_date, clean_publisher_mentions, process_feed
# ═══════════════════════════════════════════════════════════════════

class TestRetryAICall:

    @patch('ai_engine.modules.rss_aggregator.time.sleep')
    def test_retry_success_on_second(self, mock_sleep):
        """L20-33: Succeed on second attempt."""
        from ai_engine.modules.rss_aggregator import _retry_ai_call
        call_count = 0
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception('Temporary error')
            return 'success'
        result = _retry_ai_call(flaky_func, max_retries=3)
        assert result == 'success'

    @patch('ai_engine.modules.rss_aggregator.time.sleep')
    def test_retry_all_fail(self, mock_sleep):
        """L33: All retries fail → raise."""
        from ai_engine.modules.rss_aggregator import _retry_ai_call
        def always_fail():
            raise ValueError('Permanent error')
        with pytest.raises(ValueError, match='Permanent error'):
            _retry_ai_call(always_fail, max_retries=2)


class TestRSSAggregator:

    def _make_agg(self):
        from ai_engine.modules.rss_aggregator import RSSAggregator
        return RSSAggregator()

    def test_content_hash(self):
        agg = self._make_agg()
        h = agg.calculate_content_hash('Hello world')
        assert len(h) == 64  # SHA256

    def test_title_similarity_identical(self):
        agg = self._make_agg()
        assert agg.calculate_title_similarity('BYD Seal', 'BYD Seal') == 1.0

    def test_title_similarity_different(self):
        agg = self._make_agg()
        sim = agg.calculate_title_similarity('BYD Seal Review', 'Tesla Model 3')
        assert sim < 0.5

    @patch('ai_engine.modules.rss_aggregator.feedparser.parse')
    def test_fetch_feed_success(self, mock_parse):
        """L53-65: Valid feed → entries returned."""
        agg = self._make_agg()
        mock_parse.return_value = MagicMock(
            bozo=False,
            entries=[{'title': 'Test'}]
        )
        result = agg.fetch_feed('https://example.com/rss')
        assert result is not None

    @patch('ai_engine.modules.rss_aggregator.feedparser.parse')
    def test_fetch_feed_no_entries(self, mock_parse):
        """L60-62: Empty entries → None."""
        agg = self._make_agg()
        mock_parse.return_value = MagicMock(bozo=False, entries=[])
        assert agg.fetch_feed('https://example.com/rss') is None

    @patch('ai_engine.modules.rss_aggregator.feedparser.parse')
    def test_fetch_feed_exception(self, mock_parse):
        """L67-69: Exception → None."""
        agg = self._make_agg()
        mock_parse.side_effect = Exception('Network error')
        assert agg.fetch_feed('https://example.com/rss') is None

    def test_is_duplicate_by_hash(self):
        """L115-117: Content hash match → True."""
        from news.models import RSSFeed, RSSNewsItem
        agg = self._make_agg()
        feed = RSSFeed.objects.create(name='Dup Test', feed_url='https://dup-test.com/rss')
        content = 'This is unique content for dedup test'
        hash_val = agg.calculate_content_hash(content)
        RSSNewsItem.objects.create(
            rss_feed=feed, title='Existing', content_hash=hash_val
        )
        assert agg.is_duplicate('New Title', content) is True

    def test_is_duplicate_by_source_url(self):
        """L118-120: Source URL match → True."""
        from news.models import RSSFeed, RSSNewsItem
        agg = self._make_agg()
        feed = RSSFeed.objects.create(name='URL Test', feed_url='https://url-test.com/rss')
        RSSNewsItem.objects.create(
            rss_feed=feed, title='Existing',
            source_url='https://example.com/article-1',
        )
        assert agg.is_duplicate('Different Title', 'different content',
                                source_url='https://example.com/article-1') is True

    def test_is_duplicate_by_title_similarity(self):
        """L146-150: Title similarity ≥ 0.80 → True."""
        from news.models import RSSFeed, RSSNewsItem
        agg = self._make_agg()
        feed = RSSFeed.objects.create(name='Sim Test', feed_url='https://sim-test.com/rss')
        RSSNewsItem.objects.create(
            rss_feed=feed, title='2026 BYD Seal Premium Electric Sedan Review',
        )
        assert agg.is_duplicate(
            '2026 BYD Seal Premium Electric Sedan Reviews',
            'completely different content'
        ) is True

    def test_is_duplicate_false(self):
        """L175: No match → False."""
        agg = self._make_agg()
        assert agg.is_duplicate(
            'Completely Unique Title That Does Not Exist',
            'Completely unique content'
        ) is False

    def test_extract_images_media_content(self):
        """L196-199: media:content → image URL extracted."""
        agg = self._make_agg()
        entry = MagicMock(spec=[])
        entry.media_content = [{'medium': 'image', 'url': 'https://img.com/1.jpg'}]
        entry.media_thumbnail = []
        entry.enclosures = []
        # Make hasattr work correctly for content/summary/description
        type(entry).__dict__  # force MagicMock
        result = agg.extract_images(entry)
        assert 'https://img.com/1.jpg' in result

    def test_extract_images_enclosure(self):
        """L207-210: enclosure image → extracted."""
        agg = self._make_agg()
        entry = MagicMock()
        del entry.media_content
        del entry.media_thumbnail
        entry.enclosures = [{'type': 'image/jpeg', 'href': 'https://img.com/enc.jpg'}]
        del entry.content
        del entry.summary
        del entry.description
        result = agg.extract_images(entry)
        assert 'https://img.com/enc.jpg' in result

    def test_convert_plain_text_to_html(self):
        """L299-342: Plain text → HTML with paragraphs."""
        agg = self._make_agg()
        text = "First paragraph.\n\nSecond paragraph.\n\nhttps://example.com is a link."
        html = agg.convert_plain_text_to_html(text)
        assert '<p>' in html
        assert '<a href=' in html

    def test_clean_publisher_mentions(self):
        """L344-389: Publisher self-references removed."""
        agg = self._make_agg()
        text = "Article content. The post BYD unveils new car appeared first on CarNews."
        cleaned = agg.clean_publisher_mentions(text)
        assert 'appeared first on' not in cleaned

    def test_extract_plain_text(self):
        """L391-423: Extract plain text from entry."""
        agg = self._make_agg()
        entry = MagicMock()
        entry.content = [{'value': '<p>Hello <b>world</b></p>'}]
        del entry.summary
        del entry.description
        result = agg.extract_plain_text(entry)
        assert 'Hello world' in result

    def test_extract_plain_text_empty(self):
        """L422-423: No content → empty string."""
        agg = self._make_agg()
        entry = MagicMock()
        del entry.content
        del entry.summary
        del entry.description
        result = agg.extract_plain_text(entry)
        assert result == ""

    def test_extract_content_html(self):
        """L425-443: extract_content returns HTML."""
        agg = self._make_agg()
        entry = MagicMock()
        entry.content = [{'value': '<p>Electric vehicles are growing fast in 2026.</p>'}]
        del entry.summary
        del entry.description
        result = agg.extract_content(entry)
        assert '<p>' in result

    def test_parse_entry_date_valid(self):
        """L455-463: Valid time_struct → datetime."""
        agg = self._make_agg()
        entry = MagicMock()
        entry.published_parsed = (2026, 2, 21, 12, 0, 0, 0, 0, 0)
        result = agg.parse_entry_date(entry)
        assert result is not None

    def test_parse_entry_date_none(self):
        """L465: No date fields → None."""
        agg = self._make_agg()
        entry = MagicMock()
        del entry.published_parsed
        del entry.updated_parsed
        result = agg.parse_entry_date(entry)
        assert result is None

    @patch('requests.get')
    def test_extract_og_image(self, mock_get):
        """L246-268: og:image extraction."""
        agg = self._make_agg()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><head><meta property="og:image" content="https://img.com/og.jpg"></head></html>'
        mock_get.return_value = mock_resp
        result = agg.extract_og_image('https://example.com/article')
        assert result == 'https://img.com/og.jpg'

    def test_extract_og_image_no_url(self):
        """L243-244: No url → None."""
        agg = self._make_agg()
        assert agg.extract_og_image('') is None
        assert agg.extract_og_image(None) is None

    @patch('requests.get')
    def test_extract_og_image_error(self, mock_get):
        """L295-297: Exception → None."""
        agg = self._make_agg()
        mock_get.side_effect = Exception('timeout')
        result = agg.extract_og_image('https://example.com')
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# auto_publisher.py — 69% → 85%
# Focus: _log_decision, disabled check, daily/hourly limits,
#        safety gating, image check, publish cycle
# ═══════════════════════════════════════════════════════════════════

class TestLogDecision:

    def test_log_decision(self):
        """L16-40: _log_decision creates AutoPublishLog."""
        from ai_engine.modules.auto_publisher import _log_decision
        from news.models import PendingArticle
        pending = PendingArticle.objects.create(
            title='Log Test', video_url='https://youtube.com/watch?v=logtest'
        )
        # Should not crash
        _log_decision(pending, 'skipped_safety', 'Testing log')


class TestAutoPublishPending:

    @patch('news.models.AutomationSettings.load')
    def test_disabled(self, mock_load):
        """L54-55: auto_publish_enabled=False → 0, 'disabled'."""
        from ai_engine.modules.auto_publisher import auto_publish_pending
        mock_settings = MagicMock()
        mock_settings.auto_publish_enabled = False
        mock_load.return_value = mock_settings
        count, reason = auto_publish_pending()
        assert count == 0
        assert 'disabled' in reason

    @patch('news.models.AutomationSettings.load')
    def test_daily_limit(self, mock_load):
        """L62-64: Daily limit reached → 0."""
        from ai_engine.modules.auto_publisher import auto_publish_pending
        mock_settings = MagicMock()
        mock_settings.auto_publish_enabled = True
        mock_settings.auto_publish_today_count = 10
        mock_settings.auto_publish_max_per_day = 10
        mock_load.return_value = mock_settings
        count, reason = auto_publish_pending()
        assert count == 0
        assert 'daily limit' in reason

    @patch('news.models.Article.objects')
    @patch('news.models.AutomationSettings.load')
    def test_hourly_limit(self, mock_load, mock_article_objects):
        """L73-75: Hourly limit reached → 0."""
        from ai_engine.modules.auto_publisher import auto_publish_pending
        mock_settings = MagicMock()
        mock_settings.auto_publish_enabled = True
        mock_settings.auto_publish_today_count = 0
        mock_settings.auto_publish_max_per_day = 10
        mock_settings.auto_publish_max_per_hour = 2
        mock_load.return_value = mock_settings
        mock_article_objects.filter.return_value.count.return_value = 5
        count, reason = auto_publish_pending()
        assert count == 0
        assert 'hourly limit' in reason
