"""
AI Cost Dashboard — API endpoints for AI provider usage and cost tracking.

Uses data from provider_tracker.py (Redis) to show:
- Daily/weekly/monthly AI call counts
- Per-provider breakdown (Gemini vs Groq)
- Estimated costs based on pricing
- Generation quality metrics
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

logger = logging.getLogger(__name__)

# Pricing per 1M tokens (as of March 2026)
PRICING = {
    'gemini': {
        'input': 0.075,    # $0.075 per 1M input tokens
        'output': 0.30,    # $0.30 per 1M output tokens
        'label': 'Gemini 2.5 Flash',
    },
}

# Estimated tokens per generation (based on typical article generation)
EST_TOKENS_PER_CALL = {
    'input': 3000,    # ~3k input tokens (prompt + context)
    'output': 4000,   # ~4k output tokens (article content)
}


class AICostDashboardView(APIView):
    """
    GET /api/v1/ai-costs/
    
    Returns AI provider usage statistics and cost estimates.
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        try:
            from ai_engine.modules.provider_tracker import _load_stats
            data = _load_stats()
            records = data.get('records', [])
        except Exception as e:
            logger.warning(f"[AI-COSTS] Failed to load provider stats: {e}")
            records = []
        
        if not records:
            return Response({
                'summary': {
                    'total_calls': 0,
                    'estimated_cost_usd': 0,
                },
                'by_provider': {},
                'daily': [],
                'quality': {},
            })
        
        # Parse timestamps and filter
        now = datetime.utcnow()
        
        # Aggregate by provider
        provider_stats = defaultdict(lambda: {
            'count': 0,
            'quality_scores': [],
            'coverage_scores': [],
            'times': [],
        })
        
        # Daily aggregation (last 30 days)
        daily_stats = defaultdict(lambda: defaultdict(int))
        
        for record in records:
            provider = record.get('provider', 'gemini')
            model = record.get('model', '') or provider
            quality = record.get('quality_score', 0)
            coverage = record.get('spec_coverage', 0)
            gen_time = record.get('total_time', 0)
            timestamp_str = record.get('timestamp', '')
            
            # Provider aggregation
            provider_stats[provider]['count'] += 1
            if quality:
                provider_stats[provider]['quality_scores'].append(quality)
            if coverage:
                provider_stats[provider]['coverage_scores'].append(coverage)
            if gen_time:
                provider_stats[provider]['times'].append(gen_time)
            
            # Daily aggregation
            try:
                ts = datetime.fromisoformat(timestamp_str)
                day_key = ts.strftime('%Y-%m-%d')
                if (now - ts).days <= 30:
                    daily_stats[day_key][provider] += 1
            except (ValueError, TypeError):
                pass
        
        # Calculate costs per provider
        by_provider = {}
        total_cost = 0.0
        total_calls = 0
        
        for provider, stats in provider_stats.items():
            count = stats['count']
            total_calls += count
            
            pricing = PRICING.get(provider, PRICING['gemini'])
            # Estimate cost: (count * tokens_per_call / 1M) * price_per_1M
            input_cost = (count * EST_TOKENS_PER_CALL['input'] / 1_000_000) * pricing['input']
            output_cost = (count * EST_TOKENS_PER_CALL['output'] / 1_000_000) * pricing['output']
            provider_cost = round(input_cost + output_cost, 4)
            total_cost += provider_cost
            
            avg_quality = round(sum(stats['quality_scores']) / len(stats['quality_scores']), 1) if stats['quality_scores'] else 0
            avg_coverage = round(sum(stats['coverage_scores']) / len(stats['coverage_scores']), 1) if stats['coverage_scores'] else 0
            avg_time = round(sum(stats['times']) / len(stats['times']), 1) if stats['times'] else 0
            
            by_provider[provider] = {
                'label': pricing.get('label', provider),
                'count': count,
                'estimated_cost_usd': provider_cost,
                'avg_quality': avg_quality,
                'avg_coverage': avg_coverage,
                'avg_time_seconds': avg_time,
                'pricing': {
                    'input_per_1m': pricing['input'],
                    'output_per_1m': pricing['output'],
                },
            }
        
        # Format daily data (sorted by date)
        daily_list = []
        for day in sorted(daily_stats.keys()):
            entry = {'date': day}
            for provider in provider_stats:
                entry[provider] = daily_stats[day].get(provider, 0)
            entry['total'] = sum(daily_stats[day].values())
            daily_list.append(entry)
        
        # Monthly projection
        days_with_data = len(daily_stats) or 1
        avg_daily_cost = total_cost / days_with_data if days_with_data else 0
        monthly_projection = round(avg_daily_cost * 30, 2)
        
        return Response({
            'summary': {
                'total_calls': total_calls,
                'estimated_cost_usd': round(total_cost, 4),
                'monthly_projection_usd': monthly_projection,
                'avg_daily_calls': round(total_calls / days_with_data, 1),
                'data_days': days_with_data,
            },
            'by_provider': by_provider,
            'daily': daily_list[-30:],  # Last 30 days
        })


class TimingHistoryView(APIView):
    """
    GET /api/v1/ai-costs/timing-history/
    
    Returns generation timing history for performance trend graphing.
    Query params:
      - limit: max records to return (default 100)
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        limit = int(request.query_params.get('limit', 100))
        try:
            from ai_engine.modules.provider_tracker import get_timing_history
            return Response(get_timing_history(limit=min(limit, 500)))
        except Exception as e:
            logger.warning(f"[TIMING-HISTORY] Failed: {e}")
            return Response({'history': [], 'count': 0, 'avg': 0, 'median': 0, 'min': 0, 'max': 0})
