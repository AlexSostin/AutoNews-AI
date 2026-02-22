"""
Batch 5 — Push 0%-35% modules to 60%+
Target modules: auto_image_finder (0%), pexels_client (34%),
feed_discovery (35%), image_generator (24%)
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from types import SimpleNamespace

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════
# auto_image_finder.py — 0% → target 80%+
# ═══════════════════════════════════════════════════════════════════

class TestGetCarName:

    def test_from_car_specification(self):
        """L60-67: Extract from CarSpecification."""
        from ai_engine.modules.auto_image_finder import _get_car_name
        article = MagicMock()
        spec = MagicMock()
        spec.make = 'BMW'
        spec.model = 'iX3'
        spec.year = 2025
        article.car_specification = spec
        assert _get_car_name(article) == '2025 BMW iX3'

    def test_from_car_specification_no_year(self):
        """L66: year is None."""
        from ai_engine.modules.auto_image_finder import _get_car_name
        article = MagicMock()
        spec = MagicMock()
        spec.make = 'Tesla'
        spec.model = 'Model 3'
        spec.year = None
        article.car_specification = spec
        assert _get_car_name(article) == 'Tesla Model 3'

    def test_from_pending_specs(self):
        """L71-75: From pending_article.specs."""
        from ai_engine.modules.auto_image_finder import _get_car_name
        article = MagicMock()
        article.car_specification = None  # triggers except
        type(article).car_specification = PropertyMock(side_effect=Exception)
        pending = MagicMock()
        pending.specs = {'make': 'BYD', 'model': 'Seal', 'year': '2026'}
        assert _get_car_name(article, pending) == '2026 BYD Seal'

    def test_fallback_title(self):
        """L79-86: Fallback to cleaned title."""
        from ai_engine.modules.auto_image_finder import _get_car_name
        article = MagicMock()
        type(article).car_specification = PropertyMock(side_effect=Exception)
        article.title = '2025 BMW iX3 EV Review Test Drive 500km Range'
        result = _get_car_name(article)
        # noise words like EV, Review, Test, Drive, Range should be stripped
        assert 'BMW' in result
        assert 'Review' not in result


class TestFindReferencePhoto:

    @patch('ai_engine.modules.searcher.search_car_images')
    def test_prefer_press(self, mock_search):
        """L116-120: Press photos selected when prefer_press=True."""
        from ai_engine.modules.auto_image_finder import _find_reference_photo
        mock_search.return_value = [
            {'url': 'https://img.com/press.jpg', 'is_press': True, 'width': 800, 'height': 600, 'source': 'bmw'},
            {'url': 'https://img.com/other.jpg', 'is_press': False, 'width': 1200, 'height': 900, 'source': 'flickr'},
        ]
        result = _find_reference_photo('BMW iX3', prefer_press=True)
        assert result == 'https://img.com/press.jpg'

    @patch('ai_engine.modules.searcher.search_car_images')
    def test_fallback_to_largest(self, mock_search):
        """L124-127: No press → largest resolution."""
        from ai_engine.modules.auto_image_finder import _find_reference_photo
        mock_search.return_value = [
            {'url': 'https://img.com/small.jpg', 'is_press': False, 'width': 400, 'height': 300, 'source': 'x'},
            {'url': 'https://img.com/big.jpg', 'is_press': False, 'width': 1920, 'height': 1080, 'source': 'y'},
        ]
        result = _find_reference_photo('BMW iX3', prefer_press=True)
        assert result == 'https://img.com/big.jpg'

    @patch('ai_engine.modules.searcher.search_car_images')
    def test_no_results(self, mock_search):
        """L110-111: No results → None."""
        from ai_engine.modules.auto_image_finder import _find_reference_photo
        mock_search.return_value = []
        result = _find_reference_photo('Unknown Car')
        assert result is None


class TestFindAndAttachImage:

    @patch('news.models.AutomationSettings.load')
    def test_auto_image_off(self, mock_load):
        """L36-37: auto_image_mode='off' → skip."""
        from ai_engine.modules.auto_image_finder import find_and_attach_image
        mock_settings = MagicMock()
        mock_settings.auto_image_mode = 'off'
        mock_load.return_value = mock_settings
        article = MagicMock()
        result = find_and_attach_image(article)
        assert result['success'] is False
        assert result['method'] == 'off'

    @patch('news.models.AutomationSettings.load')
    def test_article_already_has_image(self, mock_load):
        """L40-42: Article already has image → skip."""
        from ai_engine.modules.auto_image_finder import find_and_attach_image
        mock_settings = MagicMock()
        mock_settings.auto_image_mode = 'search_and_ai'
        mock_load.return_value = mock_settings
        article = MagicMock()
        article.image = 'images/existing.jpg'
        result = find_and_attach_image(article)
        assert result['success'] is True
        assert result['method'] == 'existing'

    @patch('ai_engine.modules.auto_image_finder._find_reference_photo')
    @patch('ai_engine.modules.auto_image_finder._get_car_name')
    @patch('news.models.AutomationSettings.load')
    def test_no_reference_found(self, mock_load, mock_name, mock_find):
        """L48-49: No reference photo → fail."""
        from ai_engine.modules.auto_image_finder import find_and_attach_image
        mock_settings = MagicMock()
        mock_settings.auto_image_mode = 'search_and_ai'
        mock_settings.auto_image_prefer_press = True
        mock_load.return_value = mock_settings
        mock_name.return_value = 'BMW iX3'
        mock_find.return_value = None
        article = MagicMock()
        article.image = ''
        result = find_and_attach_image(article)
        assert result['success'] is False
        assert result['method'] == 'no_reference'


class TestGenerateAiImage:

    @patch('ai_engine.modules.image_generator.generate_car_image')
    def test_success(self, mock_gen):
        """L146-155: Successful AI image generation."""
        import base64
        from ai_engine.modules.auto_image_finder import _generate_ai_image
        mock_gen.return_value = {
            'success': True,
            'image_data': base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100).decode(),
            'mime_type': 'image/png',
        }
        article = MagicMock()
        article.slug = 'test-article'
        result = _generate_ai_image(article, 'BMW iX3', 'https://img.com/ref.jpg')
        assert result['success'] is True
        assert result['method'] == 'ai_generate'
        article.image.save.assert_called_once()

    @patch('ai_engine.modules.image_generator.generate_car_image')
    def test_generation_failed(self, mock_gen):
        """L149-151: AI generation returns error."""
        from ai_engine.modules.auto_image_finder import _generate_ai_image
        mock_gen.return_value = {'success': False, 'error': 'API rate limit'}
        article = MagicMock()
        result = _generate_ai_image(article, 'BMW iX3', 'https://img.com/ref.jpg')
        assert result['success'] is False
        assert 'API rate limit' in result['error']


# ═══════════════════════════════════════════════════════════════════
# pexels_client.py — 34% → target 80%+
# ═══════════════════════════════════════════════════════════════════

class TestPexelsClient:

    @patch.dict('os.environ', {'PEXELS_API_KEY': ''}, clear=False)
    def test_init_no_key(self):
        """L38-41: No API key → warning."""
        from ai_engine.modules.pexels_client import PexelsClient
        client = PexelsClient(api_key='')
        assert client.api_key == ''

    @patch.dict('os.environ', {'PEXELS_API_KEY': ''}, clear=False)
    def test_search_no_key(self):
        """L58-60: search_photos without key → None."""
        from ai_engine.modules.pexels_client import PexelsClient
        client = PexelsClient(api_key='')
        result = client.search_photos('tesla')
        assert result is None

    @patch('ai_engine.modules.pexels_client.requests.get')
    def test_search_success(self, mock_get):
        """L73-86: Successful search."""
        from ai_engine.modules.pexels_client import PexelsClient
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'total_results': 5,
            'photos': [{'src': {'large': 'https://img.pexels.com/1.jpg'}}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        client = PexelsClient(api_key='test-key')
        result = client.search_photos('tesla car')
        assert result is not None
        assert result['total_results'] == 5

    @patch('ai_engine.modules.pexels_client.requests.get')
    def test_search_error(self, mock_get):
        """L88-90: Request error → None."""
        import requests
        from ai_engine.modules.pexels_client import PexelsClient, REQUEST_CACHE
        REQUEST_CACHE.clear()
        mock_get.side_effect = requests.exceptions.ConnectionError('timeout')
        client = PexelsClient(api_key='test-key-unique')
        result = client.search_photos('uniquequery_error_test_12345')
        assert result is None

    def test_get_best_photo_url(self):
        """L107-120: Extract best photo URL."""
        from ai_engine.modules.pexels_client import PexelsClient
        client = PexelsClient(api_key='test')
        results = {
            'photos': [
                {'src': {'large': 'https://img.pexels.com/large.jpg', 'medium': 'https://img.pexels.com/med.jpg'}}
            ]
        }
        url = client.get_best_photo_url(results)
        assert url == 'https://img.pexels.com/large.jpg'

    def test_get_best_photo_url_empty(self):
        """L106-107: No photos → None."""
        from ai_engine.modules.pexels_client import PexelsClient
        client = PexelsClient(api_key='test')
        assert client.get_best_photo_url(None) is None
        assert client.get_best_photo_url({}) is None
        assert client.get_best_photo_url({'photos': []}) is None


class TestPexelsExtractKeywords:

    def test_with_brand(self):
        """L124-178: Extract keywords from title with brand."""
        from ai_engine.modules.pexels_client import extract_keywords
        result = extract_keywords('2025 BMW iX3 Electric SUV Review', brand='BMW')
        assert 'BMW' in result

    def test_auto_detect_brand(self):
        """L148-154: Brand auto-detected from title."""
        from ai_engine.modules.pexels_client import extract_keywords
        result = extract_keywords('Tesla Model 3 gets new update')
        assert 'Tesla' in result

    def test_adds_car_suffix(self):
        """L172-173: If no automotive term, adds 'car'."""
        from ai_engine.modules.pexels_client import extract_keywords
        result = extract_keywords('Review of 2025 Performance')
        assert 'car' in result.lower()


class TestSearchAutomotiveImage:

    @patch('ai_engine.modules.pexels_client.PEXELS_ENABLED', False)
    def test_disabled(self):
        """L196-198: Disabled → None."""
        from ai_engine.modules.pexels_client import search_automotive_image
        result = search_automotive_image('Tesla Model 3')
        assert result is None

    @patch('ai_engine.modules.pexels_client.PexelsClient')
    @patch('ai_engine.modules.pexels_client.PEXELS_ENABLED', True)
    def test_primary_success(self, mock_cls):
        """L203-207: Primary query returns image."""
        from ai_engine.modules.pexels_client import search_automotive_image
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.search_photos.return_value = {'photos': [{'src': {'large': 'https://img.com/1.jpg'}}]}
        mock_client.get_best_photo_url.return_value = 'https://img.com/1.jpg'
        result = search_automotive_image('Tesla Model 3', brand='Tesla')
        assert result == 'https://img.com/1.jpg'

    @patch('ai_engine.modules.pexels_client.PexelsClient')
    @patch('ai_engine.modules.pexels_client.PEXELS_ENABLED', True)
    def test_fallback_brand_car(self, mock_cls):
        """L210-215: Primary fails, fallback to brand + car."""
        from ai_engine.modules.pexels_client import search_automotive_image
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        # First call returns None, second returns URL
        mock_client.get_best_photo_url.side_effect = [None, 'https://img.com/fallback.jpg']
        result = search_automotive_image('Unusual concept', brand='BMW')
        assert result == 'https://img.com/fallback.jpg'


# ═══════════════════════════════════════════════════════════════════
# feed_discovery.py — 35% → target 70%+
# ═══════════════════════════════════════════════════════════════════

class TestValidateFeed:

    @patch('feedparser.parse')
    @patch('ai_engine.modules.feed_discovery.requests.get')
    def test_valid_feed(self, mock_get, mock_fp):
        """L202-222: Valid feed returns title + entry_count."""
        from ai_engine.modules.feed_discovery import _validate_feed
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'<rss></rss>'
        mock_get.return_value = mock_resp
        mock_parsed = MagicMock()
        mock_parsed.entries = [MagicMock(), MagicMock()]
        mock_parsed.feed.get.return_value = 'Test Feed'
        mock_fp.return_value = mock_parsed
        result = _validate_feed('https://example.com/feed')
        assert result['valid'] is True
        assert result['entry_count'] == 2

    @patch('ai_engine.modules.feed_discovery.requests.get')
    def test_invalid_status(self, mock_get):
        """L212-213: Non-200 → invalid."""
        from ai_engine.modules.feed_discovery import _validate_feed
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        result = _validate_feed('https://example.com/feed')
        assert result['valid'] is False

    @patch('ai_engine.modules.feed_discovery.requests.get')
    def test_exception(self, mock_get):
        """L226-228: Exception → invalid."""
        from ai_engine.modules.feed_discovery import _validate_feed
        mock_get.side_effect = Exception('timeout')
        result = _validate_feed('https://example.com/feed')
        assert result['valid'] is False


class TestAutoDetectRSS:

    @patch('ai_engine.modules.feed_discovery.requests.get')
    def test_detect_from_link_tag(self, mock_get):
        """L164-177: RSS link tag in HTML."""
        from ai_engine.modules.feed_discovery import _auto_detect_rss
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><head><link type="application/rss+xml" href="/feed/rss.xml"></head></html>'
        mock_get.return_value = mock_resp
        result = _auto_detect_rss('https://example.com')
        assert result is not None
        assert 'feed' in result

    @patch('ai_engine.modules.feed_discovery.requests.get')
    def test_detect_not_found(self, mock_get):
        """L161-162: Non-200 → None."""
        from ai_engine.modules.feed_discovery import _auto_detect_rss
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        result = _auto_detect_rss('https://example.com')
        assert result is None

    @patch('ai_engine.modules.feed_discovery.requests.get')
    def test_detect_exception(self, mock_get):
        """L197-199: RequestException → None."""
        import requests
        from ai_engine.modules.feed_discovery import _auto_detect_rss
        mock_get.side_effect = requests.RequestException('timeout')
        result = _auto_detect_rss('https://example.com')
        assert result is None


class TestDiscoverFeeds:

    @patch('ai_engine.modules.feed_discovery._validate_feed')
    @patch('ai_engine.modules.feed_discovery._auto_detect_rss')
    @patch('news.models.RSSFeed.objects')
    def test_discover_basic(self, mock_qs, mock_detect, mock_validate):
        """L70-154: Full discover flow — simple path."""
        from ai_engine.modules.feed_discovery import discover_feeds
        mock_qs.values_list.return_value = []
        mock_detect.return_value = None
        mock_validate.return_value = {'valid': True, 'title': 'Test', 'entry_count': 5}
        results = discover_feeds(check_license=False)
        assert isinstance(results, list)
        assert len(results) > 0
        # All items should have expected keys
        for r in results[:3]:
            assert 'name' in r
            assert 'website_url' in r
            assert 'source_type' in r


# ═══════════════════════════════════════════════════════════════════
# image_generator.py — 24% → target 50%+
# ═══════════════════════════════════════════════════════════════════

class TestImageGenerator:

    def test_get_available_styles(self):
        """L173-178: Returns style list."""
        from ai_engine.modules.image_generator import get_available_styles
        styles = get_available_styles()
        assert isinstance(styles, list)
        assert len(styles) > 0
        for style in styles:
            assert 'value' in style or 'key' in style or isinstance(style, dict)

    def test_scene_styles_dict(self):
        """L28-44: SCENE_STYLES has expected keys."""
        from ai_engine.modules.image_generator import SCENE_STYLES
        assert 'scenic_road' in SCENE_STYLES
        assert 'showroom' in SCENE_STYLES
        assert isinstance(SCENE_STYLES['scenic_road'], str)

    @patch('ai_engine.modules.image_generator.GENAI_NEW_SDK', False)
    def test_generate_no_sdk(self):
        """L56-57: No SDK → error."""
        from ai_engine.modules.image_generator import generate_car_image
        result = generate_car_image('https://img.com/ref.jpg', 'BMW iX3')
        assert result.get('success') is False


# ═══════════════════════════════════════════════════════════════════
# pexels_client.py — test_pexels_connection
# ═══════════════════════════════════════════════════════════════════

class TestPexelsConnection:

    @patch('ai_engine.modules.pexels_client.PEXELS_ENABLED', False)
    def test_not_configured(self):
        """L229-232: No API key → False."""
        from ai_engine.modules.pexels_client import test_pexels_connection
        result = test_pexels_connection()
        assert result is False

    @patch('ai_engine.modules.pexels_client.search_automotive_image')
    @patch('ai_engine.modules.pexels_client.PEXELS_ENABLED', True)
    def test_success(self, mock_search):
        """L237-240: API returns image → True."""
        from ai_engine.modules.pexels_client import test_pexels_connection
        mock_search.return_value = 'https://img.com/tesla.jpg'
        result = test_pexels_connection()
        assert result is True

    @patch('ai_engine.modules.pexels_client.search_automotive_image')
    @patch('ai_engine.modules.pexels_client.PEXELS_ENABLED', True)
    def test_failure(self, mock_search):
        """L242-243: API fails → False."""
        from ai_engine.modules.pexels_client import test_pexels_connection
        mock_search.return_value = None
        result = test_pexels_connection()
        assert result is False


# ═══════════════════════════════════════════════════════════════════
# PexelsClient cache
# ═══════════════════════════════════════════════════════════════════

class TestPexelsClientCache:

    @patch('ai_engine.modules.pexels_client.requests.get')
    def test_cache_hit(self, mock_get):
        """L64-68: Second call uses cache."""
        from ai_engine.modules.pexels_client import PexelsClient, REQUEST_CACHE
        # Clear cache
        REQUEST_CACHE.clear()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'total_results': 1, 'photos': []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        client = PexelsClient(api_key='test-key')
        # First call
        client.search_photos('cache test query unique123')
        # Second call — should be cached
        result = client.search_photos('cache test query unique123')
        assert result is not None
        # requests.get called only once (second was cache)
        assert mock_get.call_count == 1
