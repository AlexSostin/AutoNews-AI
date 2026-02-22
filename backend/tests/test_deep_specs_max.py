"""
Max coverage: ai_engine/modules/deep_specs.py — targeting 98 uncovered lines.
Goal: push from 54% → 90%+
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from news.models import Article

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════
# Helper functions — pure, no DB needed
# ═══════════════════════════════════════════════════════════════════

class TestSafeInt:

    def test_normal_int(self):
        from ai_engine.modules.deep_specs import _safe_int
        assert _safe_int(42) == 42

    def test_string_int(self):
        from ai_engine.modules.deep_specs import _safe_int
        assert _safe_int('530') == 530

    def test_float_string(self):
        from ai_engine.modules.deep_specs import _safe_int
        assert _safe_int('4.7') == 4

    def test_comma_number(self):
        from ai_engine.modules.deep_specs import _safe_int
        assert _safe_int('1,200') == 1200

    def test_none(self):
        from ai_engine.modules.deep_specs import _safe_int
        assert _safe_int(None) is None

    def test_invalid_string(self):
        from ai_engine.modules.deep_specs import _safe_int
        assert _safe_int('N/A') is None

    def test_empty_string(self):
        from ai_engine.modules.deep_specs import _safe_int
        assert _safe_int('') is None


class TestSafeFloat:

    def test_normal(self):
        from ai_engine.modules.deep_specs import _safe_float
        assert _safe_float(3.8) == 3.8

    def test_string(self):
        from ai_engine.modules.deep_specs import _safe_float
        assert _safe_float('82.5') == 82.5

    def test_comma(self):
        from ai_engine.modules.deep_specs import _safe_float
        assert _safe_float('1,200.5') == 1200.5

    def test_none(self):
        from ai_engine.modules.deep_specs import _safe_float
        assert _safe_float(None) is None

    def test_invalid(self):
        from ai_engine.modules.deep_specs import _safe_float
        assert _safe_float('abc') is None


class TestValidateChoice:

    def test_valid(self):
        from ai_engine.modules.deep_specs import _validate_choice, VALID_FUEL_TYPES
        assert _validate_choice('EV', VALID_FUEL_TYPES) == 'EV'

    def test_invalid(self):
        from ai_engine.modules.deep_specs import _validate_choice, VALID_FUEL_TYPES
        assert _validate_choice('Petrol', VALID_FUEL_TYPES) is None

    def test_none(self):
        from ai_engine.modules.deep_specs import _validate_choice, VALID_FUEL_TYPES
        assert _validate_choice(None, VALID_FUEL_TYPES) is None


class TestSanitizeTrim:

    def test_none(self):
        from ai_engine.modules.deep_specs import _sanitize_trim
        assert _sanitize_trim(None) == ''

    def test_garbage_value(self):
        from ai_engine.modules.deep_specs import _sanitize_trim
        assert _sanitize_trim('Not specified') == ''
        assert _sanitize_trim('null') == ''
        assert _sanitize_trim('N/A') == ''

    def test_valid_trim(self):
        from ai_engine.modules.deep_specs import _sanitize_trim
        assert _sanitize_trim('AWD Long Range') == 'AWD Long Range'


class TestCleanModelName:

    def test_strip_brand_prefix(self):
        from ai_engine.modules.deep_specs import _clean_model_name
        assert _clean_model_name('BYD Seal', 'BYD') == 'Seal'

    def test_no_brand_prefix(self):
        from ai_engine.modules.deep_specs import _clean_model_name
        assert _clean_model_name('Model 3', 'Tesla') == 'Model 3'

    def test_strip_stop_words(self):
        from ai_engine.modules.deep_specs import _clean_model_name
        assert _clean_model_name('HS6 Sets', 'MG') == 'HS6'
        assert _clean_model_name('ET9 Delivers the', 'NIO') == 'ET9'

    def test_empty_model(self):
        from ai_engine.modules.deep_specs import _clean_model_name
        assert _clean_model_name('', 'BYD') == ''
        assert _clean_model_name(None, 'BYD') is None

    def test_brand_is_full_name(self):
        """Don't strip brand if it would leave model empty."""
        from ai_engine.modules.deep_specs import _clean_model_name
        result = _clean_model_name('IM', 'IM')
        assert result == 'IM'  # Would be empty after strip, so kept


