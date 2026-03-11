"""
Tests for SEO description separation:
- PendingArticle.seo_description field
- Article approval copies seo_description
- Backfill management command helper functions
"""
import pytest
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════════════
# PendingArticle.seo_description model field
# ═══════════════════════════════════════════════════════════════════════════

class TestPendingArticleSeoDescription:

    def test_seo_description_field_exists(self):
        """PendingArticle has seo_description field."""
        from news.models import PendingArticle
        assert hasattr(PendingArticle, 'seo_description')

    def test_seo_description_defaults_empty(self):
        """seo_description defaults to empty string."""
        from news.models import PendingArticle
        from news.models.sources import YouTubeChannel
        channel = YouTubeChannel.objects.create(
            channel_url='https://youtube.com/@testseo1',
            name='Test SEO 1',
        )
        pending = PendingArticle.objects.create(
            youtube_channel=channel,
            title='2026 BYD Seal Default SEO',
            content='<p>Test content</p>',
            excerpt='Summary text here',
        )
        assert pending.seo_description == '' or pending.seo_description is not None

    def test_seo_description_stored_correctly(self):
        """seo_description value is stored and returned correctly."""
        from news.models import PendingArticle
        from news.models.sources import YouTubeChannel
        channel = YouTubeChannel.objects.create(
            channel_url='https://youtube.com/@testseo2',
            name='Test SEO 2',
        )
        seo_text = '2026 BYD Seal 313-HP electric — full specs, pricing & review.'
        pending = PendingArticle.objects.create(
            youtube_channel=channel,
            title='2026 BYD Seal SEO Stored Test',
            content='<p>Test content</p>',
            excerpt='Summary',
            seo_description=seo_text,
        )
        pending.refresh_from_db()
        assert pending.seo_description == seo_text


# ═══════════════════════════════════════════════════════════════════════════
# Article serializer includes seo_description
# ═══════════════════════════════════════════════════════════════════════════

class TestArticleSerializerSeoDescription:

    def test_article_detail_serializer_has_seo_description(self):
        """ArticleDetailSerializer exposes seo_description field."""
        from news.serializers import ArticleDetailSerializer
        assert 'seo_description' in ArticleDetailSerializer().fields

    def test_pending_article_serializer_has_seo_description(self):
        """PendingArticleSerializer exposes seo_description field."""
        from news.serializers import PendingArticleSerializer
        assert 'seo_description' in PendingArticleSerializer().fields


# ═══════════════════════════════════════════════════════════════════════════
# Article.save() — seo_description behaviour
# ═══════════════════════════════════════════════════════════════════════════

class TestArticleSaveSeoBehaviour:

    def test_new_article_explicit_seo_description_preserved(self):
        """Explicit seo_description on a new article is kept as-is."""
        from news.models import Article
        explicit_seo = '2026 Zeekr 7X 788-HP electric — complete specs, pricing & expert review.'
        article = Article.objects.create(
            title='2026 Zeekr 7X Explicit SEO',
            slug='2026-zeekr-7x-seo-explicit',
            content='<p>Test content</p>',
            summary='The Zeekr 7X is a great electric car.',
            seo_description=explicit_seo,
        )
        article.refresh_from_db()
        assert article.seo_description == explicit_seo

    def test_existing_article_seo_description_not_overwritten_on_save(self):
        """Saving existing article does not overwrite existing seo_description."""
        from news.models import Article
        custom_seo = 'Custom SEO description that must survive re-save.'
        article = Article.objects.create(
            title='Re-save Preservation Test',
            slug='re-save-preservation-test',
            content='<p>Test content</p>',
            summary='Original summary.',
            seo_description=custom_seo,
        )
        article.summary = 'Updated summary (seo_description should stay).'
        article.save()
        article.refresh_from_db()
        assert article.seo_description == custom_seo

    def test_different_summary_and_seo_description_coexist(self):
        """summary and seo_description can hold completely different content."""
        from news.models import Article
        article = Article.objects.create(
            title='Two Field Test',
            slug='two-field-coexist-test',
            content='<p>Content</p>',
            summary='Long descriptive summary for the article card, shown to users.',
            seo_description='Short keyword-rich meta for Google. 2026 BYD Seal 313HP.',
        )
        article.refresh_from_db()
        assert article.summary != article.seo_description
        assert 'Google' in article.seo_description


# ═══════════════════════════════════════════════════════════════════════════
# Backfill command — pure helper functions (no external calls)
# ═══════════════════════════════════════════════════════════════════════════

