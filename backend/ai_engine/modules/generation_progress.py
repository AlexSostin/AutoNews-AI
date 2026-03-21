"""
Progress reporting for article generation pipeline.

Sends progress updates via Celery state (primary), Django cache, and WebSocket (fallback).
"""
import logging

logger = logging.getLogger(__name__)


def _send_progress(task_id, step, progress, message, celery_task=None, cache_task_id=None):
    """Send progress update via Celery state (primary), Django cache, and WebSocket (fallback)."""
    print(f"[{progress}%] {message}")

    # Primary: Celery state update — readable via AsyncResult.info on polling
    if celery_task is not None:
        try:
            celery_task.update_state(
                state='PROGRESS',
                meta={'step': step, 'progress': progress, 'message': message},
            )
        except Exception as e:
            print(f"Celery update_state error: {e}")

    # Cache-based progress for thread-based flows (YouTube channels page, video inbox)
    if cache_task_id:
        try:
            import json
            from django.core.cache import cache
            cache.set(f'gen_task:{cache_task_id}', json.dumps({
                'status': 'running',
                'step': step,
                'progress': progress,
                'message': message,
            }), timeout=600)
        except Exception as e:
            print(f"Cache progress update error: {e}")

    # Secondary: WebSocket (channels) — if configured
    if task_id:
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"generation_{task_id}",
                    {
                        "type": "send_progress",
                        "step": step,
                        "progress": progress,
                        "message": message
                    }
                )
        except Exception as e:
            pass  # WebSocket not configured — that's fine
