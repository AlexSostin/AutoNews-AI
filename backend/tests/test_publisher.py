"""
Tests for ai_engine/modules/publisher.py

Covers:
- extract_summary: HTML → plain text summary extraction
- generate_seo_title: SEO title truncation and formatting
- _add_spec_based_tags: DB tag lookup from specs
- publish_article: Full article creation flow (mocked DB)
"""
import pytest
from unittest.mock import patch, MagicMock

from ai_engine.modules.publisher import extract_summary, generate_seo_title, _add_spec_based_tags


# ═══════════════════════════════════════════════════════════════════════════
# extract_summary — pure function, no mocks needed
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractSummary:
    def test_extracts_first_paragraph(self):
        html = "<h2>Title</h2><p>This is the first paragraph about BMW.</p><p>Second paragraph.</p>"
        result = extract_summary(html)
        assert "first paragraph" in result
        assert "BMW" in result

    def test_skips_h2_heading(self):
        html = "<h2>2025 BMW X5 Review</h2><p>Great car with excellent performance.</p>"
        result = extract_summary(html)
        assert "BMW X5 Review" not in result
        assert "Great car" in result

    def test_strips_inner_html_tags(self):
        html = "<p>The <strong>BMW X5</strong> is a <em>powerful</em> vehicle.</p>"
        result = extract_summary(html)
        assert "<strong>" not in result
        assert "<em>" not in result
        assert "BMW X5" in result

    def test_returns_default_when_no_paragraphs(self):
        html = "<h2>Just a heading</h2>"
        result = extract_summary(html)
        assert "AI-generated" in result

    def test_empty_content(self):
        result = extract_summary("")
        assert "AI-generated" in result

    def test_complex_nested_html(self):
        html = """
        <h2>Review</h2>
        <p>The 2025 <a href="/cars/bmw">BMW</a> X5 offers <span class="highlight">luxury</span> and comfort.</p>
        <p>Second paragraph about specs.</p>
        """
        result = extract_summary(html)
        assert "BMW" in result
        assert "<a" not in result
        assert "<span" not in result


# ═══════════════════════════════════════════════════════════════════════════
# generate_seo_title — pure function
# ═══════════════════════════════════════════════════════════════════════════

class TestGenerateSeoTitle:
    def test_short_title_unchanged(self):
        title = "2025 BMW X5 Review"
        result = generate_seo_title(title)
        assert result == title

    def test_exactly_60_chars_unchanged(self):
        title = "A" * 60
        result = generate_seo_title(title)
        assert result == title

    def test_long_title_with_year_make_model(self):
        title = "2025 BMW X5 M60i xDrive Full Review: Performance, Interior, Specs and Everything You Need to Know"
        result = generate_seo_title(title)
        assert result == "2025 BMW X5 Review & Specs"
        assert len(result) <= 60

    def test_long_title_without_pattern_truncated(self):
        title = "This is a very long title without any car information that goes beyond sixty characters limit"
        result = generate_seo_title(title)
        assert result.endswith("...")
        assert len(result) == 60

    def test_title_with_year_only(self):
        title = "2025 Mercedes GLE Coupe AMG 53 vs BMW X6 M50i Comparison Full Review Test Drive"
        result = generate_seo_title(title)
        assert "2025" in result
        assert len(result) <= 60


# ═══════════════════════════════════════════════════════════════════════════
# _add_spec_based_tags — requires DB
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAddSpecBasedTags:
    def test_adds_existing_make_tag(self):
        from news.models import Article, Tag
        # Create a tag that matches the make
        tag = Tag.objects.create(name="BMW", slug="bmw")
        article = Article.objects.create(
            title="Test Article BMW Tags",
            slug="test-article-bmw-tags",
            content="<p>Test</p>",
            is_published=True,
        )
        specs = {"make": "BMW", "model": "Not specified"}

        _add_spec_based_tags(article, specs)

        assert article.tags.filter(pk=tag.pk).exists()

    def test_skips_nonexistent_tag(self):
        from news.models import Article
        article = Article.objects.create(
            title="Test Article No Tag",
            slug="test-article-no-tag",
            content="<p>Test</p>",
            is_published=True,
        )
        specs = {"make": "NonExistentBrand", "model": "X5"}

        _add_spec_based_tags(article, specs)

        assert article.tags.count() == 0

    def test_skips_not_specified(self):
        from news.models import Article
        article = Article.objects.create(
            title="Test Not Specified",
            slug="test-not-specified",
            content="<p>Test</p>",
            is_published=True,
        )
        specs = {"make": "Not specified", "model": "Not specified"}

        _add_spec_based_tags(article, specs)

        assert article.tags.count() == 0

    def test_adds_both_make_and_model_tags(self):
        from news.models import Article, Tag
        make_tag = Tag.objects.create(name="Tesla", slug="tesla")
        model_tag = Tag.objects.create(name="Model 3", slug="model-3")
        article = Article.objects.create(
            title="Test Both Tags",
            slug="test-both-tags",
            content="<p>Test</p>",
            is_published=True,
        )
        specs = {"make": "Tesla", "model": "Model 3"}

        _add_spec_based_tags(article, specs)

        assert article.tags.count() == 2

    def test_doesnt_duplicate_existing_tag(self):
        from news.models import Article, Tag
        tag = Tag.objects.create(name="Audi", slug="audi")
        article = Article.objects.create(
            title="Test Duplicate Prevention",
            slug="test-dup-prevention",
            content="<p>Test</p>",
            is_published=True,
        )
        article.tags.add(tag)  # Already has the tag

        _add_spec_based_tags(article, {"make": "Audi", "model": "Not specified"})

        assert article.tags.count() == 1  # Still just 1