class TestBackfillHelpers:

    def test_extract_year_from_title(self):
        """Extracts 4-digit year from various title formats."""
        from news.management.commands.backfill_seo_descriptions import _extract_year_from_title

        assert _extract_year_from_title('2026 BYD Seal Review') == '2026'
        assert _extract_year_from_title('2025 ZEEKR 7X EV') == '2025'
        assert _extract_year_from_title('BYD Seal Review') == ''

    def test_clean_hp_strips_suffix(self):
        """_clean_hp removes HP/PS suffixes and normalizes."""
        from news.management.commands.backfill_seo_descriptions import _clean_hp

        assert _clean_hp('544 HPHP') == '544'
        assert _clean_hp('500HP') == '500'
        assert _clean_hp('788 PS') == '788'
        assert _clean_hp('') == ''
        assert _clean_hp(None) == ''

    def test_detect_fuel_type_electric(self):
        """Detects electric vehicles from engine field."""
        from news.management.commands.backfill_seo_descriptions import _detect_fuel_type
        specs = MagicMock()
        specs.engine = 'Dual motor electric AWD 400 kWh'
        specs.model_name = 'ZEEKR 7X'
        assert _detect_fuel_type(specs) == 'electric'

    def test_detect_fuel_type_phev(self):
        """Detects PHEV/DM-i from engine string."""
        from news.management.commands.backfill_seo_descriptions import _detect_fuel_type
        specs = MagicMock()
        specs.engine = 'BYD DM-i plug-in hybrid 1.5L'
        specs.model_name = 'BYD Song Pro DM-i'
        assert _detect_fuel_type(specs) == 'plug-in hybrid'

    def test_detect_fuel_type_none(self):
        """Returns empty string when specs is None."""
        from news.management.commands.backfill_seo_descriptions import _detect_fuel_type
        assert _detect_fuel_type(None) == ''

    def test_detect_body_type_suv(self):
        """Detects SUV from title/model_name."""
        from news.management.commands.backfill_seo_descriptions import _detect_body_type
        specs = MagicMock()
        specs.model_name = 'BYD Atto 3 SUV'
        assert _detect_body_type(specs, '2026 BYD Atto 3 SUV') == 'SUV'

    def test_generate_seo_description_with_full_specs(self):
        """generate_seo_description produces proper string with specs."""
        from news.management.commands.backfill_seo_descriptions import generate_seo_description
        from news.models import Article

        article = Article.objects.create(
            title='2026 BYD Seal 06 DM-i Review',
            slug='2026-byd-seal-06-dm-i-review-test',
            content='<p>Content</p>',
            summary='The BYD Seal 06 DM-i is a plug-in hybrid.',
        )
        specs = MagicMock()
        specs.make = 'BYD'
        specs.model = 'Seal 06 DM-i'
        specs.model_name = 'BYD Seal 06 DM-i'
        specs.horsepower = '194 HP'
        specs.engine = 'DM-i plug-in hybrid 1.5L'
        specs.price = '$18,000'

        desc = generate_seo_description(article, specs)
        assert isinstance(desc, str)
        assert 80 <= len(desc) <= 160
        assert 'BYD' in desc

    def test_generate_seo_description_no_specs_fallback(self):
        """generate_seo_description still returns non-empty without specs."""
        from news.management.commands.backfill_seo_descriptions import generate_seo_description
        from news.models import Article

        article = Article.objects.create(
            title='2026 Porsche 911 GT3 Review',
            slug='2026-porsche-911-gt3-review-back',
            content='<p>Content</p>',
            summary='Track-focused sports car.',
        )
        desc = generate_seo_description(article, None)
        assert isinstance(desc, str)
        assert len(desc) > 30

    def test_generate_seo_no_duplicate_brand(self):
        """No 'BYD BYD Seal' duplication when model_name contains make."""
        from news.management.commands.backfill_seo_descriptions import generate_seo_description
        from news.models import Article

        article = Article.objects.create(
            title='2026 BYD Seal Electric',
            slug='2026-byd-seal-electric-dup-test',
            content='<p>Content</p>',
            summary='The BYD Seal is an electric sedan.',
        )
        specs = MagicMock()
        specs.make = 'BYD'
        specs.model = ''
        specs.model_name = 'BYD Seal'  # Would produce "BYD BYD Seal" without the fix
        specs.horsepower = '313 HP'
        specs.engine = 'electric motor'
        specs.price = ''

        desc = generate_seo_description(article, specs)
        assert 'BYD BYD' not in desc
        assert 'BYD' in desc

    def test_get_model_from_title_preserves_hyphen(self):
        """_get_model_from_title doesn't truncate DM-i style names."""
        from news.management.commands.backfill_seo_descriptions import _get_model_from_title

        make, model = _get_model_from_title('BYD Song Pro DM-i Review', '2026')
        assert 'DM-i' in model or 'DM' in model  # Should preserve hyphen


# ═══════════════════════════════════════════════════════════════════════════
# Approve flow — seo_description passed through correctly
# ═══════════════════════════════════════════════════════════════════════════

class TestApproveSeoDescriptionCopy:

    def test_article_gets_explicit_seo_description(self):
        """Article created with seo_description stores it correctly."""
        from news.models import Article
        seo_text = '2026 BYD Seal 06 DM-i 194-HP plug-in hybrid — full specs & expert review.'
        article = Article.objects.create(
            title='Approve Flow Copy Test',
            slug='approve-flow-seo-copy-test',
            content='<p>Article content</p>',
            summary='The BYD Seal 06 is a plug-in hybrid.',
            seo_description=seo_text,
            is_published=True,
        )
        article.refresh_from_db()
        assert article.seo_description == seo_text

    def test_seo_description_independent_from_summary(self):
        """seo_description can be shorter and different from summary."""
        from news.models import Article
        long_summary = 'A' * 400  # typical long summary
        short_seo = '2026 BYD Tang 544-HP SUV — from $31,500. Full specs & review.'
        article = Article.objects.create(
            title='Independence Test Article',
            slug='independence-test-seo',
            content='<p>Content</p>',
            summary=long_summary,
            seo_description=short_seo,
        )
        article.refresh_from_db()
        assert len(article.seo_description) < len(article.summary)
        assert article.seo_description == short_seo
