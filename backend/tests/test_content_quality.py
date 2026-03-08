"""
Tests for AI content quality improvements:
- Correction memory (learning loop)
- (unverified) stripping from fact_checker
- New banned phrase patterns
"""
import json
import os
import pytest
import re
import tempfile
from unittest.mock import patch, MagicMock

# ─── Correction Memory Tests ────────────────────────────────────────

def test_record_and_load_corrections():
    """Test that corrections are saved to disk and reloaded."""
    from ai_engine.modules.correction_memory import (
        record_corrections, get_correction_examples, _load_memory,
    )
    # Use a temp file
    tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
    tmp_path = tmp.name
    tmp.close()

    with patch('ai_engine.modules.correction_memory.MEMORY_FILE', tmp_path):
        # Record a correction
        record_corrections(
            'BYD Sealion 06 Review',
            replaced=[{'claim': '330 Nm', 'correct': '241 hp', 'source': 'web'}],
            caveated=[{'claim': '605 km', 'note': 'per manufacturer'}],
            removed=[{'claim': '$31,500', 'reason': 'web shows CNY 143,800'}],
        )

        memory = _load_memory()
        assert len(memory) == 1
        assert memory[0]['article'] == 'BYD Sealion 06 Review'
        assert len(memory[0]['corrections']) == 2  # replaced + removed (caveated not saved)

        # Generate prompt examples
        block = get_correction_examples(n=5)
        assert '330 Nm' in block
        assert '$31,500' in block
        assert 'PAST MISTAKES' in block

    os.unlink(tmp_path)


def test_record_only_caveats_skipped():
    """Corrections with only caveats (no errors) should not be saved."""
    from ai_engine.modules.correction_memory import record_corrections, _load_memory

    tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
    tmp_path = tmp.name
    tmp.close()

    with patch('ai_engine.modules.correction_memory.MEMORY_FILE', tmp_path):
        record_corrections(
            'Good Article',
            replaced=[],
            caveated=[{'claim': '605 km', 'note': 'per manufacturer'}],
            removed=[],
        )
        memory = _load_memory()
        assert len(memory) == 0  # Nothing wrong = nothing to save

    os.unlink(tmp_path)


def test_empty_memory_returns_no_prompt():
    """Empty memory should return empty string."""
    from ai_engine.modules.correction_memory import get_correction_examples

    tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
    tmp_path = tmp.name
    tmp.close()

    with patch('ai_engine.modules.correction_memory.MEMORY_FILE', tmp_path):
        block = get_correction_examples(n=5)
        assert block == ''

    os.unlink(tmp_path)


def test_memory_trimmed_to_max():
    """Memory should be trimmed to MAX_ENTRIES."""
    from ai_engine.modules.correction_memory import record_corrections, _load_memory

    tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
    tmp_path = tmp.name
    tmp.close()

    with patch('ai_engine.modules.correction_memory.MEMORY_FILE', tmp_path):
        with patch('ai_engine.modules.correction_memory.MAX_ENTRIES', 3):
            for i in range(5):
                record_corrections(
                    f'Article {i}',
                    replaced=[{'claim': f'spec_{i}', 'correct': 'fixed', 'source': 'web'}],
                )
            memory = _load_memory()
            assert len(memory) == 3  # Trimmed to 3
            assert memory[0]['article'] == 'Article 2'  # Oldest kept

    os.unlink(tmp_path)


def test_memory_stats():
    """Test get_memory_stats returns correct data."""
    from ai_engine.modules.correction_memory import record_corrections, get_memory_stats

    tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
    tmp_path = tmp.name
    tmp.close()

    with patch('ai_engine.modules.correction_memory.MEMORY_FILE', tmp_path):
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

    os.unlink(tmp_path)


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