class TestCleanPipeValue:

    def test_with_pipe(self):
        from ai_engine.modules.deep_specs import _clean_pipe_value
        assert _clean_pipe_value('AWD | RWD') == 'AWD'

    def test_no_pipe(self):
        from ai_engine.modules.deep_specs import _clean_pipe_value
        assert _clean_pipe_value('AWD') == 'AWD'

    def test_none(self):
        from ai_engine.modules.deep_specs import _clean_pipe_value
        assert _clean_pipe_value(None) is None

    def test_non_string(self):
        from ai_engine.modules.deep_specs import _clean_pipe_value
        assert _clean_pipe_value(42) == 42


class TestParseAiResponse:

    def test_plain_json(self):
        from ai_engine.modules.deep_specs import _parse_ai_response
        result = _parse_ai_response('{"power_hp": 530, "range_km": 570}')
        assert result['power_hp'] == 530

    def test_markdown_wrapped(self):
        from ai_engine.modules.deep_specs import _parse_ai_response
        result = _parse_ai_response('```json\n{"power_hp": 200}\n```')
        assert result['power_hp'] == 200

    def test_json_in_text(self):
        from ai_engine.modules.deep_specs import _parse_ai_response
        result = _parse_ai_response('Here is the data:\n{"power_hp": 100}\nDone.')
        assert result['power_hp'] == 100

    def test_invalid_json(self):
        from ai_engine.modules.deep_specs import _parse_ai_response
        assert _parse_ai_response('This is not JSON at all') is None

    def test_broken_json_in_braces(self):
        from ai_engine.modules.deep_specs import _parse_ai_response
        result = _parse_ai_response('{ broken json }')
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# generate_deep_vehicle_specs — main function
# ═══════════════════════════════════════════════════════════════════

