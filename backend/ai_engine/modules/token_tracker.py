"""
Token Usage Tracker — records Gemini API token consumption per function.

Storage: Django cache (Redis) — survives deploys.
Key: 'token_usage_records' → JSON list of usage records.
Key: 'token_usage_summary' → pre-computed aggregates (updated on each record).
"""
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

RECORDS_KEY = 'token_usage_records'
MAX_RECORDS = 2000  # Keep last 2000 calls (~1 week at normal usage)

# Gemini pricing (per 1M tokens, as of March 2026)
# https://ai.google.dev/pricing
PRICING = {
    'gemini-2.0-flash': {'input': 0.10, 'output': 0.40},
    'gemini-2.5-flash': {'input': 0.15, 'output': 0.60},
    'gemini-2.5-pro-exp-03-25': {'input': 0.0, 'output': 0.0},  # Free experimental
    'gemini-3-flash-preview': {'input': 0.15, 'output': 0.60},
    'gemini-3.1-pro-preview': {'input': 1.25, 'output': 5.00},
}
DEFAULT_PRICING = {'input': 0.15, 'output': 0.60}


def _get_cache():
    """Get Django cache (Redis)."""
    from django.core.cache import cache
    return cache


def record(caller: str, model: str, prompt_tokens: int, completion_tokens: int):
    """
    Record a single AI API call.

    Args:
        caller: Function label (e.g. 'article_generate', 'fact_check')
        model: Model name (e.g. 'gemini-2.5-flash')
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
    """
    try:
        cache = _get_cache()
        total = prompt_tokens + completion_tokens

        # Estimate cost
        pricing = PRICING.get(model, DEFAULT_PRICING)
        cost = (prompt_tokens / 1_000_000 * pricing['input'] +
                completion_tokens / 1_000_000 * pricing['output'])

        entry = {
            'caller': caller,
            'model': model,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total,
            'cost': round(cost, 6),
            'ts': datetime.utcnow().isoformat(),
        }

        # Append to records list
        raw = cache.get(RECORDS_KEY)
        records = json.loads(raw) if raw else []
        records.append(entry)

        # Trim to MAX_RECORDS
        if len(records) > MAX_RECORDS:
            records = records[-MAX_RECORDS:]

        cache.set(RECORDS_KEY, json.dumps(records), timeout=30 * 86400)  # 30 days

        logger.info(f"[TOKEN] {caller} | {model} | in={prompt_tokens} out={completion_tokens} "
                    f"total={total} | ${cost:.4f}")

    except Exception as e:
        logger.warning(f"[TOKEN] Failed to record: {e}")


def get_summary(hours: int = 24) -> dict:
    """
    Get aggregated token usage summary.

    Args:
        hours: Time window (default 24h)

    Returns:
        Dict with total stats, per-caller breakdown, per-model breakdown.
    """
    try:
        cache = _get_cache()
        raw = cache.get(RECORDS_KEY)
        records = json.loads(raw) if raw else []
    except Exception:
        records = []

    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    filtered = [r for r in records if r.get('ts', '') >= cutoff]

    # Totals
    total_prompt = sum(r.get('prompt_tokens', 0) for r in filtered)
    total_completion = sum(r.get('completion_tokens', 0) for r in filtered)
    total_cost = sum(r.get('cost', 0) for r in filtered)

    # Per caller
    by_caller = defaultdict(lambda: {
        'calls': 0, 'prompt_tokens': 0, 'completion_tokens': 0,
        'total_tokens': 0, 'cost': 0.0
    })
    for r in filtered:
        c = r.get('caller', 'unknown')
        by_caller[c]['calls'] += 1
        by_caller[c]['prompt_tokens'] += r.get('prompt_tokens', 0)
        by_caller[c]['completion_tokens'] += r.get('completion_tokens', 0)
        by_caller[c]['total_tokens'] += r.get('total_tokens', 0)
        by_caller[c]['cost'] += r.get('cost', 0)

    # Per model
    by_model = defaultdict(lambda: {
        'calls': 0, 'total_tokens': 0, 'cost': 0.0
    })
    for r in filtered:
        m = r.get('model', 'unknown')
        by_model[m]['calls'] += 1
        by_model[m]['total_tokens'] += r.get('total_tokens', 0)
        by_model[m]['cost'] += r.get('cost', 0)

    # Sort by_caller by total_tokens desc
    sorted_callers = dict(sorted(
        by_caller.items(),
        key=lambda x: x[1]['total_tokens'],
        reverse=True
    ))

    # Round costs
    for v in sorted_callers.values():
        v['cost'] = round(v['cost'], 4)
    for v in by_model.values():
        v['cost'] = round(v['cost'], 4)

    # Find top consumer
    top_caller = max(sorted_callers.items(), key=lambda x: x[1]['total_tokens'])[0] if sorted_callers else None

    return {
        'hours': hours,
        'total_calls': len(filtered),
        'total_prompt_tokens': total_prompt,
        'total_completion_tokens': total_completion,
        'total_tokens': total_prompt + total_completion,
        'total_cost': round(total_cost, 4),
        'top_caller': top_caller,
        'by_caller': sorted_callers,
        'by_model': dict(by_model),
    }


def get_realtime(minutes: int = 5) -> list:
    """
    Get recent API calls for live feed.

    Args:
        minutes: Time window (default 5 min)

    Returns:
        List of recent records, newest first.
    """
    try:
        cache = _get_cache()
        raw = cache.get(RECORDS_KEY)
        records = json.loads(raw) if raw else []
    except Exception:
        records = []

    cutoff = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
    recent = [r for r in records if r.get('ts', '') >= cutoff]
    return list(reversed(recent))  # newest first
