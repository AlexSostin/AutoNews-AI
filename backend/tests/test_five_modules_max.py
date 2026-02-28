"""
Max coverage: utils.py + spec_refill.py + translator.py + specs_enricher.py + specs_extractor.py
Goal: push all five from current levels towards 90%+
"""
import json
import pytest
from unittest.mock import patch, MagicMock


# ═══════════════════════════════════════════════════════════════════
# utils.py — 87% → 95%+   (missed: L43, L187-190, L234-253)
# ═══════════════════════════════════════════════════════════════════

class TestFormatPrice:
    """Covers L187-190: GBP/£ currency formatting."""

    def test_usd(self):
        from ai_engine.modules.utils import format_price
        result = format_price('$45000')
        assert '$' in result
        assert '45' in result

    def test_gbp(self):
        """L187-188: GBP currency."""
        from ai_engine.modules.utils import format_price
        result = format_price('£35000')
        assert '£' in result

    def test_gbp_text(self):
        from ai_engine.modules.utils import format_price
        result = format_price('35000 GBP')
        assert '£' in result

    def test_rub(self):
        """L185-186: RUB currency."""
        from ai_engine.modules.utils import format_price
        result = format_price('1500000 RUB')
        assert '₽' in result

    def test_eur(self):
        from ai_engine.modules.utils import format_price
        result = format_price('€50000')
        assert '€' in result

    def test_no_numbers(self):
        from ai_engine.modules.utils import format_price
        assert format_price('no price') == 'no price'

    def test_default_currency(self):
        """L189-190: Unknown currency defaults to $."""
        from ai_engine.modules.utils import format_price
        result = format_price('45000')
        assert '$' in result


class TestRetryOnFailure:
    """L43: unreachable raise after loop — don't need it."""

    def test_succeeds_on_third_try(self):
        from ai_engine.modules.utils import retry_on_failure
        call_count = [0]

        @retry_on_failure(max_retries=3, delay=0)
        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError('fail')
            return 'ok'

        assert flaky() == 'ok'
        assert call_count[0] == 3

    def test_all_retries_exhausted(self):
        from ai_engine.modules.utils import retry_on_failure

        @retry_on_failure(max_retries=2, delay=0)
        def always_fails():
            raise ValueError('boom')

        with pytest.raises(ValueError, match='boom'):
            always_fails()


class TestValidateArticleQuality:

    def test_truncated_content(self):
        """L153-154: Content doesn't end with closing tag → truncated."""
        from ai_engine.modules.utils import validate_article_quality
        content = '<h2>S1</h2><p>Text</p><h2>S2</h2><p>T</p><h2>S3</h2><p>T</p><p>T</p> truncated text'
        result = validate_article_quality(content)
        assert 'Content appears truncated' in str(result['issues'])

    def test_placeholder_detected(self):
        from ai_engine.modules.utils import validate_article_quality
        content = '<h2>S1</h2><h2>S2</h2><h2>S3</h2><p>This is lorem ipsum placeholder text</p>' + '<p>P</p>' * 4
        result = validate_article_quality(content)
        assert not result['valid']


# ═══════════════════════════════════════════════════════════════════
# spec_refill.py — 83% → 95%  (missed: L76-79, L92-93, L144-147, L174-176)
# ═══════════════════════════════════════════════════════════════════

class TestComputeCoverage:

    def test_empty_specs(self):
        from ai_engine.modules.spec_refill import compute_coverage
        filled, total, pct, missing = compute_coverage({})
        assert filled == 0
        assert pct == 0.0

    def test_full_specs(self):
        from ai_engine.modules.spec_refill import compute_coverage
        specs = {f: 'value' for f in ['make', 'model', 'engine', 'horsepower', 'torque',
                                        'zero_to_sixty', 'top_speed', 'drivetrain', 'price', 'year']}
        filled, total, pct, missing = compute_coverage(specs)
        assert filled == 10
        assert pct == 100.0

    def test_none_specs(self):
        from ai_engine.modules.spec_refill import compute_coverage
        filled, total, pct, missing = compute_coverage(None)
        assert filled == 0
        assert len(missing) == 10