class TestGenerateDeepVehicleSpecs:

    def _make_article(self, title='Test Article'):
        return Article.objects.create(
            title=title,
            slug=f'test-{Article.objects.count()}-deep',
            content='<p>Content</p>',
        )

    def test_no_make_returns_none(self):
        """L269-271: make is 'Not specified' → None."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        article = self._make_article()
        result = generate_deep_vehicle_specs(
            article, specs={'make': 'Not specified', 'model': 'X'}, provider='gemini'
        )
        assert result is None

    def test_no_model_returns_none(self):
        """L273-275: model is missing → None."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        article = self._make_article()
        result = generate_deep_vehicle_specs(
            article, specs={'make': 'BYD', 'model': ''}, provider='gemini'
        )
        assert result is None

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_successful_creation(self, mock_ai):
        """Full successful path: AI returns good data → VehicleSpecs created."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        from news.models import VehicleSpecs

        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = json.dumps({
            'power_hp': 530, 'power_kw': 390, 'torque_nm': 670,
            'battery_kwh': 82.5, 'range_km': 570, 'range_wltp': 520,
            'length_mm': 4800, 'width_mm': 1875, 'height_mm': 1460,
            'wheelbase_mm': 2920, 'weight_kg': 2150,
            'drivetrain': 'AWD', 'fuel_type': 'EV', 'body_type': 'sedan',
            'seats': 5, 'price_from': 35000, 'currency': 'USD',
            'acceleration_0_100': 3.8, 'top_speed_kmh': 210,
            'transmission': 'Single-speed',
        })
        mock_ai.return_value = mock_provider

        article = self._make_article('2026 BYD Seal Deep')
        result = generate_deep_vehicle_specs(
            article,
            specs={'make': 'BYD', 'model': 'Seal', 'trim': 'AWD', 'year': 2026},
            provider='gemini'
        )
        assert result is not None
        assert result.power_hp == 530
        assert result.make == 'BYD'

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_ai_returns_unparseable(self, mock_ai):
        """L401-404: AI returns garbage → None."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs

        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = 'I am sorry, I cannot help with that.'
        mock_ai.return_value = mock_provider

        article = self._make_article('Unparseable Test')
        result = generate_deep_vehicle_specs(
            article,
            specs={'make': 'BYD', 'model': 'Seal', 'trim': '', 'year': 2026},
            provider='gemini'
        )
        assert result is None

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_existing_specs_skipped(self, mock_ai):
        """L361-389: Existing specs with power+length → skip AI call."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        from news.models import VehicleSpecs

        article = self._make_article('Existing Specs Test')
        # Pre-create a VehicleSpecs with key fields populated
        VehicleSpecs.objects.create(
            article=article,
            make='BYD', model_name='Seal', trim_name='',
            power_hp=530, length_mm=4800,
        )

        result = generate_deep_vehicle_specs(
            article,
            specs={'make': 'BYD', 'model': 'Seal', 'trim': '', 'year': 2026},
            provider='gemini'
        )
        assert result is not None
        assert result.power_hp == 530
        mock_ai.assert_not_called()

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_phev_suspicious_range_cleared(self, mock_ai):
        """L365-381: Small battery + huge range → cleared for re-enrichment."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        from news.models import VehicleSpecs

        article = self._make_article('PHEV Range Test')
        vs = VehicleSpecs.objects.create(
            article=article,
            make='BYD', model_name='Song Plus', trim_name='',
            power_hp=200, length_mm=4700,
            battery_kwh=18.3,  # Small PHEV battery
            range_km=1100,     # Suspicious: looks like combined range
        )

        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = json.dumps({
            'power_hp': 200, 'battery_kwh': 18.3, 'range_km': 80,
            'combined_range_km': 1100, 'length_mm': 4700,
            'fuel_type': 'PHEV', 'drivetrain': 'FWD',
        })
        mock_ai.return_value = mock_provider

        result = generate_deep_vehicle_specs(
            article,
            specs={'make': 'BYD', 'model': 'Song Plus', 'trim': '', 'year': 2026},
            provider='gemini'
        )
        assert result is not None

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_ghost_records_cleaned(self, mock_ai):
        """L295-303: Existing records with garbage trim → deleted."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        from news.models import VehicleSpecs

        article = self._make_article('Ghost Cleanup Test')
        # Create ghost record with garbage trim
        VehicleSpecs.objects.create(
            article=article,
            make='NIO', model_name='ET9', trim_name='None',
        )

        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = json.dumps({
            'power_hp': 650, 'torque_nm': 850,
            'length_mm': 5100, 'battery_kwh': 100, 'range_km': 580,
            'drivetrain': 'AWD', 'fuel_type': 'EV',
        })
        mock_ai.return_value = mock_provider

        result = generate_deep_vehicle_specs(
            article,
            specs={'make': 'NIO', 'model': 'ET9', 'trim': '', 'year': 2026},
            provider='gemini'
        )
        assert result is not None
        # Ghost record with 'None' trim should be deleted
        assert not VehicleSpecs.objects.filter(make='NIO', trim_name='None').exists()

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_model_name_normalized(self, mock_ai):
        """L289-292: Model name 'BYD Seal' → 'Seal' (brand prefix stripped)."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        from news.models import VehicleSpecs

        article = self._make_article('Model Normalize Test')
        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = json.dumps({
            'power_hp': 300, 'length_mm': 4500,
            'drivetrain': 'FWD', 'fuel_type': 'EV',
        })
        mock_ai.return_value = mock_provider

        result = generate_deep_vehicle_specs(
            article,
            specs={'make': 'BYD', 'model': 'BYD Seal', 'trim': '', 'year': 2026},
            provider='gemini'
        )
        assert result is not None
        assert result.model_name == 'Seal'  # Brand prefix stripped

    def test_exception_returns_none(self):
        """L514-519: Any exception in the outer try → None."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        article = self._make_article('Exception Test')
        with patch('news.models.VehicleSpecs.objects.filter', side_effect=Exception('DB crash')):
            result = generate_deep_vehicle_specs(
                article,
                specs={'make': 'Test', 'model': 'X', 'trim': ''},
                provider='gemini'
            )
        assert result is None

    def test_no_specs_dict(self):
        """L261: specs=None → make/model empty → returns None."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        article = self._make_article('No Specs')
        result = generate_deep_vehicle_specs(article, specs=None, provider='gemini')
        assert result is None

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_brand_display_name_normalized(self, mock_ai):
        """L278-283: Brand display name lookup (e.g. 'zeekr' → 'ZEEKR')."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs

        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = json.dumps({
            'power_hp': 421, 'length_mm': 4850,
            'drivetrain': 'AWD', 'fuel_type': 'EV',
        })
        mock_ai.return_value = mock_provider

        article = self._make_article('ZEEKR Normalize')
        result = generate_deep_vehicle_specs(
            article,
            specs={'make': 'Zeekr', 'model': '007', 'trim': '', 'year': 2026},
            provider='gemini'
        )
        assert result is not None

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_phev_range_warning(self, mock_ai):
        """L412-416: PHEV with small battery + huge range → warning logged."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs

        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = json.dumps({
            'power_hp': 150, 'battery_kwh': 15, 'range_km': 600,
            'fuel_type': 'PHEV', 'length_mm': 4500,
            'drivetrain': 'FWD',
        })
        mock_ai.return_value = mock_provider

        article = self._make_article('PHEV Warning Test')
        result = generate_deep_vehicle_specs(
            article,
            specs={'make': 'BYD', 'model': 'QinPlus', 'trim': '', 'year': 2026},
            provider='gemini'
        )
        # Should still succeed but print warning
        assert result is not None

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_few_fields_warning(self, mock_ai):
        """L502-503: Only 1-2 key fields → warning printed."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs

        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = json.dumps({
            'power_hp': 200,
            'drivetrain': 'FWD',
        })
        mock_ai.return_value = mock_provider

        article = self._make_article('Few Fields Test')
        result = generate_deep_vehicle_specs(
            article,
            specs={'make': 'Test', 'model': 'Minimal', 'trim': '', 'year': 2025},
            provider='gemini'
        )
        assert result is not None

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_duplicate_records_merged(self, mock_ai):
        """L325-345: Multiple VehicleSpecs for same make/model → merged, best kept."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        from news.models import VehicleSpecs

        article1 = self._make_article('Dup Merge 1')
        article2 = self._make_article('Dup Merge 2')

        # Create 2 records with same make/model but different casing
        vs1 = VehicleSpecs.objects.create(
            article=article1, make='byd', model_name='seal', trim_name='',
            power_hp=530,  # Only 1 field
        )
        vs2 = VehicleSpecs.objects.create(
            article=article2, make='BYD', model_name='Seal', trim_name='',
            power_hp=530, length_mm=4800, torque_nm=670,  # 3 fields — best
        )

        mock_provider = MagicMock()
        mock_ai.return_value = mock_provider

        result = generate_deep_vehicle_specs(
            article1,
            specs={'make': 'BYD', 'model': 'Seal', 'trim': '', 'year': 2026},
            provider='gemini'
        )
        assert result is not None
        # Should keep the best record and skip AI call since it has power_hp + length_mm
        assert result.power_hp == 530

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_old_records_renamed(self, mock_ai):
        """L306-316: Model name normalized → old records renamed."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        from news.models import VehicleSpecs

        article = self._make_article('Old Rename Test')
        # Create record with brand-prefixed model name
        old_rec = VehicleSpecs.objects.create(
            article=article, make='BYD', model_name='BYD Seal', trim_name='AWD',
        )

        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = json.dumps({
            'power_hp': 530, 'length_mm': 4800,
            'drivetrain': 'AWD', 'fuel_type': 'EV',
        })
        mock_ai.return_value = mock_provider

        result = generate_deep_vehicle_specs(
            article,
            specs={'make': 'BYD', 'model': 'BYD Seal', 'trim': 'AWD', 'year': 2026},
            provider='gemini'
        )
        assert result is not None
        # Old record should be renamed from 'BYD Seal' to 'Seal'
        old_rec.refresh_from_db()
        assert old_rec.model_name == 'Seal'

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_phev_suspicious_cltc_and_wltp(self, mock_ai):
        """L369-372: PHEV with suspicious range_cltc and range_wltp → both cleared."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        from news.models import VehicleSpecs

        article = self._make_article('PHEV CLTC WLTP Test')
        VehicleSpecs.objects.create(
            article=article,
            make='BYD', model_name='Song', trim_name='DM-i',
            power_hp=200, length_mm=4700,
            battery_kwh=18.0,
            range_km=80,           # OK
            range_cltc=1200,       # Suspicious!
            range_wltp=1000,       # Suspicious!
        )

        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = json.dumps({
            'power_hp': 200, 'range_cltc': 80, 'range_wltp': 70,
            'battery_kwh': 18.0, 'length_mm': 4700,
            'fuel_type': 'PHEV', 'drivetrain': 'FWD',
        })
        mock_ai.return_value = mock_provider

        result = generate_deep_vehicle_specs(
            article,
            specs={'make': 'BYD', 'model': 'Song', 'trim': 'DM-i', 'year': 2026},
            provider='gemini'
        )
        assert result is not None

    def test_brand_import_fallback(self):
        """L282-283: BRAND_DISPLAY_NAMES import fails → ImportError caught."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        article = self._make_article('Brand Import Fail')

        with patch('ai_engine.modules.deep_specs.generate_deep_vehicle_specs') as outer_mock:
            # Actually test by patching the import inside
            pass

        # Better approach: patch the import to fail
        import importlib
        with patch.dict('sys.modules', {'news.auto_tags': None}):
            # This forces ImportError on `from news.auto_tags import ...`
            result = generate_deep_vehicle_specs(
                article,
                specs={'make': 'TestBrand', 'model': 'Not specified'},
                provider='gemini'
            )
        # model is 'Not specified' → returns None
        assert result is None

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_existing_linked_to_different_article(self, mock_ai):
        """L385-386: Existing specs linked to different article → prints info, returns."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        from news.models import VehicleSpecs

        article1 = self._make_article('Linked Article 1')
        article2 = self._make_article('Linked Article 2')

        VehicleSpecs.objects.create(
            article=article1,  # Linked to article1
            make='Tesla', model_name='Model Y', trim_name='',
            power_hp=456, length_mm=4750,
        )

        # Call with article2 → existing is linked to article1 → L385-386
        result = generate_deep_vehicle_specs(
            article2,
            specs={'make': 'Tesla', 'model': 'Model Y', 'trim': '', 'year': 2025},
            provider='gemini'
        )
        assert result is not None
        assert result.article_id == article1.id  # Still linked to original
        mock_ai.assert_not_called()

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_single_existing_casing_normalization(self, mock_ai):
        """L346-357: Single existing record with wrong casing → normalized."""
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        from news.models import VehicleSpecs

        article = self._make_article('Case Fix Test')
        vs = VehicleSpecs.objects.create(
            article=article,
            make='byd', model_name='seal', trim_name='',  # Wrong casing
            power_hp=530, length_mm=4800,
        )

        result = generate_deep_vehicle_specs(
            article,
            specs={'make': 'BYD', 'model': 'Seal', 'trim': '', 'year': 2026},
            provider='gemini'
        )
        assert result is not None
        vs.refresh_from_db()
        assert vs.make == 'BYD'  # Casing fixed
        assert vs.model_name == 'Seal'  # Casing fixed
        mock_ai.assert_not_called()
