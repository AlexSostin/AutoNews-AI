"""
Tests for Content Recommender helper functions and spec extraction.

Tests cover pure-Python utility functions that don't require ML model:
- _strip_html: HTML tag removal
- _prepare_text: title weighting and text combination
- _clean_text: text normalization for TF-IDF
- extract_specs_from_text: regex-based vehicle spec extraction
"""
from ai_engine.modules.content_recommender import (
    _strip_html, _prepare_text, _clean_text, extract_specs_from_text,
)


class TestStripHtml:
    """Test HTML tag removal."""

    def test_removes_basic_tags(self):
        assert _strip_html('<p>Hello</p>') == 'Hello'

    def test_removes_nested_tags(self):
        result = _strip_html('<div><p>Hello <strong>World</strong></p></div>')
        assert 'Hello' in result
        assert 'World' in result
        assert '<' not in result

    def test_normalizes_whitespace(self):
        result = _strip_html('<p>Too   many    spaces</p>')
        assert '  ' not in result

    def test_empty_string(self):
        assert _strip_html('') == ''

    def test_plain_text_unchanged(self):
        assert _strip_html('No tags here') == 'No tags here'


class TestPrepareText:
    """Test text preparation with title weighting."""

    def test_title_repeated_3x(self):
        result = _prepare_text('Tesla', 'Summary', 'Content body')
        assert result.count('Tesla') == 3

    def test_combines_all_fields(self):
        result = _prepare_text('Title', 'Summary text', '<p>Content</p>')
        assert 'Title' in result
        assert 'Summary text' in result
        assert 'Content' in result
        assert '<p>' not in result  # HTML stripped from content

    def test_empty_summary(self):
        result = _prepare_text('Title', '', 'Content')
        assert 'Title' in result
        assert 'Content' in result


class TestCleanText:
    """Test text cleaning for TF-IDF comparison."""

    def test_lowercases(self):
        result = _clean_text('Hello WORLD')
        assert result == 'hello world'

    def test_removes_punctuation(self):
        result = _clean_text('Hello, world! Test?')
        assert ',' not in result
        assert '!' not in result
        assert '?' not in result

    def test_strips_html(self):
        result = _clean_text('<p>Hello</p>')
        assert '<' not in result
        assert 'hello' in result

    def test_normalizes_whitespace(self):
        result = _clean_text('Too   much   space')
        assert '  ' not in result


class TestExtractSpecsFromText:
    """Test regex-based vehicle specification extraction."""

    def test_extracts_hp(self):
        specs = extract_specs_from_text('Powerful Engine', 'The car produces 450 hp of power')
        assert specs.get('power_hp') == 450

    def test_extracts_kw(self):
        specs = extract_specs_from_text('Electric Motor', 'Maximum output of 150 kW')
        assert specs.get('power_kw') == 150
        assert 'power_hp' in specs  # Auto-converted

    def test_extracts_torque(self):
        specs = extract_specs_from_text('Performance', 'Peak torque of 530 Nm')
        assert specs.get('torque_nm') == 530

    def test_extracts_battery_kwh(self):
        specs = extract_specs_from_text('Battery', 'Equipped with a 77.4 kWh battery pack')
        assert specs.get('battery_kwh') == 77.4

    def test_extracts_0_100_acceleration(self):
        specs = extract_specs_from_text('Speed', '0-100 km/h in 3.8 seconds')
        assert specs.get('acceleration_0_100') == 3.8

    def test_extracts_wltp_range(self):
        specs = extract_specs_from_text('Range', 'Up to 510 km WLTP range')
        assert specs.get('range_wltp') == 510

    def test_extracts_epa_range(self):
        specs = extract_specs_from_text('Range', '350 km EPA rated range')
        assert specs.get('range_epa') == 350

    def test_extracts_top_speed(self):
        specs = extract_specs_from_text('Top Speed', 'Top speed of 250 km/h')
        assert specs.get('top_speed_kmh') == 250

    def test_extracts_dimensions(self):
        specs = extract_specs_from_text('Dimensions', 'Length: 4,900 mm, Width: 1,920 mm, Wheelbase: 2,920 mm')
        assert specs.get('length_mm') == 4900
        assert specs.get('width_mm') == 1920
        assert specs.get('wheelbase_mm') == 2920

    def test_extracts_weight(self):
        specs = extract_specs_from_text('Weight', 'Curb weight: 2150 kg')
        assert specs.get('weight_kg') == 2150

    def test_extracts_voltage_800v(self):
        specs = extract_specs_from_text('Architecture', 'Built on 800V architecture')
        assert specs.get('voltage_architecture') == 800

    def test_extracts_seats(self):
        specs = extract_specs_from_text('Interior', 'Comfortable 5-seater with leather trim')
        assert specs.get('seats') == 5

    def test_extracts_awd_drivetrain(self):
        specs = extract_specs_from_text('Drive', 'Standard AWD system')
        assert specs.get('drivetrain') == 'AWD'

    def test_extracts_rwd_drivetrain(self):
        specs = extract_specs_from_text('Drive', 'Rear-wheel drive for sportiness')
        assert specs.get('drivetrain') == 'RWD'

    def test_extracts_dual_motor(self):
        specs = extract_specs_from_text('Motor', 'Dual-motor all-wheel drive')
        assert specs.get('motor_count') == 2

    def test_extracts_tri_motor(self):
        specs = extract_specs_from_text('Motor', 'Tri-motor configuration')
        assert specs.get('motor_count') == 3

    def test_no_specs_from_generic_text(self):
        specs = extract_specs_from_text('Weather', 'Sunny skies expected tomorrow')
        assert len(specs) == 0

    def test_combined_specs(self):
        """Full article-style text should extract multiple specs."""
        title = 'Tesla Model S Plaid Review'
        content = (
            'The Tesla Model S Plaid produces 1020 hp and 760 kW '
            'with 1420 Nm of torque. '
            'It sprints 0-100 in 2.1 seconds with a top speed of 322 km/h. '
            'The 100 kWh battery provides 637 km WLTP range. '
            'It features a dual-motor AWD system.'
        )
        specs = extract_specs_from_text(title, content)
        assert specs['power_hp'] == 1020
        assert specs['power_kw'] == 760
        assert specs['torque_nm'] == 1420
        assert specs['acceleration_0_100'] == 2.1
        assert specs['top_speed_kmh'] == 322
        assert specs['battery_kwh'] == 100.0
        assert specs['range_wltp'] == 637
        assert specs['drivetrain'] == 'AWD'
        assert specs['motor_count'] == 2