# ═══════════════════════════════════════════════════════════════════════════
# publish_article — full integration with DB
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPublishArticle:
    def test_creates_article_with_required_fields(self):
        from ai_engine.modules.publisher import publish_article

        article = publish_article(
            title="2025 BMW X5 Test Article",
            content="<h2>Review</h2><p>Great car.</p>",
            category_name="Reviews",
            is_published=True,
        )

        assert article.id is not None
        assert article.title == "2025 BMW X5 Test Article"
        assert article.is_published is True
        assert article.slug  # Should auto-generate

    def test_creates_category_on_the_fly(self):
        from news.models import Category
        from ai_engine.modules.publisher import publish_article

        article = publish_article(
            title="Unique Category Test XYZ",
            content="<p>Content</p>",
            category_name="Electric Vehicles Test",
        )

        assert Category.objects.filter(slug="electric-vehicles-test").exists()
        assert article.categories.filter(slug="electric-vehicles-test").exists()

    def test_adds_tags(self):
        from ai_engine.modules.publisher import publish_article

        article = publish_article(
            title="Tagged Article Test",
            content="<p>Content</p>",
            tag_names=["BMW", "SUV", "Review"],
        )

        assert article.tags.count() == 3

    def test_saves_car_specs(self):
        """Note: publisher.py has a known bug — it passes 'year' to CarSpecification
        which doesn't have that field. This test uses specs without year to verify
        the happy path. The year bug is logged separately."""
        from news.models import CarSpecification
        from ai_engine.modules.publisher import publish_article

        specs = {
            "make": "BMW",
            "model": "X5",
            "engine": "3.0L Inline-6 Turbo",
            "horsepower": 375,
            # Note: 'year' intentionally omitted — CarSpecification model
            # doesn't have this field, and publisher.py will fail if it's passed
        }

        article = publish_article(
            title="Specs Test Article Pub",
            content="<p>Content</p>",
            specs=specs,
        )

        car_spec = CarSpecification.objects.get(article=article)
        assert car_spec.make == "BMW"
        assert car_spec.model == "X5"
        assert int(car_spec.horsepower) == 375

    def test_generates_summary_from_content(self):
        from ai_engine.modules.publisher import publish_article

        article = publish_article(
            title="Auto Summary Test",
            content="<h2>Heading</h2><p>This is an auto-generated summary from content.</p>",
        )

        assert "auto-generated summary" in article.summary

    def test_trims_long_summary(self):
        from ai_engine.modules.publisher import publish_article

        long_summary = "A" * 500
        article = publish_article(
            title="Long Summary Test",
            content="<p>Short</p>",
            summary=long_summary,
        )

        assert len(article.summary) <= 300
        assert article.summary.endswith("...")

    def test_draft_mode(self):
        from ai_engine.modules.publisher import publish_article

        article = publish_article(
            title="Draft Article Test",
            content="<p>Draft content</p>",
            is_published=False,
        )

        assert article.is_published is False

    def test_author_metadata(self):
        from ai_engine.modules.publisher import publish_article

        article = publish_article(
            title="Author Metadata Test",
            content="<p>Content</p>",
            author_name="Doug DeMuro",
            author_channel_url="https://youtube.com/@DougDeMuro",
        )

        assert article.author_name == "Doug DeMuro"
        assert article.author_channel_url == "https://youtube.com/@DougDeMuro"
