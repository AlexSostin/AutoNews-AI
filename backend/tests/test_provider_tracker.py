"""
Tests for provider_tracker module.
"""
import pytest
import json
import os
import tempfile
from unittest.mock import patch
from ai_engine.modules.provider_tracker import (
    record_generation, recommend_provider, get_provider_summary,
    _load_stats, _save_stats, STATS_FILE
)


class TestProviderTracker:
    """Tests for provider performance tracking"""

    @pytest.fixture(autouse=True)
    def use_temp_stats(self, tmp_path):
        """Use a temporary stats file for each test"""
        temp_file = str(tmp_path / 'provider_stats.json')
        with patch('ai_engine.modules.provider_tracker.STATS_FILE', temp_file):
            with patch('ai_engine.modules.provider_tracker.DATA_DIR', str(tmp_path)):
                yield temp_file

    def test_record_generation(self, use_temp_stats):
        """Recording a generation should save to file"""
        record_generation(
            provider='gemini', make='BMW',
            quality_score=8, spec_coverage=80.0,
            total_time=45.5, spec_fields_filled=8
        )
        data = _load_stats()
        assert len(data['records']) == 1
        assert data['records'][0]['provider'] == 'gemini'
        assert data['records'][0]['make'] == 'Bmw'  # title-cased

    def test_recommend_default(self, use_temp_stats):
        """With no data, should default to gemini"""
        result = recommend_provider()
        assert result == 'gemini'

    def test_recommend_best_provider(self, use_temp_stats):
        """Should recommend provider with better quality"""
        for _ in range(5):
            record_generation(provider='gemini', make='BMW', quality_score=8, spec_coverage=90.0)
            record_generation(provider='groq', make='BMW', quality_score=5, spec_coverage=50.0)
        
        result = recommend_provider('BMW')
        assert result == 'gemini'

    def test_summary_structure(self, use_temp_stats):
        """Summary should have correct structure"""
        record_generation(provider='gemini', make='BMW', quality_score=8, spec_coverage=90.0)
        record_generation(provider='groq', make='Toyota', quality_score=7, spec_coverage=70.0)
        
        summary = get_provider_summary()
        assert 'providers' in summary
        assert 'total_records' in summary
        assert summary['total_records'] == 2
        assert 'gemini' in summary['providers']
        assert 'groq' in summary['providers']

    def test_max_records_cap(self, use_temp_stats):
        """Should cap at 500 records"""
        for i in range(510):
            record_generation(provider='gemini', make='Test', quality_score=5)
        
        data = _load_stats()
        assert len(data['records']) <= 500
