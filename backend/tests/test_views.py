"""
Group 5: Django view tests — robots.txt, API root, and basic URL responses.
Tests only the URLs actually registered in Django (not Next.js frontend routes).
"""
import pytest
from django.test import Client
from news.models import Article


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def article(db):
    return Article.objects.create(
        title='View Test Article', slug='view-test-article',
        content='<p>Great BMW car review content here.</p>',
        is_published=True
    )


@pytest.mark.django_db
class TestRobotsTxt:
    """Tests for robots.txt endpoint"""

    def test_robots_txt_returns_text(self, client):
        resp = client.get('/robots.txt')
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'text/plain'
        content = resp.content.decode()
        assert 'User-agent' in content

    def test_robots_contains_sitemap(self, client):
        resp = client.get('/robots.txt')
        content = resp.content.decode()
        assert 'Sitemap' in content

    def test_robots_disallows_admin(self, client):
        resp = client.get('/robots.txt')
        content = resp.content.decode()
        assert 'Disallow: /admin/' in content

    def test_robots_allows_articles(self, client):
        resp = client.get('/robots.txt')
        content = resp.content.decode()
        assert 'Allow: /articles/' in content


@pytest.mark.django_db
class TestArticleDetailView:
    """Tests for the legacy article detail view"""

    def test_article_not_found(self, client):
        resp = client.get('/article/nonexistent-slug/')
        assert resp.status_code == 404

    def test_unpublished_article_404(self, client):
        Article.objects.create(
            title='Draft', slug='draft-view-article',
            content='<p>Draft</p>', is_published=False
        )
        resp = client.get('/article/draft-view-article/')
        assert resp.status_code == 404


@pytest.mark.django_db
class TestAPIRoot:
    """Tests for the API root endpoint"""

    def test_api_root_ok(self, client):
        resp = client.get('/')
        assert resp.status_code == 200

    def test_api_v1_with_ua(self, client):
        """API v1 root with proper User-Agent returns 200"""
        resp = client.get('/api/v1/', HTTP_USER_AGENT='Mozilla/5.0 TestBot')
        assert resp.status_code == 200
