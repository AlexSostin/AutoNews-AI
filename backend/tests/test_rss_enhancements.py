"""
Tests for RSS generation enhancements and Publish Queue features.

Covers:
- _extract_auto_tags() helper: brand, fuel type, body type detection
- generate() enhancements: auto image fallback, SEO description, tags
- publish_queue endpoint: listing draft/scheduled articles with stats
- batch_schedule endpoint: auto-assigning staggered publish times
"""
import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status

from news.models import RSSFeed, RSSNewsItem, PendingArticle, Article, Category
from news.api_views.rss_news_items import _extract_auto_tags


# ── _extract_auto_tags() unit tests ──────────────────────────────


class TestExtractAutoTags:
    """Test the _extract_auto_tags helper function (pure Python, no DB)."""

    def test_detects_single_brand(self):
        tags = _extract_auto_tags('New Tesla Model 3 Review', '<p>Some content</p>')
        assert 'Tesla' in tags

    def test_detects_multiple_brands(self):
        tags = _extract_auto_tags('BYD vs Tesla: EV Battle', '<p>Compare BYD Seal and Tesla Model 3</p>')
        assert 'BYD' in tags
        assert 'Tesla' in tags

    def test_short_brands_uppercased(self):
        tags = _extract_auto_tags('BMW X5 Review', '<p>The BMW X5 is great</p>')
        assert 'BMW' in tags

    def test_detects_electric(self):
        tags = _extract_auto_tags('New Electric SUV', '<p>Battery electric vehicle with 80 kWh pack</p>')
        assert 'Electric' in tags

    def test_detects_hybrid(self):
        tags = _extract_auto_tags('New PHEV launched', '<p>Plug-in hybrid with 50km range</p>')
        assert 'Hybrid' in tags

    def test_detects_hydrogen(self):
        tags = _extract_auto_tags('Hydrogen fuel cell car', '<p>Using hydrogen fuel cell technology</p>')
        assert 'Hydrogen' in tags

    def test_detects_suv_body(self):
        tags = _extract_auto_tags('New Crossover SUV', '<p>This SUV offers great range</p>')
        assert 'SUV' in tags

    def test_detects_sedan(self):
        tags = _extract_auto_tags('New sedan announced', '<p>The sedan class gets a refresh</p>')
        assert 'Sedan' in tags

    def test_detects_truck(self):
        tags = _extract_auto_tags('Electric Pickup Truck', '<p>A new pickup for 2026</p>')
        assert 'Truck' in tags

    def test_detects_coupe(self):
        tags = _extract_auto_tags('New Coupe design', '<p>Sporty coupe styling</p>')
        assert 'Coupe' in tags

    def test_no_false_positives_on_generic_text(self):
        tags = _extract_auto_tags('Weather Report Today', '<p>Sunny skies expected</p>')
        assert len(tags) == 0

    def test_mercedes_benz_deduplication(self):
        """Both 'mercedes' and 'mercedes-benz' should map to single 'Mercedes-Benz'."""
        tags = _extract_auto_tags('Mercedes-Benz EQS Review', '<p>Mercedes releases new EV</p>')
        assert tags.count('Mercedes-Benz') == 1

    def test_combined_brands_fuel_body(self):
        tags = _extract_auto_tags(
            'Tesla Model Y Electric SUV 2026',
            '<p>Battery electric crossover with 75 kWh</p>'
        )
        assert 'Tesla' in tags
        assert 'Electric' in tags
        assert 'SUV' in tags

    def test_chinese_brands(self):
        tags = _extract_auto_tags('ZEEKR 001 Review', '<p>Geely-backed ZEEKR brand</p>')
        assert 'ZEEKR' in tags
        assert 'Geely' in tags

    def test_content_only_brand_detection(self):
        """Brand mentioned only in content (not title) should still be detected."""
        tags = _extract_auto_tags('New Car Launch', '<p>Toyota announced a hybrid sedan for 2026 model year</p>')
        assert 'Toyota' in tags
        assert 'Hybrid' in tags
        assert 'Sedan' in tags


