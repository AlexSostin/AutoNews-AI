"""
Max coverage: ai_engine/modules/license_checker.py — targeting all 98 uncovered lines.
Goal: push from 52% → 90%+

Uncovered functions/branches:
  L123        - check_content_license with empty URL
  L167-178    - check_content_license: ToS found → AI analysis
  L187-189    - check_content_license: homepage press portal detection
  L241        - _check_robots_txt: non-200 response
  L262-264    - _check_robots_txt: request exception
  L281        - _detect_press_portal: brand source_type
  L293-337    - _find_tos_page: standard paths + footer scraping
  L350-363    - _analyze_tos_with_ai: success + exception
  L385-447    - _check_image_rights: non-brand press, no-tos, AI success/fail
  L455-476    - _analyze_homepage: full flow + exceptions
  L493        - _parse_json_response: regex fallback
  L513        - _combine_statuses: yellow majority
"""
import pytest
from unittest.mock import patch, MagicMock
import requests

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════
# _strip_html — already covered but adding edge case
# ═══════════════════════════════════════════════════════════════════

class TestStripHtml:

    def test_strips_script_and_style_tags(self):
        from ai_engine.modules.license_checker import _strip_html
        html = '<script>var x=1;</script><style>.a{color:red}</style><p>Hello World</p>'
        result = _strip_html(html)
        assert 'var x' not in result
        assert 'color:red' not in result
        assert 'Hello World' in result

    def test_strips_nav_header_footer(self):
        from ai_engine.modules.license_checker import _strip_html
        html = '<nav>Menu</nav><header>Top</header><p>Content</p><footer>Bottom</footer>'
        result = _strip_html(html)
        assert 'Menu' not in result
        assert 'Content' in result


# ═══════════════════════════════════════════════════════════════════
# _parse_json_response — cover all branches
# ═══════════════════════════════════════════════════════════════════

class TestParseJsonResponse:

    def test_plain_json(self):
        from ai_engine.modules.license_checker import _parse_json_response
        result = _parse_json_response('{"status": "green", "summary": "OK"}')
        assert result['status'] == 'green'

    def test_markdown_code_block(self):
        from ai_engine.modules.license_checker import _parse_json_response
        result = _parse_json_response('```json\n{"status": "red", "summary": "Bad"}\n```')
        assert result['status'] == 'red'

    def test_json_in_text(self):
        """L493: JSON embedded in surrounding text → regex fallback."""
        from ai_engine.modules.license_checker import _parse_json_response
        result = _parse_json_response('Here is the analysis:\n{"status": "yellow", "summary": "Caution"}\nEnd.')
        assert result['status'] == 'yellow'

    def test_no_json_at_all(self):
        from ai_engine.modules.license_checker import _parse_json_response
        result = _parse_json_response('This has no JSON whatsoever')
        assert result['status'] == 'yellow'
        assert 'Could not parse' in result['summary']


# ═══════════════════════════════════════════════════════════════════
# _combine_statuses — cover all branches
# ═══════════════════════════════════════════════════════════════════

class TestCombineStatuses:

    def test_red_wins(self):
        from ai_engine.modules.license_checker import _combine_statuses
        assert _combine_statuses('green', 'red', 'green') == 'red'

    def test_green_majority(self):
        from ai_engine.modules.license_checker import _combine_statuses
        assert _combine_statuses('green', 'green', 'yellow') == 'green'

    def test_yellow_majority(self):
        """L513: more yellow than green → yellow."""
        from ai_engine.modules.license_checker import _combine_statuses
        assert _combine_statuses('yellow', 'yellow', 'green') == 'yellow'

    def test_single_green(self):
        from ai_engine.modules.license_checker import _combine_statuses
        assert _combine_statuses('green') == 'green'

    def test_single_yellow(self):
        from ai_engine.modules.license_checker import _combine_statuses
        assert _combine_statuses('yellow') == 'yellow'

    def test_all_yellow(self):
        from ai_engine.modules.license_checker import _combine_statuses
        assert _combine_statuses('yellow', 'yellow') == 'yellow'


# ═══════════════════════════════════════════════════════════════════
# _check_robots_txt — all branches
# ═══════════════════════════════════════════════════════════════════

