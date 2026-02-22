"""
Max coverage: ai_engine/modules/publisher.py — targeting 73 uncovered lines.
Goal: push from 60% → 90%+
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from news.models import Article, Category, Tag, CarSpecification

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════
# extract_summary
# ═══════════════════════════════════════════════════════════════════

class TestExtractSummary:

    def test_extract_first_paragraph(self):
        from ai_engine.modules.publisher import extract_summary
        html = '<h2>Title</h2><p>This is the first paragraph content.</p><p>Second.</p>'
        result = extract_summary(html)
        assert 'first paragraph' in result

    def test_no_paragraph_fallback(self):
        from ai_engine.modules.publisher import extract_summary
        result = extract_summary('<div>No paragraph tags here</div>')
        assert 'AI-generated' in result


# ═══════════════════════════════════════════════════════════════════
# generate_seo_title
# ═══════════════════════════════════════════════════════════════════

class TestGenerateSeoTitle:

    def test_short_title_unchanged(self):
        from ai_engine.modules.publisher import generate_seo_title
        assert generate_seo_title('2026 BYD Seal Review') == '2026 BYD Seal Review'

    def test_long_title_with_year_make_model(self):
        """L276-277: Long title with year+make+model pattern → extracted."""
        from ai_engine.modules.publisher import generate_seo_title
        long_title = '2026 BYD Seal AWD Electric Sedan — Comprehensive Review and Specifications Analysis'
        result = generate_seo_title(long_title)
        assert 'BYD' in result
        assert 'Seal' in result
        assert len(result) <= 60

    def test_long_title_no_pattern(self):
        from ai_engine.modules.publisher import generate_seo_title
        long_title = 'A Very Long Article Title Without Any Year Make Model Pattern That Exceeds Sixty Characters Easily'
        result = generate_seo_title(long_title)
        assert result.endswith('...')
        assert len(result) <= 60


# ═══════════════════════════════════════════════════════════════════
# _add_spec_based_tags
# ═══════════════════════════════════════════════════════════════════

class TestAddSpecBasedTags:

    def test_adds_make_tag(self):
        """L296-299: Make tag exists in DB → added to article."""
        from ai_engine.modules.publisher import _add_spec_based_tags
        Tag.objects.create(name='BYD', slug='byd')

        article = Article.objects.create(
            title='Test Article', slug='test-spec-tags', content='<p>C</p>'
        )
        _add_spec_based_tags(article, {'make': 'BYD', 'model': 'Not specified'})
        assert article.tags.filter(slug='byd').exists()

    def test_adds_model_tag(self):
        """L308-311: Model tag exists in DB → added to article."""
        from ai_engine.modules.publisher import _add_spec_based_tags
        Tag.objects.create(name='Seal', slug='seal')

        article = Article.objects.create(
            title='Test Model Tag', slug='test-model-tag', content='<p>C</p>'
        )
        _add_spec_based_tags(article, {'make': 'BYD', 'model': 'Seal'})
        assert article.tags.filter(slug='seal').exists()

    def test_make_not_in_db_skipped(self):
        """L300-301: Make tag doesn't exist → DoesNotExist caught, skipped."""
        from ai_engine.modules.publisher import _add_spec_based_tags
        article = Article.objects.create(
            title='Test No Make', slug='test-no-make', content='<p>C</p>'
        )
        _add_spec_based_tags(article, {'make': 'UnknownBrand', 'model': 'X99'})
        assert article.tags.count() == 0

    def test_not_specified_skipped(self):
        from ai_engine.modules.publisher import _add_spec_based_tags
        article = Article.objects.create(
            title='Test Not Specified', slug='test-not-spec', content='<p>C</p>'
        )
        _add_spec_based_tags(article, {'make': 'Not specified', 'model': 'Not specified'})
        assert article.tags.count() == 0

    def test_tag_already_on_article(self):
        """L297+L309: Tag already on article → not duplicated."""
        from ai_engine.modules.publisher import _add_spec_based_tags
        tag = Tag.objects.create(name='BYD', slug='byd')
        article = Article.objects.create(
            title='Test Already Tagged', slug='test-already', content='<p>C</p>'
        )
        article.tags.add(tag)
        _add_spec_based_tags(article, {'make': 'BYD', 'model': 'Not specified'})
        assert article.tags.filter(slug='byd').count() == 1


