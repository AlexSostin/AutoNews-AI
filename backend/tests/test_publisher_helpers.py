"""
Group 3: Publisher helper function tests.
Tests extract_summary, generate_seo_title, _add_spec_based_tags.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ai_engine'))

import pytest
from ai_engine.modules.publisher import extract_summary, generate_seo_title, _add_spec_based_tags
from news.models import Article, Tag


class TestExtractSummary:
    """Tests for extract_summary — extracts first paragraph from HTML"""

    def test_basic_paragraph(self):
        html = '<p>This is the summary text.</p><p>Second paragraph.</p>'
        assert extract_summary(html) == 'This is the summary text.'

    def test_skips_h2(self):
        html = '<h2>Big Title</h2><p>Actual summary here.</p>'
        assert extract_summary(html) == 'Actual summary here.'

    def test_strips_inner_html(self):
        html = '<p>Text with <strong>bold</strong> and <a href="#">link</a>.</p>'
        result = extract_summary(html)
        assert '<strong>' not in result
        assert '<a' not in result
        assert 'bold' in result

    def test_no_paragraphs(self):
        """When no <p> tags, returns default text"""
        html = '<div>Some content</div>'
        result = extract_summary(html)
        assert 'AI-generated' in result

    def test_empty_content(self):
        result = extract_summary('')
        assert 'AI-generated' in result


class TestGenerateSeoTitle:
    """Tests for generate_seo_title — SEO-optimized titles"""

    def test_short_title_unchanged(self):
        title = "2024 BMW M3 Review"
        assert generate_seo_title(title) == title

    def test_exactly_60_chars(self):
        title = "A" * 60
        assert generate_seo_title(title) == title

    def test_long_title_truncated(self):
        title = "X" * 100
        result = generate_seo_title(title)
        assert len(result) <= 60

    def test_year_make_model_extraction(self):
        title = "2024 Tesla Model3 - Comprehensive Review with Full Specification Analysis and Market Comparison for Buyers"
        result = generate_seo_title(title)
        assert len(result) <= 60
        assert '2024' in result
        assert 'Tesla' in result

    def test_truncation_with_ellipsis(self):
        """Long title without year-make-model pattern gets truncated with ..."""
        title = "The Ultimate Comprehensive Guide to Everything About Electric Vehicles in the Modern Automotive Market"
        result = generate_seo_title(title)
        assert result.endswith('...')
        assert len(result) <= 60


@pytest.mark.django_db
class TestAddSpecBasedTags:
    """Tests for _add_spec_based_tags — adds existing tags to articles"""

    def test_adds_existing_make_tag(self):
        tag = Tag.objects.create(name='BMW', slug='bmw')
        article = Article.objects.create(
            title='Test', slug='test-spec-tag', content='<p>X</p>',
            is_published=True
        )
        _add_spec_based_tags(article, {'make': 'BMW', 'model': 'M3'})
        assert article.tags.filter(pk=tag.pk).exists()

    def test_skips_nonexistent_tag(self):
        """Should not create new tags"""
        article = Article.objects.create(
            title='Test2', slug='test-spec-tag2', content='<p>X</p>',
            is_published=True
        )
        _add_spec_based_tags(article, {'make': 'SomeBrandThatDoesNotExist'})
        assert article.tags.count() == 0

    def test_skips_not_specified(self):
        """Should not add tag for 'Not specified'"""
        article = Article.objects.create(
            title='Test3', slug='test-spec-tag3', content='<p>X</p>',
            is_published=True
        )
        _add_spec_based_tags(article, {'make': 'Not specified'})
        assert article.tags.count() == 0

    def test_adds_model_tag_too(self):
        Tag.objects.create(name='Tesla', slug='tesla')
        model_tag = Tag.objects.create(name='Model 3', slug='model-3')
        article = Article.objects.create(
            title='Test4', slug='test-spec-tag4', content='<p>X</p>',
            is_published=True
        )
        _add_spec_based_tags(article, {'make': 'Tesla', 'model': 'Model 3'})
        assert article.tags.filter(pk=model_tag.pk).exists()