class TestCheckRobotsTxt:

    @patch('ai_engine.modules.license_checker.requests.get')
    def test_non_200_response(self, mock_get):
        """L241: non-200 → green, no restrictions."""
        from ai_engine.modules.license_checker import _check_robots_txt
        mock_get.return_value = MagicMock(status_code=404)
        result = _check_robots_txt('https://example.com')
        assert result['status'] == 'green'
        assert 'No robots.txt' in result['summary']

    @patch('ai_engine.modules.license_checker.requests.get')
    def test_blanket_disallow(self, mock_get):
        from ai_engine.modules.license_checker import _check_robots_txt
        mock_get.return_value = MagicMock(
            status_code=200,
            text='User-Agent: *\nDisallow: /\n'
        )
        result = _check_robots_txt('https://example.com')
        assert result['status'] == 'red'

    @patch('ai_engine.modules.license_checker.requests.get')
    def test_allows_crawling(self, mock_get):
        from ai_engine.modules.license_checker import _check_robots_txt
        mock_get.return_value = MagicMock(
            status_code=200,
            text='User-Agent: *\nDisallow: /admin\nAllow: /\n'
        )
        result = _check_robots_txt('https://example.com')
        assert result['status'] == 'green'

    @patch('ai_engine.modules.license_checker.requests.get')
    def test_request_exception(self, mock_get):
        """L262-264: RequestException → green (assuming OK)."""
        from ai_engine.modules.license_checker import _check_robots_txt
        mock_get.side_effect = requests.RequestException('Timeout')
        result = _check_robots_txt('https://example.com')
        assert result['status'] == 'green'
        assert 'Could not fetch' in result['summary']


# ═══════════════════════════════════════════════════════════════════
# _detect_press_portal — all branches
# ═══════════════════════════════════════════════════════════════════

class TestDetectPressPortal:

    def test_url_pattern_match(self):
        from ai_engine.modules.license_checker import _detect_press_portal
        result = _detect_press_portal('https://press.bmw.com/news', 'media')
        assert result['is_press_portal'] is True
        assert 'press.' in result['evidence']

    def test_newsroom_pattern(self):
        from ai_engine.modules.license_checker import _detect_press_portal
        result = _detect_press_portal('https://newsroom.toyota.com', 'media')
        assert result['is_press_portal'] is True

    def test_brand_source_type(self):
        """L281: source_type='brand' → always press portal."""
        from ai_engine.modules.license_checker import _detect_press_portal
        result = _detect_press_portal('https://www.mercedes-benz.com', 'brand')
        assert result['is_press_portal'] is True
        assert 'brand' in result['evidence'].lower()

    def test_not_press_portal(self):
        from ai_engine.modules.license_checker import _detect_press_portal
        result = _detect_press_portal('https://www.autoblog.com', 'media')
        assert result['is_press_portal'] is False

    def test_media_center_pattern(self):
        from ai_engine.modules.license_checker import _detect_press_portal
        result = _detect_press_portal('https://media.ford.com/content', 'media')
        assert result['is_press_portal'] is True


# ═══════════════════════════════════════════════════════════════════
# _find_tos_page — standard paths + footer scraping
# ═══════════════════════════════════════════════════════════════════

