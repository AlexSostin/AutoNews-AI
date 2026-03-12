"""
Expanded GSC service tests — previously had only 1 test.
Now covers error paths, no-credentials, empty responses, slug matching.
"""
import pytest
from unittest.mock import patch, MagicMock
from news.services.gsc_service import GSCService
from news.models import GSCReport, ArticleGSCStats, Article


@pytest.fixture
def gsc_service():
    """Create a GSCService with mocked credentials and API client."""
    with patch.object(GSCService, '_get_credentials', return_value=MagicMock()):
        with patch('news.services.gsc_service.build') as mock_build:
            mock_gsc_client = MagicMock()
            mock_build.return_value = mock_gsc_client
            service = GSCService()
            yield service, mock_gsc_client


# ═══════════════════════════════════════════════════════════════════════════
# Existing test (kept for regression)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_sync_data_success(gsc_service):
    service, mock_gsc_client = gsc_service

    # Mock Site Analytics
    mock_site_query = MagicMock()
    mock_site_query.execute.return_value = {
        'rows': [{'keys': ['2026-02-25'], 'clicks': 1500, 'impressions': 50000, 'ctr': 0.03, 'position': 12.5}]
    }

    # Mock Article Analytics
    mock_article_query = MagicMock()
    mock_article_query.execute.return_value = {
        'rows': [
            {'keys': ['https://freshmotors.net/articles/test-article', '2026-02-25'], 'clicks': 100, 'impressions': 1000, 'ctr': 0.1, 'position': 5.2}
        ]
    }

    # Configure mock chain: service.searchanalytics().query() returns our mocks in sequence
    mock_gsc_client.searchanalytics().query.side_effect = [mock_site_query, mock_article_query]

    # Create matching article
    article = Article.objects.create(title='Test Article', slug='test-article')

    result = service.sync_data(days=1)

    assert result is True
    assert GSCReport.objects.filter(date='2026-02-25').exists()
    assert ArticleGSCStats.objects.filter(article=article, date='2026-02-25').exists()


# ═══════════════════════════════════════════════════════════════════════════
# NEW: No-credentials path
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_sync_data_no_credentials():
    """If credentials are None, sync_data returns False."""
    with patch.object(GSCService, '_get_credentials', return_value=None):
        with patch('news.services.gsc_service.build') as mock_build:
            service = GSCService()
            result = service.sync_data(days=1)
            assert result is False


# ═══════════════════════════════════════════════════════════════════════════
# NEW: Empty response handling
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db(transaction=True)
def test_sync_data_empty_rows(gsc_service):
    """If API returns empty rows, sync still returns True without errors."""
    # Clean slate — transaction=True doesn't auto-rollback other tests' data
    GSCReport.objects.all().delete()

    service, mock_gsc_client = gsc_service

    mock_empty_query = MagicMock()
    mock_empty_query.execute.return_value = {'rows': []}

    mock_gsc_client.searchanalytics().query.side_effect = [mock_empty_query, mock_empty_query]

    result = service.sync_data(days=1)
    assert result is True
    assert GSCReport.objects.count() == 0


# ═══════════════════════════════════════════════════════════════════════════
# NEW: fetch_site_overview / fetch_article_performance error handling
# ═══════════════════════════════════════════════════════════════════════════

def test_fetch_site_overview_no_service():
    """Without credentials, fetch_site_overview returns None."""
    with patch.object(GSCService, '_get_credentials', return_value=None):
        with patch('news.services.gsc_service.build'):
            service = GSCService()
            service.service = None  # No service
            from datetime import datetime
            result = service.fetch_site_overview(datetime(2026, 1, 1), datetime(2026, 1, 7))
            assert result is None


def test_fetch_article_performance_no_service():
    """Without credentials, fetch_article_performance returns None."""
    with patch.object(GSCService, '_get_credentials', return_value=None):
        with patch('news.services.gsc_service.build'):
            service = GSCService()
            service.service = None
            from datetime import datetime
            result = service.fetch_article_performance(datetime(2026, 1, 1), datetime(2026, 1, 7))
            assert result is None


def test_fetch_site_overview_api_error(gsc_service):
    """API error returns empty list, not crash."""
    service, mock_gsc_client = gsc_service
    mock_gsc_client.searchanalytics().query.side_effect = Exception("API Error 500")

    from datetime import datetime
    result = service.fetch_site_overview(datetime(2026, 1, 1), datetime(2026, 1, 7))
    assert result == []


# ═══════════════════════════════════════════════════════════════════════════
# NEW: Slug matching — article not found (DoesNotExist)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_sync_data_unknown_slug(gsc_service):
    """Articles with unknown slugs are gracefully skipped."""
    service, mock_gsc_client = gsc_service

    mock_site_query = MagicMock()
    mock_site_query.execute.return_value = {'rows': []}

    mock_article_query = MagicMock()
    mock_article_query.execute.return_value = {
        'rows': [
            {'keys': ['https://freshmotors.net/articles/nonexistent-slug', '2026-02-25'],
             'clicks': 50, 'impressions': 500, 'ctr': 0.1, 'position': 8.0}
        ]
    }

    mock_gsc_client.searchanalytics().query.side_effect = [mock_site_query, mock_article_query]

    result = service.sync_data(days=1)
    assert result is True
    assert ArticleGSCStats.objects.count() == 0  # Nothing created
