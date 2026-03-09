"""
Provider Performance Tracker — records & recommends AI providers per brand.

Storage: Django cache (Redis) — survives Railway deploys.
Key: 'provider_stats' → JSON dict with records list.
"""
import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

CACHE_KEY = 'provider_stats'
MAX_RECORDS = 500


def _load_stats() -> dict:
    """Load provider stats from Django cache (Redis)."""
    try:
        from django.core.cache import cache
        data = cache.get(CACHE_KEY)
        if data is None:
            return {'records': []}
        if isinstance(data, str):
            return json.loads(data)
        return data
    except Exception as e:
        logger.warning(f"[PROVIDER-TRACKER] Failed to load stats: {e}")
        return {'records': []}


def _save_stats(data: dict):
    """Save provider stats to Django cache (Redis)."""
    try:
        from django.core.cache import cache
        # Keep only last MAX_RECORDS
        if len(data.get('records', [])) > MAX_RECORDS:
            data['records'] = data['records'][-MAX_RECORDS:]
        # Store for 365 days (effectively permanent)
        cache.set(CACHE_KEY, json.dumps(data, default=str), timeout=365 * 86400)
    except Exception as e:
        logger.warning(f"[PROVIDER-TRACKER] Failed to save stats: {e}")


def record_generation(provider: str, make: str, quality_score: int = 0,
                      spec_coverage: float = 0.0, total_time: float = 0.0,
                      spec_fields_filled: int = 0, model: str = ''):
    """
    Record a generation event for provider performance tracking.
    
    Args:
        provider: 'gemini' or 'groq'
        make: car brand name
        quality_score: article quality score (1-10)
        spec_coverage: spec coverage percentage (0-100)
        total_time: total generation time in seconds
        spec_fields_filled: number of spec fields filled
        model: specific model name used (e.g. 'gemini-2.5-flash-lite')
    """
    from datetime import datetime
    
    data = _load_stats()
    
    record = {
        'provider': provider,
        'model': model or provider,
        'make': make.strip().title() if make else 'Unknown',
        'quality_score': quality_score,
        'spec_coverage': round(spec_coverage, 1),
        'total_time': round(total_time, 1),
        'spec_fields_filled': spec_fields_filled,
        'timestamp': datetime.utcnow().isoformat(),
    }
    
    data['records'].append(record)
    _save_stats(data)
    logger.info(f"[PROVIDER-TRACKER] Recorded: {model or provider} × {make} — "
                f"quality={quality_score}, coverage={spec_coverage:.0f}%")


def recommend_provider(make: str = None) -> str:
    """
    Recommend the best provider based on historical performance.
    
    Args:
        make: car brand name (optional, for brand-specific recommendation)
    
    Returns:
        'gemini' or 'groq' (defaults to 'gemini' if no data)
    """
    data = _load_stats()
    records = data.get('records', [])
    
    if not records:
        return 'gemini'  # Default when no data
    
    # Filter by brand if specified
    if make:
        make_lower = make.strip().lower()
        brand_records = [r for r in records if r.get('make', '').lower() == make_lower]
        
        # Need at least 3 records per brand to make a recommendation
        if len(brand_records) >= 3:
            records = brand_records
    
    # Aggregate by provider
    provider_stats = defaultdict(lambda: {'total_quality': 0, 'total_coverage': 0,
                                          'total_time': 0, 'count': 0})
    
    for r in records:
        p = r.get('provider', 'gemini')
        provider_stats[p]['total_quality'] += r.get('quality_score', 0)
        provider_stats[p]['total_coverage'] += r.get('spec_coverage', 0)
        provider_stats[p]['total_time'] += r.get('total_time', 0)
        provider_stats[p]['count'] += 1
    
    # Score each provider: weighted average of quality (60%) + coverage (40%)
    best_provider = 'gemini'
    best_score = -1
    
    for provider, stats in provider_stats.items():
        if stats['count'] == 0:
            continue
        avg_quality = stats['total_quality'] / stats['count']  # 1-10
        avg_coverage = stats['total_coverage'] / stats['count']  # 0-100
        
        # Normalise both to 0-1 scale and compute weighted score
        composite = (avg_quality / 10) * 0.6 + (avg_coverage / 100) * 0.4
        
        if composite > best_score:
            best_score = composite
            best_provider = provider
    
    logger.info(f"[PROVIDER-TRACKER] Recommended: {best_provider} "
                f"(make={make or 'all'}, score={best_score:.2f})")
    
    return best_provider


def get_provider_summary() -> dict:
    """
    Get aggregated provider performance summary for dashboard display.
    
    Returns:
        Dict with per-provider averages and per-brand breakdown.
    """
    data = _load_stats()
    records = data.get('records', [])
    
    if not records:
        return {'providers': {}, 'by_brand': {}, 'total_records': 0, 'storage': 'redis'}
    
    # Overall per-provider (key = model name or provider name)
    providers = defaultdict(lambda: {'quality': [], 'coverage': [], 'time': [], 'count': 0})
    by_brand = defaultdict(lambda: defaultdict(lambda: {'quality': [], 'count': 0}))
    key_to_provider = {}
    
    for r in records:
        p = r.get('provider', 'gemini')
        model = r.get('model', '') or p
        make = r.get('make', 'Unknown')
        
        providers[model]['quality'].append(r.get('quality_score', 0))
        providers[model]['coverage'].append(r.get('spec_coverage', 0))
        providers[model]['time'].append(r.get('total_time', 0))
        providers[model]['count'] += 1
        key_to_provider[model] = p
        
        by_brand[make][model]['quality'].append(r.get('quality_score', 0))
        by_brand[make][model]['count'] += 1
    
    # Compute averages
    result_providers = {}
    for model_key, stats in providers.items():
        result_providers[model_key] = {
            'avg_quality': round(sum(stats['quality']) / len(stats['quality']), 1) if stats['quality'] else 0,
            'avg_coverage': round(sum(stats['coverage']) / len(stats['coverage']), 1) if stats['coverage'] else 0,
            'avg_time': round(sum(stats['time']) / len(stats['time']), 1) if stats['time'] else 0,
            'count': stats['count'],
            'provider': key_to_provider.get(model_key, model_key),
        }
    
    # Top brands with per-model comparison
    result_brands = {}
    for make, model_data in sorted(by_brand.items(), key=lambda x: sum(p['count'] for p in x[1].values()), reverse=True)[:10]:
        result_brands[make] = {}
        for model_key, stats in model_data.items():
            result_brands[make][model_key] = {
                'avg_quality': round(sum(stats['quality']) / len(stats['quality']), 1) if stats['quality'] else 0,
                'count': stats['count'],
            }
    
    return {
        'providers': result_providers,
        'by_brand': result_brands,
        'total_records': len(records),
        'storage': 'redis',
    }
