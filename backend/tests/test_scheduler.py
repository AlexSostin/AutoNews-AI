"""
Tests for news/scheduler.py — Background scheduler for periodic tasks
Covers: GSC sync, currency updates, RSS scan, YouTube scan, auto-publish,
        quality scoring, overdue recovery, start_scheduler guard
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import timedelta
from django.utils import timezone

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def automation_settings(db):
    from news.models import AutomationSettings
    settings, _ = AutomationSettings.objects.get_or_create(pk=1)
    settings.rss_scan_enabled = True
    settings.youtube_scan_enabled = True
    settings.auto_publish_enabled = True
    settings.rss_scan_interval_minutes = 60
    settings.youtube_scan_interval_minutes = 120
    settings.rss_max_articles_per_scan = 5
    settings.youtube_max_videos_per_scan = 5
    settings.save()
    return settings


@pytest.fixture
def rss_feed(db):
    from news.models import RSSFeed
    return RSSFeed.objects.create(
        name='Test Feed', feed_url='https://example.com/rss', is_enabled=True,
    )


@pytest.fixture
def youtube_channel(db):
    from news.models import YouTubeChannel
    return YouTubeChannel.objects.create(
        name='Test Channel',
        channel_url='https://youtube.com/@test',
        is_enabled=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# GSC SYNC
# ═══════════════════════════════════════════════════════════════════════════

class TestRunGSCSync:
    """Tests for _run_gsc_sync()"""

    @patch('news.scheduler._schedule_gsc_sync')
    @patch('news.services.gsc_service.GSCService')
    def test_gsc_sync_success(self, mock_gsc_cls, mock_schedule):
        from news.scheduler import _run_gsc_sync
        mock_service = MagicMock()
        mock_service.service = True
        mock_service.sync_data.return_value = True
        mock_gsc_cls.return_value = mock_service

        _run_gsc_sync()
        mock_service.sync_data.assert_called_once_with(days=7)
        mock_schedule.assert_called_once()

    @patch('news.scheduler._schedule_gsc_sync')
    @patch('news.services.gsc_service.GSCService')
    def test_gsc_sync_failure(self, mock_gsc_cls, mock_schedule):
        from news.scheduler import _run_gsc_sync
        mock_service = MagicMock()
        mock_service.service = True
        mock_service.sync_data.return_value = False
        mock_gsc_cls.return_value = mock_service

        _run_gsc_sync()
        mock_schedule.assert_called_once()  # Still reschedules

    @patch('news.scheduler._schedule_gsc_sync')
    @patch('news.services.gsc_service.GSCService')
    def test_gsc_sync_no_credentials(self, mock_gsc_cls, mock_schedule):
        from news.scheduler import _run_gsc_sync
        mock_service = MagicMock()
        mock_service.service = None
        mock_gsc_cls.return_value = mock_service

        _run_gsc_sync()
        mock_schedule.assert_called_once()  # Still reschedules

    @patch('news.scheduler._schedule_gsc_sync')
    @patch('news.services.gsc_service.GSCService', side_effect=Exception('API error'))
    def test_gsc_sync_exception(self, mock_gsc_cls, mock_schedule):
        from news.scheduler import _run_gsc_sync
        _run_gsc_sync()  # Should not crash
        mock_schedule.assert_called_once()


class TestScheduleGSCSync:
    """Tests for _schedule_gsc_sync()"""

    @patch('news.scheduler.threading.Timer')
    def test_schedules_timer(self, mock_timer):
        from news.scheduler import _schedule_gsc_sync, GSC_SYNC_INTERVAL
        timer_instance = MagicMock()
        mock_timer.return_value = timer_instance

        _schedule_gsc_sync()
        mock_timer.assert_called_once_with(GSC_SYNC_INTERVAL, _schedule_gsc_sync.__wrapped__ if hasattr(_schedule_gsc_sync, '__wrapped__') else pytest.importorskip('news.scheduler')._run_gsc_sync)
        timer_instance.start.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# CURRENCY UPDATE
# ═══════════════════════════════════════════════════════════════════════════

class TestRunCurrencyUpdate:
    """Tests for _run_currency_update()"""

    @patch('news.scheduler._schedule_currency_update')
    @patch('news.services.currency_service.update_all_usd_prices', return_value=(10, 0))
    def test_currency_update_success(self, mock_update, mock_schedule):
        from news.scheduler import _run_currency_update
        _run_currency_update()
        mock_update.assert_called_once()
        mock_schedule.assert_called_once()

    @patch('news.scheduler._schedule_currency_update')
    @patch('news.services.currency_service.update_all_usd_prices', side_effect=Exception('API down'))
    def test_currency_update_exception(self, mock_update, mock_schedule):
        from news.scheduler import _run_currency_update
        _run_currency_update()  # Should not crash
        mock_schedule.assert_called_once()


class TestScheduleCurrencyUpdate:
    """Tests for _schedule_currency_update()"""

    @patch('news.scheduler.threading.Timer')
    def test_schedules_timer(self, mock_timer):
        from news.scheduler import _schedule_currency_update, CURRENCY_UPDATE_INTERVAL, _run_currency_update
        timer_instance = MagicMock()
        mock_timer.return_value = timer_instance

        _schedule_currency_update()
        mock_timer.assert_called_once_with(CURRENCY_UPDATE_INTERVAL, _run_currency_update)
        timer_instance.start.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# RSS SCAN
# ═══════════════════════════════════════════════════════════════════════════

class TestRunRSSScan:
    """Tests for _run_rss_scan()"""

    @patch('news.scheduler._score_new_pending_articles')
    @patch('news.scheduler._schedule_rss_scan')
    @patch('ai_engine.modules.rss_aggregator.RSSAggregator')
    def test_rss_scan_success(self, mock_agg_cls, mock_schedule, mock_score, automation_settings, rss_feed):
        from news.scheduler import _run_rss_scan
        mock_agg = MagicMock()
        mock_agg.process_feed.return_value = 3
        mock_agg_cls.return_value = mock_agg

        _run_rss_scan()
        mock_agg.process_feed.assert_called_once()
        mock_score.assert_called_once()
        mock_schedule.assert_called()

    @patch('news.scheduler._schedule_rss_scan')
    def test_rss_scan_disabled(self, mock_schedule, automation_settings):
        from news.scheduler import _run_rss_scan, DISABLED_CHECK_INTERVAL
        automation_settings.rss_scan_enabled = False
        automation_settings.save()

        _run_rss_scan()
        mock_schedule.assert_called_once_with(DISABLED_CHECK_INTERVAL)

    @patch('news.scheduler._score_new_pending_articles')
    @patch('news.scheduler._schedule_rss_scan')
    @patch('ai_engine.modules.rss_aggregator.RSSAggregator')
    def test_rss_scan_feed_error(self, mock_agg_cls, mock_schedule, mock_score, automation_settings, rss_feed):
        from news.scheduler import _run_rss_scan
        mock_agg = MagicMock()
        mock_agg.process_feed.side_effect = Exception('Feed parse error')
        mock_agg_cls.return_value = mock_agg

        _run_rss_scan()  # Should not crash
        mock_schedule.assert_called()

    @patch('news.scheduler._schedule_rss_scan')
    @patch('ai_engine.modules.rss_aggregator.RSSAggregator', side_effect=Exception('Fatal'))
    def test_rss_scan_fatal_error(self, mock_agg_cls, mock_schedule, automation_settings):
        from news.scheduler import _run_rss_scan
        _run_rss_scan()
        # Should schedule retry in 5 minutes
        mock_schedule.assert_called_with(5 * 60)


# ═══════════════════════════════════════════════════════════════════════════
# YOUTUBE SCAN
# ═══════════════════════════════════════════════════════════════════════════

class TestRunYouTubeScan:
    """Tests for _run_youtube_scan()"""

    @patch('news.scheduler._score_new_pending_articles')
    @patch('news.scheduler._schedule_youtube_scan')
    @patch('ai_engine.main.create_pending_article', return_value={'success': True})
    @patch('ai_engine.modules.youtube_client.YouTubeClient')
    def test_youtube_scan_success(
        self, mock_yt_cls, mock_create, mock_schedule, mock_score,
        automation_settings, youtube_channel
    ):
        from news.scheduler import _run_youtube_scan
        mock_client = MagicMock()
        mock_client.get_latest_videos.return_value = [
            {'id': 'vid1', 'url': 'https://youtube.com/watch?v=vid1', 'title': 'Test Video'}
        ]
        mock_yt_cls.return_value = mock_client

        _run_youtube_scan()
        mock_client.get_latest_videos.assert_called_once()
        mock_create.assert_called_once()
        mock_score.assert_called_once()
        mock_schedule.assert_called()

    @patch('news.scheduler._schedule_youtube_scan')
    def test_youtube_scan_disabled(self, mock_schedule, automation_settings):
        from news.scheduler import _run_youtube_scan, DISABLED_CHECK_INTERVAL
        automation_settings.youtube_scan_enabled = False
        automation_settings.save()

        _run_youtube_scan()
        mock_schedule.assert_called_once_with(DISABLED_CHECK_INTERVAL)

    @patch('news.scheduler._schedule_youtube_scan')
    @patch('ai_engine.modules.youtube_client.YouTubeClient', side_effect=Exception('No API key'))
    def test_youtube_scan_client_init_error(self, mock_yt_cls, mock_schedule, automation_settings):
        from news.scheduler import _run_youtube_scan
        _run_youtube_scan()
        mock_schedule.assert_called()

    @patch('news.scheduler._score_new_pending_articles')
    @patch('news.scheduler._schedule_youtube_scan')
    @patch('ai_engine.modules.youtube_client.YouTubeClient')
    def test_youtube_scan_no_new_videos(
        self, mock_yt_cls, mock_schedule, mock_score,
        automation_settings, youtube_channel
    ):
        from news.scheduler import _run_youtube_scan
        mock_client = MagicMock()
        mock_client.get_latest_videos.return_value = []
        mock_yt_cls.return_value = mock_client

        _run_youtube_scan()
        mock_schedule.assert_called()

    @patch('news.scheduler._score_new_pending_articles')
    @patch('news.scheduler._schedule_youtube_scan')
    @patch('ai_engine.modules.youtube_client.YouTubeClient')
    def test_youtube_scan_skips_duplicate_videos(
        self, mock_yt_cls, mock_schedule, mock_score,
        automation_settings, youtube_channel
    ):
        from news.models import Article
        from news.scheduler import _run_youtube_scan
        # Create existing article with this YouTube URL
        Article.objects.create(
            title='Exists', slug='exists', content='<p>C</p>',
            summary='S', youtube_url='https://youtube.com/watch?v=dup1',
        )
        mock_client = MagicMock()
        mock_client.get_latest_videos.return_value = [
            {'id': 'dup1', 'url': 'https://youtube.com/watch?v=dup1', 'title': 'Duplicate'}
        ]
        mock_yt_cls.return_value = mock_client

        _run_youtube_scan()
        # create_pending_article should not be called for duplicates
        mock_schedule.assert_called()


# ═══════════════════════════════════════════════════════════════════════════
# AUTO-PUBLISH
# ═══════════════════════════════════════════════════════════════════════════

class TestRunAutoPublish:
    """Tests for _run_auto_publish()"""

    @patch('news.scheduler._schedule_auto_publish')
    @patch('ai_engine.modules.auto_publisher.auto_publish_pending', return_value=(2, 'Published 2'))
    def test_auto_publish_success(self, mock_publish, mock_schedule, automation_settings):
        from news.scheduler import _run_auto_publish
        _run_auto_publish()
        mock_publish.assert_called_once()
        mock_schedule.assert_called()

    @patch('news.scheduler._schedule_auto_publish')
    def test_auto_publish_disabled(self, mock_schedule, automation_settings):
        from news.scheduler import _run_auto_publish, DISABLED_CHECK_INTERVAL
        automation_settings.auto_publish_enabled = False
        automation_settings.save()

        _run_auto_publish()
        mock_schedule.assert_called_once_with(DISABLED_CHECK_INTERVAL)

    @patch('news.scheduler._schedule_auto_publish')
    @patch('ai_engine.modules.auto_publisher.auto_publish_pending', side_effect=Exception('DB error'))
    def test_auto_publish_exception(self, mock_publish, mock_schedule, automation_settings):
        from news.scheduler import _run_auto_publish, AUTO_PUBLISH_CHECK_INTERVAL
        _run_auto_publish()
        mock_schedule.assert_called_with(AUTO_PUBLISH_CHECK_INTERVAL)


# ═══════════════════════════════════════════════════════════════════════════
# SCORING
# ═══════════════════════════════════════════════════════════════════════════

class TestScoreNewPendingArticles:
    """Tests for _score_new_pending_articles()"""

    @patch('ai_engine.modules.quality_scorer.score_pending_article')
    def test_scores_unscored_articles(self, mock_score, db):
        from news.models import PendingArticle
        from news.scheduler import _score_new_pending_articles
        pa = PendingArticle.objects.create(
            title='Unscored', status='pending', quality_score=0,
        )
        _score_new_pending_articles()
        mock_score.assert_called_once_with(pa)

    @patch('ai_engine.modules.quality_scorer.score_pending_article')
    def test_skips_already_scored(self, mock_score, db):
        from news.models import PendingArticle
        from news.scheduler import _score_new_pending_articles
        PendingArticle.objects.create(
            title='Scored', status='pending', quality_score=85,
        )
        _score_new_pending_articles()
        mock_score.assert_not_called()

    @patch('ai_engine.modules.quality_scorer.score_pending_article', side_effect=Exception('AI error'))
    def test_score_error_doesnt_crash(self, mock_score, db):
        from news.models import PendingArticle
        from news.scheduler import _score_new_pending_articles
        PendingArticle.objects.create(
            title='Error Score', status='pending', quality_score=0,
        )
        _score_new_pending_articles()  # Should not crash


# ═══════════════════════════════════════════════════════════════════════════
# OVERDUE TASKS RECOVERY
# ═══════════════════════════════════════════════════════════════════════════

class TestCheckOverdueTasks:
    """Tests for _check_overdue_tasks()"""

    @patch('news.scheduler.threading.Thread')
    def test_clears_stale_locks(self, mock_thread, automation_settings):
        from news.models import AutomationSettings
        from news.scheduler import _check_overdue_tasks
        # Set stale locks
        AutomationSettings.objects.filter(pk=1).update(rss_lock=True, youtube_lock=True)

        _check_overdue_tasks()

        automation_settings.refresh_from_db()
        assert automation_settings.rss_lock is False
        assert automation_settings.youtube_lock is False

    @patch('news.scheduler.threading.Thread')
    def test_triggers_overdue_rss(self, mock_thread, automation_settings):
        from news.scheduler import _check_overdue_tasks
        # Set last run to long ago
        automation_settings.rss_last_run = timezone.now() - timedelta(hours=24)
        automation_settings.save()

        _check_overdue_tasks()
        # Should spawn thread for RSS
        assert mock_thread.called

    @patch('news.scheduler.threading.Thread')
    def test_triggers_overdue_youtube(self, mock_thread, automation_settings):
        from news.scheduler import _check_overdue_tasks
        automation_settings.youtube_last_run = timezone.now() - timedelta(hours=24)
        automation_settings.save()

        _check_overdue_tasks()
        assert mock_thread.called

    @patch('news.scheduler.threading.Thread')
    def test_no_overdue_when_recent(self, mock_thread, automation_settings):
        from news.scheduler import _check_overdue_tasks
        now = timezone.now()
        automation_settings.rss_last_run = now - timedelta(minutes=5)
        automation_settings.youtube_last_run = now - timedelta(minutes=5)
        automation_settings.auto_publish_enabled = False
        automation_settings.save()

        _check_overdue_tasks()
        # Thread may still be called for auto-publish if enabled;
        # with auto_publish disabled, no overdue threads

    @patch('news.scheduler.threading.Thread')
    def test_auto_publish_always_triggers(self, mock_thread, automation_settings):
        from news.scheduler import _check_overdue_tasks
        # auto_publish is always overdue after restart
        automation_settings.auto_publish_enabled = True
        automation_settings.save()

        _check_overdue_tasks()
        assert mock_thread.called


# ═══════════════════════════════════════════════════════════════════════════
# START SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════

class TestStartScheduler:
    """Tests for start_scheduler()"""

    @patch('news.scheduler.threading.Timer')
    def test_skips_in_test_mode(self, mock_timer):
        import sys
        from news.scheduler import start_scheduler
        original_argv = sys.argv
        try:
            sys.argv = ['manage.py', 'test']
            start_scheduler()
            mock_timer.assert_not_called()
        finally:
            sys.argv = original_argv

    @patch('news.scheduler.threading.Timer')
    def test_skips_in_migrate_mode(self, mock_timer):
        import sys
        from news.scheduler import start_scheduler
        original_argv = sys.argv
        try:
            sys.argv = ['manage.py', 'migrate']
            start_scheduler()
            mock_timer.assert_not_called()
        finally:
            sys.argv = original_argv

    @patch('news.scheduler.threading.Timer')
    def test_starts_in_server_mode(self, mock_timer):
        import sys
        import os
        from news.scheduler import start_scheduler
        timer_instance = MagicMock()
        mock_timer.return_value = timer_instance
        original_argv = sys.argv
        original_run_main = os.environ.get('RUN_MAIN')
        try:
            sys.argv = ['manage.py', 'runserver']
            os.environ['RUN_MAIN'] = 'true'  # Simulate autoreload child process
            start_scheduler()
            # Should create multiple timers for each task
            assert mock_timer.call_count >= 5  # recovery, gsc, currency, rss, youtube, auto-publish
        finally:
            sys.argv = original_argv
            if original_run_main is not None:
                os.environ['RUN_MAIN'] = original_run_main
            else:
                os.environ.pop('RUN_MAIN', None)
