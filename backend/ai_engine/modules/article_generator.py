"""
article_generator — backward-compatibility re-exports.

All logic has been moved to focused modules:
- banned_phrases.py: AI filler detection/removal (~260 lines)
- article_post_processor.py: HTML cleanup pipeline (~480 lines)
- article_prompt_builder.py: Prompt construction + AI calls (~1070 lines)
- article_self_review.py: AI editor + verdict injector (~240 lines)
- html_normalizer.py: Markdown→HTML conversion (~80 lines)

This file re-exports every public symbol so that all existing imports
(from 12+ files) continue to work without modification.
"""

# ── Core generation ────────────────────────────────────────────────────
from ai_engine.modules.article_prompt_builder import (
    generate_article,
    expand_press_release,
    enhance_existing_article,
)

# ── Post-processing pipeline ──────────────────────────────────────────
from ai_engine.modules.article_post_processor import (
    post_process_article,
    _detect_missing_sections,
    _strip_empty_compare_cards,
    _dedup_guard,
)

# ── AI self-review & verdict ──────────────────────────────────────────
from ai_engine.modules.article_self_review import (
    _self_review_pass,
    _ensure_verdict_written,
)

# ── HTML normalizer ───────────────────────────────────────────────────
from ai_engine.modules.html_normalizer import ensure_html_only

# ── Banned phrases ────────────────────────────────────────────────────
from ai_engine.modules.banned_phrases import (
    clean_banned_phrases as _clean_banned_phrases,
)

__all__ = [
    'generate_article',
    'expand_press_release',
    'enhance_existing_article',
    'post_process_article',
    'ensure_html_only',
    '_clean_banned_phrases',
    '_detect_missing_sections',
    '_strip_empty_compare_cards',
    '_dedup_guard',
    '_self_review_pass',
    '_ensure_verdict_written',
]
