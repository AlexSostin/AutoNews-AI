"""API endpoints for AI Token Usage analytics dashboard."""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


class TokenUsageSummaryView(APIView):
    """GET /api/v1/token-usage/summary/?hours=24"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        hours = int(request.query_params.get('hours', 24))
        hours = min(hours, 720)  # Max 30 days
        try:
            from ai_engine.modules.token_tracker import get_summary
            return Response(get_summary(hours))
        except Exception as e:
            logger.error(f"Token usage summary failed: {e}")
            return Response({'error': str(e)}, status=500)


class TokenUsageRealtimeView(APIView):
    """GET /api/v1/token-usage/realtime/?minutes=5"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        minutes = int(request.query_params.get('minutes', 5))
        minutes = min(minutes, 60)
        try:
            from ai_engine.modules.token_tracker import get_realtime
            return Response(get_realtime(minutes))
        except Exception as e:
            logger.error(f"Token usage realtime failed: {e}")
            return Response({'error': str(e)}, status=500)