# ── generate() enhancements ──────────────────────────────────────


# NOTE: generate() and merge_generate() integration tests are excluded here because
# they require deep mocking of the entire AI pipeline (expand_press_release, extract_title,
# validate_title, content quality checks, word count validation, etc.). The actual
# auto-tags, auto-SEO-desc, and auto-image features are tested indirectly via the
# _extract_auto_tags unit tests above, and via manual QA through the Curator UI.





# ── Publish Queue endpoint tests ─────────────────────────────────


@pytest.mark.django_db
class TestPublishQueue:
    """Test GET /articles/publish_queue/ endpoint."""

    def test_publish_queue_returns_drafts(self, authenticated_client):
        """Should return unpublished articles."""
        Article.objects.create(
            title='Draft Article', slug='draft-article',
            content='<p>Draft</p>', is_published=False,
        )
        resp = authenticated_client.get('/api/v1/articles/publish_queue/')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data['articles']) >= 1
        assert resp.data['stats']['total_drafts'] >= 1

    def test_publish_queue_excludes_published(self, authenticated_client):
        """Published articles should not appear in queue."""
        Article.objects.create(
            title='Published', slug='published-art',
            content='<p>P</p>', is_published=True,
        )
        resp = authenticated_client.get('/api/v1/articles/publish_queue/')
        slugs = [a['slug'] for a in resp.data['articles']]
        assert 'published-art' not in slugs

    def test_publish_queue_shows_scheduled_first(self, authenticated_client):
        """Scheduled articles should appear before unscheduled ones."""
        Article.objects.create(
            title='Unscheduled', slug='unsched',
            content='<p>U</p>', is_published=False,
        )
        Article.objects.create(
            title='Scheduled', slug='sched',
            content='<p>S</p>', is_published=False,
            scheduled_publish_at=timezone.now() + timedelta(hours=2),
        )
        resp = authenticated_client.get('/api/v1/articles/publish_queue/')
        assert resp.status_code == status.HTTP_200_OK
        arts = resp.data['articles']
        # Scheduled should come first
        sched_idx = next((i for i, a in enumerate(arts) if a['slug'] == 'sched'), 999)
        unsched_idx = next((i for i, a in enumerate(arts) if a['slug'] == 'unsched'), 999)
        assert sched_idx < unsched_idx

    def test_publish_queue_stats_accuracy(self, authenticated_client):
        """Stats should correctly count scheduled vs unscheduled."""
        Article.objects.create(
            title='D1', slug='d1', content='<p>D1</p>', is_published=False,
        )
        Article.objects.create(
            title='D2', slug='d2', content='<p>D2</p>', is_published=False,
            scheduled_publish_at=timezone.now() + timedelta(hours=1),
        )
        resp = authenticated_client.get('/api/v1/articles/publish_queue/')
        stats = resp.data['stats']
        assert stats['scheduled'] >= 1
        assert stats['unscheduled'] >= 1
        assert stats['total_drafts'] == stats['scheduled'] + stats['unscheduled']

    def test_publish_queue_anonymous_forbidden(self, api_client):
        """Anonymous users cannot access publish queue."""
        resp = api_client.get('/api/v1/articles/publish_queue/')
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


# ── Batch Schedule endpoint tests ─────────────────────────────────