# ═══════════════════════════════════════════════════════════════════
# publish_article — image processing branches
# ═══════════════════════════════════════════════════════════════════

class TestPublishArticleImages:

    def test_cloudinary_image_assigned(self):
        """L94-96, L132-139: Cloudinary URL → assigned directly without download."""
        from ai_engine.modules.publisher import publish_article
        try:
            article = publish_article(
                title='Cloudinary Image Test',
                content='<p>Content here.</p>',
                image_paths=[
                    'https://res.cloudinary.com/test/v1/image1.jpg',
                    'https://res.cloudinary.com/test/v1/image2.jpg',
                    'https://res.cloudinary.com/test/v1/image3.jpg',
                ],
            )
        except OSError:
            pytest.skip('Cloudinary storage not available in test')
        # Use .name or str() to avoid Cloudinary storage OSError on read
        refreshed = Article.objects.get(pk=article.pk)
        assert str(refreshed.image) == 'https://res.cloudinary.com/test/v1/image1.jpg'
        assert str(refreshed.image_2) == 'https://res.cloudinary.com/test/v1/image2.jpg'
        assert str(refreshed.image_3) == 'https://res.cloudinary.com/test/v1/image3.jpg'

    @patch('requests.get')
    def test_http_image_downloaded(self, mock_get):
        """L99-106: Non-Cloudinary URL → download and attach."""
        from ai_engine.modules.publisher import publish_article
        mock_get.return_value = MagicMock(status_code=200, content=b'\xff\xd8\xff' + b'\x00' * 100)
        try:
            article = publish_article(
                title='HTTP Image Test',
                content='<p>Content.</p>',
                image_paths=['https://images.pexels.com/photo.jpg'],
            )
            assert article.id is not None
        except OSError:
            pytest.skip('Cloudinary storage not available')

    @patch('requests.get')
    def test_http_image_download_fails(self, mock_get):
        """L105-106: HTTP download returns non-200 → skipped."""
        from ai_engine.modules.publisher import publish_article
        mock_get.return_value = MagicMock(status_code=404)
        article = publish_article(
            title='HTTP Image Fail',
            content='<p>Content.</p>',
            image_paths=['https://images.pexels.com/404.jpg'],
        )
        assert article.id is not None

    def test_none_image_path_skipped(self):
        """L84-86: None in image_paths → skipped."""
        from ai_engine.modules.publisher import publish_article
        try:
            article = publish_article(
                title='None Image Test',
                content='<p>Content.</p>',
                image_paths=[None, 'https://res.cloudinary.com/test/img.jpg'],
            )
        except OSError:
            pytest.skip('Cloudinary storage not available in test')
        assert article.id is not None
        refreshed = Article.objects.get(pk=article.pk)
        assert str(refreshed.image_2) == 'https://res.cloudinary.com/test/img.jpg'

    def test_nonexistent_local_file(self):
        """L128-129: Local file doesn't exist → warning printed."""
        from ai_engine.modules.publisher import publish_article
        article = publish_article(
            title='Missing Local Image',
            content='<p>Content.</p>',
            image_paths=['/nonexistent/path/image.jpg'],
        )
        assert article.id is not None

    def test_media_relative_path(self):
        """L109-119: /media/ path → resolves to absolute, checks existence."""
        from ai_engine.modules.publisher import publish_article
        article = publish_article(
            title='Media Path Test',
            content='<p>Content.</p>',
            image_paths=['/media/screenshots/nonexistent.jpg'],
        )
        assert article.id is not None

    def test_image_processing_exception(self):
        """L149-150: Exception during image processing → caught."""
        from ai_engine.modules.publisher import publish_article
        with patch('requests.get', side_effect=Exception('Network error')):
            article = publish_article(
                title='Image Exception Test',
                content='<p>Content.</p>',
                image_paths=['https://example.com/broken.jpg'],
            )
        assert article.id is not None


# ═══════════════════════════════════════════════════════════════════
# publish_article — tags, specs, summary, Google indexing
# ═══════════════════════════════════════════════════════════════════

