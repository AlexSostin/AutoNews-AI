"""
Tests for AI content quality improvements:
- Correction memory (learning loop) — now using Django cache/Redis
- (unverified) stripping from fact_checker
- New banned phrase patterns
"""
import json
import pytest
import re
from unittest.mock import patch, MagicMock


# ─── Correction Memory Tests ────────────────────────────────────────

def test_record_and_load_corrections():
    """Test that corrections are saved to cache and reloaded."""
    from ai_engine.modules.correction_memory import (
        record_corrections, get_correction_examples, _load_memory,
    )
    # Use a fake cache dict to simulate Django cache
    fake_cache = {}

    def fake_get(key):
        return fake_cache.get(key)

    def fake_set(key, value, timeout=None):
        fake_cache[key] = value

    mock_cache = MagicMock()
    mock_cache.get = fake_get
    mock_cache.set = fake_set

    with patch('ai_engine.modules.correction_memory.cache', mock_cache, create=True), \
         patch('django.core.cache.cache', mock_cache):
        # Patch the import inside the functions
        import ai_engine.modules.correction_memory as cm
        original_load = cm._load_memory
        original_save = cm._save_memory

        def patched_load():
            data = fake_cache.get('correction_memory')
            if data is None:
                return []
            if isinstance(data, str):
                return json.loads(data)
            return data

        def patched_save(entries):
            trimmed = entries[-200:]
            fake_cache['correction_memory'] = json.dumps(trimmed, ensure_ascii=False)

        cm._load_memory = patched_load
        cm._save_memory = patched_save

        try:
            # Record a correction
            record_corrections(
                'BYD Sealion 06 Review',
                replaced=[{'claim': '330 Nm', 'correct': '241 hp', 'source': 'web'}],
                caveated=[{'claim': '605 km', 'note': 'per manufacturer'}],
                removed=[{'claim': '$31,500', 'reason': 'web shows CNY 143,800'}],
            )

            memory = patched_load()
            assert len(memory) == 1
            assert memory[0]['article'] == 'BYD Sealion 06 Review'
            assert len(memory[0]['corrections']) == 2  # replaced + removed (caveated not saved)

            # Generate prompt examples
            block = get_correction_examples(n=5)
            assert '330 Nm' in block
            assert '$31,500' in block
            assert 'PAST MISTAKES' in block
        finally:
            cm._load_memory = original_load
            cm._save_memory = original_save


def test_record_only_caveats_skipped():
    """Corrections with only caveats (no errors) should not be saved."""
    from ai_engine.modules.correction_memory import record_corrections
    import ai_engine.modules.correction_memory as cm

    fake_cache = {}

    def patched_load():
        data = fake_cache.get('correction_memory')
        if data is None:
            return []
        return json.loads(data) if isinstance(data, str) else data

    def patched_save(entries):
        fake_cache['correction_memory'] = json.dumps(entries[-200:], ensure_ascii=False)

    original_load = cm._load_memory
    original_save = cm._save_memory
    cm._load_memory = patched_load
    cm._save_memory = patched_save

    try:
        record_corrections(
            'Good Article',
            replaced=[],
            caveated=[{'claim': '605 km', 'note': 'per manufacturer'}],
            removed=[],
        )
        memory = patched_load()
        assert len(memory) == 0  # Nothing wrong = nothing to save
    finally:
        cm._load_memory = original_load
        cm._save_memory = original_save


def test_empty_memory_returns_no_prompt():
    """Empty memory should return empty string."""
    from ai_engine.modules.correction_memory import get_correction_examples
    import ai_engine.modules.correction_memory as cm

    fake_cache = {}

    def patched_load():
        return []

    original_load = cm._load_memory
    cm._load_memory = patched_load

    try:
        block = get_correction_examples(n=5)
        assert block == ''
    finally:
        cm._load_memory = original_load


