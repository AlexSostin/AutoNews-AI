"""
Group 2: Spec extractor tests — regex functions, pure logic.
Tests normalize_make, normalize_hp, _parse_specs, _extract_specs_regex.
"""
import sys, os, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from news.spec_extractor import normalize_make, normalize_hp, _parse_specs, _extract_specs_regex


# ── normalize_make ──────────────────────────────────────────────────────────

class TestNormalizeMake:
    """Tests for canonical make name normalization"""

    def test_byd_lowercase(self):
        assert normalize_make('byd') == 'BYD'

    def test_zeekr_lowercase(self):
        assert normalize_make('zeekr') == 'ZEEKR'

    def test_nio_mixed(self):
        assert normalize_make('Nio') == 'NIO'

    def test_xpeng_lowercase(self):
        assert normalize_make('xpeng') == 'XPENG'

    def test_toyota(self):
        assert normalize_make('toyota') == 'Toyota'

    def test_unknown_brand_passthrough(self):
        """Unknown brands are returned as-is"""
        assert normalize_make('SomeBrand') == 'SomeBrand'

    def test_whitespace_stripped(self):
        assert normalize_make('  byd  ') == 'BYD'


# ── normalize_hp ────────────────────────────────────────────────────────────

class TestNormalizeHP:
    """Tests for horsepower string normalization"""

    def test_plain_number(self):
        assert normalize_hp('300') == '300'

    def test_with_hp_suffix(self):
        assert normalize_hp('300 hp') == '300'

    def test_with_HP_suffix(self):
        assert normalize_hp('450 HP') == '450'

    def test_horsepower_word(self):
        assert normalize_hp('500 horsepower') == '500'

    def test_kw_conversion(self):
        """200 kW ≈ 268 hp"""
        result = normalize_hp('200 kW')
        assert result == '268'

    def test_kw_small(self):
        """100 kW ≈ 134 hp"""
        result = normalize_hp('100 kW')
        assert result == '134'

    def test_over_prefix(self):
        assert normalize_hp('Over 500 hp') == '500'

    def test_up_to_prefix(self):
        assert normalize_hp('Up to 600 hp') == '600'

    def test_approximately_prefix(self):
        assert normalize_hp('approximately 400') == '400'

    def test_dual_motor_takes_highest(self):
        """Dual motor: 200 hp / 400 hp → 400"""
        result = normalize_hp('200 hp / 400 hp')
        assert result == '400'

    def test_empty_string(self):
        assert normalize_hp('') == ''

    def test_none(self):
        assert normalize_hp(None) == ''

    def test_not_specified(self):
        assert normalize_hp('Not specified') == ''

    def test_zero(self):
        assert normalize_hp('0') == ''

    def test_na(self):
        assert normalize_hp('N/A') == ''

    def test_horsepower_with_kw_in_parens(self):
        """'500 horsepower (373 kW)' → 500"""
        result = normalize_hp('500 horsepower (373 kW)')
        assert result == '500'


# ── _parse_specs ────────────────────────────────────────────────────────────

class TestParseSpecs:
    """Tests for parsing AI text output into specs dict"""

    def test_full_parse(self):
        text = """Make: ZEEKR
Model: 007GT
Trim/Version: Performance
Engine: Electric
Horsepower: 544
Torque: 710 Nm
Acceleration: 3.5s
Top Speed: 210 km/h
Drivetrain: AWD
Price: $45,000"""
        specs = _parse_specs(text)
        assert specs['make'] == 'ZEEKR'
        assert specs['model'] == '007GT'
        assert specs['trim'] == 'Performance'
        assert specs['engine'] == 'Electric'
        assert specs['horsepower'] == '544'
        assert specs['torque'] == '710 Nm'
        assert specs['acceleration'] == '3.5s'
        assert specs['top_speed'] == '210 km/h'
        assert specs['drivetrain'] == 'AWD'
        assert specs['price'] == '$45,000'

    def test_partial_parse(self):
        text = "Make: BYD\nModel: Seal"
        specs = _parse_specs(text)
        assert specs['make'] == 'BYD'
        assert specs['model'] == 'Seal'
        assert 'engine' not in specs

    def test_empty_text(self):
        assert _parse_specs('') == {}

    def test_drive_alias(self):
        """'Drive:' should work as alias for 'Drivetrain:'"""
        text = "Drive: RWD"
        specs = _parse_specs(text)
        assert specs['drivetrain'] == 'RWD'

    def test_extra_whitespace(self):
        text = "  Make:   Tesla  \n  Model:   Model 3  "
        specs = _parse_specs(text)
        assert specs['make'] == 'Tesla'
        assert specs['model'] == 'Model 3'