class TestPublishArticleMetadata:

    def test_summary_trimmed(self):
        """L53-54: Summary > 300 chars → trimmed."""
        from ai_engine.modules.publisher import publish_article
        long_summary = 'A' * 400
        article = publish_article(
            title='Summary Trim Test',
            content='<p>Content.</p>',
            summary=long_summary,
        )
        assert len(article.summary) <= 300
        assert article.summary.endswith('...')

    def test_specs_saved(self):
        """L191-209: Specs dict → CarSpecification created."""
        from ai_engine.modules.publisher import publish_article
        specs = {
            'make': 'BYD', 'model': 'Seal', 'trim': 'AWD',
            'engine': 'Electric', 'horsepower': 530, 'drivetrain': 'AWD',
            'price': '$35,000',
        }
        article = publish_article(
            title='Specs Save Test',
            content='<p>Content.</p>',
            specs=specs,
        )
        assert CarSpecification.objects.filter(article=article).exists()
        cs = CarSpecification.objects.get(article=article)
        assert cs.make == 'BYD'
        assert str(cs.horsepower) == '530'

    def test_specs_save_exception(self):
        """L210-211: Specs save fails → caught, article still returned."""
        from ai_engine.modules.publisher import publish_article
        # Bad specs that might cause DB error
        specs = {'make': 'Test', 'model': 'X'}
        with patch.object(CarSpecification.objects, 'update_or_create', side_effect=Exception('DB error')):
            article = publish_article(
                title='Specs Error Test',
                content='<p>Content.</p>',
                specs=specs,
            )
        assert article.id is not None

    def test_tags_added(self):
        from ai_engine.modules.publisher import publish_article
        article = publish_article(
            title='Tags Test',
            content='<p>Content.</p>',
            tag_names=['BYD', 'Electric', 'Sedan'],
        )
        assert article.tags.count() == 3

    @patch('news.management.commands.submit_to_google.submit_url_to_google')
    def test_google_indexing_success(self, mock_submit):
        """L225-237: Google indexing enabled + success."""
        from ai_engine.modules.publisher import publish_article
        mock_submit.return_value = {'success': True}

        with patch('news.models.AutomationSettings.load') as mock_load:
            mock_settings = MagicMock(google_indexing_enabled=True)
            mock_load.return_value = mock_settings
            article = publish_article(
                title='Indexing Success Test',
                content='<p>Content.</p>',
                is_published=True,
            )
        assert article.id is not None

    @patch('news.management.commands.submit_to_google.submit_url_to_google')
    def test_google_indexing_failure(self, mock_submit):
        """L238-244: Google indexing enabled + failure."""
        from ai_engine.modules.publisher import publish_article
        mock_submit.return_value = {'success': False, 'error': 'Invalid key'}

        with patch('news.models.AutomationSettings.load') as mock_load:
            mock_settings = MagicMock(google_indexing_enabled=True)
            mock_load.return_value = mock_settings
            article = publish_article(
                title='Indexing Fail Test',
                content='<p>Content.</p>',
                is_published=True,
            )
        assert article.id is not None

    def test_google_indexing_disabled(self):
        """L223-224: Google indexing disabled in settings."""
        from ai_engine.modules.publisher import publish_article
        with patch('news.models.AutomationSettings.load') as mock_load:
            mock_settings = MagicMock(google_indexing_enabled=False)
            mock_load.return_value = mock_settings
            article = publish_article(
                title='Indexing Disabled Test',
                content='<p>Content.</p>',
                is_published=True,
            )
        assert article.id is not None

    def test_google_indexing_exception(self):
        """L245-246: AutomationSettings not available → caught."""
        from ai_engine.modules.publisher import publish_article
        with patch('news.models.AutomationSettings.load', side_effect=Exception('No settings')):
            article = publish_article(
                title='Indexing Exception Test',
                content='<p>Content.</p>',
                is_published=True,
            )
        assert article.id is not None

    def test_not_published_skips_indexing(self):
        """L216: is_published=False → skip indexing entirely."""
        from ai_engine.modules.publisher import publish_article
        article = publish_article(
            title='Draft Test',
            content='<p>Content.</p>',
            is_published=False,
        )
        assert article.id is not None
        assert article.is_published is False