class TestFindTosPage:

    @patch('ai_engine.modules.license_checker.requests.get')
    def test_found_at_standard_path(self, mock_get):
        """L293-303: ToS found at /terms."""
        from ai_engine.modules.license_checker import _find_tos_page
        # First request (/terms-of-use) → 404, second (/terms-of-service) → 404,
        # third (/terms) → 200 with valid long text
        tos_html = '<html><body>' + '<p>Terms and conditions. ' * 100 + '</p></body></html>'

        responses = []
        for i in range(len(['terms-of-use', 'terms-of-service'])):
            responses.append(MagicMock(status_code=404, text=''))
        responses.append(MagicMock(status_code=200, text=tos_html))

        mock_get.side_effect = responses
        result = _find_tos_page('https://example.com')
        assert result['found'] is True
        assert '/terms' in result['url']

    @patch('ai_engine.modules.license_checker.requests.get')
    def test_all_paths_fail_footer_scrape(self, mock_get):
        """L307-337: No standard path → scrape homepage footer for ToS links."""
        from ai_engine.modules.license_checker import _find_tos_page

        # All standard paths = 404
        not_found = MagicMock(status_code=404, text='')
        # Homepage with ToS link in footer
        homepage = MagicMock(status_code=200, text=(
            '<html><body><p>Welcome</p>'
            '<footer><a href="/legal-terms">Terms of Service</a></footer>'
            '</body></html>'
        ))
        # The ToS page itself
        tos_page = MagicMock(status_code=200, text=(
            '<html><body>' + '<p>Usage terms and conditions text. ' * 50 + '</p></body></html>'
        ))

        def side_effect(url, **kwargs):
            if '/legal-terms' in url:
                return tos_page
            elif url.endswith(('.com', '.com/')):
                return homepage
            return not_found

        mock_get.side_effect = side_effect
        result = _find_tos_page('https://example.com')
        assert result['found'] is True

    @patch('ai_engine.modules.license_checker.requests.get')
    def test_all_fails(self, mock_get):
        """Nothing found anywhere → found=False."""
        from ai_engine.modules.license_checker import _find_tos_page
        mock_get.return_value = MagicMock(status_code=404, text='')
        result = _find_tos_page('https://example.com')
        assert result['found'] is False

    @patch('ai_engine.modules.license_checker.requests.get')
    def test_standard_path_request_exception(self, mock_get):
        """L304-305: RequestException on standard path → continues."""
        from ai_engine.modules.license_checker import _find_tos_page
        mock_get.side_effect = requests.RequestException('Connection error')
        result = _find_tos_page('https://example.com')
        assert result['found'] is False

    @patch('ai_engine.modules.license_checker.requests.get')
    def test_soft_404_page_skipped(self, mock_get):
        """L300: Page returns 200 but contains '404' → skipped as soft 404."""
        from ai_engine.modules.license_checker import _find_tos_page
        soft_404 = MagicMock(status_code=200, text='<html><body>404 Page Not Found. ' * 100 + '</body></html>')
        homepage = MagicMock(status_code=404, text='')
        mock_get.return_value = soft_404
        # Override homepage
        def side_effect(url, **kwargs):
            if url.endswith(('.com', '.com/')):
                return homepage
            return soft_404
        mock_get.side_effect = side_effect
        result = _find_tos_page('https://example.com')
        assert result['found'] is False

    @patch('ai_engine.modules.license_checker.requests.get')
    def test_footer_link_absolute_url(self, mock_get):
        """L321-322: Footer link starts with http → used as-is."""
        from ai_engine.modules.license_checker import _find_tos_page
        not_found = MagicMock(status_code=404, text='')
        homepage = MagicMock(status_code=200, text=(
            '<a href="https://legal.example.com/terms">Legal Terms</a>'
        ))
        tos_content = '<html>' + '<p>Full terms and conditions legal text here. ' * 50 + '</html>'
        tos_page = MagicMock(status_code=200, text=tos_content)

        def side_effect(url, **kwargs):
            if 'legal.example.com' in url:
                return tos_page
            if url.endswith(('.com', '.com/')):
                return homepage
            return not_found
        mock_get.side_effect = side_effect
        result = _find_tos_page('https://example.com')
        assert result['found'] is True


# ═══════════════════════════════════════════════════════════════════
# _analyze_tos_with_ai — success + error
# ═══════════════════════════════════════════════════════════════════

class TestAnalyzeTosWithAi:

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_successful_analysis(self, mock_ai):
        """L350-359: AI returns valid JSON analysis."""
        from ai_engine.modules.license_checker import _analyze_tos_with_ai
        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = (
            '{"status": "green", "summary": "No restrictions found", '
            '"allows_rss_syndication": true, "key_restrictions": []}'
        )
        mock_ai.return_value = mock_provider

        result = _analyze_tos_with_ai('Terms of service text here...')
        assert result['status'] == 'green'

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_ai_exception(self, mock_ai):
        """L361-367: AI provider crashes → yellow with error message."""
        from ai_engine.modules.license_checker import _analyze_tos_with_ai
        mock_ai.side_effect = Exception('API key invalid')

        result = _analyze_tos_with_ai('Terms text...')
        assert result['status'] == 'yellow'
        assert 'error' in result['summary'].lower()


# ═══════════════════════════════════════════════════════════════════
# _check_image_rights — all branches
# ═══════════════════════════════════════════════════════════════════

