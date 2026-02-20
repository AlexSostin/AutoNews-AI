"""
Tests for news/scheduler.py

Covers:
- _run_rss_scan: RSS feed scanning logic with locks and settings
- _run_auto_publish: Auto-publication of pending articles
- _score_new_pending_articles: Quality scoring for unscored articles
- _check_overdue_tasks: Startup recovery after downtime
- start_scheduler: Entry point validation
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import timedelta

from django.utils import timezone


# ═══════════════════════════════════════════════════════════════════════════
# _run_rss_scan
# ═══════════════════════════════════════════════════════════════════════════

class TestRunRssScan:
    @patch('news.scheduler._schedule_rss_scan')
    @patch('news.scheduler._score_new_pending_articles')
    def test_disabled_reschedules_quickly(self, mock_score, mock_schedule):
        """When RSS is disabled, should reschedule with short interval."""
        from news.scheduler import _run_rss_scan, DISABLED_CHECK_INTERVAL

        with patch('news.models.AutomationSettings.load') as mock_load:
            settings = MagicMock()
            settings.rss_scan_enabled = False
            mock_load.return_value = settings

            _run_rss_scan()

            mock_schedule.assert_called_once_with(DISABLED_CHECK_INTERVAL)
            mock_score.assert_not_called()

    @patch('news.scheduler._schedule_rss_scan')
    @patch('news.scheduler._score_new_pending_articles')
    def test_lock_not_acquired_reschedules(self, mock_score, mock_schedule):
        """When lock can't be acquired, reschedule in 60s."""
        from news.scheduler import _run_rss_scan

        with patch('news.models.AutomationSettings.load') as mock_load, \
             patch('news.models.AutomationSettings.acquire_lock', return_value=False):
            settings = MagicMock()
            settings.rss_scan_enabled = True
            mock_load.return_value = settings

            _run_rss_scan()

            mock_schedule.assert_called_once_with(60)

    @pytest.mark.django_db
    @patch('news.scheduler._schedule_rss_scan')
    @patch('news.scheduler._score_new_pending_articles')
    def test_processes_enabled_feeds(self, mock_score, mock_schedule):
        """When enabled and lock acquired, should process feeds."""
        from news.scheduler import _run_rss_scan
        from news.models import AutomationSettings

        # Ensure settings exist
        AutomationSettings.objects.get_or_create(pk=1)

        with patch('news.models.AutomationSettings.load') as mock_load, \
             patch('news.models.AutomationSettings.acquire_lock', return_value=True), \
             patch('news.models.RSSFeed.objects') as mock_feed_qs, \
             patch('ai_engine.modules.rss_aggregator.RSSAggregator') as mock_agg_cls:

            settings = MagicMock()
            settings.rss_scan_enabled = True
            settings.rss_max_articles_per_scan = 10
            settings.rss_scan_interval_minutes = 30
            mock_load.return_value = settings

            # Empty feed queryset (use MagicMock, not list, since list.count is read-only)
            mock_feeds = MagicMock()
            mock_feeds.__iter__ = MagicMock(return_value=iter([]))
            mock_feeds.count.return_value = 0
            mock_feed_qs.filter.return_value = mock_feeds

            _run_rss_scan()

            mock_score.assert_called_once()
            mock_schedule.assert_called()


# ═══════════════════════════════════════════════════════════════════════════
# _run_auto_publish
# ═══════════════════════════════════════════════════════════════════════════

class TestRunAutoPublish:
    @patch('news.scheduler._schedule_auto_publish')
    def test_disabled_reschedules(self, mock_schedule):
        """When auto-publish is disabled, reschedule with short interval."""
        from news.scheduler import _run_auto_publish, DISABLED_CHECK_INTERVAL

        with patch('news.models.AutomationSettings.load') as mock_load:
            settings = MagicMock()
            settings.auto_publish_enabled = False
            mock_load.return_value = settings

            _run_auto_publish()

            mock_schedule.assert_called_once_with(DISABLED_CHECK_INTERVAL)

    @patch('news.scheduler._schedule_auto_publish')
    def test_enabled_calls_auto_publish_pending(self, mock_schedule):
        """When enabled, should call auto_publish_pending and reschedule."""
        from news.scheduler import _run_auto_publish, AUTO_PUBLISH_CHECK_INTERVAL

        with patch('news.models.AutomationSettings.load') as mock_load, \
             patch('ai_engine.modules.auto_publisher.auto_publish_pending', return_value=(2, "ok")) as mock_pub:

            settings = MagicMock()
            settings.auto_publish_enabled = True
            mock_load.return_value = settings

            _run_auto_publish()

            mock_pub.assert_called_once()
            mock_schedule.assert_called_once_with(AUTO_PUBLISH_CHECK_INTERVAL)

    @patch('news.scheduler._schedule_auto_publish')
    def test_error_still_reschedules(self, mock_schedule):
        """Even on error, should reschedule to avoid stopping."""
        from news.scheduler import _run_auto_publish, AUTO_PUBLISH_CHECK_INTERVAL

        with patch('news.models.AutomationSettings.load', side_effect=Exception("DB error")):
            _run_auto_publish()

            mock_schedule.assert_called_once_with(AUTO_PUBLISH_CHECK_INTERVAL)


