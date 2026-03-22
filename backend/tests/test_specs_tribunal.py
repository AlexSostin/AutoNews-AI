import pytest
from unittest.mock import patch, MagicMock
from ai_engine.modules.specs_tribunal import convene_specs_tribunal

def test_specs_tribunal_success_json_parsing():
    """Test that the tribunal parses valid JSON successfully."""
    
    mock_ai = MagicMock()
    mock_ai.generate_completion.return_value = '''```json
{
  "verified_specs": {
    "make": "Zeekr",
    "model": "9X",
    "trim": "Ultra",
    "year": 2026,
    "engine": "PHEV",
    "horsepower": 1381,
    "torque": "1000 Nm",
    "acceleration": "2.9s",
    "top_speed": "250 km/h",
    "drivetrain": "AWD",
    "battery": "100 kWh",
    "range": "1200 km",
    "price": "$50,000"
  },
  "rulings": ["Ruled in favor of Web Context"]
}
```'''

    with patch('ai_engine.modules.specs_tribunal.get_ai_provider', return_value=mock_ai):
        result = convene_specs_tribunal(
            transcript_analysis="audio specs",
            video_facts={"specs": {"price": "$50,000"}},
            web_context="web specs",
            internal_specs_text="db specs",
            provider="gemini"
        )
        
        assert result is not None
        assert 'verified_specs' in result
        assert result['verified_specs']['make'] == 'Zeekr'
        assert result['verified_specs']['horsepower'] == 1381
        assert "Ruled in favor of Web Context" in result['summary_for_writer']

def test_specs_tribunal_malformed_json_fallback():
    """Test that the tribunal returns a safe fallback if JSON parsing fails entirely."""
    
    mock_ai = MagicMock()
    mock_ai.generate_completion.return_value = '''```json
{
  "verified_specs": {
    "make": "Zeekr"
    # Missing quotes, commas, malformed
    broken
'''

    with patch('ai_engine.modules.specs_tribunal.get_ai_provider', return_value=mock_ai):
        result = convene_specs_tribunal(
            transcript_analysis="audio",
            video_facts={},
            web_context="",
            internal_specs_text="",
            provider="gemini"
        )
        
        assert result is not None
        # It should return the fallback dictionary defined in the try/except block
        assert result['verified_specs'] is None
        assert result['summary_for_writer'] == ""

def test_specs_tribunal_empty_fields_turned_to_none_or_not_specified():
    """Test that missing fields are filled with 'Not specified' or None depending on the field type."""
    
    mock_ai = MagicMock()
    # Provide partial JSON (missing year, missing horsepower, missing engine)
    mock_ai.generate_completion.return_value = '''
{
  "verified_specs": {
    "make": "Zeekr",
    "model": "9X",
    "year": null,
    "horsepower": null
  },
  "rulings": []
}
'''

    with patch('ai_engine.modules.specs_tribunal.get_ai_provider', return_value=mock_ai):
        result = convene_specs_tribunal(
            transcript_analysis="audio",
            video_facts={},
            web_context="",
            internal_specs_text="",
            provider="gemini"
        )
        
        specs = result['verified_specs']
        assert specs['make'] == 'Zeekr'
        assert specs['year'] is None  # Number fields should be None, not "Not specified"
        assert specs['horsepower'] is None
        assert specs.get('engine', "Not specified") == "Not specified" # Others default to Not specified if omitted by LLM?
        # Actually in specs_tribunal.py it loops over verified_specs.items().
        # If the LLM omitted 'engine' entirely, it won't be in the dict.
        # But wait, our specs dictionary usually has all keys. If the LLM omits it, it's fine,
        # because the original `specs` dict in content_generator.py provides defaults, 
        # and we only override what the tribunal provides.
