"""
Tests for Next.js ISR cache revalidation on article changes.

Ensures that when articles are published, unpublished, deleted, or edited
the frontend cache is invalidated via trigger_nextjs_revalidation().
"""
import pytest
from unittest import mock
from django.test import TestCase


@pytest.mark.django_db
class TestNextJSRevalidationOnArticleSave(TestCase):
    """Verify trigger_nextjs_revalidation fires on publish-relevant saves."""

    def _create_article(self, **overrides):
        from news.models import Article
        defaults = {
            'title': 'Test Revalidation Article',
            'slug': 'test-revalidation-article',
            'content': '<p>Test</p>',
            'summary': 'Test summary',
            'is_published': False,
        }
        defaults.update(overrides)
        return Article.objects.create(**defaults)

    @mock.patch('news.cache_signals.trigger_nextjs_revalidation', create=True)
    def test_full_save_triggers_revalidation(self, mock_revalidate):
        """Admin list_editable toggle (full save) must trigger revalidation."""
        # Patch at the import point inside cache_signals
        with mock.patch(
            'news.api_views._shared.trigger_nextjs_revalidation'
        ) as mock_reval:
            article = self._create_article()
            mock_reval.reset_mock()

            # Simulate admin list_editable toggle: full save without update_fields
            article.is_published = True
            article.save()  # full save, update_fields=None

            assert mock_reval.called, (
                "Full Article.save() must trigger Next.js revalidation "
                "(covers admin list_editable toggles)"
            )
            # Verify paths include the article slug
            call_kwargs = mock_reval.call_args
            paths = call_kwargs.kwargs.get('paths') or call_kwargs[1].get('paths', [])
            assert f'/articles/{article.slug}' in paths

    def test_targeted_publish_triggers_revalidation(self):
        """save(update_fields=['is_published']) must trigger revalidation."""
        with mock.patch(
            'news.api_views._shared.trigger_nextjs_revalidation'
        ) as mock_reval:
            article = self._create_article()
            mock_reval.reset_mock()

            article.is_published = True
            article.save(update_fields=['is_published'])

            assert mock_reval.called, (
                "save(update_fields=['is_published']) must trigger revalidation"
            )

    def test_view_count_update_skips_revalidation(self):
        """save(update_fields=['views']) must NOT trigger revalidation."""
        with mock.patch(
            'news.api_views._shared.trigger_nextjs_revalidation'
        ) as mock_reval:
            article = self._create_article()
            mock_reval.reset_mock()

            article.views = 42
            article.save(update_fields=['views'])

            assert not mock_reval.called, (
                "View count updates must NOT trigger Vercel revalidation "
                "(would flood Vercel with unnecessary requests)"
            )

    def test_delete_triggers_revalidation(self):
        """Article.delete() must trigger revalidation."""
        with mock.patch(
            'news.api_views._shared.trigger_nextjs_revalidation'
        ) as mock_reval:
            article = self._create_article(is_published=True)
            mock_reval.reset_mock()

            article.delete()

            assert mock_reval.called, (
                "Article deletion must trigger revalidation "
                "(deleted article must disappear from homepage)"
            )

    def test_soft_delete_triggers_revalidation(self):
        """save(update_fields=['is_deleted']) must trigger revalidation."""
        with mock.patch(
            'news.api_views._shared.trigger_nextjs_revalidation'
        ) as mock_reval:
            article = self._create_article(is_published=True)
            mock_reval.reset_mock()

            article.is_deleted = True
            article.save(update_fields=['is_deleted', 'is_published'])

            assert mock_reval.called, (
                "Soft delete must trigger revalidation"
            )

    def test_title_change_triggers_revalidation(self):
        """Changing title (visible on cards) must trigger revalidation."""
        with mock.patch(
            'news.api_views._shared.trigger_nextjs_revalidation'
        ) as mock_reval:
            article = self._create_article(is_published=True)
            mock_reval.reset_mock()

            article.title = 'Updated Title'
            article.save(update_fields=['title'])

            assert mock_reval.called, (
                "Title changes must trigger revalidation (visible on cards)"
            )

    def test_metadata_update_skips_revalidation(self):
        """save(update_fields=['generation_metadata']) must NOT trigger."""
        with mock.patch(
            'news.api_views._shared.trigger_nextjs_revalidation'
        ) as mock_reval:
            article = self._create_article()
            mock_reval.reset_mock()

            article.generation_metadata = {'test': True}
            article.save(update_fields=['generation_metadata'])

            assert not mock_reval.called, (
                "Internal metadata updates must NOT trigger revalidation"
            )
