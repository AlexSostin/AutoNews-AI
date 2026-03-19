"""
Generation error types and fallback tracker for the article pipeline.

Philosophy:
  - Every step in the pipeline either SUCCEEDS or FAILS LOUDLY.
  - Partial fallbacks are explicitly tracked and reported, not silently swallowed.
  - Token-limit errors get scheduled auto-retry (5 min delay) instead of failing.

Usage:
    from ai_engine.modules.generation_errors import FallbackTracker, GenerationError

    tracker = FallbackTracker()
    tracker.add("web_context", "ConnectionError: timeout", critical=False)
    tracker.add("competitor_lookup", "DB error", critical=True)  # → will fail generation

    if tracker.has_critical:
        raise GenerationError.from_tracker(tracker)
"""

import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  Error Classification
# ══════════════════════════════════════════════════════════════════════

# Errors that should trigger an auto-retry after a delay (not hard fail)
TOKEN_LIMIT_PHRASES = [
    'resource_exhausted',
    'quota exceeded',
    'rate limit',
    'too many tokens',
    '429',
    'token_count',
    'context_length',
    'max tokens',
]

# Non-critical steps — their failure is logged but does NOT kill the pipeline
NON_CRITICAL_STEPS = {
    'video_facts',          # Gemini video visual extraction
    'web_context',          # Web search enrichment
    'screenshot',           # YouTube screenshot
    'deep_specs',           # /cars/{brand}/{model} enrichment
    'ab_variants',          # A/B title variants
    'token_tracking',       # Usage metrics
    'next_js_revalidation', # Frontend cache
    'quality_gate',         # Quality gate check itself
}


def is_token_limit_error(error_str: str) -> bool:
    """Return True if the error string looks like a rate/token limit issue."""
    s = str(error_str).lower()
    return any(phrase in s for phrase in TOKEN_LIMIT_PHRASES)


# ══════════════════════════════════════════════════════════════════════
#  Data Classes
# ══════════════════════════════════════════════════════════════════════

@dataclass
class FallbackEvent:
    step: str
    error: str
    critical: bool
    timestamp: float = field(default_factory=time.time)
    is_token_limit: bool = False

    def __post_init__(self):
        self.is_token_limit = is_token_limit_error(self.error)

    def __str__(self) -> str:
        tag = '🔴 CRITICAL' if self.critical else '🟡 non-critical'
        retry = ' [TOKEN LIMIT — retry eligible]' if self.is_token_limit else ''
        return f"[{tag}]{retry} {self.step}: {self.error}"


class FallbackTracker:
    """
    Tracks all fallback/skip events during a generation run.

    Call .add() for every degraded step. At the end:
    - .has_critical → True if pipeline should abort
    - .needs_token_retry → True if should be retried after backoff
    - .summary() → human-readable report for admin/error storage
    """

    def __init__(self):
        self.events: List[FallbackEvent] = []

    def add(self, step: str, error: str, critical: Optional[bool] = None) -> None:
        """
        Record a fallback event.

        Args:
            step: Name of the pipeline step that degraded.
            error: Error message or description.
            critical: If None, auto-determined from NON_CRITICAL_STEPS list.
        """
        if critical is None:
            critical = step not in NON_CRITICAL_STEPS

        evt = FallbackEvent(step=step, error=str(error)[:500], critical=critical)
        self.events.append(evt)
        level = logging.ERROR if critical else logging.WARNING
        logger.log(level, f"⚡ Pipeline step degraded: {evt}")

    @property
    def has_critical(self) -> bool:
        return any(e.critical for e in self.events)

    @property
    def needs_token_retry(self) -> bool:
        """True if any critical failure was a token/rate limit → auto-retry."""
        return any(e.critical and e.is_token_limit for e in self.events)

    @property
    def critical_events(self) -> List[FallbackEvent]:
        return [e for e in self.events if e.critical]

    @property
    def non_critical_events(self) -> List[FallbackEvent]:
        return [e for e in self.events if not e.critical]

    def summary(self) -> str:
        if not self.events:
            return "All steps succeeded."
        lines = ['Pipeline Degradation Report:']
        for evt in self.events:
            lines.append(f"  {evt}")
        return '\n'.join(lines)

    def to_dict(self) -> dict:
        return {
            'has_critical': self.has_critical,
            'needs_token_retry': self.needs_token_retry,
            'events': [
                {
                    'step': e.step,
                    'error': e.error,
                    'critical': e.critical,
                    'is_token_limit': e.is_token_limit,
                }
                for e in self.events
            ],
        }


# ══════════════════════════════════════════════════════════════════════
#  Exception Classes
# ══════════════════════════════════════════════════════════════════════

class GenerationError(Exception):
    """
    Raised when article generation fails due to a critical pipeline step.
    
    The error includes a structured report of all fallback events so the
    admin UI can display exactly what went wrong.
    """

    def __init__(self, message: str, tracker: Optional[FallbackTracker] = None,
                 step: Optional[str] = None):
        super().__init__(message)
        self.tracker = tracker
        self.step = step
        self.needs_token_retry = tracker.needs_token_retry if tracker else False

    @classmethod
    def from_tracker(cls, tracker: FallbackTracker, step: str = 'unknown') -> 'GenerationError':
        critical = tracker.critical_events
        main_err = critical[0] if critical else None
        msg = (
            f"Generation failed at step '{main_err.step if main_err else step}': "
            f"{main_err.error if main_err else 'unknown error'}"
        )
        if len(critical) > 1:
            msg += f" (+ {len(critical)-1} more critical failures)"
        return cls(message=msg, tracker=tracker, step=step)

    @classmethod
    def token_limit(cls, step: str, error: str) -> 'GenerationError':
        """Convenience constructor for token/rate limit errors."""
        tracker = FallbackTracker()
        tracker.add(step, error, critical=True)
        err = cls(message=f"Token/rate limit at step '{step}': {error}",
                  tracker=tracker, step=step)
        err.needs_token_retry = True
        return err

    def to_result_dict(self) -> dict:
        """Convert to the standard {success: False, ...} result format."""
        return {
            'success': False,
            'error': str(self),
            'error_step': self.step,
            'needs_retry': self.needs_token_retry,
            'retry_after_seconds': 300 if self.needs_token_retry else None,
            'degradation_report': self.tracker.to_dict() if self.tracker else None,
        }
