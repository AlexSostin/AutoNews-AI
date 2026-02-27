import pytest
from unittest.mock import patch, MagicMock
from news.services.gsc_service import GSCService
from news.models import GSCReport, ArticleGSCStats, Article
from datetime import datetime, timedelta


@pytest.fixture
def gsc_service():
    """Create a GSCService with mocked credentials and API client."""
    with patch.object(GSCService, '_get_credentials', return_value=MagicMock()):
        with patch('news.services.gsc_service.build') as mock_build:
            mock_gsc_client = MagicMock()
            mock_build.return_value = mock_gsc_client
            service = GSCService()
            yield service, mock_gsc_client


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
