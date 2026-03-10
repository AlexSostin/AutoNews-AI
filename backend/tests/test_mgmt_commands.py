"""
Tests for high-priority management commands previously at 0% coverage:
- score_competitor_pairs (ML learning loop)
- scan_rss_feeds (core RSS ingestion)
- send_telegram_post (social publishing)
- cleanup_tags (data maintenance)
- sync_gsc_data (Google Search Console)
"""
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock
from django.core.management import call_command
from django.core.management.base import CommandError


# ═══════════════════════════════════════════════════════════════════════════
# score_competitor_pairs — ML feedback loop
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestScoreCompetitorPairs:
    def test_no_pairs_to_score(self):
        """Empty DB → 'Found 0' message, no errors."""
        out = StringIO()
        call_command('score_competitor_pairs', stdout=out)
        output = out.getvalue()
        assert 'Found 0' in output

    def test_scores_eligible_pair(self):
        """Pair with article older than 48h gets scored."""
        from news.models import Article, CompetitorPairLog
        from django.utils import timezone
        from datetime import timedelta

        article = Article.objects.create(
            title='BMW X5 2025', slug='score-bmw-x5', content='<p>C</p>',
            engagement_score=8.5,
        )
        # Fake created_at to be 72h ago
        CompetitorPairLog.objects.create(
            article=article,
            subject_make='BMW', subject_model='X5',
            competitor_make='Audi', competitor_model='Q7',
        )
        CompetitorPairLog.objects.filter(article=article).update(
            created_at=timezone.now() - timedelta(hours=72)
        )

        out = StringIO()
        call_command('score_competitor_pairs', stdout=out)
        output = out.getvalue()
        assert 'Scored 1' in output

        pair = CompetitorPairLog.objects.get(article=article)
        assert pair.engagement_score_at_log == 8.5

    def test_dry_run_does_not_save(self):
        """--dry-run prints but doesn't update DB."""
        from news.models import Article, CompetitorPairLog
        from django.utils import timezone
        from datetime import timedelta

        article = Article.objects.create(
            title='Dry Run Car', slug='dry-run-cr', content='<p>C</p>',
            engagement_score=7.0,
        )
        CompetitorPairLog.objects.create(
            article=article,
            subject_make='Tesla', subject_model='Model 3',
            competitor_make='BYD', competitor_model='Seal',
        )
        CompetitorPairLog.objects.filter(article=article).update(
            created_at=timezone.now() - timedelta(hours=72)
        )

        out = StringIO()
        call_command('score_competitor_pairs', '--dry-run', stdout=out)
        output = out.getvalue()
        assert 'DRY-RUN' in output

        pair = CompetitorPairLog.objects.get(article=article)
        assert pair.engagement_score_at_log is None  # Not saved

    def test_scores_with_zero_engagement(self):
        """Pairs with engagement_score=0 are still scored (only None is skipped)."""
        from news.models import Article, CompetitorPairLog
        from django.utils import timezone
        from datetime import timedelta

        article = Article.objects.create(
            title='Zero Score Car', slug='zero-score-cr', content='<p>C</p>',
            engagement_score=0.0,
        )
        CompetitorPairLog.objects.create(
            article=article,
            subject_make='Rivian', subject_model='R1T',
            competitor_make='Ford', competitor_model='F-150',
        )
        CompetitorPairLog.objects.filter(article=article).update(
            created_at=timezone.now() - timedelta(hours=72)
        )

        out = StringIO()
        call_command('score_competitor_pairs', stdout=out)
        output = out.getvalue()
        assert 'Scored 1' in output

        pair = CompetitorPairLog.objects.get(article=article)
        assert pair.engagement_score_at_log == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# scan_rss_feeds — core RSS ingestion
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestScanRssFeeds:
    def test_no_args_shows_error(self):
        """Running without --all or --feed-id → error message."""
        out = StringIO()
        call_command('scan_rss_feeds', stdout=out)
        output = out.getvalue()
        assert 'specify' in output.lower() or '--all' in output

    def test_feed_id_not_found(self):
        """--feed-id with nonexistent ID → error."""
        out = StringIO()
        call_command('scan_rss_feeds', '--feed-id', '99999', stdout=out)
        assert 'not found' in out.getvalue().lower()

    def test_no_enabled_feeds(self):
        """--all but no enabled feeds → warning."""
        out = StringIO()
        call_command('scan_rss_feeds', '--all', stdout=out)
        assert 'no' in out.getvalue().lower()

    @patch('news.management.commands.scan_rss_feeds.RSSAggregator')
    def test_dry_run_with_feed(self, mock_agg_cls):
        """--dry-run fetches feed but doesn't create articles."""
        from news.models import RSSFeed
        feed = RSSFeed.objects.create(
            name='Test RSS', feed_url='https://example.com/rss',
            is_enabled=True,
        )

        mock_agg = MagicMock()
        mock_agg_cls.return_value = mock_agg
        mock_feed_data = MagicMock()
        mock_feed_data.entries = [
            {'title': 'Test Entry 1'},
            {'title': 'Test Entry 2'},
        ]
        mock_agg.fetch_feed.return_value = mock_feed_data

        out = StringIO()
        call_command('scan_rss_feeds', '--feed-id', str(feed.id), '--dry-run', stdout=out)
        output = out.getvalue()
        assert 'DRY RUN' in output
        mock_agg.process_feed.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════