def test_memory_trimmed_to_max():
    """Memory should be trimmed to MAX_ENTRIES."""
    from ai_engine.modules.correction_memory import record_corrections
    import ai_engine.modules.correction_memory as cm

    fake_cache = {}

    def patched_load():
        data = fake_cache.get('correction_memory')
        if data is None:
            return []
        return json.loads(data) if isinstance(data, str) else data

    def patched_save(entries):
        trimmed = entries[-3:]  # Using MAX_ENTRIES = 3 for test
        fake_cache['correction_memory'] = json.dumps(trimmed, ensure_ascii=False)

    original_load = cm._load_memory
    original_save = cm._save_memory
    cm._load_memory = patched_load
    cm._save_memory = patched_save

    try:
        for i in range(5):
            record_corrections(
                f'Article {i}',
                replaced=[{'claim': f'spec_{i}', 'correct': 'fixed', 'source': 'web'}],
            )
        memory = patched_load()
        assert len(memory) == 3  # Trimmed to 3
        assert memory[0]['article'] == 'Article 2'  # Oldest kept
    finally:
        cm._load_memory = original_load
        cm._save_memory = original_save


def test_memory_stats():
    """Test get_memory_stats returns correct data."""
    from ai_engine.modules.correction_memory import record_corrections, get_memory_stats
    import ai_engine.modules.correction_memory as cm

    fake_cache = {}

    def patched_load():
        data = fake_cache.get('correction_memory')
        if data is None:
            return []
        return json.loads(data) if isinstance(data, str) else data

    def patched_save(entries):
        fake_cache['correction_memory'] = json.dumps(entries[-200:], ensure_ascii=False)

    original_load = cm._load_memory
    original_save = cm._save_memory
    cm._load_memory = patched_load
    cm._save_memory = patched_save

    try:
        record_corrections(
            'Test Article',
            replaced=[
                {'claim': 'a', 'correct': 'b', 'source': 'web'},
                {'claim': 'c', 'correct': 'd', 'source': 'web'},
            ],
            removed=[{'claim': 'e', 'reason': 'wrong'}],
        )
        stats = get_memory_stats()
        assert stats['total_entries'] == 1
        assert stats['total_corrections'] == 3
        assert stats['storage'] == 'redis'
    finally:
        cm._load_memory = original_load
        cm._save_memory = original_save


# ─── Unverified Stripping Tests ──────────────────────────────────────

def test_strip_unverified_from_html():
    """Verify (unverified) tags are stripped from auto-resolved HTML."""
    html = (
        '<p>The battery is 78 kWh (unverified) with a range of '
        '605 km (per manufacturer) and 185 km/h top speed (not independently verified).</p>'
    )
    # Apply the same regex used in fact_checker.py
    cleaned = re.sub(r'\s*\((?:unverified|per manufacturer|not independently verified)\)', '', html)
    assert '(unverified)' not in cleaned
    assert '(per manufacturer)' not in cleaned
    assert '(not independently verified)' not in cleaned
    assert '78 kWh' in cleaned
    assert '605 km' in cleaned
    assert '185 km/h' in cleaned


# ─── Banned Phrases Tests ────────────────────────────────────────────

def test_new_banned_phrases_replaced():
    """Test that Round 4 banned phrases from BYD Sealion article are processed."""
    from ai_engine.modules.article_generator import _clean_banned_phrases

    html = (
        '<p>The car arrives in the burgeoning electric SUV market as a significant contender, '
        'aiming to blend practicality and style, offering brisk acceleration '
        'and a compelling option for buyers.</p>'
    )
    cleaned = _clean_banned_phrases(html)
    assert 'burgeoning' not in cleaned
    assert 'significant contender' not in cleaned
    assert 'brisk acceleration' not in cleaned
    assert 'compelling option' not in cleaned
    # Check replacements are present
    assert 'this market segment' in cleaned
    assert 'strong option' in cleaned
    assert 'quick acceleration' in cleaned
    assert 'strong choice' in cleaned


def test_range_anxiety_phrase():
    """Test 'reduces range anxiety' is replaced."""
    from ai_engine.modules.article_generator import _clean_banned_phrases

    html = '<p>The 605 km range effectively reduces range anxiety for most drivers.</p>'
    cleaned = _clean_banned_phrases(html)
    assert 'range anxiety' not in cleaned
    assert 'provides sufficient range' in cleaned