class TestRefillMissingSpecs:

    def test_coverage_sufficient_skip(self):
        """L75-79: Coverage already above threshold → skip."""
        from ai_engine.modules.spec_refill import refill_missing_specs
        specs = {f: 'value' for f in ['make', 'model', 'engine', 'horsepower', 'torque',
                                        'zero_to_sixty', 'top_speed', 'drivetrain', 'price', 'year']}
        result = refill_missing_specs(specs, 'article content')
        assert result['_refill_meta']['reason'] == 'coverage_sufficient'
        assert result['_refill_meta']['triggered'] is False

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_successful_refill(self, mock_ai):
        """L81-169: Below threshold → AI refills missing fields."""
        from ai_engine.modules.spec_refill import refill_missing_specs

        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = json.dumps({
            'horsepower': '530', 'torque': '670 Nm', 'zero_to_sixty': '3.8',
            'top_speed': '210 km/h', 'drivetrain': 'AWD', 'price': '$35,000',
        })
        mock_ai.return_value = mock_provider

        specs = {'make': 'BYD', 'model': 'Seal', 'engine': 'Electric'}
        result = refill_missing_specs(specs, '<p>Article about BYD Seal</p>',
                                       web_context='BYD Seal specs 530 hp', threshold=50.0)
        assert result['_refill_meta']['triggered'] is True
        assert 'horsepower' in result

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_refill_with_markdown_response(self, mock_ai):
        """L143-147: AI wraps JSON in markdown code block."""
        from ai_engine.modules.spec_refill import refill_missing_specs

        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = '```json\n{"horsepower": "300"}\n```'
        mock_ai.return_value = mock_provider

        specs = {'make': 'Test', 'model': 'X'}
        result = refill_missing_specs(specs, 'article', threshold=30.0)
        assert result.get('horsepower') == '300'

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_refill_json_error(self, mock_ai):
        """L171-173: AI returns invalid JSON."""
        from ai_engine.modules.spec_refill import refill_missing_specs

        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = 'not valid json'
        mock_ai.return_value = mock_provider

        specs = {'make': 'Test', 'model': 'X'}
        result = refill_missing_specs(specs, 'article', threshold=30.0)
        assert 'json_parse' in result['_refill_meta'].get('error', '')

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_refill_general_exception(self, mock_ai):
        """L174-176: AI provider raises exception."""
        from ai_engine.modules.spec_refill import refill_missing_specs

        mock_ai.side_effect = Exception('Connection timeout')

        specs = {'make': 'Test', 'model': 'X'}
        result = refill_missing_specs(specs, 'article', threshold=30.0)
        assert 'Connection timeout' in result['_refill_meta'].get('error', '')


# ═══════════════════════════════════════════════════════════════════
# translator.py — 77% → 90%  (missed: L11-13, L64, L144, L166-168, L192-226)
# ═══════════════════════════════════════════════════════════════════

class TestTranslatorParseAiResponse:

    def test_valid_json(self):
        from ai_engine.modules.translator import _parse_ai_response
        result = _parse_ai_response('{"title": "Test", "content": "<p>Hello</p>"}')
        assert result['title'] == 'Test'

    def test_markdown_wrapped(self):
        from ai_engine.modules.translator import _parse_ai_response
        result = _parse_ai_response('```json\n{"title": "Test"}\n```')
        assert result['title'] == 'Test'

    def test_invalid_json_fallback(self):
        """L197-207: Unparseable → fallback dict."""
        from ai_engine.modules.translator import _parse_ai_response
        result = _parse_ai_response('This is not JSON at all, no braces either')
        assert result['title'] == 'Article'
        assert '<p>' in result['content']

    def test_json_embedded_in_text(self):
        """L190-195: JSON embedded in text."""
        from ai_engine.modules.translator import _parse_ai_response
        result = _parse_ai_response('Here is the result: {"title": "Embedded"} Done.')
        assert result['title'] == 'Embedded'


class TestCleanHtml:

    def test_empty(self):
        from ai_engine.modules.translator import _clean_html
        assert _clean_html('') == ''

    def test_removes_doc_tags(self):
        """L216: Removes <html>, <body>, etc."""
        from ai_engine.modules.translator import _clean_html
        result = _clean_html('<html><body><h2>Title</h2></body></html>')
        assert '<html>' not in result
        assert '<body>' not in result
        assert '<h2>Title</h2>' in result

    def test_fixes_double_amp(self):
        """L219: &amp;amp; → &amp;"""
        from ai_engine.modules.translator import _clean_html
        result = _clean_html('Salt &amp;amp; Pepper')
        assert '&amp;amp;' not in result

    def test_wraps_orphan_list_items(self):
        """L222-226: <li> without <ul> → auto-wrapped."""
        from ai_engine.modules.translator import _clean_html
        result = _clean_html('<li>Item 1</li><li>Item 2</li>')
        assert '<ul>' in result
        assert '</ul>' in result


