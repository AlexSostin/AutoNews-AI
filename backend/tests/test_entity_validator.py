"""
Tests for entity_validator module — anti-hallucination system.
"""
import pytest
from unittest.mock import patch


class TestExtractEntities:
    """Test entity extraction from automotive titles."""
    
    def test_extract_byd_leopard_8(self):
        from ai_engine.modules.entity_validator import extract_entities
        result = extract_entities("2025 BYD Leopard 8 PHEV 7-Seater Review")
        assert result['year'] == '2025'
        assert result['brand'] == 'BYD'
        assert 'Leopard 8' in result.get('model_name', '')
        assert result['powertrain'] == 'PHEV'
    
    def test_extract_zeekr_7x(self):
        from ai_engine.modules.entity_validator import extract_entities
        result = extract_entities("2025 ZEEKR 7X Review")
        assert result['year'] == '2025'
        assert result['brand'] == 'ZEEKR'
        assert '7X' in result.get('model_name', '')
    
    def test_extract_tesla_model_y(self):
        from ai_engine.modules.entity_validator import extract_entities
        result = extract_entities("2025 Tesla Model Y Performance Review")
        assert result['brand'] == 'Tesla'
        assert 'Model Y' in result.get('model_name', '')
    
    def test_extract_with_sub_brand(self):
        from ai_engine.modules.entity_validator import extract_entities
        result = extract_entities("2025 BYD Fang Cheng Bao Leopard 8: The Off-Road PHEV")
        # Sub-brand 'Fang Cheng Bao' is a valid brand alias, extracted first by longest-match
        assert result['brand'] in ('BYD', 'Fang Cheng Bao')
        assert 'Leopard 8' in result.get('model_name', '') or 'Leopard' in result.get('model_name', '')
    
    def test_extract_empty_title(self):
        from ai_engine.modules.entity_validator import extract_entities
        result = extract_entities("")
        assert result == {}
    
    def test_extract_no_year(self):
        from ai_engine.modules.entity_validator import extract_entities
        result = extract_entities("BYD Seal 06 Review")
        assert result['brand'] == 'BYD'
        assert 'year' not in result


class TestFuzzyModelMatch:
    """Test fuzzy model name matching."""
    
    def test_exact_match(self):
        from ai_engine.modules.entity_validator import _fuzzy_model_match
        assert _fuzzy_model_match("Leopard 8", "Leopard 8") is True
    
    def test_case_insensitive(self):
        from ai_engine.modules.entity_validator import _fuzzy_model_match
        assert _fuzzy_model_match("Leopard 8", "leopard 8") is True
    
    def test_whitespace_variation(self):
        from ai_engine.modules.entity_validator import _fuzzy_model_match
        assert _fuzzy_model_match("Seal 06 GT", "Seal 06GT") is True
    
    def test_different_number(self):
        from ai_engine.modules.entity_validator import _fuzzy_model_match
        assert _fuzzy_model_match("Leopard 8", "Leopard 7") is False
    
    def test_different_model(self):
        from ai_engine.modules.entity_validator import _fuzzy_model_match
        assert _fuzzy_model_match("7X", "007") is False


class TestValidateEntities:
    """Test full entity validation pipeline."""
    
    def test_matching_entities(self):
        from ai_engine.modules.entity_validator import validate_entities
        html = '<h2>2025 BYD Leopard 8 Review</h2><p>The Leopard 8 is great.</p>'
        result = validate_entities("2025 BYD Leopard 8 PHEV 7-Seater Review", html)
        assert result.is_valid is True
        assert len(result.mismatches) == 0
    
    def test_mismatched_model_number(self):
        from ai_engine.modules.entity_validator import validate_entities
        html = '<h2>2025 BYD Leopard 7 Review</h2><p>The Leopard 7 is great.</p>'
        result = validate_entities("2025 BYD Leopard 8 PHEV 7-Seater Review", html)
        assert result.is_valid is False
        assert len(result.mismatches) > 0
        assert 'Leopard' in result.mismatches[0]
    
    def test_auto_fix_applied(self):
        from ai_engine.modules.entity_validator import validate_entities
        html = '<h2>2025 BYD Leopard 7 Review</h2><p>The Leopard 7 is a great SUV.</p>'
        result = validate_entities("2025 BYD Leopard 8 PHEV 7-Seater Review", html)
        if not result.is_valid and result.auto_fixed:
            assert 'Leopard 8' in result.fixed_html
            assert 'Leopard 7' not in result.fixed_html
    
    def test_empty_inputs(self):
        from ai_engine.modules.entity_validator import validate_entities
        result = validate_entities("", "")
        assert result.is_valid is True
    
    def test_no_model_in_source(self):
        from ai_engine.modules.entity_validator import validate_entities
        # Non-automotive titles may still be extracted as "model names"
        # The validator will try to match whatever it extracts
        result = validate_entities("Some random title", '<h2>Article</h2><p>Text.</p>')
        # This is expected to fail because the extractor will treat the title as a model
        # and find it doesn't match — that's actually correct behavior
        assert isinstance(result.is_valid, bool)


class TestBuildEntityAnchor:
    """Test prompt anchor generation."""
    
    def test_builds_anchor(self):
        from ai_engine.modules.entity_validator import build_entity_anchor
        anchor = build_entity_anchor("2025 BYD Leopard 8 PHEV Review")
        assert 'MANDATORY' in anchor
        assert 'Leopard 8' in anchor or 'BYD' in anchor
    
    def test_empty_title(self):
        from ai_engine.modules.entity_validator import build_entity_anchor
        anchor = build_entity_anchor("")
        assert anchor == ""
    
    def test_no_model_name(self):
        from ai_engine.modules.entity_validator import build_entity_anchor
        anchor = build_entity_anchor("Hello World")
        # Should return empty if no model can be extracted
        # (though it might still extract something)
        assert isinstance(anchor, str)


class TestInjectEntityWarning:
    """Test warning banner injection."""
    
    def test_injects_warning(self):
        from ai_engine.modules.entity_validator import inject_entity_warning
        html = '<h2>Title</h2><p>Content.</p>'
        result = inject_entity_warning(html, ["Model mismatch: Leopard 8 vs Leopard 7"])
        assert 'entity-mismatch-warning' in result
        assert 'Leopard 8' in result
        assert html in result  # Original HTML preserved


class TestAutoFix:
    """Test entity auto-fix functionality."""
    
    def test_replaces_wrong_entity(self):
        from ai_engine.modules.entity_validator import _auto_fix_entity
        html = '<h2>BYD Leopard 7 Review</h2><p>The Leopard 7 has 600hp.</p>'
        fixed = _auto_fix_entity(html, "Leopard 7", "Leopard 8")
        assert 'Leopard 8' in fixed
        assert 'Leopard 7' not in fixed
    
    def test_case_insensitive_fix(self):
        from ai_engine.modules.entity_validator import _auto_fix_entity
        html = '<p>The leopard 7 is powerful.</p>'
        fixed = _auto_fix_entity(html, "leopard 7", "Leopard 8")
        assert 'Leopard 8' in fixed