# send_telegram_post — social publishing
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSendTelegramPost:
    def test_no_args_shows_error(self):
        """No args → error message."""
        out = StringIO()
        call_command('send_telegram_post', stdout=out)
        assert 'specify' in out.getvalue().lower() or '--article-id' in out.getvalue()

    def test_article_not_found(self):
        """--article-id with invalid ID → error."""
        out = StringIO()
        call_command('send_telegram_post', '--article-id', '99999', stdout=out)
        assert 'not found' in out.getvalue().lower()

    @patch('ai_engine.modules.telegram_publisher.send_test_message')
    def test_test_mode(self, mock_send_test):
        """--test sends test message to channel."""
        mock_send_test.return_value = {'ok': True, 'result': {'message_id': 42}}
        out = StringIO()
        call_command('send_telegram_post', '--test', stdout=out)
        output = out.getvalue()
        assert 'Test message sent' in output or 'msg_id=42' in output
        mock_send_test.assert_called_once()

    @patch('ai_engine.modules.telegram_publisher.format_telegram_post')
    def test_dry_run(self, mock_format):
        """--dry-run previews post without sending."""
        from news.models import Article
        article = Article.objects.create(
            title='Telegram Test', slug='tg-test', content='<p>C</p>',
            is_published=True,
        )
        mock_format.return_value = '<b>Telegram Test</b>\n\nContent here'

        out = StringIO()
        call_command('send_telegram_post', '--article-id', str(article.id), '--dry-run', stdout=out)
        output = out.getvalue()
        assert 'Dry-run' in output or 'dry-run' in output.lower()


# ═══════════════════════════════════════════════════════════════════════════
# sync_gsc_data — GSC management command wrapper
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestSyncGscDataCommand:
    @patch('news.management.commands.sync_gsc_data.GSCService')
    def test_success(self, mock_svc_cls):
        """Successful sync → success message."""
        mock_svc = MagicMock()
        mock_svc.sync_data.return_value = True
        mock_svc_cls.return_value = mock_svc

        out = StringIO()
        call_command('sync_gsc_data', stdout=out)
        assert 'success' in out.getvalue().lower()

    @patch('news.management.commands.sync_gsc_data.GSCService')
    def test_failure(self, mock_svc_cls):
        """Failed sync → error message."""
        mock_svc = MagicMock()
        mock_svc.sync_data.return_value = False
        mock_svc_cls.return_value = mock_svc

        out = StringIO()
        call_command('sync_gsc_data', stdout=out)
        assert 'failed' in out.getvalue().lower()

    @patch('news.management.commands.sync_gsc_data.GSCService')
    def test_custom_days(self, mock_svc_cls):
        """--days parameter is passed through."""
        mock_svc = MagicMock()
        mock_svc.sync_data.return_value = True
        mock_svc_cls.return_value = mock_svc

        out = StringIO()
        call_command('sync_gsc_data', '--days', '14', stdout=out)
        mock_svc.sync_data.assert_called_once_with(days=14)


# ═══════════════════════════════════════════════════════════════════════════
# cleanup_tags — data maintenance (dry-run only to avoid mutation)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCleanupTags:
    def test_dry_run_no_crash(self):
        """--dry-run completes without errors on empty DB."""
        out = StringIO()
        call_command('cleanup_tags', '--dry-run', stdout=out)
        output = out.getvalue()
        assert 'Phase' in output or 'Summary' in output or 'cleanup' in output.lower()

    def test_all_phases_dry_run(self):
        """--dry-run runs all phases without errors."""
        out = StringIO()
        call_command('cleanup_tags', '--dry-run', stdout=out)
        output = out.getvalue()
        assert len(output) > 0  # Some output produced