# ═══════════════════════════════════════════════════════════════════════════
# _score_new_pending_articles
# ═══════════════════════════════════════════════════════════════════════════

class TestScoreNewPendingArticles:
    @patch('ai_engine.modules.quality_scorer.score_pending_article')
    def test_scores_unscored_articles(self, mock_scorer):
        """Should call score function for each unscored pending article."""
        from news.scheduler import _score_new_pending_articles

        pending1 = MagicMock()
        pending1.title = "Test Article 1"
        pending2 = MagicMock()
        pending2.title = "Test Article 2"

        with patch('news.models.PendingArticle.objects') as mock_qs:
            mock_qs.filter.return_value = [pending1, pending2]

            _score_new_pending_articles()

            assert mock_scorer.call_count == 2

    @patch('ai_engine.modules.quality_scorer.score_pending_article')
    def test_no_unscored_articles(self, mock_scorer):
        """Should do nothing when all articles are scored."""
        from news.scheduler import _score_new_pending_articles

        with patch('news.models.PendingArticle.objects') as mock_qs:
            mock_qs.filter.return_value = []

            _score_new_pending_articles()

            mock_scorer.assert_not_called()

    @patch('ai_engine.modules.quality_scorer.score_pending_article', side_effect=Exception("AI error"))
    def test_handles_scoring_errors_gracefully(self, mock_scorer):
        """Should continue scoring other articles if one fails."""
        from news.scheduler import _score_new_pending_articles

        pending1 = MagicMock()
        pending1.title = "Failing Article"
        pending2 = MagicMock()
        pending2.title = "OK Article"

        with patch('news.models.PendingArticle.objects') as mock_qs:
            mock_qs.filter.return_value = [pending1, pending2]

            # Should not raise
            _score_new_pending_articles()

            # Should have tried both
            assert mock_scorer.call_count == 2


# ═══════════════════════════════════════════════════════════════════════════
# _check_overdue_tasks
# ═══════════════════════════════════════════════════════════════════════════

class TestCheckOverdueTasks:
    @pytest.mark.django_db
    @patch('news.scheduler._run_rss_scan')
    @patch('news.scheduler._run_youtube_scan')
    @patch('news.scheduler._run_auto_publish')
    @patch('threading.Thread')
    def test_triggers_overdue_rss(self, mock_thread, mock_pub, mock_yt, mock_rss):
        """Should trigger RSS scan if overdue."""
        from news.scheduler import _check_overdue_tasks
        from news.models import AutomationSettings

        settings, _ = AutomationSettings.objects.get_or_create(pk=1)
        settings.rss_scan_enabled = True
        settings.rss_last_run = timezone.now() - timedelta(hours=24)  # Way overdue
        settings.rss_scan_interval_minutes = 30
        settings.youtube_scan_enabled = False
        settings.auto_publish_enabled = False
        settings.save()

        _check_overdue_tasks()

        # Thread should have been started for overdue RSS
        assert mock_thread.called

    @pytest.mark.django_db
    @patch('threading.Thread')
    def test_clears_stale_locks(self, mock_thread):
        """Should clear all locks on startup."""
        from news.scheduler import _check_overdue_tasks
        from news.models import AutomationSettings

        settings, _ = AutomationSettings.objects.get_or_create(pk=1)
        settings.rss_lock = True
        settings.youtube_lock = True
        settings.save()

        _check_overdue_tasks()

        settings.refresh_from_db()
        assert settings.rss_lock is False
        assert settings.youtube_lock is False

    @pytest.mark.django_db
    @patch('threading.Thread')
    def test_no_overdue_when_recently_run(self, mock_thread):
        """Should not trigger tasks that were recently run."""
        from news.scheduler import _check_overdue_tasks
        from news.models import AutomationSettings

        settings, _ = AutomationSettings.objects.get_or_create(pk=1)
        settings.rss_scan_enabled = True
        settings.rss_last_run = timezone.now() - timedelta(minutes=5)  # Just ran
        settings.rss_scan_interval_minutes = 30
        settings.youtube_scan_enabled = True
        settings.youtube_last_run = timezone.now() - timedelta(minutes=5)
        settings.youtube_scan_interval_minutes = 60
        settings.auto_publish_enabled = False
        settings.save()

        _check_overdue_tasks()

        # Thread should NOT have been called for non-overdue tasks
        # (auto_publish is disabled, so no thread spawning at all)
        mock_thread.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════
# Scheduling helpers — verify they use threading.Timer
# ═══════════════════════════════════════════════════════════════════════════

class TestScheduleHelpers:
    @patch('threading.Timer')
    def test_schedule_rss_scan(self, mock_timer):
        from news.scheduler import _schedule_rss_scan

        _schedule_rss_scan(300)

        mock_timer.assert_called_once()
        args = mock_timer.call_args
        assert args[0][0] == 300  # interval in seconds

    @patch('threading.Timer')
    def test_schedule_auto_publish(self, mock_timer):
        from news.scheduler import _schedule_auto_publish

        _schedule_auto_publish(600)

        mock_timer.assert_called_once()
        args = mock_timer.call_args
        assert args[0][0] == 600
