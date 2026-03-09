"""
Tests for provider_tracker module (Redis-based storage).
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from ai_engine.modules.provider_tracker import (
    record_generation, recommend_provider, get_provider_summary,
)


class TestProviderTracker:
    """Tests for provider performance tracking"""

    @pytest.fixture(autouse=True)
    def use_fake_cache(self):
        """Use a fake in-memory cache dict to simulate Django cache."""
        self.fake_cache_store = {}

        fake_cache = MagicMock()
        fake_cache.get = lambda key: self.fake_cache_store.get(key)
        fake_cache.set = lambda key, value, timeout=None: self.fake_cache_store.__setitem__(key, value)

        with patch('ai_engine.modules.provider_tracker.cache', fake_cache, create=True):
            # Also patch django.core.cache.cache for the import inside functions
            with patch.dict('sys.modules', {}):
                import django.core.cache
                with patch.object(django.core.cache, 'cache', fake_cache):
                    yield

    def test_record_generation(self):
        """Recording a generation should save to cache."""
        record_generation(
            provider='gemini', make='BMW',
            quality_score=8, spec_coverage=80.0,
            total_time=45.5, spec_fields_filled=8
        )
        # Read directly from our fake store
        raw = self.fake_cache_store.get('provider_stats')
        assert raw is not None
        data = json.loads(raw)
        assert len(data['records']) == 1
        assert data['records'][0]['provider'] == 'gemini'
        assert data['records'][0]['make'] == 'Bmw'

    def test_recommend_default(self):
        """With no data, should default to gemini."""
        result = recommend_provider()
        assert result == 'gemini'

    def test_recommend_best_provider(self):
        """Should recommend provider with better quality."""
        for _ in range(5):
            record_generation(provider='gemini', make='BMW', quality_score=8, spec_coverage=90.0)
            record_generation(provider='groq', make='BMW', quality_score=5, spec_coverage=50.0)

        result = recommend_provider('BMW')
        assert result == 'gemini'

    def test_summary_structure(self):
        """Summary should have correct structure."""
        record_generation(provider='gemini', make='BMW', quality_score=8, spec_coverage=90.0)
        record_generation(provider='groq', make='Toyota', quality_score=7, spec_coverage=70.0)

        summary = get_provider_summary()
        assert 'providers' in summary
        assert 'total_records' in summary
        assert summary['total_records'] == 2
        assert summary['storage'] == 'redis'

    def test_max_records_cap(self):
        """Should cap at 500 records."""
        for i in range(510):
            record_generation(provider='gemini', make='Test', quality_score=5)

        raw = self.fake_cache_store.get('provider_stats')
        data = json.loads(raw)
        assert len(data['records']) <= 500