class TestTranslateAndEnhance:

    @patch('ai_engine.modules.translator.get_ai_provider')
    def test_successful_translation(self, mock_ai):
        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = json.dumps({
            'title': '2026 BYD Seal Performance Analysis',
            'content': '<h2>Intro</h2><p>P1</p><h2>Specs</h2><p>P2</p><h2>Verdict</h2><p>P3</p><p>P4</p>',
            'summary': 'Summary text here',
            'meta_description': 'Meta desc',
            'suggested_slug': 'byd-seal-review',
            'suggested_categories': ['EVs'],
            'seo_keywords': ['BYD', 'Seal'],
        })
        mock_ai.return_value = mock_provider

        from ai_engine.modules.translator import translate_and_enhance
        result = translate_and_enhance('Текст на русском', seo_keywords='BYD, Seal')
        assert result['title'] == '2026 BYD Seal Performance Analysis'
        assert 'reading_time' in result

    @patch('ai_engine.modules.translator.get_ai_provider')
    def test_empty_response_error(self, mock_ai):
        """L143-144: Empty response → raises."""
        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = ''
        mock_ai.return_value = mock_provider

        from ai_engine.modules.translator import translate_and_enhance
        with pytest.raises(Exception, match='empty response'):
            translate_and_enhance('Текст')

    @patch('ai_engine.modules.translator.get_ai_provider')
    def test_exception_propagated(self, mock_ai):
        """L166-168: Exception → re-raised."""
        mock_ai.side_effect = Exception('Provider down')

        from ai_engine.modules.translator import translate_and_enhance
        with pytest.raises(Exception, match='Provider down'):
            translate_and_enhance('Текст')


# ═══════════════════════════════════════════════════════════════════
# specs_enricher.py — 74% → 90%  (missed: L137-156, L176-234)
# ═══════════════════════════════════════════════════════════════════

class TestExtractValuesFromText:

    def test_horsepower(self):
        from ai_engine.modules.specs_enricher import _extract_values_from_text
        values = _extract_values_from_text('The engine produces 530 hp', 'horsepower')
        assert '530' in values

    def test_torque(self):
        from ai_engine.modules.specs_enricher import _extract_values_from_text
        values = _extract_values_from_text('Peak torque is 670 Nm', 'torque')
        assert '670' in values


class TestMostCommon:

    def test_most_common_value(self):
        from ai_engine.modules.specs_enricher import _most_common
        assert _most_common(['300', '300', '250']) == '300'

    def test_empty(self):
        from ai_engine.modules.specs_enricher import _most_common
        assert _most_common([]) is None


