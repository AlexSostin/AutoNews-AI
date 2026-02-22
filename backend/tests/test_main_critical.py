"""
Critical coverage: ai_engine/main.py (20% → 60%+)

Tests for:
- _generate_article_content (L231-732) — full YouTube→article pipeline
- generate_article_from_youtube (L815-875) — publish flow
- create_pending_article (L878-957) — pending queue flow
- generate_title_variants (L734-812) — A/B testing
- check_duplicate (L209-228)
- validate_title, extract_title, _is_generic_header
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from django.contrib.auth.models import User
from news.models import (
    Article, Category, Tag, TagGroup, CarSpecification,
    PendingArticle, YouTubeChannel, ArticleTitleVariant,
)

pytestmark = pytest.mark.django_db

# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

@pytest.fixture
def article():
    return Article.objects.create(
        title='2026 BYD Seal Review',
        slug='byd-seal-review',
        content='<h2>BYD Seal</h2><p>Full review of the BYD Seal</p>',
        youtube_url='https://www.youtube.com/watch?v=test123abc',
        is_published=True,
    )


@pytest.fixture
def category():
    return Category.objects.create(name='Reviews', slug='reviews')


@pytest.fixture
def channel(category):
    return YouTubeChannel.objects.create(
        name='Test Auto Channel',
        channel_url='https://www.youtube.com/@testauto',
        is_enabled=True,
        default_category=category,
    )


MOCK_ANALYSIS = (
    "Make: BYD\nModel: Seal\nYear: 2026\nEngine: Electric\n"
    "Horsepower: 530 hp\nDrivetrain: AWD\nBattery: 82.5 kWh\n"
    "Range: 570 km\nPrice: $35,000\nSummary: The BYD Seal is great."
)

MOCK_ARTICLE_HTML = (
    '<h2>2026 BYD Seal Review</h2>'
    '<p>The 2026 BYD Seal is an impressive electric sedan.</p>'
    '<h2>Performance &amp; Specifications</h2>'
    '<p>It produces 530 horsepower from dual motors with AWD.</p>'
    '<p>The 82.5 kWh battery provides up to 570 km of range.</p>'
)

MOCK_SPECS = {
    'make': 'BYD', 'model': 'Seal', 'year': 2026,
    'trim': 'AWD', 'engine': 'Electric', 'horsepower': 530,
    'drivetrain': 'AWD', 'battery': '82.5 kWh', 'range': '570 km',
    'price': '$35,000', 'seo_title': '',
}


def _build_full_mock_patchset():
    """Returns dict of patches needed for _generate_article_content."""
    return {
        'ai_engine.main.transcribe_from_youtube': MOCK_ANALYSIS[:200],
        'ai_engine.main.analyze_transcript': MOCK_ANALYSIS,
        'ai_engine.main.generate_article': MOCK_ARTICLE_HTML,
        'ai_engine.main.extract_video_screenshots': [],
        'ai_engine.main.publish_article': MagicMock(),
    }


# ═══════════════════════════════════════════════════════════════════
# _is_generic_header + _contains_non_latin (L66-103)
# ═══════════════════════════════════════════════════════════════════

class TestHelpers:

    def test_is_generic_header_true(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header('Performance & Specs') is True
        assert _is_generic_header('conclusion') is True

    def test_is_generic_header_false(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header('2026 BYD Seal AWD Review') is False

    def test_contains_non_latin(self):
        from ai_engine.main import _contains_non_latin
        assert _contains_non_latin('Тест') is True
        assert _contains_non_latin('Test') is False

    def test_validate_title_good(self):
        from ai_engine.main import validate_title
        result = validate_title('2026 BYD Seal Review')
        assert 'BYD' in result

    def test_validate_title_generic_fallback(self):
        from ai_engine.main import validate_title
        result = validate_title('Performance & Specs',
                                video_title='2026 BYD Seal Full Review',
                                specs={'make': 'BYD', 'model': 'Seal'})
        assert len(result) > 10

    def test_validate_title_none(self):
        from ai_engine.main import validate_title
        result = validate_title(None, specs={'make': 'BYD', 'model': 'Seal', 'year': 2026})
        assert 'BYD' in result

    def test_extract_title_from_html(self):
        from ai_engine.main import extract_title
        result = extract_title('<h2>2026 NIO ET9 Review</h2><p>Content</p>')
        assert result == '2026 NIO ET9 Review'

    def test_extract_title_skips_generic(self):
        from ai_engine.main import extract_title
        html = '<h2>Performance & Specs</h2><h2>2026 NIO ET9 Review</h2>'
        result = extract_title(html)
        assert 'NIO' in result


# ═══════════════════════════════════════════════════════════════════
# check_duplicate (L209-228)
# ═══════════════════════════════════════════════════════════════════

class TestCheckDuplicate:

    def test_no_duplicate(self):
        from ai_engine.main import check_duplicate
        result = check_duplicate('https://www.youtube.com/watch?v=nonexistent')
        assert result is None

    def test_has_duplicate(self, article):
        from ai_engine.main import check_duplicate
        result = check_duplicate('https://www.youtube.com/watch?v=test123abc')
        assert result is not None
        assert result.id == article.id


# ═══════════════════════════════════════════════════════════════════
# _generate_article_content (L231-732)
# ═══════════════════════════════════════════════════════════════════

class TestGenerateArticleContent:

    @patch('ai_engine.main.requests.get')
    @patch('ai_engine.main.transcribe_from_youtube')
    @patch('ai_engine.main.analyze_transcript')
    @patch('ai_engine.modules.analyzer.categorize_article')
    @patch('ai_engine.modules.analyzer.extract_specs_dict')
    @patch('ai_engine.main.generate_article')
    @patch('ai_engine.main.extract_video_screenshots')
    @patch('ai_engine.modules.article_reviewer.review_article')
    @patch('ai_engine.modules.searcher.get_web_context')
    @patch('ai_engine.modules.specs_enricher.enrich_specs_from_web')
    @patch('ai_engine.modules.spec_refill.compute_coverage')
    @patch('ai_engine.modules.provider_tracker.record_generation')
    def test_full_pipeline_success(
        self, mock_record, mock_coverage, mock_enrich_web,
        mock_web_ctx, mock_reviewer, mock_screenshots,
        mock_gen_article, mock_specs, mock_categorize,
        mock_analyze, mock_transcribe, mock_oembed
    ):
        from ai_engine.main import _generate_article_content

        # Setup mocks
        mock_oembed.return_value = MagicMock(
            status_code=200,
            json=lambda: {'title': 'BYD Seal Review', 'author_name': 'Test Channel', 'author_url': 'https://youtube.com/@test'}
        )
        mock_transcribe.return_value = 'This is a long transcript about the BYD Seal electric car with many details...' * 5
        mock_analyze.return_value = MOCK_ANALYSIS
        mock_categorize.return_value = ('Reviews', ['BYD', 'Electric', 'Sedan'])
        mock_specs.return_value = MOCK_SPECS.copy()
        mock_gen_article.return_value = MOCK_ARTICLE_HTML
        mock_screenshots.return_value = []
        mock_reviewer.return_value = MOCK_ARTICLE_HTML
        mock_web_ctx.return_value = 'Web context data about BYD Seal specs'
        mock_enrich_web.return_value = MOCK_SPECS.copy()
        mock_coverage.return_value = (8, 12, 67, ['range', 'price', 'torque', 'acceleration'])
        mock_record.return_value = None

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=abc123xyz',
            provider='gemini'
        )

        assert result['success'] is True
        assert 'title' in result
        assert 'content' in result
        assert 'specs' in result
        assert 'tag_names' in result

    @patch('ai_engine.main.transcribe_from_youtube')
    def test_transcript_failure(self, mock_transcribe):
        from ai_engine.main import _generate_article_content
        mock_transcribe.return_value = 'ERROR: No transcript found'

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=bad123',
            provider='gemini'
        )
        assert result['success'] is False
        assert 'error' in result

    @patch('ai_engine.main.transcribe_from_youtube')
    def test_transcript_too_short(self, mock_transcribe):
        from ai_engine.main import _generate_article_content
        mock_transcribe.return_value = 'Hi'

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=short1',
            provider='gemini'
        )
        assert result['success'] is False

    @patch('ai_engine.main.requests.get')
    @patch('ai_engine.main.transcribe_from_youtube')
    @patch('ai_engine.main.analyze_transcript')
    def test_analysis_failure(self, mock_analyze, mock_transcribe, mock_oembed):
        from ai_engine.main import _generate_article_content
        mock_oembed.return_value = MagicMock(status_code=404)
        mock_transcribe.return_value = 'Long transcript about cars and specifications...' * 5
        mock_analyze.return_value = None

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=fail1',
            provider='gemini'
        )
        assert result['success'] is False

    @patch('ai_engine.main.requests.get')
    @patch('ai_engine.main.transcribe_from_youtube')
    @patch('ai_engine.main.analyze_transcript')
    @patch('ai_engine.modules.analyzer.categorize_article')
    @patch('ai_engine.modules.analyzer.extract_specs_dict')
    @patch('ai_engine.main.generate_article')
    @patch('ai_engine.main.extract_video_screenshots')
    @patch('ai_engine.modules.article_reviewer.review_article')
    @patch('ai_engine.modules.spec_refill.compute_coverage')
    @patch('ai_engine.modules.provider_tracker.record_generation')
    def test_duplicate_detection(
        self, mock_record, mock_coverage,
        mock_reviewer, mock_screenshots,
        mock_gen_article, mock_specs, mock_categorize,
        mock_analyze, mock_transcribe, mock_oembed, article
    ):
        """If article already exists with same make+model, return skipped."""
        from ai_engine.main import _generate_article_content

        CarSpecification.objects.create(article=article, make='BYD', model='Seal')

        mock_oembed.return_value = MagicMock(status_code=200, json=lambda: {'title': 'test'})
        mock_transcribe.return_value = 'Transcript about the BYD Seal electric car review' * 5
        mock_analyze.return_value = MOCK_ANALYSIS
        mock_categorize.return_value = ('Reviews', ['BYD'])
        mock_specs.return_value = {'make': 'BYD', 'model': 'Seal', 'year': 2026, 'drivetrain': 'AWD'}
        mock_coverage.return_value = (5, 12, 42, [])

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=dup_test_1',
            provider='gemini'
        )
        assert result['success'] is False
        assert result.get('reason') == 'duplicate'

    @patch('ai_engine.main.requests.get')
    @patch('ai_engine.main.transcribe_from_youtube')
    @patch('ai_engine.main.analyze_transcript')
    @patch('ai_engine.modules.analyzer.categorize_article')
    @patch('ai_engine.modules.analyzer.extract_specs_dict')
    @patch('ai_engine.main.generate_article')
    @patch('ai_engine.main.extract_video_screenshots')
    @patch('ai_engine.modules.article_reviewer.review_article')
    @patch('ai_engine.modules.spec_refill.compute_coverage')
    @patch('ai_engine.modules.provider_tracker.record_generation')
    def test_with_groq_provider(
        self, mock_record, mock_coverage,
        mock_reviewer, mock_screenshots,
        mock_gen_article, mock_specs, mock_categorize,
        mock_analyze, mock_transcribe, mock_oembed
    ):
        from ai_engine.main import _generate_article_content

        mock_oembed.return_value = MagicMock(status_code=200, json=lambda: {'title': 'test'})
        mock_transcribe.return_value = 'Transcript about the NIO ET9 luxury sedan' * 5
        mock_analyze.return_value = MOCK_ANALYSIS
        mock_categorize.return_value = ('Reviews', ['NIO'])
        mock_specs.return_value = {'make': 'NIO', 'model': 'ET9', 'year': 2026}
        mock_gen_article.return_value = '<h2>2026 NIO ET9</h2><p>Review content</p>' * 3
        mock_screenshots.return_value = []
        mock_reviewer.return_value = '<h2>2026 NIO ET9</h2><p>Reviewed content</p>' * 3
        mock_coverage.return_value = (3, 12, 25, [])
        mock_record.return_value = None

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=groq_test_1',
            provider='groq'
        )
        assert result['success'] is True

    @patch('ai_engine.main.requests.get')
    @patch('ai_engine.main.transcribe_from_youtube')
    @patch('ai_engine.main.analyze_transcript')
    @patch('ai_engine.modules.analyzer.categorize_article')
    @patch('ai_engine.modules.analyzer.extract_specs_dict')
    @patch('ai_engine.main.generate_article')
    def test_article_too_short(
        self, mock_gen_article, mock_specs, mock_categorize,
        mock_analyze, mock_transcribe, mock_oembed
    ):
        from ai_engine.main import _generate_article_content

        mock_oembed.return_value = MagicMock(status_code=200, json=lambda: {'title': 'test'})
        mock_transcribe.return_value = 'Transcript content about cars' * 5
        mock_analyze.return_value = MOCK_ANALYSIS
        mock_categorize.return_value = ('Reviews', ['BMW'])
        mock_specs.return_value = {'make': 'BMW', 'model': 'iX3', 'year': 2026}
        mock_gen_article.return_value = '<p>Too short</p>'  # < 100 chars

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=short_article',
            provider='gemini'
        )
        assert result['success'] is False

    @patch('ai_engine.main.requests.get')
    @patch('ai_engine.main.transcribe_from_youtube')
    @patch('ai_engine.main.analyze_transcript')
    @patch('ai_engine.modules.analyzer.categorize_article')
    @patch('ai_engine.modules.analyzer.extract_specs_dict')
    @patch('ai_engine.main.generate_article')
    @patch('ai_engine.main.extract_video_screenshots')
    @patch('ai_engine.modules.article_reviewer.review_article')
    @patch('ai_engine.modules.spec_refill.compute_coverage')
    @patch('ai_engine.modules.provider_tracker.record_generation')
    def test_with_task_id_websocket(
        self, mock_record, mock_coverage,
        mock_reviewer, mock_screenshots,
        mock_gen_article, mock_specs, mock_categorize,
        mock_analyze, mock_transcribe, mock_oembed
    ):
        """With task_id → send_progress tries WebSocket."""
        from ai_engine.main import _generate_article_content

        mock_oembed.return_value = MagicMock(status_code=200, json=lambda: {'title': 'test'})
        mock_transcribe.return_value = 'Long transcript about ZEEKR 007 GT review' * 5
        mock_analyze.return_value = MOCK_ANALYSIS
        mock_categorize.return_value = ('Reviews', ['ZEEKR'])
        mock_specs.return_value = {'make': 'ZEEKR', 'model': '007 GT', 'year': 2026}
        mock_gen_article.return_value = MOCK_ARTICLE_HTML * 2
        mock_screenshots.return_value = []
        mock_reviewer.return_value = MOCK_ARTICLE_HTML * 2
        mock_coverage.return_value = (3, 12, 25, [])
        mock_record.return_value = None

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=ws_test',
            task_id='test-task-123',
            provider='gemini'
        )
        assert result['success'] is True


# ═══════════════════════════════════════════════════════════════════
# generate_article_from_youtube (L815-875)
# ═══════════════════════════════════════════════════════════════════

class TestGenerateArticleFromYouTube:

    def test_duplicate_returns_early(self, article):
        from ai_engine.main import generate_article_from_youtube
        result = generate_article_from_youtube(
            'https://www.youtube.com/watch?v=test123abc'
        )
        assert result['success'] is False
        assert result['duplicate'] is True

    @patch('ai_engine.main._generate_article_content')
    def test_generation_failure_propagated(self, mock_gen):
        from ai_engine.main import generate_article_from_youtube
        mock_gen.return_value = {'success': False, 'error': 'Transcript fail'}

        result = generate_article_from_youtube(
            'https://www.youtube.com/watch?v=new_video_1'
        )
        assert result['success'] is False

    @patch('ai_engine.modules.deep_specs.generate_deep_vehicle_specs')
    @patch('ai_engine.main.generate_title_variants')
    @patch('ai_engine.main.publish_article')
    @patch('ai_engine.main._generate_article_content')
    def test_success_publishes(self, mock_gen, mock_publish, mock_ab, mock_deep):
        from ai_engine.main import generate_article_from_youtube
        mock_article = MagicMock()
        mock_article.id = 999
        mock_article.slug = 'test-article'
        mock_publish.return_value = mock_article
        mock_gen.return_value = {
            'success': True,
            'title': '2026 Test Car Review',
            'content': '<p>Content</p>',
            'summary': 'Summary',
            'category_name': 'Reviews',
            'tag_names': ['Test'],
            'specs': {'make': 'Test', 'model': 'Car'},
            'image_paths': [],
            'meta_keywords': 'test, car',
            'author_name': 'Tester',
            'author_channel_url': 'https://youtube.com/@test',
            'generation_metadata': {},
            'web_context': '',
        }
        mock_ab.return_value = []
        mock_deep.return_value = None

        result = generate_article_from_youtube(
            'https://www.youtube.com/watch?v=brand_new',
            is_published=False
        )
        assert result['success'] is True
        assert result['article_id'] == 999
        mock_publish.assert_called_once()

    @patch('ai_engine.modules.deep_specs.generate_deep_vehicle_specs')
    @patch('ai_engine.main.generate_title_variants')
    @patch('ai_engine.main.publish_article')
    @patch('ai_engine.main._generate_article_content')
    def test_deep_specs_failure_doesnt_crash(self, mock_gen, mock_publish, mock_ab, mock_deep):
        from ai_engine.main import generate_article_from_youtube
        mock_article = MagicMock()
        mock_article.id = 1000
        mock_article.slug = 'test-deep-fail'
        mock_publish.return_value = mock_article
        mock_gen.return_value = {
            'success': True, 'title': 'T', 'content': '<p>C</p>',
            'summary': 'S', 'category_name': 'R', 'tag_names': [],
            'specs': {}, 'image_paths': [], 'meta_keywords': '',
            'author_name': '', 'author_channel_url': '',
            'generation_metadata': {}, 'web_context': '',
        }
        mock_ab.return_value = []
        mock_deep.side_effect = Exception('Deep specs crash')

        result = generate_article_from_youtube(
            'https://www.youtube.com/watch?v=deep_fail_1'
        )
        # Should still succeed despite deep_specs failure
        assert result['success'] is True


# ═══════════════════════════════════════════════════════════════════
# create_pending_article (L878-957)
# ═══════════════════════════════════════════════════════════════════

class TestCreatePendingArticle:

    def test_existing_article_skipped(self, article):
        from ai_engine.main import create_pending_article
        result = create_pending_article(
            youtube_url='https://www.youtube.com/watch?v=test123abc',
            channel_id=1,
            video_title='Test',
            video_id='test123abc',
        )
        assert result['success'] is False
        assert result['reason'] == 'exists'

    def test_already_pending(self, channel):
        PendingArticle.objects.create(
            title='Pending Test',
            content='<p>Content</p>',
            video_url='https://www.youtube.com/watch?v=pending_vid',
            video_id='pending_vid',
            video_title='Pending Video',
            status='pending',
        )
        from ai_engine.main import create_pending_article
        result = create_pending_article(
            youtube_url='https://www.youtube.com/watch?v=pending_vid',
            channel_id=channel.id,
            video_title='Pending Video',
            video_id='pending_vid',
        )
        assert result['success'] is False
        assert result['reason'] == 'pending'

    @patch('ai_engine.main._generate_article_content')
    def test_generation_failure(self, mock_gen, channel):
        from ai_engine.main import create_pending_article
        mock_gen.return_value = {'success': False, 'error': 'Failed'}

        result = create_pending_article(
            youtube_url='https://www.youtube.com/watch?v=gen_fail_1',
            channel_id=channel.id,
            video_title='Fail Video',
            video_id='gen_fail_1',
        )
        assert result['success'] is False

    @patch('ai_engine.main._generate_article_content')
    def test_success_creates_pending(self, mock_gen, channel):
        from ai_engine.main import create_pending_article
        mock_gen.return_value = {
            'success': True,
            'title': '2026 Xpeng G6 Review',
            'content': '<h2>Xpeng G6</h2><p>Content about the Xpeng G6</p>',
            'summary': 'Xpeng G6 review summary',
            'category_name': 'Reviews',
            'tag_names': ['Xpeng', 'Electric'],
            'specs': {'make': 'Xpeng', 'model': 'G6'},
            'image_paths': ['https://example.com/img1.jpg'],
            'video_title': 'Xpeng G6 Full Review',
        }

        result = create_pending_article(
            youtube_url='https://www.youtube.com/watch?v=xpeng_new_1',
            channel_id=channel.id,
            video_title='Xpeng G6 Full Review',
            video_id='xpeng_new_1',
        )
        assert result['success'] is True
        assert 'pending_id' in result
        pending = PendingArticle.objects.get(id=result['pending_id'])
        assert pending.title == '2026 Xpeng G6 Review'

    @patch('ai_engine.main._generate_article_content')
    def test_no_channel(self, mock_gen):
        """No valid channel_id → still creates with channel=None."""
        from ai_engine.main import create_pending_article
        mock_gen.return_value = {
            'success': True,
            'title': 'No Channel Article',
            'content': '<p>Content goes here</p>',
            'summary': 'Summary',
            'category_name': 'News',
            'tag_names': [],
            'specs': {},
            'image_paths': [],
            'video_title': 'Video Title',
        }

        result = create_pending_article(
            youtube_url='https://www.youtube.com/watch?v=no_channel_1',
            channel_id=9999,  # doesn't exist
            video_title='Video Title',
            video_id='no_channel_1',
        )
        assert result['success'] is True


# ═══════════════════════════════════════════════════════════════════
# generate_title_variants (L734-812)
# ═══════════════════════════════════════════════════════════════════

class TestGenerateTitleVariants:

    def test_skips_if_variants_exist(self, article):
        ArticleTitleVariant.objects.create(
            article=article, variant='A', title=article.title
        )
        from ai_engine.main import generate_title_variants
        result = generate_title_variants(article)
        assert result == []

    @patch('modules.ai_provider.get_ai_provider')
    def test_creates_variants(self, mock_provider, article):
        from ai_engine.main import generate_title_variants
        mock_ai = MagicMock()
        mock_ai.generate_completion.return_value = (
            "2026 BYD Seal: The Electric Sedan That Redefines Value\n"
            "BYD Seal 2026 — Is This the Best EV Under $40K?"
        )
        mock_provider.return_value = mock_ai

        result = generate_title_variants(article, provider='gemini')
        assert len(result) >= 2  # A (original) + at least B
        variants = ArticleTitleVariant.objects.filter(article=article)
        assert variants.count() >= 2

    @pytest.mark.slow
    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_empty_ai_response(self, mock_provider, article):
        from ai_engine.main import generate_title_variants
        mock_ai = MagicMock()
        mock_ai.generate_completion.return_value = ''
        mock_provider.return_value = mock_ai

        result = generate_title_variants(article)
        assert result == []

    @patch('modules.ai_provider.get_ai_provider')
    def test_ai_exception_returns_empty(self, mock_provider):
        # Create a fresh article for this test to avoid variant collision
        art = Article.objects.create(
            title='2026 ZEEKR Test', slug='zeekr-test-exc',
            content='<p>Content</p>', is_published=True,
        )
        from ai_engine.main import generate_title_variants
        mock_provider.side_effect = Exception('AI provider unavailable')

        result = generate_title_variants(art)
        assert result == []
