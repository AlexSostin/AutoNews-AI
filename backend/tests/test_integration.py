"""
Phase 5 — Integration Tests.
Covers previously untested integration points:
- AI provider factory + failover
- Django signals (post_save notifications)
- WebSocket consumer (GenerationConsumer)
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from io import StringIO


# ═══════════════════════════════════════════════════════════════════════════
# AI Provider Factory — get_ai_provider + get_available_providers
# ═══════════════════════════════════════════════════════════════════════════

class TestGetAiProvider:
    def test_gemini_provider_returned(self):
        """get_ai_provider('gemini') → GeminiProvider."""
        from ai_engine.modules.ai_provider import get_ai_provider, GeminiProvider
        provider = get_ai_provider('gemini')
        assert isinstance(provider, GeminiProvider)

    def test_unknown_provider_raises(self):
        """Unknown provider name → ValueError."""
        from ai_engine.modules.ai_provider import get_ai_provider
        with pytest.raises(ValueError, match='Unknown AI provider'):
            get_ai_provider('openai')


    def test_case_insensitive(self):
        """Provider name is case-insensitive."""
        from ai_engine.modules.ai_provider import get_ai_provider, GeminiProvider
        provider = get_ai_provider('GEMINI')
        assert isinstance(provider, GeminiProvider)


class TestGeminiProviderConfig:
    def test_gemini_is_default(self):
        """Gemini is the only supported provider."""
        from ai_engine.modules.ai_provider import get_ai_provider, GeminiProvider
        provider = get_ai_provider('gemini')
        assert isinstance(provider, GeminiProvider)


class TestGeminiProviderNoKey:
    def test_gemini_no_api_key_raises(self):
        """GeminiProvider without API key → raises Exception."""
        from ai_engine.modules.ai_provider import GeminiProvider
        with patch('ai_engine.modules.ai_provider.GEMINI_API_KEY', None):
            with pytest.raises(Exception, match='not configured'):
                GeminiProvider.generate_completion('test prompt')


class TestGetAvailableProviders:
    def test_returns_list(self):
        """get_available_providers always returns a list."""
        from ai_engine.modules.ai_provider import get_available_providers
        result = get_available_providers()
        assert isinstance(result, list)

    def test_gemini_available_when_key_set(self):
        """With GEMINI_API_KEY set, gemini appears in available providers."""
        from ai_engine.modules.ai_provider import get_available_providers
        with patch('ai_engine.modules.ai_provider.GEMINI_API_KEY', 'test-key'), \
             patch('ai_engine.modules.ai_provider.GENAI_AVAILABLE', True), \
             patch('ai_engine.modules.ai_provider.gemini_client', MagicMock()):
            result = get_available_providers()
            names = [p['name'] for p in result]
            assert 'gemini' in names

    def test_no_providers_without_keys(self):
        """Without any API keys, no providers available."""
        from ai_engine.modules.ai_provider import get_available_providers
        with patch('ai_engine.modules.ai_provider.GEMINI_API_KEY', None):
            result = get_available_providers()
            assert len(result) == 0


# ═══════════════════════════════════════════════════════════════════════════
# Django Signals — Notification creation on post_save
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSignalNotifyNewComment:
    def test_comment_creates_notification(self):
        """Creating a Comment fires signal → AdminNotification created."""
        from news.models import Article, Comment, AdminNotification

        article = Article.objects.create(
            title='Signal Test Article', slug='signal-test', content='<p>C</p>'
        )
        initial_count = AdminNotification.objects.count()

        Comment.objects.create(
            article=article,
            name='Test User',
            email='test@test.com',
            content='Great article!',
        )

        assert AdminNotification.objects.count() > initial_count
        latest = AdminNotification.objects.order_by('-created_at').first()
        assert latest.notification_type == 'comment'


@pytest.mark.django_db
class TestSignalNotifyNewSubscriber:
    def test_subscriber_creates_notification(self):
        """Creating a Subscriber → notification created."""
        from news.models import Subscriber, AdminNotification

        initial_count = AdminNotification.objects.count()
        Subscriber.objects.create(email='signal-test@example.com')

        assert AdminNotification.objects.count() > initial_count
        latest = AdminNotification.objects.order_by('-created_at').first()
        assert latest.notification_type == 'subscriber'


@pytest.mark.django_db
class TestSignalNotifyNewArticle:
    @patch('news.signals.threading.Thread')
    def test_article_creates_notification(self, mock_thread):
        """Creating an Article → notification created."""
        from news.models import Article, AdminNotification

        initial_count = AdminNotification.objects.filter(notification_type='article').count()
        Article.objects.create(
            title='Signal Notification Article', slug='signal-notif', content='<p>C</p>'
        )

        assert AdminNotification.objects.filter(notification_type='article').count() > initial_count


@pytest.mark.django_db
class TestSignalNotifyPendingArticle:
    def test_pending_article_creates_notification(self):
        """Creating a PendingArticle → 'video_pending' notification."""
        from news.models import PendingArticle, AdminNotification

        initial_count = AdminNotification.objects.filter(notification_type='video_pending').count()
        PendingArticle.objects.create(
            title='Pending Review Video',
            source_url='https://example.com/video',
        )

        assert AdminNotification.objects.filter(notification_type='video_pending').count() > initial_count


# ═══════════════════════════════════════════════════════════════════════════
# WebSocket Consumer — GenerationConsumer
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestGenerationConsumer:
    def test_connect_accepts(self):
        """Consumer accepts WebSocket connection."""
        import asyncio
        from news.consumers import GenerationConsumer

        consumer = GenerationConsumer()
        consumer.scope = {
            'type': 'websocket',
            'url_route': {'kwargs': {'task_id': 'test-123'}},
        }
        consumer.channel_name = 'test_channel'
        consumer.channel_layer = AsyncMock()
        consumer.accept = AsyncMock()

        asyncio.run(consumer.connect())

        consumer.accept.assert_called_once()
        consumer.channel_layer.group_add.assert_called_once_with(
            'generation_test-123', 'test_channel'
        )
        assert consumer.task_id == 'test-123'
        assert consumer.group_name == 'generation_test-123'

    def test_disconnect_leaves_group(self):
        """Consumer leaves group on disconnect."""
        import asyncio
        from news.consumers import GenerationConsumer

        consumer = GenerationConsumer()
        consumer.group_name = 'generation_test-456'
        consumer.channel_name = 'test_channel'
        consumer.channel_layer = AsyncMock()

        asyncio.run(consumer.disconnect(1000))

        consumer.channel_layer.group_discard.assert_called_once_with(
            'generation_test-456', 'test_channel'
        )

    def test_send_progress(self):
        """send_progress sends JSON to client."""
        import asyncio
        import json
        from news.consumers import GenerationConsumer

        consumer = GenerationConsumer()
        consumer.send = AsyncMock()

        event = {
            'step': 'generating',
            'progress': 50,
            'message': 'Generating content...',
        }

        asyncio.run(consumer.send_progress(event))

        consumer.send.assert_called_once()
        call_args = consumer.send.call_args
        text_data = call_args.kwargs.get('text_data') or call_args[1].get('text_data')
        sent_data = json.loads(text_data)
        assert sent_data['step'] == 'generating'
        assert sent_data['progress'] == 50
