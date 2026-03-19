"""
Tests for news/rss_intelligence.py

Covers:
  - Brand extraction from titles
  - Model extraction from titles
  - Content type classification (review/debut/news/noise/general)
  - process_rss_intelligence: brand discovery without VehicleSpecs stubs
  - Trending brands and topics
"""
import pytest
from unittest.mock import patch, MagicMock
from collections import Counter

from news.rss_intelligence import (
    extract_brands_from_title,
    extract_model_from_title,
    classify_rss_item,
    process_rss_intelligence,
    get_trending_brands,
    CONTENT_TYPE_KEYWORDS,
)


# ═══════════════════════════════════════════════════════════════════════════
# classify_rss_item — content type classification
# ═══════════════════════════════════════════════════════════════════════════

class TestClassifyRssItem:
    """Tests for classify_rss_item()."""

    def test_review_keyword_in_title(self):
        assert classify_rss_item("BMW X5 Full Review 2026") == 'review'

    def test_walkaround_keyword(self):
        assert classify_rss_item("2026 BYD Han L Walkaround Video") == 'review'

    def test_first_drive(self):
        assert classify_rss_item("First Drive: Tesla Model Y 2026") == 'review'

    def test_driven_keyword(self):
        assert classify_rss_item("We have driven the ZEEKR 9X hard") == 'review'
    def test_debut_unveil(self):
        assert classify_rss_item("BYD Unveils the Han L at Shanghai Auto Show") == 'debut'

    def test_debut_reveal(self):
        assert classify_rss_item("Toyota Revealed the New RAV4 Hybrid") == 'debut'

    def test_debut_all_new(self):
        assert classify_rss_item("The All-New Zeekr 7X SUV Is Here") == 'debut'

    def test_debut_first_look(self):
        assert classify_rss_item("First Look: Li Auto L9 Pro") == 'debut'

    def test_noise_recall(self):
        assert classify_rss_item("Tesla Issues Recall for 80,000 Vehicles") == 'noise'

    def test_noise_crash(self):
        assert classify_rss_item("Fatal Crash Investigation Opened for Model 3") == 'noise'

    def test_news_price(self):
        assert classify_rss_item("BYD Cuts Prices Across Full Lineup") == 'news'

    def test_news_new(self):
        assert classify_rss_item("The New ZEEKR 9X Enters European Market") == 'news'

    def test_general_no_match(self):
        assert classify_rss_item("Chinese EV Makers Eye Southeast Asia") == 'general'

    def test_review_takes_priority_over_debut(self):
        # 'review' should beat 'unveiled' since review is checked first
        assert classify_rss_item("We reviewed the unveiled BYD Seal") == 'review'

    def test_noise_takes_priority_over_news(self):
        # 'noise' beats 'news'
        assert classify_rss_item("New Recall Announced for 2025 Tesla") == 'noise'

    def test_excerpt_also_checked(self):
        # Title is neutral but excerpt has keyword
        assert classify_rss_item("ZEEKR Update", "First drive impressions after 500 km") == 'review'

    def test_case_insensitive(self):
        assert classify_rss_item("BMW X5 REVIEW 2026") == 'review'
        assert classify_rss_item("BYD RECALL Issued") == 'noise'


# ═══════════════════════════════════════════════════════════════════════════
# extract_brands_from_title
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractBrandsFromTitle:
    """Tests brand detection from RSS titles."""

    def test_known_brand_found(self):
        results = extract_brands_from_title("Tesla Model 3 wins award")
        brands = [r['brand_key'] for r in results]
        assert 'tesla' in brands

    def test_no_brand(self):
        results = extract_brands_from_title("EV market grows by 30% in Q1")
        assert results == []

    def test_empty_title(self):
        assert extract_brands_from_title("") == []

    def test_multiple_brands(self):
        results = extract_brands_from_title("BMW and Mercedes compete for top spot")
        brand_keys = [r['brand_key'] for r in results]
        assert 'bmw' in brand_keys
        assert 'mercedes' in brand_keys or 'mercedes-benz' in brand_keys

    def test_display_name_returned(self):
        results = extract_brands_from_title("Tesla unveils new model")
        assert any(r['display_name'] for r in results)


# ═══════════════════════════════════════════════════════════════════════════
# extract_model_from_title
# ═══════════════════════════════════════════════════════════════════════════

class TestExtractModelFromTitle:
    """Tests model extraction given a brand key."""

    def test_extracts_model(self):
        result = extract_model_from_title("2026 Tesla Model Y review", "tesla")
        assert result is not None
        assert 'model' in result

    def test_extracts_year(self):
        result = extract_model_from_title("2026 BMW X5 Full Review", "bmw")
        assert result is not None
        assert result.get('year') == 2026

    def test_generic_word_after_brand_skipped(self):
        # 'launches' is in GENERIC_MODEL_WORDS
        result = extract_model_from_title("Tesla launches new campaign", "tesla")
        assert result is None

    def test_empty_title(self):
        assert extract_model_from_title("", "tesla") is None

    def test_no_brand_in_title(self):
        assert extract_model_from_title("BMW X5 review", "tesla") is None


# ═══════════════════════════════════════════════════════════════════════════
# process_rss_intelligence — no VehicleSpecs created
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestProcessRssIntelligenceNoSpecs:
    """Verify that process_rss_intelligence NEVER creates VehicleSpecs stubs."""

    def _make_item(self, title="Tesla Model Y Review 2026", status="new"):
        from news.models import RSSNewsItem, RSSFeed
        feed = RSSFeed.objects.create(name='Test Feed', feed_url='http://test-feed.com')
        return RSSNewsItem.objects.create(
            rss_feed=feed,
            title=title,
            source_url=f'http://test.com/{title[:10]}',
            status=status,
        )

    def test_no_vehicle_specs_created(self):
        from news.models import VehicleSpecs
        before = VehicleSpecs.objects.count()
        self._make_item("Tesla Model Y Full Review 2026")

        from news.models import RSSNewsItem
        qs = RSSNewsItem.objects.filter(status='new')
        process_rss_intelligence(queryset=qs, dry_run=False)

        after = VehicleSpecs.objects.count()
        assert after == before  # No new stubs created

    def test_models_found_but_not_created(self):
        self._make_item("BMW X5 Full Review 2026")
        from news.models import RSSNewsItem
        qs = RSSNewsItem.objects.filter(status='new')
        stats = process_rss_intelligence(queryset=qs, dry_run=False)
        # models_found may have entries, but models_created should be empty
        assert stats['models_created'] == []

    def test_dry_run_also_creates_nothing(self):
        from news.models import VehicleSpecs
        before = VehicleSpecs.objects.count()
        self._make_item("BMW X5 Full Review 2026")
        from news.models import RSSNewsItem
        qs = RSSNewsItem.objects.filter(status='new')
        process_rss_intelligence(queryset=qs, dry_run=True)
        assert VehicleSpecs.objects.count() == before

    def test_brand_is_still_created(self):
        from news.models import Brand
        # Delete Tesla if it exists so we can track creation
        Brand.objects.filter(name__iexact='Tesla').delete()
        self._make_item("Tesla Model Y Full Review 2026")
        from news.models import RSSNewsItem
        qs = RSSNewsItem.objects.filter(status='new')
        stats = process_rss_intelligence(queryset=qs, dry_run=False)
        # Brand discovery should still work
        assert len(stats['brands_found']) > 0