# ── _extract_specs_regex ────────────────────────────────────────────────────

class TestExtractSpecsRegex:
    """Tests for regex-based spec extraction from article-like objects"""

    def _make_article(self, title, content=''):
        """Create a minimal article-like object"""
        obj = types.SimpleNamespace()
        obj.title = title
        obj.content = content
        return obj

    def test_basic_brand_model(self):
        art = self._make_article('2026 ZEEKR 007GT EV Review')
        specs = _extract_specs_regex(art)
        assert specs is not None
        assert specs['make'] == 'ZEEKR'
        assert '007GT' in specs['model']

    def test_byd_seal(self):
        art = self._make_article('BYD Seal Review — Best EV Under $30k')
        specs = _extract_specs_regex(art)
        assert specs is not None
        assert specs['make'] == 'BYD'

    def test_year_brand_model_pattern(self):
        art = self._make_article('2024 Tesla Model3 Performance Review')
        specs = _extract_specs_regex(art)
        assert specs is not None
        assert specs['make'] == 'Tesla'

    def test_no_brand_returns_none(self):
        art = self._make_article('Top 10 Cars of 2025')
        specs = _extract_specs_regex(art)
        assert specs is None

    def test_price_extraction(self):
        art = self._make_article(
            'NIO ET5 Review',
            '<p>Starting price of $35,900 in the US market.</p>'
        )
        specs = _extract_specs_regex(art)
        assert specs is not None
        assert '$35,900' in specs.get('price', '')

    def test_hp_extraction(self):
        art = self._make_article(
            'XPENG G6 Specs',
            '<p>The motor produces 296 horsepower and 440 Nm of torque.</p>'
        )
        specs = _extract_specs_regex(art)
        assert specs is not None
        assert specs.get('horsepower') == '296'

    def test_engine_type_electric(self):
        art = self._make_article(
            'BYD Dolphin Review',
            '<p>This battery electric vehicle offers 300 km range.</p>'
        )
        specs = _extract_specs_regex(art)
        assert specs.get('engine') == 'Electric'

    def test_engine_type_phev(self):
        art = self._make_article(
            'BYD Han Specs',
            '<p>The plug-in hybrid version combines efficiency with power.</p>'
        )
        specs = _extract_specs_regex(art)
        assert specs.get('engine') == 'PHEV'

    def test_engine_type_hybrid(self):
        art = self._make_article(
            'Toyota Camry Specs',
            '<p>The hybrid powertrain delivers 225 combined hp.</p>'
        )
        specs = _extract_specs_regex(art)
        assert specs.get('engine') == 'Hybrid'

    def test_drivetrain_awd(self):
        art = self._make_article(
            'NIO ES8 Review',
            '<p>Standard AWD with dual motors for confident handling.</p>'
        )
        specs = _extract_specs_regex(art)
        assert specs.get('drivetrain') == 'AWD'

    def test_drivetrain_rwd(self):
        art = self._make_article(
            'Tesla Model3 Review',
            '<p>The base rear-wheel drive version is the most efficient.</p>'
        )
        specs = _extract_specs_regex(art)
        # rear-wheel maps to RWD
        assert specs.get('drivetrain') == 'RWD'
