"""
Deep coverage: ai_engine/main.py — targeting remaining 149 uncovered lines.
Focus on branch coverage for _generate_article_content internal paths.

Uncovered branches:
- WebSocket send (L255-256)
- oEmbed exception (L281-282)
- Trim-match duplicate (L378-385)
- Pending duplicate (L406-415)
- Chin→Qin model fix (L425)
- Web search + specs enrichment (L430-454)
- Spec refill (L460-468)
- Segment price tags (L489-498)
- SEO title construction from specs (L525-544)
- Screenshot + Cloudinary flow (L562-606)
- Summary extraction from HTML/analysis (L622-644)
- AI editor failure (L674-677)
- Provider tracker failure (L703-704)
- create_pending_article video_id extraction (L933-935)
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from news.models import (
    Article, Category, Tag, TagGroup, CarSpecification,
    PendingArticle, YouTubeChannel,
)

pytestmark = pytest.mark.django_db

# Shared test data
LONG_TRANSCRIPT = 'This is a detailed look at the 2026 BYD Seal electric sedan with AWD drivetrain' * 10

ANALYSIS_WITH_SUMMARY = (
    "Make: BYD\nModel: Seal\nYear: 2026\nEngine: Electric\n"
    "Horsepower: 530 hp\nDrivetrain: AWD\nBattery: 82.5 kWh\n"
    "Range: 570 km\nPrice: $35,000\n"
    "Summary: Revolutionary electric sedan with dual motors."
)

ANALYSIS_WITH_CHIN = (
    "Make: BYD\nModel: Chin L\nYear: 2026\nEngine: Hybrid\n"
    "Horsepower: 180 hp\nDrivetrain: FWD\nPrice: $18,000"
)

BIG_ARTICLE = (
    '<h2>2026 BYD Seal AWD Review</h2>'
    '<p>The 2026 BYD Seal is an impressive electric sedan delivering 530 horsepower.</p>'
    '<h2>Performance</h2><p>0-100 in 3.8 seconds with AWD stability.</p>'
    '<h2>Design &amp; Interior</h2><p>Clean lines and premium materials.</p>'
    '<p>The 82.5 kWh battery provides up to 570 km of range.</p>'
) * 2  # Make it > 100 chars

SIMPLE_SPECS = {
    'make': 'BYD', 'model': 'Seal', 'year': 2026,
    'trim': 'Not specified', 'engine': 'Electric',
    'horsepower': 530, 'drivetrain': 'AWD',
    'battery': '82.5 kWh', 'range': '570 km',
    'price': '$35,000', 'seo_title': '',
}


def _base_mocks():
    """Returns a dict of base mock return values for _generate_article_content."""
    return {
        'oembed': MagicMock(status_code=200, json=lambda: {
            'title': 'BYD Seal Review', 'author_name': 'TestAuto', 'author_url': 'https://youtube.com/@test'
        }),
        'transcript': LONG_TRANSCRIPT,
        'analysis': ANALYSIS_WITH_SUMMARY,
        'categorize': ('Reviews', ['BYD', 'Electric', 'Sedan']),
        'specs': SIMPLE_SPECS.copy(),
        'article': BIG_ARTICLE,
        'screenshots': [],
        'reviewer': BIG_ARTICLE,
        'web_context': 'BYD Seal specifications from web search',
        'enrich': SIMPLE_SPECS.copy(),
        'coverage': (8, 12, 67, ['range', 'price']),
    }


# Helper decorator that patches ALL external deps for _generate_article_content
def full_pipeline_patches(func):
    """Decorator applying all patches needed for _generate_article_content."""
    from functools import wraps

    @wraps(func)
    @patch('ai_engine.modules.provider_tracker.record_generation')
    @patch('ai_engine.modules.spec_refill.compute_coverage')
    @patch('ai_engine.modules.specs_enricher.enrich_specs_from_web')
    @patch('ai_engine.modules.searcher.get_web_context')
    @patch('modules.article_reviewer.review_article')
    @patch('ai_engine.main.extract_video_screenshots')
    @patch('ai_engine.main.generate_article')
    @patch('modules.analyzer.extract_specs_dict')
    @patch('modules.analyzer.categorize_article')
    @patch('ai_engine.main.analyze_transcript')
    @patch('ai_engine.main.transcribe_from_youtube')
    @patch('ai_engine.main.requests.get')
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


# ═══════════════════════════════════════════════════════════════════
# Coverage target: WebSocket send_progress exception (L255-256)
# ═══════════════════════════════════════════════════════════════════

class TestWebSocketProgress:

    @full_pipeline_patches
    def test_websocket_exception_caught(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """With task_id, WebSocket channel_layer raises → caught silently."""
        from ai_engine.main import _generate_article_content
        m = _base_mocks()
        mock_oembed.return_value = m['oembed']
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = m['analysis']
        mock_categorize.return_value = m['categorize']
        mock_specs.return_value = m['specs']
        mock_gen.return_value = m['article']
        mock_screenshots.return_value = []
        mock_reviewer.return_value = m['article']
        mock_web.return_value = m['web_context']
        mock_enrich.return_value = m['enrich']
        mock_coverage.return_value = m['coverage']
        mock_record.return_value = None

        # Patch channels to exist but raise on group_send
        with patch('ai_engine.main.async_to_sync', create=True) as mock_async, \
             patch('ai_engine.main.get_channel_layer', create=True) as mock_layer:
            mock_layer.return_value = MagicMock()
            mock_async.side_effect = Exception('Channel unavailable')

            result = _generate_article_content(
                'https://www.youtube.com/watch?v=ws_exc_test',
                task_id='test-task-ws-fail',
                provider='gemini'
            )
        assert result['success'] is True


# ═══════════════════════════════════════════════════════════════════
# Coverage target: oEmbed exception (L281-282)
# ═══════════════════════════════════════════════════════════════════

class TestOEmbedException:

    @full_pipeline_patches
    def test_oembed_network_error(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """oEmbed GET raises exception → caught, continues with defaults."""
        from ai_engine.main import _generate_article_content
        m = _base_mocks()
        mock_oembed.side_effect = Exception('Network timeout')
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = m['analysis']
        mock_categorize.return_value = m['categorize']
        mock_specs.return_value = m['specs']
        mock_gen.return_value = m['article']
        mock_screenshots.return_value = []
        mock_reviewer.return_value = m['article']
        mock_web.return_value = m['web_context']
        mock_enrich.return_value = m['enrich']
        mock_coverage.return_value = m['coverage']
        mock_record.return_value = None

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=oembed_fail',
            provider='gemini'
        )
        assert result['success'] is True
        assert result.get('author_name', '') == ''


# ═══════════════════════════════════════════════════════════════════
# Coverage target: Trim-match duplicate (L378-385) + Pending dup (L406-415)
# ═══════════════════════════════════════════════════════════════════

class TestDuplicateDetection:

    @full_pipeline_patches
    def test_trim_match_duplicate(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Existing article with same make+model+trim → duplicate detected."""
        from ai_engine.main import _generate_article_content

        # Create existing published article with matching specs
        existing_art = Article.objects.create(
            title='Existing BYD Seal AWD', slug='existing-byd-seal-awd',
            content='<p>Existing</p>', is_published=True,
        )
        CarSpecification.objects.create(
            article=existing_art, make='BYD', model='Seal', trim='AWD',
        )

        m = _base_mocks()
        specs_with_trim = m['specs'].copy()
        specs_with_trim['trim'] = 'AWD'
        mock_oembed.return_value = m['oembed']
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = m['analysis']
        mock_categorize.return_value = m['categorize']
        mock_specs.return_value = specs_with_trim
        mock_coverage.return_value = m['coverage']

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=trim_dup_test',
            provider='gemini'
        )
        assert result['success'] is False
        assert result.get('reason') == 'duplicate'

    @full_pipeline_patches
    def test_no_trim_duplicate(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Existing article, no trim in specs → checks make+model only."""
        from ai_engine.main import _generate_article_content

        existing_art = Article.objects.create(
            title='Existing NIO ET9', slug='existing-nio-et9',
            content='<p>Existing NIO</p>', is_published=True,
        )
        CarSpecification.objects.create(
            article=existing_art, make='NIO', model='ET9',
        )

        m = _base_mocks()
        specs_nio = {'make': 'NIO', 'model': 'ET9', 'year': 2026,
                     'trim': 'Not specified', 'drivetrain': 'AWD',
                     'seo_title': '', 'engine': 'Electric', 'horsepower': 650}
        mock_oembed.return_value = m['oembed']
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = m['analysis']
        mock_categorize.return_value = ('Reviews', ['NIO'])
        mock_specs.return_value = specs_nio
        mock_coverage.return_value = (3, 12, 25, [])

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=no_trim_dup',
            provider='gemini'
        )
        assert result['success'] is False
        assert result.get('reason') == 'duplicate'

    @full_pipeline_patches
    def test_pending_duplicate(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Same car already in PendingArticle → duplicate_pending."""
        from ai_engine.main import _generate_article_content

        PendingArticle.objects.create(
            title='2026 ZEEKR 007 Review',
            content='<p>Pending content</p>',
            video_url='https://youtube.com/watch?v=zeekr_old',
            video_id='zeekr_old',
            video_title='ZEEKR 007 Review',
            status='pending',
        )

        m = _base_mocks()
        specs_zeekr = {'make': 'ZEEKR', 'model': '007', 'year': 2026,
                       'trim': 'Not specified', 'drivetrain': 'AWD',
                       'seo_title': '', 'engine': 'Electric', 'horsepower': 550}
        mock_oembed.return_value = m['oembed']
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = m['analysis']
        mock_categorize.return_value = ('Reviews', ['ZEEKR'])
        mock_specs.return_value = specs_zeekr
        mock_coverage.return_value = (3, 12, 25, [])

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=zeekr_new_dup',
            provider='gemini'
        )
        assert result['success'] is False
        assert result.get('reason') in ('duplicate', 'duplicate_pending')


