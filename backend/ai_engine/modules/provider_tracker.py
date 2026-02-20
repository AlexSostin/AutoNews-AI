"""
Provider Performance Tracker — records & recommends AI providers per brand.

Stores generation quality metrics per provider×brand in a JSON file.
No database migration required.
"""
import json
import os
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# Data file location
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
STATS_FILE = os.path.join(DATA_DIR, 'provider_stats.json')


def _load_stats() -> dict:
    """Load provider stats from JSON file."""
    if not os.path.exists(STATS_FILE):
        return {'records': []}
    try:
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"[PROVIDER-TRACKER] Failed to load stats: {e}")
        return {'records': []}


def _save_stats(data: dict):
    """Save provider stats to JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    except IOError as e:
        logger.warning(f"[PROVIDER-TRACKER] Failed to save stats: {e}")


def record_generation(provider: str, make: str, quality_score: int = 0,
                      spec_coverage: float = 0.0, total_time: float = 0.0,
                      spec_fields_filled: int = 0):
    """
    Record a generation event for provider performance tracking.
    
    Args:
        provider: 'gemini' or 'groq'
        make: car brand name
        quality_score: article quality score (1-10)
        spec_coverage: spec coverage percentage (0-100)
        total_time: total generation time in seconds
        spec_fields_filled: number of spec fields filled
    """
    from datetime import datetime
    
    data = _load_stats()
    
    record = {
        'provider': provider,
        'make': make.strip().title() if make else 'Unknown',
        'quality_score': quality_score,
        'spec_coverage': round(spec_coverage, 1),
        'total_time': round(total_time, 1),
        'spec_fields_filled': spec_fields_filled,
        'timestamp': datetime.utcnow().isoformat(),
    }
    
    data['records'].append(record)
    
    # Keep only last 500 records to prevent file bloat
    if len(data['records']) > 500:
        data['records'] = data['records'][-500:]
    
    _save_stats(data)
    logger.info(f"[PROVIDER-TRACKER] Recorded: {provider} × {make} — "
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
        return {'providers': {}, 'by_brand': {}, 'total_records': 0}
    
    # Overall per-provider
    providers = defaultdict(lambda: {'quality': [], 'coverage': [], 'time': [], 'count': 0})
    by_brand = defaultdict(lambda: defaultdict(lambda: {'quality': [], 'count': 0}))
    
    for r in records:
        p = r.get('provider', 'gemini')
        make = r.get('make', 'Unknown')
        
        providers[p]['quality'].append(r.get('quality_score', 0))
        providers[p]['coverage'].append(r.get('spec_coverage', 0))
        providers[p]['time'].append(r.get('total_time', 0))
        providers[p]['count'] += 1
        
        by_brand[make][p]['quality'].append(r.get('quality_score', 0))
        by_brand[make][p]['count'] += 1
    
    # Compute averages
    result_providers = {}
    for p, stats in providers.items():
        result_providers[p] = {
            'avg_quality': round(sum(stats['quality']) / len(stats['quality']), 1) if stats['quality'] else 0,
            'avg_coverage': round(sum(stats['coverage']) / len(stats['coverage']), 1) if stats['coverage'] else 0,
            'avg_time': round(sum(stats['time']) / len(stats['time']), 1) if stats['time'] else 0,
            'count': stats['count'],
        }
    
    # Top brands with per-provider comparison
    result_brands = {}
    for make, provider_data in sorted(by_brand.items(), key=lambda x: sum(p['count'] for p in x[1].values()), reverse=True)[:10]:
        result_brands[make] = {}
        for p, stats in provider_data.items():
            result_brands[make][p] = {
                'avg_quality': round(sum(stats['quality']) / len(stats['quality']), 1) if stats['quality'] else 0,
                'count': stats['count'],
            }
    
    return {
        'providers': result_providers,
        'by_brand': result_brands,
        'total_records': len(records),
    }
