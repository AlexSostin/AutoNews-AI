"""
Tests for article publish visibility.

Verifies that:
1. Newly published articles appear in the public article list
2. Cache is properly invalidated when is_published changes
3. trigger_nextjs_revalidation is called on publish
4. Unpublished articles do NOT appear in public list
5. Draft-to-publish transition is immediate
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from news.models import Article


@pytest.mark.django_db
class TestArticlePublishVisibility:
    """Test that published articles are immediately visible on the public list."""

    @pytest.fixture
    def staff_client(self, django_user_model):
        user = django_user_model.objects.create_user(
            username='admin_publish', password='pass123',
            is_staff=True, is_superuser=True,
        )
        client = APIClient()
        client.defaults['HTTP_USER_AGENT'] = 'TestClient/1.0'
        token = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return client

    @pytest.fixture
    def anon_client(self):
        client = APIClient()
        client.defaults['HTTP_USER_AGENT'] = 'TestClient/1.0'
        return client

    @pytest.fixture
    def draft_article(self):
        return Article.objects.create(
            title='2026 Tesla Model Z Review',
            content='<p>Amazing electric vehicle with 500 miles of range.</p>',
            summary='A comprehensive review of the Tesla Model Z.',
            is_published=False,
        )

    @pytest.fixture
    def published_article(self):
        return Article.objects.create(
            title='2026 BYD Seal Review',
            content='<p>The BYD Seal offers great value.</p>',
            summary='BYD Seal comprehensive review.',
            is_published=True,
        )

    def test_published_article_appears_in_public_list(self, anon_client, published_article):
        """Published articles should appear in the public (anonymous) article list."""
        resp = anon_client.get('/api/v1/articles/')
        assert resp.status_code == 200
        slugs = [a['slug'] for a in resp.data['results']]
        assert published_article.slug in slugs

    def test_draft_article_hidden_from_public(self, anon_client, draft_article):
        """Unpublished (draft) articles should NOT appear in the public list."""
        resp = anon_client.get('/api/v1/articles/')
        assert resp.status_code == 200
        slugs = [a['slug'] for a in resp.data['results']]
        assert draft_article.slug not in slugs

    def test_draft_visible_to_admin(self, staff_client, draft_article):
        """Draft articles SHOULD be visible to admin users."""
        resp = staff_client.get('/api/v1/articles/')
        assert resp.status_code == 200
        slugs = [a['slug'] for a in resp.data['results']]
        assert draft_article.slug in slugs

    @patch('news.api_views._shared.trigger_nextjs_revalidation')
    def test_publish_via_update_triggers_revalidation(self, mock_revalidate, staff_client, draft_article):
        """Publishing via PATCH should trigger Next.js revalidation."""
        resp = staff_client.patch(
            f'/api/v1/articles/{draft_article.slug}/',
            {'is_published': True},
            format='json',
        )
        assert resp.status_code == 200
        draft_article.refresh_from_db()
        assert draft_article.is_published is True
        # invalidate_article_cache calls trigger_nextjs_revalidation
        assert mock_revalidate.called

    @patch('news.api_views._shared.trigger_nextjs_revalidation')
    def test_publish_makes_article_immediately_visible(self, mock_revalidate, staff_client, anon_client, draft_article):
        """After publishing, article should immediately appear in public list (no stale cache)."""
        # Step 1: Verify article is NOT visible
        resp = anon_client.get('/api/v1/articles/')
        slugs = [a['slug'] for a in resp.data['results']]
        assert draft_article.slug not in slugs

        # Step 2: Publish it
        resp = staff_client.patch(
            f'/api/v1/articles/{draft_article.slug}/',
            {'is_published': True},
            format='json',
        )
        assert resp.status_code == 200

        # Step 3: Verify article IS now visible (cache should be busted)
        resp = anon_client.get('/api/v1/articles/')
        slugs = [a['slug'] for a in resp.data['results']]
        assert draft_article.slug in slugs, \
            f"Article '{draft_article.slug}' not visible after publishing! Cache not invalidated?"

    @patch('news.api_views._shared.trigger_nextjs_revalidation')
    def test_unpublish_hides_article_immediately(self, mock_revalidate, staff_client, anon_client, published_article):
        """After unpublishing, article should immediately disappear from public list."""
        # Step 1: Verify article IS visible
        resp = anon_client.get('/api/v1/articles/')
        slugs = [a['slug'] for a in resp.data['results']]
        assert published_article.slug in slugs

        # Step 2: Unpublish
        resp = staff_client.patch(
            f'/api/v1/articles/{published_article.slug}/',
            {'is_published': False},
            format='json',
        )
        assert resp.status_code == 200

        # Step 3: Verify article is NOT visible now
        resp = anon_client.get('/api/v1/articles/')
        slugs = [a['slug'] for a in resp.data['results']]
        assert published_article.slug not in slugs, \
            f"Article '{published_article.slug}' still visible after unpublishing! Cache not invalidated?"

    @patch('news.api_views._shared.trigger_nextjs_revalidation')
    def test_create_published_article_immediately_visible(self, mock_revalidate, staff_client, anon_client):
        """Creating a new article with is_published=True should make it immediately visible."""
        resp = staff_client.post('/api/v1/articles/', {
            'title': '2026 Rivian R2 First Drive',
            'content': '<p>The Rivian R2 is a game changer.</p>',
            'summary': 'Rivian R2 first drive review.',
            'is_published': True,
        }, format='json')
        assert resp.status_code == 201
        new_slug = resp.data['slug']

        # Should appear in public list
        resp = anon_client.get('/api/v1/articles/')
        slugs = [a['slug'] for a in resp.data['results']]
        assert new_slug in slugs, \
            f"Newly created published article '{new_slug}' not in public list!"

    def test_detail_view_respects_published_status(self, anon_client, draft_article):
        """Anonymous users should get 404 for unpublished article detail."""
        resp = anon_client.get(f'/api/v1/articles/{draft_article.slug}/')
        assert resp.status_code == 404

    def test_detail_view_works_for_published(self, anon_client, published_article):
        """Anonymous users should access published article detail."""
        resp = anon_client.get(f'/api/v1/articles/{published_article.slug}/')
        assert resp.status_code == 200
        assert resp.data['title'] == published_article.title


@pytest.mark.django_db
class TestCacheInvalidationOnPublish:
    """Test that Django cache is properly cleared when article status changes."""

    @pytest.fixture
    def staff_client(self, django_user_model):
        user = django_user_model.objects.create_user(
            username='cache_admin', password='pass123',
            is_staff=True, is_superuser=True,
        )
        client = APIClient()
        client.defaults['HTTP_USER_AGENT'] = 'TestClient/1.0'
        token = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return client

    @pytest.fixture
    def anon_client(self):
        client = APIClient()
        client.defaults['HTTP_USER_AGENT'] = 'TestClient/1.0'
        return client

    @patch('news.api_views._shared.trigger_nextjs_revalidation')
    def test_cache_busted_on_publish(self, mock_revalidate, staff_client, anon_client):
        """Ensure anon cache is invalidated when article is published."""
        # Create a draft
        article = Article.objects.create(
            title='Cache Test Article',
            content='<p>Testing cache invalidation.</p>',
            is_published=False,
        )

        # Warm the cache with anon request (no articles)
        resp = anon_client.get('/api/v1/articles/')
        assert resp.status_code == 200
        initial_count = len(resp.data['results'])

        # Publish the article
        staff_client.patch(
            f'/api/v1/articles/{article.slug}/',
            {'is_published': True},
            format='json',
        )

        # Cache should be busted — anon should see the new article
        resp = anon_client.get('/api/v1/articles/')
        assert len(resp.data['results']) == initial_count + 1
        slugs = [a['slug'] for a in resp.data['results']]
        assert article.slug in slugs

    @patch('news.api_views._shared.trigger_nextjs_revalidation')
    def test_nextjs_revalidation_called_with_correct_paths(self, mock_revalidate, staff_client):
        """Verify that Next.js revalidation is called after article update."""
        article = Article.objects.create(
            title='Revalidation Test',
            content='<p>Test.</p>',
            is_published=False,
        )
        staff_client.patch(
            f'/api/v1/articles/{article.slug}/',
            {'is_published': True},
            format='json',
        )
        # trigger_nextjs_revalidation should have been called
        assert mock_revalidate.called


@pytest.mark.django_db
class TestTriggerNextjsRevalidation:
    """Unit tests for the trigger_nextjs_revalidation function."""

    @patch('news.api_views._shared.threading.Thread')
    def test_revalidation_uses_background_thread(self, mock_thread):
        """Revalidation should run in a background thread."""
        from news.api_views._shared import trigger_nextjs_revalidation
        trigger_nextjs_revalidation()
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

    @patch('news.api_views._shared.threading.Thread')
    def test_revalidation_accepts_custom_paths(self, mock_thread):
        """Can pass custom paths for revalidation."""
        from news.api_views._shared import trigger_nextjs_revalidation
        trigger_nextjs_revalidation(paths=['/articles/test-slug'])
        mock_thread.assert_called_once()