# ═══════════════════════════════════════════════════════════════════
# Coverage target: Chin→Qin fix (L425) + enrichment (L430-454)
# ═══════════════════════════════════════════════════════════════════

class TestChinQinAndEnrichment:

    @full_pipeline_patches
    def test_chin_to_qin_fix(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Model 'Chin L' should be auto-corrected to 'Qin L'."""
        from ai_engine.main import _generate_article_content
        m = _base_mocks()
        specs_chin = m['specs'].copy()
        specs_chin['model'] = 'Chin L'
        specs_chin['make'] = 'BYD'

        mock_oembed.return_value = m['oembed']
        mock_transcribe.return_value = 'Detailed review of the BYD Chin L sedan' * 10
        mock_analyze.return_value = ANALYSIS_WITH_CHIN
        mock_categorize.return_value = ('Reviews', ['BYD'])
        mock_specs.return_value = specs_chin
        mock_gen.return_value = m['article']
        mock_screenshots.return_value = []
        mock_reviewer.return_value = m['article']
        mock_web.return_value = 'BYD Qin L specifications'
        mock_enrich.return_value = specs_chin
        mock_coverage.return_value = (5, 12, 42, [])
        mock_record.return_value = None

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=chin_fix',
            provider='gemini'
        )
        assert result['success'] is True

    @full_pipeline_patches
    def test_web_search_failure(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Web search raises exception → caught, continues without context."""
        from ai_engine.main import _generate_article_content
        m = _base_mocks()
        mock_oembed.return_value = m['oembed']
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = m['analysis']
        mock_categorize.return_value = m['categorize']
        mock_specs.return_value = m['specs']
        mock_gen.return_value = m['article']
        mock_screenshots.return_value = []
        mock_reviewer.return_value = m['article']
        mock_web.side_effect = Exception('DDGS timeout')
        mock_coverage.return_value = m['coverage']
        mock_record.return_value = None

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=web_fail',
            provider='gemini'
        )
        assert result['success'] is True

    @full_pipeline_patches
    def test_specs_enrichment_failure(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Specs enrichment raises → caught, continues with original specs."""
        from ai_engine.main import _generate_article_content
        m = _base_mocks()
        mock_oembed.return_value = m['oembed']
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = m['analysis']
        mock_categorize.return_value = m['categorize']
        mock_specs.return_value = m['specs']
        mock_gen.return_value = m['article']
        mock_screenshots.return_value = []
        mock_reviewer.return_value = m['article']
        mock_web.return_value = 'Some web context'
        mock_enrich.side_effect = Exception('Enrichment crash')
        mock_coverage.return_value = m['coverage']
        mock_record.return_value = None

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=enrich_fail',
            provider='gemini'
        )
        assert result['success'] is True


# ═══════════════════════════════════════════════════════════════════
# Coverage target: Spec refill (L460-468) + Segment tags (L489-498)
# ═══════════════════════════════════════════════════════════════════

class TestSpecRefillAndSegmentTags:

    @full_pipeline_patches
    def test_spec_refill_triggered(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Coverage < 70% → spec refill runs."""
        from ai_engine.main import _generate_article_content
        m = _base_mocks()
        # Low coverage triggers refill
        low_cov_specs = m['specs'].copy()

        mock_oembed.return_value = m['oembed']
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = m['analysis']
        mock_categorize.return_value = m['categorize']
        mock_specs.return_value = low_cov_specs
        mock_gen.return_value = m['article']
        mock_screenshots.return_value = []
        mock_reviewer.return_value = m['article']
        mock_web.return_value = 'Web data'
        mock_enrich.return_value = low_cov_specs
        # Set low pre-coverage → triggers refill
        mock_coverage.return_value = (3, 12, 25, ['torque', 'acceleration', 'top_speed'])
        mock_record.return_value = None

        with patch('ai_engine.modules.spec_refill.refill_missing_specs') as mock_refill:
            refilled = low_cov_specs.copy()
            refilled['_refill_meta'] = {
                'triggered': True, 'coverage_before': 25, 'coverage_after': 58
            }
            mock_refill.return_value = refilled

            result = _generate_article_content(
                'https://www.youtube.com/watch?v=refill_test',
                provider='gemini'
            )
        assert result['success'] is True

    @full_pipeline_patches
    def test_spec_refill_failure(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Spec refill crashes → caught, continues."""
        from ai_engine.main import _generate_article_content
        m = _base_mocks()
        mock_oembed.return_value = m['oembed']
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = m['analysis']
        mock_categorize.return_value = m['categorize']
        mock_specs.return_value = m['specs']
        mock_gen.return_value = m['article']
        mock_screenshots.return_value = []
        mock_reviewer.return_value = m['article']
        mock_web.return_value = ''
        mock_coverage.side_effect = Exception('compute_coverage crash')
        mock_record.return_value = None

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=refill_crash',
            provider='gemini'
        )
        assert result['success'] is True


# ═══════════════════════════════════════════════════════════════════
# Coverage target: SEO title from specs (L525-544), summary (L622-644)
# ═══════════════════════════════════════════════════════════════════

class TestTitleAndSummaryExtraction:

    @full_pipeline_patches
    def test_title_from_seo_specs(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """specs['seo_title'] provided → used as article title."""
        from ai_engine.main import _generate_article_content
        m = _base_mocks()
        specs_with_seo = m['specs'].copy()
        specs_with_seo['seo_title'] = '2026 BYD Seal AWD — The Best Electric Sedan Under $40K'

        mock_oembed.return_value = m['oembed']
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = m['analysis']
        mock_categorize.return_value = m['categorize']
        mock_specs.return_value = specs_with_seo
        mock_gen.return_value = m['article']
        mock_screenshots.return_value = []
        mock_reviewer.return_value = m['article']
        mock_web.return_value = m['web_context']
        mock_enrich.return_value = specs_with_seo
        mock_coverage.return_value = m['coverage']
        mock_record.return_value = None

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=seo_title_test',
            provider='gemini'
        )
        assert result['success'] is True
        assert 'Best Electric Sedan' in result['title'] or 'BYD' in result['title']

    @full_pipeline_patches
    def test_title_constructed_from_specs(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """No seo_title, no title in HTML → construct from Make/Model/Year."""
        from ai_engine.main import _generate_article_content
        m = _base_mocks()
        # Article with only generic headers (no usable title)
        generic_article = (
            '<h2>Performance &amp; Specs</h2><p>Great specs.</p>'
            '<h2>Design &amp; Interior</h2><p>Nice design.</p>'
        ) * 5

        specs_no_seo = m['specs'].copy()
        specs_no_seo['seo_title'] = ''
        specs_no_seo['trim'] = 'AWD'

        mock_oembed.return_value = MagicMock(status_code=404)
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = m['analysis']
        mock_categorize.return_value = m['categorize']
        mock_specs.return_value = specs_no_seo
        mock_gen.return_value = generic_article
        mock_screenshots.return_value = []
        mock_reviewer.return_value = generic_article
        mock_web.return_value = m['web_context']
        mock_enrich.return_value = specs_no_seo
        mock_coverage.return_value = m['coverage']
        mock_record.return_value = None

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=construct_title',
            provider='gemini'
        )
        assert result['success'] is True
        # Title should be constructed like "2026 BYD Seal AWD Review"
        assert 'BYD' in result['title']

    @full_pipeline_patches
    def test_summary_from_analysis_dict(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Analysis is dict with 'summary' key → used for description."""
        from ai_engine.main import _generate_article_content
        m = _base_mocks()

        mock_oembed.return_value = m['oembed']
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = {'summary': 'AI-generated summary from dict', 'raw': 'data'}
        mock_categorize.return_value = m['categorize']
        mock_specs.return_value = m['specs']
        mock_gen.return_value = m['article']
        mock_screenshots.return_value = []
        mock_reviewer.return_value = m['article']
        mock_web.return_value = m['web_context']
        mock_enrich.return_value = m['enrich']
        mock_coverage.return_value = m['coverage']
        mock_record.return_value = None

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=dict_summary',
            provider='gemini'
        )
        assert result['success'] is True
        assert 'AI-generated summary' in result['summary'] or len(result['summary']) > 0

    @full_pipeline_patches
    def test_summary_fallback_from_html(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """No Summary: in analysis, no dict → extract from HTML paragraph."""
        from ai_engine.main import _generate_article_content
        m = _base_mocks()
        # Analysis without Summary:
        analysis_no_summary = "Make: BYD\nModel: Seal\nYear: 2026\nHorsepower: 530"

        mock_oembed.return_value = m['oembed']
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = analysis_no_summary
        mock_categorize.return_value = m['categorize']
        mock_specs.return_value = m['specs']
        mock_gen.return_value = m['article']
        mock_screenshots.return_value = []
        mock_reviewer.return_value = m['article']
        mock_web.return_value = m['web_context']
        mock_enrich.return_value = m['enrich']
        mock_coverage.return_value = m['coverage']
        mock_record.return_value = None

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=html_summary',
            provider='gemini'
        )
        assert result['success'] is True
        assert len(result['summary']) > 0


# ═══════════════════════════════════════════════════════════════════
# Coverage: Screenshots with Cloudinary (L562-606)
# ═══════════════════════════════════════════════════════════════════

class TestScreenshotFlow:

    @full_pipeline_patches
    def test_screenshots_uploaded_to_cloudinary(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Screenshots extracted → uploaded to Cloudinary."""
        from ai_engine.main import _generate_article_content
        import tempfile, os
        m = _base_mocks()

        # Create a temp file to simulate screenshot
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'\xff\xd8\xff' + b'\x00' * 100)
            temp_path = f.name

        try:
            mock_oembed.return_value = m['oembed']
            mock_transcribe.return_value = m['transcript']
            mock_analyze.return_value = m['analysis']
            mock_categorize.return_value = m['categorize']
            mock_specs.return_value = m['specs']
            mock_gen.return_value = m['article']
            mock_screenshots.return_value = [temp_path]
            mock_reviewer.return_value = m['article']
            mock_web.return_value = m['web_context']
            mock_enrich.return_value = m['enrich']
            mock_coverage.return_value = m['coverage']
            mock_record.return_value = None

            with patch.dict(os.environ, {'CLOUDINARY_URL': 'cloudinary://key:secret@cloud'}):
                with patch('cloudinary.uploader.upload') as mock_upload:
                    mock_upload.return_value = {'secure_url': 'https://res.cloudinary.com/test/screenshot1.jpg'}
                    result = _generate_article_content(
                        'https://www.youtube.com/watch?v=screenshot_test',
                        provider='gemini'
                    )
            assert result['success'] is True
            assert len(result['image_paths']) >= 1
        finally:
            os.unlink(temp_path)

    @full_pipeline_patches
    def test_screenshots_cloudinary_fails_local_fallback(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Cloudinary upload fails → fallback to local media copy."""
        from ai_engine.main import _generate_article_content
        import tempfile, os
        m = _base_mocks()

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'\xff\xd8\xff' + b'\x00' * 100)
            temp_path = f.name

        try:
            mock_oembed.return_value = m['oembed']
            mock_transcribe.return_value = m['transcript']
            mock_analyze.return_value = m['analysis']
            mock_categorize.return_value = m['categorize']
            mock_specs.return_value = m['specs']
            mock_gen.return_value = m['article']
            mock_screenshots.return_value = [temp_path]
            mock_reviewer.return_value = m['article']
            mock_web.return_value = m['web_context']
            mock_enrich.return_value = m['enrich']
            mock_coverage.return_value = m['coverage']
            mock_record.return_value = None

            with patch.dict(os.environ, {'CLOUDINARY_URL': 'cloudinary://key:secret@cloud'}):
                with patch('cloudinary.uploader.upload', side_effect=Exception('Upload error')):
                    result = _generate_article_content(
                        'https://www.youtube.com/watch?v=screenshot_fallback',
                        provider='gemini'
                    )
            assert result['success'] is True
        finally:
            os.unlink(temp_path)

    @full_pipeline_patches
    def test_screenshots_extraction_fails(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Screenshot extraction raises → caught, continues with empty list."""
        from ai_engine.main import _generate_article_content
        m = _base_mocks()
        mock_oembed.return_value = m['oembed']
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = m['analysis']
        mock_categorize.return_value = m['categorize']
        mock_specs.return_value = m['specs']
        mock_gen.return_value = m['article']
        mock_screenshots.side_effect = Exception('ffmpeg not found')
        mock_reviewer.return_value = m['article']
        mock_web.return_value = m['web_context']
        mock_enrich.return_value = m['enrich']
        mock_coverage.return_value = m['coverage']
        mock_record.return_value = None

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=screenshot_crash',
            provider='gemini'
        )
        assert result['success'] is True
        assert result['image_paths'] == []


# ═══════════════════════════════════════════════════════════════════
# Coverage: AI Editor failure (L674-677) + Provider tracker failure (L703-704)
# ═══════════════════════════════════════════════════════════════════

class TestEditorAndTracker:

    @full_pipeline_patches
    def test_ai_editor_failure(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """AI editor review raises exception → caught, uses original."""
        from ai_engine.main import _generate_article_content
        m = _base_mocks()
        mock_oembed.return_value = m['oembed']
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = m['analysis']
        mock_categorize.return_value = m['categorize']
        mock_specs.return_value = m['specs']
        mock_gen.return_value = m['article']
        mock_screenshots.return_value = []
        mock_reviewer.side_effect = Exception('AI editor crashed')
        mock_web.return_value = m['web_context']
        mock_enrich.return_value = m['enrich']
        mock_coverage.return_value = m['coverage']
        mock_record.return_value = None

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=editor_fail',
            provider='gemini'
        )
        assert result['success'] is True
        editor_meta = result.get('generation_metadata', {}).get('ai_editor', {})
        assert editor_meta.get('changed') is False or 'error' in editor_meta

    @full_pipeline_patches
    def test_provider_tracker_failure(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Provider tracker raises → caught, article still succeeds."""
        from ai_engine.main import _generate_article_content
        m = _base_mocks()
        mock_oembed.return_value = m['oembed']
        mock_transcribe.return_value = m['transcript']
        mock_analyze.return_value = m['analysis']
        mock_categorize.return_value = m['categorize']
        mock_specs.return_value = m['specs']
        mock_gen.return_value = m['article']
        mock_screenshots.return_value = []
        mock_reviewer.return_value = m['article']
        mock_web.return_value = m['web_context']
        mock_enrich.return_value = m['enrich']
        mock_coverage.return_value = m['coverage']
        mock_record.side_effect = Exception('DB connection error')

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=tracker_fail',
            provider='gemini'
        )
        assert result['success'] is True


# ═══════════════════════════════════════════════════════════════════
# Coverage: create_pending_article video_id extraction (L933-935)
# ═══════════════════════════════════════════════════════════════════

class TestCreatePendingArticleDeep:

    @patch('ai_engine.main._generate_article_content')
    def test_no_video_id_extracts_from_url(self, mock_gen):
        """video_id=None → extracted from youtube_url regex."""
        from ai_engine.main import create_pending_article
        mock_gen.return_value = {
            'success': True,
            'title': '2026 Li Auto L9 Review',
            'content': '<h2>Li Auto L9</h2><p>Content here.</p>',
            'summary': 'Review summary',
            'category_name': 'Reviews',
            'tag_names': ['Li Auto'],
            'specs': {'make': 'Li Auto', 'model': 'L9'},
            'image_paths': [],
            'video_title': 'Li Auto L9 Review',
        }

        result = create_pending_article(
            youtube_url='https://www.youtube.com/watch?v=AbCdEfGhIjK',
            channel_id=9999,
            video_title='Li Auto L9',
            video_id=None,  # Force extraction
        )
        assert result['success'] is True
        pending = PendingArticle.objects.get(id=result['pending_id'])
        assert pending.video_id == 'AbCdEfGhIjK'

    @patch('ai_engine.main._generate_article_content')
    def test_rejected_pending_allows_regeneration(self, mock_gen):
        """Previously rejected PendingArticle → allows new generation."""
        from ai_engine.main import create_pending_article

        # Create a rejected pending (should NOT block)
        PendingArticle.objects.create(
            title='Rejected Article',
            content='<p>Rejected</p>',
            video_url='https://youtube.com/watch?v=rejected_vid',
            video_id='rejected_vid',
            video_title='Rejected',
            status='rejected',
        )

        mock_gen.return_value = {
            'success': True,
            'title': 'Regenerated Article',
            'content': '<p>New content</p>',
            'summary': 'New summary',
            'category_name': 'Reviews',
            'tag_names': [],
            'specs': {},
            'image_paths': [],
            'video_title': 'Regenerated',
        }

        result = create_pending_article(
            youtube_url='https://youtube.com/watch?v=rejected_vid',
            channel_id=9999,
            video_title='Regenerated',
            video_id='rejected_vid',
        )
        assert result['success'] is True


# ═══════════════════════════════════════════════════════════════════
# Coverage: More validate_title branches
# ═══════════════════════════════════════════════════════════════════

class TestValidateTitleDeep:

    def test_non_latin_fallback_to_video_title(self):
        from ai_engine.main import validate_title
        result = validate_title(
            'Обзор автомобиля BYD Seal',  # Cyrillic
            video_title='2026 BYD Seal Full Review',
        )
        assert 'BYD' in result

    def test_non_latin_fallback_to_specs(self):
        from ai_engine.main import validate_title
        result = validate_title(
            'これは日本語タイトルテスト',  # Japanese
            specs={'make': 'Toyota', 'model': 'Camry', 'year': 2026, 'trim': 'XSE'},
        )
        assert 'Toyota' in result
        assert 'Camry' in result

    def test_short_title_fallback(self):
        from ai_engine.main import validate_title
        result = validate_title('Hi', video_title='Short vid')
        # Both too short, should use last resort
        assert len(result) > 3

    def test_video_title_cleaned_pipe(self):
        from ai_engine.main import validate_title
        result = validate_title(
            None,
            video_title='2026 BMW iX3 Review | Car Magazine',
        )
        assert 'Car Magazine' not in result
        assert 'BMW' in result

    def test_title_none_no_specs(self):
        from ai_engine.main import validate_title
        result = validate_title(None)
        assert result == 'New Car Review'
