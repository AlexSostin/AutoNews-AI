"""
Correction Memory — persistent learning loop for AI article generation.

Stores past fact-check corrections so the article generator can learn from
previous mistakes and avoid repeating them.

Usage:
    # After auto_resolve:
    record_corrections('BYD Sealion 06', replaced=[...], caveated=[...], removed=[...])

    # Before generating a new article:
    prompt_block = get_correction_examples(n=15)
    # → inserts "DO NOT repeat these past mistakes:" into the generation prompt
"""
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Store corrections next to other AI data files
MEMORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
MEMORY_FILE = os.path.join(MEMORY_DIR, 'correction_memory.json')
MAX_ENTRIES = 200  # Keep last 200 corrections to avoid file bloat


def _load_memory() -> list:
    """Load correction memory from disk."""
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Correction memory load failed: {e}")
        return []


def _save_memory(entries: list):
    """Save correction memory to disk, trimming to MAX_ENTRIES."""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    # Keep only the most recent entries
    trimmed = entries[-MAX_ENTRIES:]
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(trimmed, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logger.error(f"Correction memory save failed: {e}")


def record_corrections(article_title: str, replaced: list = None,
                       caveated: list = None, removed: list = None):
    """
    Record corrections from auto_resolve into persistent memory.

    Args:
        article_title: Title of the article that was corrected
        replaced: List of {'claim': ..., 'correct': ..., 'source': ...}
        caveated: List of {'claim': ..., 'note': ...}
        removed: List of {'claim': ..., 'reason': ...}
    """
    replaced = replaced or []
    caveated = caveated or []
    removed = removed or []

    if not replaced and not removed:
        return  # Only caveats = nothing wrong, no lesson to learn

    entries = _load_memory()

    entry = {
        'timestamp': datetime.now().isoformat(),
        'article': article_title[:80],
        'corrections': [],
    }

    for r in replaced:
        entry['corrections'].append({
            'type': 'replaced',
            'wrong': r.get('claim', ''),
            'correct': r.get('correct', ''),
        })

    for r in removed:
        entry['corrections'].append({
            'type': 'removed',
            'wrong': r.get('claim', ''),
            'reason': r.get('reason', ''),
        })

    if entry['corrections']:
        entries.append(entry)
        _save_memory(entries)
        print(f"  📝 Correction memory: saved {len(entry['corrections'])} lessons from '{article_title[:40]}'")


def get_correction_examples(n: int = 15) -> str:
    """
    Build a prompt block with recent correction examples for the article generator.

    Args:
        n: Maximum number of individual corrections to include

    Returns:
        Formatted prompt string with past mistakes, or empty string if no memory.
    """
    entries = _load_memory()
    if not entries:
        return ''

    # Collect individual corrections from recent entries (newest first)
    examples = []
    for entry in reversed(entries):
        for corr in entry['corrections']:
            if corr['type'] == 'replaced':
                examples.append(
                    f"  ❌ In \"{entry['article']}\": claimed \"{corr['wrong']}\" "
                    f"→ correct was \"{corr['correct']}\""
                )
            elif corr['type'] == 'removed':
                examples.append(
                    f"  ❌ In \"{entry['article']}\": fabricated \"{corr['wrong']}\" "
                    f"({corr['reason']})"
                )
            if len(examples) >= n:
                break
        if len(examples) >= n:
            break

    if not examples:
        return ''

    block = (
        "\n═══ LEARN FROM PAST MISTAKES ═══\n"
        "Our fact-checker caught these errors in recent articles. DO NOT repeat them:\n"
        + "\n".join(examples)
        + "\n\nThese were REAL corrections. If you don't have a verified source for a number, "
        "OMIT IT rather than guess. A shorter accurate article > a longer hallucinated one.\n"
        "═══════════════════════════════\n"
    )
    return block


def get_memory_stats() -> dict:
    """Get stats about correction memory (for dashboard/debugging)."""
    entries = _load_memory()
    if not entries:
        return {'total_entries': 0, 'total_corrections': 0}

    total_corrections = sum(len(e.get('corrections', [])) for e in entries)
    return {
        'total_entries': len(entries),
        'total_corrections': total_corrections,
        'oldest': entries[0].get('timestamp', ''),
        'newest': entries[-1].get('timestamp', ''),
    }