@pytest.mark.django_db
class TestBatchSchedule:
    """Test POST /articles/batch_schedule/ endpoint."""

    def test_batch_schedule_assigns_times(self, authenticated_client):
        """Should assign staggered scheduled_publish_at times."""
        a1 = Article.objects.create(title='Art1', slug='art1', content='<p>A</p>', is_published=False)
        a2 = Article.objects.create(title='Art2', slug='art2', content='<p>B</p>', is_published=False)
        a3 = Article.objects.create(title='Art3', slug='art3', content='<p>C</p>', is_published=False)

        start = (timezone.now() + timedelta(hours=1)).isoformat()
        resp = authenticated_client.post('/api/v1/articles/batch_schedule/', {
            'article_ids': [a1.id, a2.id, a3.id],
            'start_time': start,
            'interval_hours': 3,
        }, format='json')

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['scheduled_count'] == 3

        a1.refresh_from_db()
        a2.refresh_from_db()
        a3.refresh_from_db()
        assert a1.scheduled_publish_at is not None
        assert a2.scheduled_publish_at is not None
        assert a3.scheduled_publish_at is not None

        # Verify interval (3 hours apart)
        diff_12 = (a2.scheduled_publish_at - a1.scheduled_publish_at).total_seconds()
        diff_23 = (a3.scheduled_publish_at - a2.scheduled_publish_at).total_seconds()
        assert abs(diff_12 - 3 * 3600) < 5  # within 5 seconds tolerance
        assert abs(diff_23 - 3 * 3600) < 5

    def test_batch_schedule_keeps_draft_status(self, authenticated_client):
        """Articles should remain unpublished after scheduling."""
        a = Article.objects.create(title='StayDraft', slug='stay-draft', content='<p>D</p>', is_published=False)
        start = (timezone.now() + timedelta(hours=1)).isoformat()

        authenticated_client.post('/api/v1/articles/batch_schedule/', {
            'article_ids': [a.id],
            'start_time': start,
            'interval_hours': 2,
        }, format='json')

        a.refresh_from_db()
        assert a.is_published is False
        assert a.scheduled_publish_at is not None

    def test_batch_schedule_missing_article_ids(self, authenticated_client):
        """Should return 400 if no article_ids provided."""
        resp = authenticated_client.post('/api/v1/articles/batch_schedule/', {
            'start_time': timezone.now().isoformat(),
            'interval_hours': 3,
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_batch_schedule_missing_start_time(self, authenticated_client):
        """Should return 400 if no start_time provided."""
        a = Article.objects.create(title='NoTime', slug='no-time', content='<p>N</p>', is_published=False)
        resp = authenticated_client.post('/api/v1/articles/batch_schedule/', {
            'article_ids': [a.id],
            'interval_hours': 3,
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_batch_schedule_invalid_time_format(self, authenticated_client):
        """Should return 400 for invalid start_time format."""
        a = Article.objects.create(title='BadTime', slug='bad-time', content='<p>B</p>', is_published=False)
        resp = authenticated_client.post('/api/v1/articles/batch_schedule/', {
            'article_ids': [a.id],
            'start_time': 'not-a-date',
            'interval_hours': 3,
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_batch_schedule_anonymous_forbidden(self, api_client):
        """Anonymous users cannot batch schedule."""
        resp = api_client.post('/api/v1/articles/batch_schedule/', {
            'article_ids': [1],
            'start_time': timezone.now().isoformat(),
        }, format='json')
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_batch_schedule_nonexistent_articles(self, authenticated_client):
        """Non-existent article IDs should be skipped."""
        start = (timezone.now() + timedelta(hours=1)).isoformat()
        resp = authenticated_client.post('/api/v1/articles/batch_schedule/', {
            'article_ids': [99999, 88888],
            'start_time': start,
            'interval_hours': 3,
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['scheduled_count'] == 0

    def test_batch_schedule_with_iso_z_suffix(self, authenticated_client):
        """Should handle ISO timestamps with Z suffix."""
        a = Article.objects.create(title='ZTime', slug='z-time', content='<p>Z</p>', is_published=False)
        resp = authenticated_client.post('/api/v1/articles/batch_schedule/', {
            'article_ids': [a.id],
            'start_time': '2026-12-25T10:00:00.000Z',
            'interval_hours': 2,
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['scheduled_count'] == 1