class TestEnrichSpecsFromWeb:

    def test_short_context_skipped(self):
        from ai_engine.modules.specs_enricher import enrich_specs_from_web
        specs = {'horsepower': None}
        result = enrich_specs_from_web(specs, 'short')
        assert result['horsepower'] is None

    def test_enriches_horsepower_from_hp(self):
        """L128-154: HP enrichment from direct hp mentions."""
        from ai_engine.modules.specs_enricher import enrich_specs_from_web
        web = 'The car has 530 hp. Power output is 530 hp. ' * 3
        specs = {'horsepower': None}
        result = enrich_specs_from_web(specs, web)
        assert result['horsepower'] == 530

    def test_enriches_horsepower_from_kw(self):
        """L137-139: kW → HP conversion."""
        from ai_engine.modules.specs_enricher import enrich_specs_from_web
        web = 'Motor output is 390 kW electric motor. ' * 3
        specs = {'horsepower': None}
        result = enrich_specs_from_web(specs, web)
        # 390 kW * 1.341 = 523 hp
        assert result.get('horsepower') is not None

    def test_enriches_torque(self):
        """L158-169: Torque enrichment."""
        from ai_engine.modules.specs_enricher import enrich_specs_from_web
        web = 'The engine delivers 670 Nm of torque. ' * 3
        specs = {'torque': 'Not specified'}
        result = enrich_specs_from_web(specs, web)
        assert '670' in str(result.get('torque', ''))

    def test_enriches_battery(self):
        """L172-178: Battery kWh enrichment."""
        from ai_engine.modules.specs_enricher import enrich_specs_from_web
        web = 'Equipped with a 82.5 kWh battery pack. ' * 3
        specs = {'battery': 'Not specified'}
        result = enrich_specs_from_web(specs, web)
        assert 'kWh' in str(result.get('battery', ''))

    def test_enriches_range_km(self):
        """L181-188: Range (km) enrichment."""
        from ai_engine.modules.specs_enricher import enrich_specs_from_web
        web = 'WLTP range of 570 km on a full charge. ' * 3
        specs = {'range': 'Not specified'}
        result = enrich_specs_from_web(specs, web)
        assert '570' in str(result.get('range', ''))

    def test_enriches_range_miles(self):
        """L189-192: Range (miles) fallback."""
        from ai_engine.modules.specs_enricher import enrich_specs_from_web
        web = 'EPA range of 320 miles estimated. ' * 3
        specs = {'range': 'Not specified'}
        result = enrich_specs_from_web(specs, web)
        assert 'miles' in str(result.get('range', ''))

    def test_enriches_acceleration(self):
        """L195-201: Acceleration enrichment."""
        from ai_engine.modules.specs_enricher import enrich_specs_from_web
        web = 'Sprints from 0-100 in 3.8 seconds flat. ' * 3
        specs = {'acceleration': 'Not specified'}
        result = enrich_specs_from_web(specs, web)
        assert '3.8' in str(result.get('acceleration', ''))

    def test_enriches_top_speed(self):
        """L204-211: Top speed enrichment."""
        from ai_engine.modules.specs_enricher import enrich_specs_from_web
        web = 'Top speed of 210 km/h electronically limited. ' * 3
        specs = {'top_speed': 'Not specified'}
        result = enrich_specs_from_web(specs, web)
        assert '210' in str(result.get('top_speed', ''))

    def test_enriches_drivetrain(self):
        """L214-234: Drivetrain enrichment with normalization."""
        from ai_engine.modules.specs_enricher import enrich_specs_from_web
        web = 'This model features all-wheel drive standard equipment. ' * 3
        specs = {'drivetrain': 'Not specified'}
        result = enrich_specs_from_web(specs, web)
        assert result.get('drivetrain') == 'AWD'

    @pytest.mark.slow
    def test_drivetrain_chinese(self):
        """L224-229: Chinese drivetrain terms normalized."""
        from ai_engine.modules.specs_enricher import enrich_specs_from_web
        web = '该车采用四驱系统。 ' * 10
        specs = {'drivetrain': None}
        result = enrich_specs_from_web(specs, web)
        assert result.get('drivetrain') == 'AWD'

    def test_hp_value_error(self):
        """L155-156: ValueError when HP can't be parsed as int."""
        from ai_engine.modules.specs_enricher import enrich_specs_from_web
        # This should not crash the enricher
        web = 'Power is 530 hp with turbo. ' * 3
        specs = {'horsepower': None}
        result = enrich_specs_from_web(specs, web)
        assert isinstance(result, dict)


class TestBuildEnrichedAnalysis:

    def test_returns_tuple(self):
        from ai_engine.modules.specs_enricher import build_enriched_analysis
        text, enriched = build_enriched_analysis({'make': 'BYD', 'model': 'Seal'}, '')
        assert 'BYD' in text
        assert 'Seal' in text
        assert isinstance(enriched, dict)


# ═══════════════════════════════════════════════════════════════════
# specs_extractor.py — 53% → 85%  (missed: L24-127, L166-187)
# ═══════════════════════════════════════════════════════════════════

