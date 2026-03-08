"""
Tests for Telegram publishing and SocialPost audit trail.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone


@pytest.mark.django_db
class TestTelegramPublisher:
    """Tests for telegram_publisher.py module"""

    @pytest.fixture
    def article(self):
        from news.models import Article, Category
        cat = Category.objects.create(name='Test', slug='test')
        a = Article.objects.create(
            title='2026 Tesla Model S Review',
            content='<p>Great electric sedan with impressive range</p>',
            summary='The new Tesla Model S delivers 600hp and 400-mile range.',
            slug='2026-tesla-model-s-review',
            is_published=True,
        )
        a.categories.add(cat)
        return a

    def test_format_telegram_post(self, article):
        """format_telegram_post should create a proper HTML message"""
        from ai_engine.modules.telegram_publisher import format_telegram_post
        post = format_telegram_post(article)
        
        assert '2026 Tesla Model S Review' in post
        assert 'Tesla Model S delivers' in post
        assert 'Read full article' in post
        assert 'freshmotors.net' in post

    def test_format_telegram_post_escapes_html(self, article):
        """Special characters in title should be escaped"""
        from ai_engine.modules.telegram_publisher import format_telegram_post
        article.title = 'Test <b>HTML</b> & "Quotes"'
        article.save()
        post = format_telegram_post(article)
        
        assert '&lt;b&gt;' in post
        assert '&amp;' in post

    def test_format_telegram_post_truncates_summary(self, article):
        """Long summaries should be truncated to ~300 chars"""
        from ai_engine.modules.telegram_publisher import format_telegram_post
        article.summary = 'A' * 500
        article.save()
        post = format_telegram_post(article)
        
        assert 'A' * 297 + '...' in post

    @patch('ai_engine.modules.telegram_publisher._call_api')
    def test_send_test_message(self, mock_api):
        """send_test_message should call sendMessage API"""
        from ai_engine.modules.telegram_publisher import send_test_message
        mock_api.return_value = {'ok': True, 'result': {'message_id': 99}}
        
        with self.settings(TELEGRAM_BOT_TOKEN='test-token', TELEGRAM_CHANNEL_ID='@test'):
            result = send_test_message('Hello!')
        
        assert result['ok'] is True
        mock_api.assert_called_once()
        call_args = mock_api.call_args
        assert call_args[0][1] == 'sendMessage'
        assert call_args[0][2]['text'] == 'Hello!'

    @patch('ai_engine.modules.telegram_publisher._call_api')
    def test_send_to_channel_with_image(self, mock_api, article):
        """send_to_channel should try sendPhoto first, then text fallback"""
        from ai_engine.modules.telegram_publisher import send_to_channel
        mock_api.return_value = {'ok': True, 'result': {'message_id': 42}}
        article.image = 'https://res.cloudinary.com/test/image.jpg'
        article.save()
        
        with self.settings(TELEGRAM_BOT_TOKEN='test-token', TELEGRAM_CHANNEL_ID='@test', TELEGRAM_AUTO_POST=True):
            result = send_to_channel(article)
        
        assert result['ok'] is True
        assert mock_api.call_args[0][1] == 'sendPhoto'

    @patch('ai_engine.modules.telegram_publisher._call_api')
    def test_send_to_channel_disabled(self, mock_api, article):
        """send_to_channel should skip when auto_post is disabled and force=False"""
        from ai_engine.modules.telegram_publisher import send_to_channel
        
        with self.settings(TELEGRAM_BOT_TOKEN='test-token', TELEGRAM_CHANNEL_ID='@test', TELEGRAM_AUTO_POST=False):
            result = send_to_channel(article, force=False)
        
        assert result.get('reason') == 'auto_post_disabled'
        mock_api.assert_not_called()

    @patch('ai_engine.modules.telegram_publisher._call_api')
    def test_send_to_channel_force(self, mock_api, article):
        """send_to_channel with force=True should send even if auto_post disabled"""
        from ai_engine.modules.telegram_publisher import send_to_channel
        mock_api.return_value = {'ok': True, 'result': {'message_id': 55}}
        
        with self.settings(TELEGRAM_BOT_TOKEN='test-token', TELEGRAM_CHANNEL_ID='@test', TELEGRAM_AUTO_POST=False):
            result = send_to_channel(article, force=True)
        
        assert result['ok'] is True

    def test_get_config_missing_token(self):
        """_get_config should raise if token is missing"""
        from ai_engine.modules.telegram_publisher import _get_config
        
        with self.settings(TELEGRAM_BOT_TOKEN='', TELEGRAM_CHANNEL_ID='@test'):
            with pytest.raises(ValueError, match='TELEGRAM_BOT_TOKEN'):
                _get_config()

    # Helper to use Django test settings override
    from django.test import override_settings
    
    def settings(self, **kwargs):
        from django.test import override_settings
        return override_settings(**kwargs)


@pytest.mark.django_db
class TestSocialPostModel:
    """Tests for SocialPost model"""

    @pytest.fixture
    def article(self):
        from news.models import Article, Category
        cat = Category.objects.create(name='Test', slug='test-sp')
        a = Article.objects.create(
            title='Test Social Post Article',
            content='<p>Content</p>',
            slug='test-social-post',
            is_published=True,
        )
        a.categories.add(cat)
        return a

    def test_create_social_post_sent(self, article):
        """Can create a SocialPost with status sent"""
        from news.models import SocialPost
        post = SocialPost.objects.create(
            article=article,
            platform='telegram',
            status='sent',
            message_text='Test message',
            external_id='123',
            channel_id='@freshmotors_news',
            posted_at=timezone.now(),
        )
        assert post.id is not None
        assert str(post) == f'📱✅ {article.title[:40]}'

    def test_create_social_post_failed(self, article):
        """Can create a SocialPost with status failed"""
        from news.models import SocialPost
        post = SocialPost.objects.create(
            article=article,
            platform='telegram',
            status='failed',
            error_message='API timeout',
        )
        assert '❌' in str(post)

    def test_social_post_platforms(self, article):
        """All platforms should be valid"""
        from news.models import SocialPost
        for platform in ['telegram', 'twitter', 'reddit']:
            post = SocialPost.objects.create(
                article=article, platform=platform, status='pending',
            )
            assert post.platform == platform


@pytest.mark.django_db
class TestAutomationSettingsTelegram:
    """Tests for telegram fields in AutomationSettings"""

    def test_default_telegram_settings(self):
        """AutomationSettings should have correct telegram defaults"""
        from news.models import AutomationSettings
        settings = AutomationSettings.load()
        assert settings.telegram_enabled is False
        assert settings.telegram_channel_id == '@freshmotors_news'
        assert settings.telegram_post_with_image is True
        assert settings.telegram_today_count == 0

    def test_telegram_counter_reset(self):
        """Daily counter reset should include telegram_today_count"""
        from news.models import AutomationSettings
        settings = AutomationSettings.load()
        settings.telegram_today_count = 5
        settings.counters_reset_date = None  # Force reset
        settings.save()
        
        settings.reset_daily_counters()
        settings.refresh_from_db()
        assert settings.telegram_today_count == 0

    def test_telegram_in_str_repr(self):
        """__str__ should show Telegram when enabled"""
        from news.models import AutomationSettings
        settings = AutomationSettings.load()
        settings.telegram_enabled = True
        settings.save()
        assert 'Telegram' in str(settings)
