"""
Surgical tests for ai_engine/main.py — targeting every remaining coverable line.
Goal: push from 88% → 95%+

Lines targeted:
  L92   - _is_generic_header regex patterns (Final Verdict, 2025 Performance, etc.)
  L131  - validate_title: clean_vt short → fall to video_title.strip()
  L148  - validate_title: short latin title last resort
  L167  - extract_title: h2 with < 10 chars skipped
  L351-362 - Model tag auto-add from DB
  L414-415 - Duplicate check exception catch
  L476-477 - Post-enrichment drivetrain tag (2nd pass, when first pass skipped AWD)
  L492-493 - Price segment: Premium ($50K-$80K)
  L495-496 - Price segment: Luxury ($80K+)
  L600-604 - Screenshot path doesn't exist → appended raw
  L643-644 - Summary: no <p> in article → full content fallback
  L647     - Summary still empty → specs-based fallback
  L672-673 - AI editor returns unchanged content
"""
import pytest
from unittest.mock import patch, MagicMock
from news.models import Article, Tag, TagGroup, CarSpecification, PendingArticle

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════
# PURE FUNCTION TESTS  (no pipeline needed)
# ═══════════════════════════════════════════════════════════════════

class TestIsGenericHeaderRegex:
    """Cover L92 — regex branch returns True."""

    def test_year_performance(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header("2025 Performance") is True

    def test_year_specs(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header("2026 Specs") is True

    def test_year_design(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header("The 2024 Design") is True

    def test_final_verdict(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header("Final Verdict") is True

    def test_final_thoughts(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header("Final Thoughts") is True

    def test_conclusions(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header("Conclusions") is True

    def test_key_features(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header("Key Features") is True

    def test_key_specifications(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header("Specifications") is True

    def test_key_highlights(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header("Key Highlights") is True

    def test_driving_experience(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header("Driving Experience") is True

    def test_road_test(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header("Road Test") is True

    def test_ride_review(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header("Ride Review") is True

    def test_pros_and(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header("Pros and") is True


class TestValidateTitleEdges:
    """Cover L131-132 and L148."""

    def test_video_title_short_cleaned_falls_to_raw(self):
        """clean_vt is ≤10 chars after stripping suffix → use raw video_title (L131-132)."""
        from ai_engine.main import validate_title
        # "BYD | Channel Name" → clean_vt = "BYD" (3 chars, too short)
        # But full video_title = "BYD | Channel Name" (18 chars, > 10)
        result = validate_title(
            None,  # no main title
            video_title='BYD Review | Channel Name',
        )
        # Should use clean_vt "BYD Review" (10 chars) — exactly at boundary
        # Actually "BYD Review" is 10 chars — need > 10, so it would fall through
        # Let's use something that cleans to exactly ≤10
        result = validate_title(
            None,
            video_title='Short Cars | Super Long Channel Name Here',
        )
        # clean_vt = "Short Cars" (10 chars, NOT > 10), so L129 fails
        # L131: not non-latin → L132 returns video_title.strip()
        assert 'Short Cars' in result

    def test_short_latin_title_last_resort(self):
        """Title 5 < len ≤ 15, no video_title, no specs → L148."""
        from ai_engine.main import validate_title
        result = validate_title('BYD Review')  # 10 chars, > 5 but ≤ 15
        assert result == 'BYD Review'

    def test_very_short_title_no_fallbacks(self):
        """Title ≤ 5, no video_title, no specs → 'New Car Review' (L149)."""
        from ai_engine.main import validate_title
        result = validate_title('Hi')
        assert result == 'New Car Review'


class TestExtractTitleEdges:
    """Cover L167 — short h2 skipped."""

    def test_short_h2_skipped(self):
        """h2 with < 10 chars is skipped, next valid h2 used."""
        from ai_engine.main import extract_title
        html = '<h2>Hey</h2><h2>2026 BYD Seal Complete Review</h2>'
        assert extract_title(html) == '2026 BYD Seal Complete Review'

    def test_all_short_h2_returns_none(self):
        """All h2 < 10 chars → returns None."""
        from ai_engine.main import extract_title
        html = '<h2>Short</h2><h2>Tiny</h2>'
        assert extract_title(html) is None


# ═══════════════════════════════════════════════════════════════════
# PIPELINE TESTS — need full mock stack
# ═══════════════════════════════════════════════════════════════════

LONG_TRANSCRIPT = 'Detailed look at the 2026 BYD Seal electric sedan with AWD' * 10

BIG_ARTICLE = (
    '<h2>2026 BYD Seal AWD Review</h2>'
    '<p>The 2026 BYD Seal delivers 530 horsepower with dual motors.</p>'
    '<h2>Performance</h2><p>0-100 in 3.8 seconds with AWD.</p>'
) * 2

ANALYSIS_STR = (
    "Make: BYD\nModel: Seal\nYear: 2026\nEngine: Electric\n"
    "Horsepower: 530\nDrivetrain: AWD\nPrice: $35,000\n"
    "Summary: Revolutionary electric sedan."
)

SPECS = {
    'make': 'BYD', 'model': 'Seal', 'year': 2026,
    'trim': 'Not specified', 'engine': 'Electric',
    'horsepower': 530, 'drivetrain': 'AWD',
    'battery': '82.5 kWh', 'range': '570 km',
    'price': '$35,000', 'seo_title': '',
}


def _pipeline_patches(func):
    """Decorator: patches ALL external deps for _generate_article_content."""
    from functools import wraps
    @wraps(func)
    @patch('ai_engine.modules.provider_tracker.record_generation')
    @patch('ai_engine.modules.spec_refill.compute_coverage')
    @patch('ai_engine.modules.specs_enricher.enrich_specs_from_web')
    @patch('ai_engine.modules.searcher.get_web_context')
    @patch('ai_engine.modules.article_reviewer.review_article')
    @patch('ai_engine.modules.downloader.extract_video_screenshots')
    @patch('ai_engine.modules.article_generator.generate_article')
    @patch('ai_engine.modules.analyzer.extract_specs_dict')
    @patch('ai_engine.modules.analyzer.categorize_article')
    @patch('ai_engine.modules.analyzer.analyze_transcript')
    @patch('ai_engine.modules.transcriber.transcribe_from_youtube')
    @patch('ai_engine.modules.content_generator.requests.get')
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def _setup_mocks(mock_oembed, mock_transcribe, mock_analyze,
                 mock_categorize, mock_specs, mock_gen, mock_screenshots,
                 mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record,
                 **overrides):
    """Configure all mocks with defaults, apply overrides."""
    mock_oembed.return_value = overrides.get('oembed', MagicMock(
        status_code=200,
        json=lambda: {'title': 'BYD Seal', 'author_name': 'TestCh', 'author_url': ''}
    ))
    mock_transcribe.return_value = overrides.get('transcript', LONG_TRANSCRIPT)
    mock_analyze.return_value = overrides.get('analysis', ANALYSIS_STR)
    mock_categorize.return_value = overrides.get('categorize', ('Reviews', overrides.get('tags', ['BYD', 'Electric'])))
    specs = overrides.get('specs', SPECS.copy())
    mock_specs.return_value = specs
    mock_gen.return_value = overrides.get('article', BIG_ARTICLE)
    mock_screenshots.return_value = overrides.get('screenshots', [])
    mock_reviewer.return_value = overrides.get('reviewer', overrides.get('article', BIG_ARTICLE))
    mock_web.return_value = overrides.get('web_context', 'Web context data')
    mock_enrich.return_value = overrides.get('enrich', specs.copy())
    mock_coverage.return_value = overrides.get('coverage', (8, 12, 80, []))
    mock_record.return_value = None
    # Handle side_effects
    for key, val in overrides.items():
        if key.endswith('_side_effect'):
            mock_name = key.replace('_side_effect', '')
            mock_map = {
                'web': mock_web, 'enrich': mock_enrich,
                'coverage': mock_coverage, 'screenshots': mock_screenshots,
                'reviewer': mock_reviewer, 'record': mock_record,
            }
            if mock_name in mock_map:
                mock_map[mock_name].side_effect = val
                mock_map[mock_name].return_value = None
    return specs


class TestModelTagAutoAdd:
    """Cover L351-362: auto-add model tag from DB when TagGroup 'Models' has matching tags."""

    @_pipeline_patches
    def test_model_tag_added_from_db(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Model tag exists in DB under 'Models' group → auto-added."""
        from ai_engine.main import _generate_article_content

        # Create TagGroup 'Models' with a tag that matches specs model
        tg = TagGroup.objects.create(name='Models')
        Tag.objects.create(name='Seal', slug='seal', group=tg)

        specs = SPECS.copy()
        # Tags don't include 'Seal' yet → should be auto-added
        _setup_mocks(
            mock_oembed, mock_transcribe, mock_analyze,
            mock_categorize, mock_specs, mock_gen, mock_screenshots,
            mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record,
            tags=['BYD', 'Electric'],  # No 'Seal' tag
            specs=specs,
        )

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=model_tag_test',
            provider='gemini'
        )
        assert result['success'] is True
        assert 'Seal' in result['tag_names']

    @_pipeline_patches
    def test_model_tag_already_present(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Model tag already in tag_names → L351-353 sets has_model_tag=True, skips add."""
        from ai_engine.main import _generate_article_content

        tg = TagGroup.objects.create(name='Models')
        Tag.objects.create(name='Seal', slug='seal-model', group=tg)

        _setup_mocks(
            mock_oembed, mock_transcribe, mock_analyze,
            mock_categorize, mock_specs, mock_gen, mock_screenshots,
            mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record,
            tags=['BYD', 'Electric', 'Seal'],  # Already has 'Seal'
        )

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=model_tag_exists',
            provider='gemini'
        )
        assert result['success'] is True
        # 'Seal' should appear only once (not duplicated)
        assert result['tag_names'].count('Seal') == 1


class TestDuplicateCheckException:
    """Cover L414-415: duplicate check itself raises exception → caught."""

    @_pipeline_patches
    def test_duplicate_check_db_exception(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        from ai_engine.main import _generate_article_content

        _setup_mocks(
            mock_oembed, mock_transcribe, mock_analyze,
            mock_categorize, mock_specs, mock_gen, mock_screenshots,
            mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record,
        )

        # Patch CarSpecification.objects.filter to raise inside _generate_article_content
        with patch('news.models.CarSpecification.objects') as mock_cs:
            mock_cs.filter.side_effect = Exception('DB connection lost')

            result = _generate_article_content(
                'https://www.youtube.com/watch?v=dup_exc_test',
                provider='gemini'
            )
        assert result['success'] is True  # Continues despite dup check failure


class TestPostEnrichmentDrivetrain:
    """Cover L476-477: drivetrain tag added post-enrichment (2nd pass)."""

    @_pipeline_patches
    def test_drivetrain_added_post_enrichment(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        from ai_engine.main import _generate_article_content

        # Specs start with drivetrain='Not specified', enricher returns 'RWD'
        specs_no_dt = SPECS.copy()
        specs_no_dt['drivetrain'] = 'Not specified'

        enriched = specs_no_dt.copy()
        enriched['drivetrain'] = 'RWD'  # Enricher found it

        _setup_mocks(
            mock_oembed, mock_transcribe, mock_analyze,
            mock_categorize, mock_specs, mock_gen, mock_screenshots,
            mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record,
            specs=specs_no_dt,
            enrich=enriched,
            tags=['BYD', 'Electric'],  # No drivetrain tag yet
        )

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=dt_post_enrich',
            provider='gemini'
        )
        assert result['success'] is True
        assert 'RWD' in result['tag_names']


class TestPriceSegmentTags:
    """Cover L492-493 (Premium) and L495-496 (Luxury)."""

    @_pipeline_patches
    def test_premium_segment_tag(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        from ai_engine.main import _generate_article_content

        _setup_mocks(
            mock_oembed, mock_transcribe, mock_analyze,
            mock_categorize, mock_specs, mock_gen, mock_screenshots,
            mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record,
            tags=['BYD', 'Electric'],
        )

        with patch('ai_engine.modules.analyzer.extract_price_usd', return_value=65000):
            result = _generate_article_content(
                'https://www.youtube.com/watch?v=premium_test',
                provider='gemini'
            )
        assert result['success'] is True
        assert 'Premium' in result['tag_names']

    @_pipeline_patches
    def test_luxury_segment_tag(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        from ai_engine.main import _generate_article_content

        _setup_mocks(
            mock_oembed, mock_transcribe, mock_analyze,
            mock_categorize, mock_specs, mock_gen, mock_screenshots,
            mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record,
            tags=['Mercedes', 'Electric'],
        )

        with patch('ai_engine.modules.analyzer.extract_price_usd', return_value=120000):
            result = _generate_article_content(
                'https://www.youtube.com/watch?v=luxury_test',
                provider='gemini'
            )
        assert result['success'] is True
        assert 'Luxury' in result['tag_names']


class TestScreenshotNonExistentPath:
    """Cover L600-604: screenshot path doesn't exist on disk → appended raw."""

    @_pipeline_patches
    def test_nonexistent_screenshot_path(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        from ai_engine.main import _generate_article_content

        _setup_mocks(
            mock_oembed, mock_transcribe, mock_analyze,
            mock_categorize, mock_specs, mock_gen, mock_screenshots,
            mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record,
            screenshots=['/nonexistent/path/screenshot1.jpg'],
        )

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=nonexist_ss',
            provider='gemini'
        )
        assert result['success'] is True
        assert '/nonexistent/path/screenshot1.jpg' in result['image_paths']


class TestSummaryFallbacks:
    """Cover L643-644 (no <p> fallback) and L647 (empty → specs fallback)."""

    @_pipeline_patches
    def test_summary_no_p_tag_fallback(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Article has no <p> tags → uses full cleaned content (L643-644)."""
        from ai_engine.main import _generate_article_content

        # Analysis without 'Summary:' and article without <p> tags
        no_p_article = (
            '<h2>2026 BYD Seal Review</h2>'
            '<div>The BYD Seal is a revolutionary electric sedan.</div>'
            '<h3>Performance</h3><div>530 hp dual motor AWD system.</div>'
        ) * 3  # Make > 100 chars

        _setup_mocks(
            mock_oembed, mock_transcribe, mock_analyze,
            mock_categorize, mock_specs, mock_gen, mock_screenshots,
            mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record,
            analysis="Make: BYD\nModel: Seal\nYear: 2026",  # No 'Summary:' line
            article=no_p_article,
            reviewer=no_p_article,
        )

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=no_p_summary',
            provider='gemini'
        )
        assert result['success'] is True
        assert len(result['summary']) > 0

    @_pipeline_patches
    def test_summary_empty_specs_fallback(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Article is effectively empty after cleaning → specs fallback (L647)."""
        from ai_engine.main import _generate_article_content

        # Article with only tags, nothing extractable
        empty_article = '<h2>     </h2>' * 20  # > 100 chars of just tags

        _setup_mocks(
            mock_oembed, mock_transcribe, mock_analyze,
            mock_categorize, mock_specs, mock_gen, mock_screenshots,
            mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record,
            analysis="Make: BYD\nModel: Seal",  # No Summary
            article=empty_article,
            reviewer=empty_article,
        )

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=empty_summary',
            provider='gemini'
        )
        assert result['success'] is True
        assert 'BYD' in result['summary']
        assert 'Seal' in result['summary']


class TestAIEditorUnchanged:
    """Cover L672-673: reviewer returns identical content → changed=False."""

    @_pipeline_patches
    def test_editor_no_changes(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        from ai_engine.main import _generate_article_content

        _setup_mocks(
            mock_oembed, mock_transcribe, mock_analyze,
            mock_categorize, mock_specs, mock_gen, mock_screenshots,
            mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record,
        )

        # Get the exact article that generate_article returns (with gen_stamp appended)
        # The reviewer must return the EXACT same string including the stamp
        # We need to match what _generate_article_content produces after stamping
        # Trick: make reviewer a side_effect that returns its input
        mock_reviewer.side_effect = lambda html, specs, provider: html

        result = _generate_article_content(
            'https://www.youtube.com/watch?v=editor_same',
            provider='gemini'
        )
        assert result['success'] is True
        meta = result['generation_metadata']['ai_editor']
        assert meta['changed'] is False


class TestWebSocketProgressCover:
    """Cover L255-256: WebSocket send_progress inner exception print."""

    @_pipeline_patches
    def test_websocket_inner_exception(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        from ai_engine.main import _generate_article_content

        _setup_mocks(
            mock_oembed, mock_transcribe, mock_analyze,
            mock_categorize, mock_specs, mock_gen, mock_screenshots,
            mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record,
        )
        mock_reviewer.side_effect = lambda html, specs, provider: html

        # Patch the channels imports inside the send_progress function
        with patch.dict('sys.modules', {
            'asgiref.sync': MagicMock(async_to_sync=MagicMock(side_effect=Exception('WS fail'))),
            'channels.layers': MagicMock(get_channel_layer=MagicMock(return_value=MagicMock())),
        }):
            result = _generate_article_content(
                'https://www.youtube.com/watch?v=ws_inner_exc',
                task_id='force-ws-path',  # task_id forces WebSocket path
                provider='gemini'
            )
        assert result['success'] is True


class TestModelTagException:
    """Cover L361-362: model tag auto-add raises exception → caught."""

    @_pipeline_patches
    def test_model_tag_query_fails(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        from ai_engine.main import _generate_article_content

        _setup_mocks(
            mock_oembed, mock_transcribe, mock_analyze,
            mock_categorize, mock_specs, mock_gen, mock_screenshots,
            mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record,
        )

        # Patch Tag.objects.filter to raise when querying Models group
        original_filter = Tag.objects.filter
        def broken_filter(**kwargs):
            if kwargs.get('group__name') == 'Models':
                raise Exception('DB error on tag query')
            return original_filter(**kwargs)

        with patch.object(Tag.objects, 'filter', side_effect=broken_filter):
            result = _generate_article_content(
                'https://www.youtube.com/watch?v=model_tag_exc',
                provider='gemini'
            )
        assert result['success'] is True


class TestCopyToMediaException:
    """Cover L600-602: shutil.copy2 fails → screenshot path appended as last resort."""

    @_pipeline_patches
    def test_copy_to_media_fails(
        self, mock_oembed, mock_transcribe, mock_analyze,
        mock_categorize, mock_specs, mock_gen, mock_screenshots,
        mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record
    ):
        """Cloudinary fails AND local copy fails → raw path appended as last resort."""
        from ai_engine.main import _generate_article_content
        import tempfile, os

        # Create a real temp file so os.path.exists returns True
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'\xff\xd8\xff' + b'\x00' * 100)
            temp_path = f.name

        try:
            _setup_mocks(
                mock_oembed, mock_transcribe, mock_analyze,
                mock_categorize, mock_specs, mock_gen, mock_screenshots,
                mock_reviewer, mock_web, mock_enrich, mock_coverage, mock_record,
                screenshots=[temp_path],
            )

            # No CLOUDINARY_URL → skips cloudinary
            # shutil.copy2 fails → L600-602 catch block
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop('CLOUDINARY_URL', None)
                with patch('shutil.copy2', side_effect=PermissionError('No write permission')):
                    result = _generate_article_content(
                        'https://www.youtube.com/watch?v=copy_fail',
                        provider='gemini'
                    )
            assert result['success'] is True
            assert temp_path in result['image_paths']
        finally:
            os.unlink(temp_path)


class TestTitleVariantsEmpty:
    """Cover L775-776: AI returns no valid title alternatives."""

    def test_ai_returns_short_lines_only(self):
        """AI returns only short/empty lines → alt_titles is [] → returns []."""
        from ai_engine.main import generate_title_variants
        from news.models import Article

        article = Article.objects.create(
            title='2026 BYD Seal AWD Review',
            slug='test-variants-empty',
            content='<p>Content</p>',
            is_published=True,
        )

        with patch('ai_engine.modules.ai_provider.get_ai_provider') as mock_ai:
            mock_provider = MagicMock()
            # Return only short lines < 10 chars or empty
            mock_provider.generate_completion.return_value = "OK\n\nHi\n"
            mock_ai.return_value = mock_provider

            result = generate_title_variants(article)
        assert result == []

    def test_ai_returns_only_numbered(self):
        """AI returns numbered lines that get filtered out → empty."""
        from ai_engine.main import generate_title_variants
        from news.models import Article

        article = Article.objects.create(
            title='2026 NIO ET9 Review',
            slug='test-variants-numbered',
            content='<p>Content</p>',
            is_published=True,
        )

        with patch('ai_engine.modules.ai_provider.get_ai_provider') as mock_ai:
            mock_provider = MagicMock()
            # Lines start with numbering → filtered, then short → filtered
            mock_provider.generate_completion.return_value = "1. Short\n2. Tiny\n"
            mock_ai.return_value = mock_provider

            result = generate_title_variants(article)
        assert result == []