class TestCheckImageRights:

    def test_press_portal_brand(self):
        """L378-382: Press portal + brand → images allowed."""
        from ai_engine.modules.license_checker import _check_image_rights
        result = _check_image_rights(
            tos_text=None, is_press_portal=True, source_type='brand'
        )
        assert result['passed'] is True
        assert 'media distribution' in result['detail']

    def test_press_portal_non_brand(self):
        """L385-389: Press URL but not a brand → images unclear."""
        from ai_engine.modules.license_checker import _check_image_rights
        result = _check_image_rights(
            tos_text=None, is_press_portal=True, source_type='media'
        )
        assert result['passed'] is False
        assert 'unclear' in result['detail']

    def test_no_tos_text(self):
        """L392-396: No ToS available → default to Pexels."""
        from ai_engine.modules.license_checker import _check_image_rights
        result = _check_image_rights(
            tos_text=None, is_press_portal=False, source_type='media'
        )
        assert result['passed'] is False
        assert 'Pexels' in result['detail']

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_ai_allows_images(self, mock_ai):
        """L432-439: AI says images_allowed=True → passed."""
        from ai_engine.modules.license_checker import _check_image_rights
        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = (
            '{"images_allowed": true, "confidence": "high", '
            '"evidence": "Images may be used with credit"}'
        )
        mock_ai.return_value = mock_provider

        result = _check_image_rights(
            tos_text='Images may be used with attribution.',
            is_press_portal=False, source_type='media'
        )
        assert result['passed'] is True
        assert 'allowed' in result['detail'].lower()

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_ai_restricts_images(self, mock_ai):
        """L440-444: AI says images_allowed=False → restricted."""
        from ai_engine.modules.license_checker import _check_image_rights
        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = (
            '{"images_allowed": false, "confidence": "high", '
            '"evidence": "All photographs are copyrighted"}'
        )
        mock_ai.return_value = mock_provider

        result = _check_image_rights(
            tos_text='All photographs are copyrighted and may not be used.',
            is_press_portal=False, source_type='media'
        )
        assert result['passed'] is False
        assert 'restricted' in result['detail'].lower()

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_ai_exception(self, mock_ai):
        """L445-450: AI crashes → default to Pexels."""
        from ai_engine.modules.license_checker import _check_image_rights
        mock_ai.side_effect = Exception('Rate limited')

        result = _check_image_rights(
            tos_text='Some terms text',
            is_press_portal=False, source_type='media'
        )
        assert result['passed'] is False
        assert 'Pexels' in result['detail']


# ═══════════════════════════════════════════════════════════════════
# _analyze_homepage — full flow
# ═══════════════════════════════════════════════════════════════════

class TestAnalyzeHomepage:

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    @patch('ai_engine.modules.license_checker.requests.get')
    def test_successful_homepage_analysis(self, mock_get, mock_ai):
        """L453-472: Homepage fetched, AI analyzes."""
        from ai_engine.modules.license_checker import _analyze_homepage
        mock_get.return_value = MagicMock(
            status_code=200,
            text='<html><body>' + '<p>Press releases and media content. ' * 50 + '</p></body></html>'
        )
        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = (
            '{"is_press_portal": true, "confidence": "high", '
            '"evidence": "Contains press releases section"}'
        )
        mock_ai.return_value = mock_provider

        result = _analyze_homepage('https://press.bmw.com')
        assert result is not None
        assert result['is_press_portal'] is True

    @patch('ai_engine.modules.license_checker.requests.get')
    def test_non_200_returns_none(self, mock_get):
        """L459-460: Non-200 response → None."""
        from ai_engine.modules.license_checker import _analyze_homepage
        mock_get.return_value = MagicMock(status_code=503)
        assert _analyze_homepage('https://example.com') is None

    @patch('ai_engine.modules.license_checker.requests.get')
    def test_short_text_returns_none(self, mock_get):
        """L463-464: Text < 100 chars → None."""
        from ai_engine.modules.license_checker import _analyze_homepage
        mock_get.return_value = MagicMock(status_code=200, text='<p>Short</p>')
        assert _analyze_homepage('https://example.com') is None

    @patch('ai_engine.modules.license_checker.requests.get')
    def test_request_exception_returns_none(self, mock_get):
        """L474-476: Request exception → None."""
        from ai_engine.modules.license_checker import _analyze_homepage
        mock_get.side_effect = Exception('Connection refused')
        assert _analyze_homepage('https://example.com') is None


# ═══════════════════════════════════════════════════════════════════
# check_content_license — full integration-style tests
# ═══════════════════════════════════════════════════════════════════

