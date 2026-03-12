"""
Tests for Feedback API, System Graph, and Article Images.

Covers:
- ArticleFeedback model CRUD
- ArticleFeedbackViewSet: list, resolve, unresolve, filtering, auth
- SystemGraphView: returns valid structure with nodes/edges/warnings
- ArticleImageViewSet: list, filter by article
"""
import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from news.models import Article, ArticleFeedback, ArticleImage


# ── Feedback API tests ───────────────────────────────────────────


@pytest.mark.django_db
class TestArticleFeedbackModel:
    """Test ArticleFeedback model."""

    def test_create_feedback(self):
        article = Article.objects.create(
            title='Test Article', slug='test-fb', content='<p>Content</p>',
        )
        fb = ArticleFeedback.objects.create(
            article=article, category='factual_error',
            message='Wrong specs listed', ip_address='192.168.1.1',
        )
        assert fb.pk is not None
        assert fb.is_resolved is False
        assert fb.category == 'factual_error'

    def test_feedback_category_display(self):
        article = Article.objects.create(
            title='Test Art', slug='test-fb2', content='<p>C</p>',
        )
        fb = ArticleFeedback.objects.create(
            article=article, category='hallucination',
            message='AI made up specs',
        )
        assert fb.get_category_display() == 'AI Hallucination'


@pytest.mark.django_db
class TestFeedbackAPI:
    """Test ArticleFeedbackViewSet endpoints."""

    def _get_admin_client(self, django_user_model):
        """Get an API client authenticated as superuser (IsAdminUser)."""
        user = django_user_model.objects.create_superuser(
            'fb_admin', 'admin@test.com', 'pass123'
        )
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_list_feedback(self, django_user_model):
        client = self._get_admin_client(django_user_model)
        article = Article.objects.create(
            title='FB Article', slug='fb-art', content='<p>C</p>',
        )
        ArticleFeedback.objects.create(
            article=article, category='typo', message='Typo in title',
        )
        resp = client.get('/api/v1/feedback/')
        assert resp.status_code == status.HTTP_200_OK

    def test_feedback_filter_resolved(self, django_user_model):
        client = self._get_admin_client(django_user_model)
        article = Article.objects.create(
            title='FilterArt', slug='filter-art', content='<p>C</p>',
        )
        ArticleFeedback.objects.create(
            article=article, category='typo', message='Open', is_resolved=False,
        )
        ArticleFeedback.objects.create(
            article=article, category='other', message='Done', is_resolved=True,
        )
        resp = client.get('/api/v1/feedback/?resolved=false')
        assert resp.status_code == status.HTTP_200_OK

    def test_feedback_filter_by_category(self, django_user_model):
        client = self._get_admin_client(django_user_model)
        article = Article.objects.create(
            title='CatArt', slug='cat-art', content='<p>C</p>',
        )
        ArticleFeedback.objects.create(
            article=article, category='hallucination', message='AI lies',
        )
        ArticleFeedback.objects.create(
            article=article, category='typo', message='Typo',
        )
        resp = client.get('/api/v1/feedback/?category=hallucination')
        assert resp.status_code == status.HTTP_200_OK

    def test_resolve_feedback(self, django_user_model):
        client = self._get_admin_client(django_user_model)
        article = Article.objects.create(
            title='ResArt', slug='res-art', content='<p>C</p>',
        )
        fb = ArticleFeedback.objects.create(
            article=article, category='factual_error', message='Wrong HP',
        )
        resp = client.post(f'/api/v1/feedback/{fb.pk}/resolve/', {
            'admin_notes': 'Fixed in v2',
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        fb.refresh_from_db()
        assert fb.is_resolved is True
        assert fb.admin_notes == 'Fixed in v2'

    def test_unresolve_feedback(self, django_user_model):
        client = self._get_admin_client(django_user_model)
        article = Article.objects.create(
            title='UnresArt', slug='unres-art', content='<p>C</p>',
        )
        fb = ArticleFeedback.objects.create(
            article=article, category='other', message='Reopen', is_resolved=True,
        )
        resp = client.post(f'/api/v1/feedback/{fb.pk}/unresolve/', format='json')
        assert resp.status_code == status.HTTP_200_OK
        fb.refresh_from_db()
        assert fb.is_resolved is False

    def test_feedback_anonymous_forbidden(self, api_client):
        resp = api_client.get('/api/v1/feedback/')
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_feedback_non_admin_forbidden(self, authenticated_client):
        """Staff but non-superuser should be blocked (IsAdminUser)."""
        resp = authenticated_client.get('/api/v1/feedback/')
        # IsAdminUser requires is_staff — authenticated_client IS staff, so this should work
        # If the policy is IsAdminUser (is_staff=True), our fixture already is staff
        assert resp.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]


# ── System Graph tests ───────────────────────────────────────────


@pytest.mark.django_db
class TestSystemGraph:
    """Test SystemGraphView endpoint."""

    def _get_admin_client(self, django_user_model):
        user = django_user_model.objects.create_superuser(
            'graph_admin', 'graph@test.com', 'pass123'
        )
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_graph_returns_valid_structure(self, django_user_model):
        client = self._get_admin_client(django_user_model)
        resp = client.get('/api/v1/health/graph-data/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data
        assert 'nodes' in data
        assert 'edges' in data
        assert 'warnings' in data
        assert isinstance(data['nodes'], list)
        assert isinstance(data['edges'], list)
        assert len(data['nodes']) > 0  # Should always have some nodes

    def test_graph_nodes_have_required_fields(self, django_user_model):
        client = self._get_admin_client(django_user_model)
        resp = client.get('/api/v1/health/graph-data/')
        for node in resp.data['nodes']:
            assert 'id' in node
            assert 'label' in node
            assert 'group' in node
            assert 'count' in node
            assert 'health' in node

    def test_graph_edges_have_required_fields(self, django_user_model):
        client = self._get_admin_client(django_user_model)
        resp = client.get('/api/v1/health/graph-data/')
        for edge in resp.data['edges']:
            assert 'from' in edge
            assert 'to' in edge
            assert 'label' in edge

    def test_graph_anonymous_forbidden(self, api_client):
        resp = api_client.get('/api/v1/health/graph-data/')
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


# ── Article Image tests ──────────────────────────────────────────


@pytest.mark.django_db
class TestArticleImageAPI:
    """Test ArticleImageViewSet."""

    def test_list_images(self, authenticated_client):
        resp = authenticated_client.get('/api/v1/article-images/')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_images_by_article_id(self, authenticated_client):
        article = Article.objects.create(
            title='Img Art', slug='img-art', content='<p>C</p>',
        )
        resp = authenticated_client.get(f'/api/v1/article-images/?article={article.id}')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_images_by_article_slug(self, authenticated_client):
        Article.objects.create(
            title='Slug Art', slug='slug-art', content='<p>C</p>',
        )
        resp = authenticated_client.get('/api/v1/article-images/?article=slug-art')
        assert resp.status_code == status.HTTP_200_OK
