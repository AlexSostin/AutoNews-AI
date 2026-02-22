"""
Tests for AI Engine core modules — main.py, deep_specs.py, publisher.py.
Focuses on pure logic functions (validators, parsers, helpers).
AI-dependent functions are mocked.
"""
import pytest
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════════════
# ai_engine/main.py — pure functions
# ═══════════════════════════════════════════════════════════════════════════

class TestIsGenericHeader:

    def test_generic_performance_header(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header('Performance & Specs') is True

    def test_generic_conclusion(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header('Final Verdict') is True

    def test_good_title(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header('2026 Tesla Model 3 Highland Review') is False

    def test_generic_key_features(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header('Key Features') is True

    def test_generic_driving_experience(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header('Driving Experience') is True

    def test_generic_interior_comfort(self):
        from ai_engine.main import _is_generic_header
        assert _is_generic_header('Interior & Comfort') is True

    def test_short_text_not_generic(self):
        from ai_engine.main import _is_generic_header
        # Short but not matching generic patterns
        assert _is_generic_header('BMW') is False


class TestContainsNonLatin:

    def test_english_text(self):
        from ai_engine.main import _contains_non_latin
        assert _contains_non_latin('Tesla Model 3 Review') is False

    def test_cyrillic_text(self):
        from ai_engine.main import _contains_non_latin
        assert _contains_non_latin('Тесла Модел 3 Обзор') is True

    def test_chinese_text(self):
        from ai_engine.main import _contains_non_latin
        assert _contains_non_latin('比亚迪汽车评测') is True

    def test_mixed_ok(self):
        from ai_engine.main import _contains_non_latin
        # 1-2 non-Latin chars should be fine
        assert _contains_non_latin('Tesla Мodel 3') is False


class TestValidateTitle:

    def test_valid_title(self):
        from ai_engine.main import validate_title
        result = validate_title('2026 Tesla Model 3 Highland Review')
        assert result == '2026 Tesla Model 3 Highland Review'

    def test_generic_title_with_video_fallback(self):
        from ai_engine.main import validate_title
        result = validate_title('Performance & Specs', video_title='BYD Seal Review 2026')
        assert 'BYD' in result or 'Seal' in result

    def test_generic_title_with_specs_fallback(self):
        from ai_engine.main import validate_title
        result = validate_title('Details', specs={'make': 'Tesla', 'model': 'Model Y', 'year': '2026'})
        assert 'Tesla' in result and 'Model Y' in result

    def test_short_title_fallback(self):
        from ai_engine.main import validate_title
        result = validate_title('Hi')
        assert result == 'New Car Review'

    def test_non_latin_title_rejected(self):
        from ai_engine.main import validate_title
        result = validate_title('Обзор автомобиля Тесла Модел', specs={'make': 'Tesla', 'model': 'Model 3'})
        assert 'Tesla' in result

    def test_none_title(self):
        from ai_engine.main import validate_title
        result = validate_title(None)
        assert result == 'New Car Review'

    def test_empty_title(self):
        from ai_engine.main import validate_title
        result = validate_title('')
        assert result == 'New Car Review'


class TestExtractTitle:

    def test_extracts_from_h2(self):
        from ai_engine.main import extract_title
        html = '<h2>2026 BMW iX xDrive50 Review</h2><p>Content</p>'
        assert extract_title(html) == '2026 BMW iX xDrive50 Review'

    def test_skips_generic_h2(self):
        from ai_engine.main import extract_title
        html = '<h2>Performance & Specifications</h2><h2>Tesla Model Y Review</h2>'
        assert extract_title(html) == 'Tesla Model Y Review'

    def test_no_h2_returns_none(self):
        from ai_engine.main import extract_title
        html = '<p>Just a paragraph</p>'
        assert extract_title(html) is None

    def test_h2_with_attributes(self):
        from ai_engine.main import extract_title
        html = '<h2 class="title">ZEEKR 001 Performance Review</h2>'
        assert extract_title(html) == 'ZEEKR 001 Performance Review'


class TestCheckDuplicate:

    def test_no_duplicate(self):
        from ai_engine.main import check_duplicate
        result = check_duplicate('https://youtube.com/watch?v=nonexistent123')
        # Returns None when no duplicate found
        assert result is None

    def test_existing_article(self):
        from ai_engine.main import check_duplicate
        from news.models import Article
        Article.objects.create(
            title='Test', slug='dup-check',
            content='c', youtube_url='https://youtube.com/watch?v=EXISTING',
        )
        result = check_duplicate('https://youtube.com/watch?v=EXISTING')
        # Returns the existing Article when duplicate found
        assert result is not None


# ═══════════════════════════════════════════════════════════════════════════
# deep_specs.py — pure validation functions
# ═══════════════════════════════════════════════════════════════════════════

class TestSafeInt:

    def test_normal(self):
        from ai_engine.modules.deep_specs import _safe_int
        assert _safe_int(200) == 200

    def test_string(self):
        from ai_engine.modules.deep_specs import _safe_int
        assert _safe_int('1,500') == 1500

    def test_float_string(self):
        from ai_engine.modules.deep_specs import _safe_int
        assert _safe_int('3.5') == 3

    def test_none(self):
        from ai_engine.modules.deep_specs import _safe_int
        assert _safe_int(None) is None

    def test_garbage(self):
        from ai_engine.modules.deep_specs import _safe_int
        assert _safe_int('not a number') is None


class TestSafeFloat:

    def test_normal(self):
        from ai_engine.modules.deep_specs import _safe_float
        assert _safe_float(3.14) == 3.14

    def test_string(self):
        from ai_engine.modules.deep_specs import _safe_float
        assert _safe_float('1,500.5') == 1500.5

    def test_none(self):
        from ai_engine.modules.deep_specs import _safe_float
        assert _safe_float(None) is None


class TestValidateChoice:

    def test_valid(self):
        from ai_engine.modules.deep_specs import _validate_choice, VALID_DRIVETRAINS
        assert _validate_choice('AWD', VALID_DRIVETRAINS) == 'AWD'

    def test_invalid(self):
        from ai_engine.modules.deep_specs import _validate_choice, VALID_DRIVETRAINS
        assert _validate_choice('XWYD', VALID_DRIVETRAINS) is None

    def test_none(self):
        from ai_engine.modules.deep_specs import _validate_choice, VALID_DRIVETRAINS
        assert _validate_choice(None, VALID_DRIVETRAINS) is None


class TestSanitizeTrim:

    def test_normal(self):
        from ai_engine.modules.deep_specs import _sanitize_trim
        assert _sanitize_trim('Long Range') == 'Long Range'

    def test_none_value(self):
        from ai_engine.modules.deep_specs import _sanitize_trim
        assert _sanitize_trim(None) == ''

    def test_garbage_none_string(self):
        from ai_engine.modules.deep_specs import _sanitize_trim
        assert _sanitize_trim('None') == ''

    def test_garbage_na(self):
        from ai_engine.modules.deep_specs import _sanitize_trim
        assert _sanitize_trim('N/A') == ''

    def test_garbage_standard(self):
        from ai_engine.modules.deep_specs import _sanitize_trim
        assert _sanitize_trim('Standard') == ''


class TestCleanModelName:

    def test_strips_brand_prefix(self):
        from ai_engine.modules.deep_specs import _clean_model_name
        assert _clean_model_name('ZEEKR 001', 'ZEEKR') == '001'

    def test_strips_trailing_verbs(self):
        from ai_engine.modules.deep_specs import _clean_model_name
        assert _clean_model_name('HS6 Sets', 'MG') == 'HS6'

    def test_preserves_valid_name(self):
        from ai_engine.modules.deep_specs import _clean_model_name
        assert _clean_model_name('Model 3', 'Tesla') == 'Model 3'

    def test_empty_input(self):
        from ai_engine.modules.deep_specs import _clean_model_name
        assert _clean_model_name('', 'Tesla') == ''

    def test_none_input(self):
        from ai_engine.modules.deep_specs import _clean_model_name
        assert _clean_model_name(None, 'Tesla') is None


class TestCleanPipeValue:

    def test_pipe_value(self):
        from ai_engine.modules.deep_specs import _clean_pipe_value
        assert _clean_pipe_value('FWD|AWD') == 'FWD'

    def test_no_pipe(self):
        from ai_engine.modules.deep_specs import _clean_pipe_value
        assert _clean_pipe_value('AWD') == 'AWD'

    def test_none(self):
        from ai_engine.modules.deep_specs import _clean_pipe_value
        assert _clean_pipe_value(None) is None


class TestParseAiResponse:

    def test_clean_json(self):
        from ai_engine.modules.deep_specs import _parse_ai_response
        result = _parse_ai_response('{"power_hp": 200}')
        assert result == {'power_hp': 200}

    def test_markdown_wrapped_json(self):
        from ai_engine.modules.deep_specs import _parse_ai_response
        result = _parse_ai_response('```json\n{"power_hp": 200}\n```')
        assert result == {'power_hp': 200}

    def test_invalid_json(self):
        from ai_engine.modules.deep_specs import _parse_ai_response
        assert _parse_ai_response('not json at all') is None

    def test_json_embedded_in_text(self):
        from ai_engine.modules.deep_specs import _parse_ai_response
        result = _parse_ai_response('Here are the specs: {"power_hp": 300}')
        assert result == {'power_hp': 300}


class TestBuildPrompt:

    def test_basic_prompt(self):
        from ai_engine.modules.deep_specs import _build_prompt
        prompt = _build_prompt('Tesla', 'Model 3', 'Long Range', 2026, None, '')
        assert 'Tesla' in prompt
        assert 'Model 3' in prompt

    def test_with_existing_specs(self):
        from ai_engine.modules.deep_specs import _build_prompt
        prompt = _build_prompt('BMW', 'iX', '', None, {'power_hp': 523}, '')
        assert '523' in prompt

    def test_with_web_context(self):
        from ai_engine.modules.deep_specs import _build_prompt
        prompt = _build_prompt('ZEEKR', '001', '', None, None, 'Web research data here')
        assert 'Web research data here' in prompt


# ═══════════════════════════════════════════════════════════════════════════
# publisher.py — pure functions
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractSummary:

    def test_extracts_first_paragraph(self):
        from ai_engine.modules.publisher import extract_summary
        html = '<h2>Title</h2><p>This is the summary paragraph.</p><p>Second para.</p>'
        result = extract_summary(html)
        assert result == 'This is the summary paragraph.'

    def test_no_paragraph(self):
        from ai_engine.modules.publisher import extract_summary
        html = '<h2>Title only</h2>'
        result = extract_summary(html)
        assert 'AI-generated' in result

    def test_strips_html_tags(self):
        from ai_engine.modules.publisher import extract_summary
        html = '<h2>Title</h2><p>Text with <strong>bold</strong> and <em>italic</em></p>'
        result = extract_summary(html)
        assert '<strong>' not in result
        assert 'bold' in result


class TestGenerateSeoTitle:

    def test_short_title_unchanged(self):
        from ai_engine.modules.publisher import generate_seo_title
        result = generate_seo_title('Tesla Model 3 Review')
        assert result == 'Tesla Model 3 Review'

    def test_long_title_truncated(self):
        from ai_engine.modules.publisher import generate_seo_title
        long_title = 'A' * 100
        result = generate_seo_title(long_title)
        assert len(result) <= 60

    def test_title_with_year_make_model(self):
        from ai_engine.modules.publisher import generate_seo_title
        result = generate_seo_title('The All New 2026 Tesla Model 3 Highland Long Range Review And Analysis')
        assert '2026' in result and 'Tesla' in result


class TestAddSpecBasedTags:

    def test_adds_existing_tag(self):
        from ai_engine.modules.publisher import _add_spec_based_tags
        from news.models import Article, Tag, TagGroup
        group = TagGroup.objects.create(name='Manufacturers', slug='manufacturers')
        Tag.objects.create(name='Tesla', slug='tesla', group=group)
        art = Article.objects.create(title='T', slug='spec-tag', content='c')
        _add_spec_based_tags(art, {'make': 'Tesla', 'model': 'Model 3'})
        assert art.tags.filter(slug='tesla').exists()

    def test_skips_nonexistent_tag(self):
        from ai_engine.modules.publisher import _add_spec_based_tags
        from news.models import Article
        art = Article.objects.create(title='T', slug='no-tag', content='c')
        # Should not crash even if brand tag doesn't exist
        _add_spec_based_tags(art, {'make': 'NonExistentBrand', 'model': 'X'})
        assert art.tags.count() == 0