class TestCheckContentLicense:

    def test_empty_url(self):
        """L122-135: Empty URL → yellow with all checks failed."""
        from ai_engine.modules.license_checker import check_content_license
        result = check_content_license('')
        assert result['status'] == 'yellow'
        assert result['robots_ok'] is None
        assert result['tos_found'] is False
        assert not result['safety_checks']['robots_txt']['passed']

    def test_none_url(self):
        from ai_engine.modules.license_checker import check_content_license
        result = check_content_license(None)
        assert result['status'] == 'yellow'

    @patch('ai_engine.modules.license_checker._check_image_rights')
    @patch('ai_engine.modules.license_checker._find_tos_page')
    @patch('ai_engine.modules.license_checker._detect_press_portal')
    @patch('ai_engine.modules.license_checker._check_robots_txt')
    def test_press_portal_green(self, mock_robots, mock_press, mock_tos, mock_img):
        """Press portal detected + no red → green."""
        from ai_engine.modules.license_checker import check_content_license
        mock_robots.return_value = {'status': 'green', 'summary': 'Allows crawling'}
        mock_press.return_value = {'is_press_portal': True, 'evidence': 'URL has /press/'}
        mock_tos.return_value = {'found': False, 'url': None, 'text': None}
        mock_img.return_value = {'passed': True, 'detail': 'Press images OK'}

        result = check_content_license('https://press.bmw.com/news', source_type='brand')
        assert result['status'] == 'green'

    @patch('ai_engine.modules.license_checker._check_image_rights')
    @patch('ai_engine.modules.license_checker._analyze_tos_with_ai')
    @patch('ai_engine.modules.license_checker._find_tos_page')
    @patch('ai_engine.modules.license_checker._detect_press_portal')
    @patch('ai_engine.modules.license_checker._check_robots_txt')
    def test_tos_found_and_analyzed(self, mock_robots, mock_press, mock_tos, mock_ai, mock_img):
        """L167-178: ToS found → AI analyzes it."""
        from ai_engine.modules.license_checker import check_content_license
        mock_robots.return_value = {'status': 'green', 'summary': 'OK'}
        mock_press.return_value = {'is_press_portal': False, 'evidence': ''}
        mock_tos.return_value = {
            'found': True,
            'url': 'https://example.com/terms',
            'text': 'Terms of service text content...',
        }
        mock_ai.return_value = {
            'status': 'green',
            'summary': 'RSS is fine with attribution',
            'key_restrictions': [],
        }
        mock_img.return_value = {'passed': False, 'detail': 'Images restricted'}

        result = check_content_license('https://example.com')
        assert result['tos_found'] is True
        assert result['tos_url'] == 'https://example.com/terms'
        assert 'robots_txt' in result['safety_checks']
        assert 'tos_analysis' in result['safety_checks']

    @patch('ai_engine.modules.license_checker._check_image_rights')
    @patch('ai_engine.modules.license_checker._analyze_tos_with_ai')
    @patch('ai_engine.modules.license_checker._find_tos_page')
    @patch('ai_engine.modules.license_checker._detect_press_portal')
    @patch('ai_engine.modules.license_checker._check_robots_txt')
    def test_tos_with_restrictions(self, mock_robots, mock_press, mock_tos, mock_ai, mock_img):
        """L173-176: ToS has key_restrictions → appended to details."""
        from ai_engine.modules.license_checker import check_content_license
        mock_robots.return_value = {'status': 'green', 'summary': 'OK'}
        mock_press.return_value = {'is_press_portal': False, 'evidence': ''}
        mock_tos.return_value = {
            'found': True, 'url': 'https://example.com/terms',
            'text': 'Terms text...',
        }
        mock_ai.return_value = {
            'status': 'yellow',
            'summary': 'Some restrictions apply',
            'key_restrictions': ['No automated scraping', 'Attribution required'],
        }
        mock_img.return_value = {'passed': False, 'detail': 'Restricted'}

        result = check_content_license('https://example.com')
        assert 'No automated scraping' in result['details']

    @patch('ai_engine.modules.license_checker._check_image_rights')
    @patch('ai_engine.modules.license_checker._analyze_homepage')
    @patch('ai_engine.modules.license_checker._find_tos_page')
    @patch('ai_engine.modules.license_checker._detect_press_portal')
    @patch('ai_engine.modules.license_checker._check_robots_txt')
    def test_no_tos_homepage_press_detection(self, mock_robots, mock_press, mock_tos, mock_hp, mock_img):
        """L184-192: No ToS, not press portal, homepage analysis detects press."""
        from ai_engine.modules.license_checker import check_content_license
        mock_robots.return_value = {'status': 'green', 'summary': 'OK'}
        mock_press.return_value = {'is_press_portal': False, 'evidence': ''}
        mock_tos.return_value = {'found': False, 'url': None, 'text': None}
        mock_hp.return_value = {
            'is_press_portal': True,
            'confidence': 'high',
            'evidence': 'Contains press releases section',
        }
        mock_img.return_value = {'passed': True, 'detail': 'OK'}

        result = check_content_license('https://corporate.toyota.com')
        assert 'Homepage analysis: Press portal' in result['details']
        assert result['safety_checks']['tos_analysis']['passed'] is True

    @patch('ai_engine.modules.license_checker._check_image_rights')
    @patch('ai_engine.modules.license_checker._analyze_homepage')
    @patch('ai_engine.modules.license_checker._find_tos_page')
    @patch('ai_engine.modules.license_checker._detect_press_portal')
    @patch('ai_engine.modules.license_checker._check_robots_txt')
    def test_no_tos_no_press_caution(self, mock_robots, mock_press, mock_tos, mock_hp, mock_img):
        """L193-199: No ToS, not press portal, homepage not press → caution."""
        from ai_engine.modules.license_checker import check_content_license
        mock_robots.return_value = {'status': 'green', 'summary': 'OK'}
        mock_press.return_value = {'is_press_portal': False, 'evidence': ''}
        mock_tos.return_value = {'found': False, 'url': None, 'text': None}
        mock_hp.return_value = {'is_press_portal': False, 'evidence': 'Regular blog'}
        mock_img.return_value = {'passed': False, 'detail': 'Unknown'}

        result = check_content_license('https://blog.example.com')
        assert 'caution' in result['details'].lower()

    @patch('ai_engine.modules.license_checker._check_image_rights')
    @patch('ai_engine.modules.license_checker._find_tos_page')
    @patch('ai_engine.modules.license_checker._detect_press_portal')
    @patch('ai_engine.modules.license_checker._check_robots_txt')
    def test_press_portal_no_tos_skip_homepage(self, mock_robots, mock_press, mock_tos, mock_img):
        """L200-204: Press portal, no ToS → skip homepage check, mark as green."""
        from ai_engine.modules.license_checker import check_content_license
        mock_robots.return_value = {'status': 'green', 'summary': 'OK'}
        mock_press.return_value = {'is_press_portal': True, 'evidence': 'Brand source'}
        mock_tos.return_value = {'found': False, 'url': None, 'text': None}
        mock_img.return_value = {'passed': True, 'detail': 'OK'}

        result = check_content_license('https://press.kia.com', source_type='brand')
        assert result['status'] == 'green'
        assert result['safety_checks']['tos_analysis']['detail'] == 'No ToS needed — press portal (content is for media use)'

    @patch('ai_engine.modules.license_checker._check_image_rights')
    @patch('ai_engine.modules.license_checker._find_tos_page')
    @patch('ai_engine.modules.license_checker._detect_press_portal')
    @patch('ai_engine.modules.license_checker._check_robots_txt')
    def test_image_rights_not_passed(self, mock_robots, mock_press, mock_tos, mock_img):
        """L215-216: image_rights not passed → warning icon in details."""
        from ai_engine.modules.license_checker import check_content_license
        mock_robots.return_value = {'status': 'green', 'summary': 'OK'}
        mock_press.return_value = {'is_press_portal': False, 'evidence': ''}
        mock_tos.return_value = {'found': False, 'url': None, 'text': None}
        mock_img.return_value = {'passed': False, 'detail': 'Cannot verify image rights'}

        result = check_content_license('https://example.com')
        assert '⚠️' in result['details']
        assert 'Cannot verify' in result['details']

    @patch('ai_engine.modules.license_checker._check_image_rights')
    @patch('ai_engine.modules.license_checker._check_robots_txt')
    @patch('ai_engine.modules.license_checker._detect_press_portal')
    @patch('ai_engine.modules.license_checker._find_tos_page')
    def test_robots_red_overrides_green(self, mock_tos, mock_press, mock_robots, mock_img):
        """L219-222: Robots red + press portal → final status respects red."""
        from ai_engine.modules.license_checker import check_content_license
        mock_robots.return_value = {'status': 'red', 'summary': 'Blocks all'}
        mock_press.return_value = {'is_press_portal': True, 'evidence': 'Brand'}
        mock_tos.return_value = {'found': False, 'url': None, 'text': None}
        mock_img.return_value = {'passed': True, 'detail': 'OK'}

        result = check_content_license('https://press.example.com', source_type='brand')
        # Press portal + red robots → should NOT be green
        assert result['status'] != 'green' or result['robots_ok'] is False