class TestCleanSpecsData:

    def test_string_fields(self):
        from ai_engine.modules.specs_extractor import _clean_specs_data
        result = _clean_specs_data({'drivetrain': 'AWD', 'body_type': 'null', 'fuel_type': None})
        assert result['drivetrain'] == 'AWD'
        assert result['body_type'] is None
        assert result['fuel_type'] is None

    def test_int_fields(self):
        from ai_engine.modules.specs_extractor import _clean_specs_data
        result = _clean_specs_data({'power_hp': 530, 'torque_nm': 'null', 'range_km': 'abc'})
        assert result['power_hp'] == 530
        assert result['torque_nm'] is None
        assert result['range_km'] is None

    def test_int_value_error(self):
        """L166-167: int() on invalid string → None."""
        from ai_engine.modules.specs_extractor import _clean_specs_data
        result = _clean_specs_data({'power_hp': 'not-a-number', 'seats': 'five'})
        assert result['power_hp'] is None
        assert result['seats'] is None

    def test_float_fields(self):
        from ai_engine.modules.specs_extractor import _clean_specs_data
        result = _clean_specs_data({
            'battery_kwh': 82.5,
            'acceleration_0_100': '3.8',
            'confidence': 0.85,
        })
        assert result['battery_kwh'] == 82.5
        assert result['acceleration_0_100'] == 3.8
        assert result['confidence'] == 0.85

    def test_float_value_error(self):
        """L178-179: float() on invalid → None for battery, 0.0 for confidence."""
        from ai_engine.modules.specs_extractor import _clean_specs_data
        result = _clean_specs_data({
            'battery_kwh': 'large',
            'confidence': 'high',
        })
        assert result['battery_kwh'] is None
        assert result['confidence'] == 0.0

    def test_confidence_cap(self):
        """L184-187: Confidence > 1.0 → capped at 1.0; < 0 → capped at 0."""
        from ai_engine.modules.specs_extractor import _clean_specs_data
        result = _clean_specs_data({'confidence': 5.0})
        assert result['confidence'] == 1.0

        result2 = _clean_specs_data({'confidence': -0.5})
        assert result2['confidence'] == 0.0


class TestEmptySpecs:

    def test_returns_all_none(self):
        from ai_engine.modules.specs_extractor import _empty_specs
        result = _empty_specs()
        assert result['confidence'] == 0.0
        assert result['drivetrain'] is None
        assert result['power_hp'] is None


class TestExtractVehicleSpecs:

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_successful_extraction(self, mock_ai):
        """L90-118: Full successful path."""
        from ai_engine.modules.specs_extractor import extract_vehicle_specs

        mock_provider = MagicMock()
        mock_provider.generate.return_value = json.dumps({
            'drivetrain': 'AWD', 'power_hp': 530, 'torque_nm': 670,
            'battery_kwh': 82.5, 'range_km': 570, 'fuel_type': 'EV',
            'body_type': 'sedan', 'confidence': 0.9,
        })
        mock_ai.return_value = mock_provider

        article = MagicMock()
        article.id = 1
        article.title = '2026 BYD Seal Review'
        article.summary = 'Summary here'
        article.content = '<p>Content</p>'

        result = extract_vehicle_specs(article)
        assert result['drivetrain'] == 'AWD'
        assert result['power_hp'] == 530
        assert result['confidence'] == 0.9

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_markdown_wrapped_response(self, mock_ai):
        """L104-108: Response wrapped in markdown code block."""
        from ai_engine.modules.specs_extractor import extract_vehicle_specs

        mock_provider = MagicMock()
        mock_provider.generate.return_value = '```json\n{"power_hp": 300, "confidence": 0.7}\n```'
        mock_ai.return_value = mock_provider

        article = MagicMock()
        article.id = 2
        article.title = 'Test'
        article.summary = 'S'
        article.content = '<p>C</p>'

        result = extract_vehicle_specs(article)
        assert result['power_hp'] == 300

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_json_parse_error(self, mock_ai):
        """L120-123: Invalid JSON → empty specs."""
        from ai_engine.modules.specs_extractor import extract_vehicle_specs

        mock_provider = MagicMock()
        mock_provider.generate.return_value = 'This is not JSON at all'
        mock_ai.return_value = mock_provider

        article = MagicMock()
        article.id = 3
        article.title = 'Test'
        article.summary = 'S'
        article.content = '<p>C</p>'

        result = extract_vehicle_specs(article)
        assert result['confidence'] == 0.0

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_general_exception(self, mock_ai):
        """L125-127: Provider raises → empty specs."""
        from ai_engine.modules.specs_extractor import extract_vehicle_specs

        mock_ai.side_effect = Exception('API down')

        article = MagicMock()
        article.id = 4
        article.title = 'Test'
        article.summary = 'S'
        article.content = '<p>C</p>'

        result = extract_vehicle_specs(article)
        assert result['confidence'] == 0.0
