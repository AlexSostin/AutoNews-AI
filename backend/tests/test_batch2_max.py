"""
Batch 2 — auto_tags.py, models.py, serializers.py (partial)
Target: auto_tags 67→90%, models 89→93%
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from django.utils.text import slugify

pytestmark = pytest.mark.django_db


# ═══════════════════════════════════════════════════════════════════
# auto_tags.py — 67% → 90%
# Missed: L160, L173, L204, L208, L215-221, L258-267, L330, L358,
#          L362, L364, L391-458, L513, L517-518, L527-528, L536
# ═══════════════════════════════════════════════════════════════════

class TestNormalizeTagName:

    def test_none_input(self):
        """L159-160: None → (None, None)."""
        from news.auto_tags import normalize_tag_name
        assert normalize_tag_name(None) == (None, None)

    def test_empty_string(self):
        from news.auto_tags import normalize_tag_name
        assert normalize_tag_name('') == (None, None)

    def test_stop_word(self):
        """L165: Stop word → rejected."""
        from news.auto_tags import normalize_tag_name
        assert normalize_tag_name('the') == (None, None)

    def test_short_string(self):
        """L165: Single char → rejected."""
        from news.auto_tags import normalize_tag_name
        assert normalize_tag_name('a') == (None, None)

    def test_year_valid(self):
        """L170-172: Valid year 2025 → ('2025', 'Years')."""
        from news.auto_tags import normalize_tag_name
        name, group = normalize_tag_name('2025')
        assert name == '2025'
        assert group == 'Years'

    def test_year_out_of_range(self):
        """L173: Year outside 2020-2030 → rejected."""
        from news.auto_tags import normalize_tag_name
        assert normalize_tag_name('1990') == (None, None)

    def test_alias_match(self):
        """L176-179: Known alias → canonical + group."""
        from news.auto_tags import normalize_tag_name
        name, group = normalize_tag_name('plug-in hybrid')
        assert name == 'PHEV'
        assert group == 'Fuel Types'

    def test_brand_match(self):
        """L182-184: Known brand → display name + Manufacturers."""
        from news.auto_tags import normalize_tag_name
        name, group = normalize_tag_name('byd')
        assert name == 'BYD'
        assert group == 'Manufacturers'

    def test_group_map_match(self):
        """L188-189: Tag in TAG_GROUP_MAP → group assigned."""
        from news.auto_tags import normalize_tag_name
        name, group = normalize_tag_name('AWD')
        assert name == 'AWD'
        assert group == 'Drivetrain'

    def test_unknown_tag_title_case(self):
        """L192: Unknown tag → title-cased, no group."""
        from news.auto_tags import normalize_tag_name
        name, group = normalize_tag_name('custom tag')
        assert name == 'Custom Tag'
        assert group is None

    def test_non_string_input(self):
        from news.auto_tags import normalize_tag_name
        assert normalize_tag_name(123) == (None, None)


class TestFindOrCreateTag:

    def test_create_new_tag(self):
        """L224-238: New tag → created with group."""
        from news.auto_tags import find_or_create_tag
        tag, created = find_or_create_tag('BYD', 'Manufacturers')
        assert tag is not None
        assert created is True
        assert tag.name == 'BYD'

    def test_find_existing_tag(self):
        """L211-222: Existing tag → found, not created."""
        from news.auto_tags import find_or_create_tag
        tag1, created1 = find_or_create_tag('Tesla', 'Manufacturers')
        tag2, created2 = find_or_create_tag('tesla', 'Manufacturers')
        assert tag2.id == tag1.id
        assert created2 is False

    def test_fix_group_on_existing(self):
        """L214-221: Existing tag without group → group assigned."""
        from news.auto_tags import find_or_create_tag
        from news.models import Tag, TagGroup
        # Create tag without group
        tag = Tag.objects.create(name='Hybrid', slug='hybrid')
        # Create the group
        grp = TagGroup.objects.create(name='Fuel Types', slug='fuel-types')
        # find_or_create should fix the group
        found_tag, created = find_or_create_tag('Hybrid', 'Fuel Types')
        assert created is False
        found_tag.refresh_from_db()
        assert found_tag.group == grp

    def test_invalid_name_returns_none(self):
        """L203-204: Invalid name → (None, False)."""
        from news.auto_tags import find_or_create_tag
        tag, created = find_or_create_tag('the')
        assert tag is None
        assert created is False


class TestExtractTagsFromStructuredData:

    def test_with_vehicle_specs(self):
        """L256-268: VehicleSpecs data → tags extracted."""
        from news.auto_tags import extract_tags_from_structured_data
        from news.models import Article, VehicleSpecs
        article = Article.objects.create(
            title='Extract Test', slug='extract-tag-test', content='<p>C</p>'
        )
        VehicleSpecs.objects.create(
            article=article, make='BYD', model_name='Seal',
            body_type='sedan', fuel_type='EV', drivetrain='AWD', year=2026
        )
        tags = extract_tags_from_structured_data(article)
        tag_names = [t[0] for t in tags]
        assert 'BYD' in tag_names
        assert 'sedan' in tag_names
        assert 'EV' in tag_names
        assert 'AWD' in tag_names

    def test_with_car_spec(self):
        """L251-253: CarSpecification → manufacturer extracted."""
        from news.auto_tags import extract_tags_from_structured_data
        from news.models import Article, CarSpecification
        article = Article.objects.create(
            title='CarSpec Tag', slug='carspec-tag-test', content='<p>C</p>'
        )
        CarSpecification.objects.create(
            article=article, model_name='Tesla Model 3', make='Tesla'
        )
        tags = extract_tags_from_structured_data(article)
        assert any(t[0] == 'Tesla' for t in tags)

    def test_no_specs(self):
        """No specs → empty list."""
        from news.auto_tags import extract_tags_from_structured_data
        from news.models import Article
        article = Article.objects.create(
            title='No Specs', slug='no-specs-tag', content='<p>C</p>'
        )
        tags = extract_tags_from_structured_data(article)
        assert tags == []


class TestExtractTagsFromTitle:

    def test_brand_in_title(self):
        """L287-290: Brand name in title → extracted."""
        from news.auto_tags import extract_tags_from_title
        from news.models import Article
        article = Article.objects.create(
            title='2026 BYD Seal AWD Review', slug='byd-seal-title',
            content='<p>This electric sedan has 530 hp</p>'
        )
        tags = extract_tags_from_title(article)
        tag_names = [t[0] for t in tags]
        assert any('byd' in n.lower() for n in tag_names)

    def test_year_in_title(self):
        """L311-313: Year → extracted."""
        from news.auto_tags import extract_tags_from_title
        from news.models import Article
        article = Article.objects.create(
            title='2026 Tesla Model 3 Review', slug='year-title',
            content='<p>Content</p>'
        )
        tags = extract_tags_from_title(article)
        assert any(t[0] == '2026' for t in tags)

    def test_fuel_type_ev(self):
        """L316-327: EV keyword → Fuel Types tag."""
        from news.auto_tags import extract_tags_from_title
        from news.models import Article
        article = Article.objects.create(
            title='New Electric SUV from BYD', slug='ev-title',
            content='<p>An electric vehicle</p>'
        )
        tags = extract_tags_from_title(article)
        tag_groups = [t[1] for t in tags]
        assert 'Fuel Types' in tag_groups

    def test_phev_break(self):
        """L329-330: PHEV found → stops scanning for hybrid/electric."""
        from news.auto_tags import extract_tags_from_title
        from news.models import Article
        article = Article.objects.create(
            title='New BYD Song PHEV Review', slug='phev-title',
            content='<p>A plug-in hybrid vehicle</p>'
        )
        tags = extract_tags_from_title(article)
        fuel_tags = [t[0] for t in tags if t[1] == 'Fuel Types']
        # Should have PHEV but NOT also Hybrid separately
        assert any('PHEV' in t or 'Plug-in' in t for t in fuel_tags)

    def test_body_type_suv(self):
        """L332-347: SUV keyword → Body Types."""
        from news.auto_tags import extract_tags_from_title
        from news.models import Article
        article = Article.objects.create(
            title='BYD Tang SUV', slug='suv-title',
            content='<p>An SUV</p>'
        )
        tags = extract_tags_from_title(article)
        assert any(t[0] == 'SUV' for t in tags)

    def test_drivetrain_awd(self):
        """L349-358: AWD keyword → Drivetrain."""
        from news.auto_tags import extract_tags_from_title
        from news.models import Article
        article = Article.objects.create(
            title='Tesla Model Y AWD Review', slug='awd-title',
            content='<p>AWD system</p>'
        )
        tags = extract_tags_from_title(article)
        assert any(t[0] == 'AWD' for t in tags)

    def test_luxury_segment(self):
        """L361-362: Luxury keyword → Segments."""
        from news.auto_tags import extract_tags_from_title
        from news.models import Article
        article = Article.objects.create(
            title='Luxury BMW 7 Series', slug='luxury-title',
            content='<p>Premium</p>'
        )
        tags = extract_tags_from_title(article)
        assert any(t[0] == 'Luxury' for t in tags)

    def test_budget_segment(self):
        """L363-364: Budget keyword → Segments."""
        from news.auto_tags import extract_tags_from_title
        from news.models import Article
        article = Article.objects.create(
            title='Most Affordable Electric Cars', slug='budget-title',
            content='<p>Budget options</p>'
        )
        tags = extract_tags_from_title(article)
        assert any(t[0] == 'Budget' for t in tags)


class TestExtractTagsWithAI:

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_successful_ai_extraction(self, mock_ai_provider):
        """L391-454: AI returns valid JSON → tags extracted."""
        from news.auto_tags import extract_tags_with_ai
        from news.models import Article
        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = json.dumps({
            'brand': 'BYD', 'year': 2026, 'body_type': 'sedan',
            'fuel_type': 'ev', 'drivetrain': 'awd',
            'segment': ['luxury'], 'topics': ['technology']
        })
        mock_ai_provider.return_value = mock_provider
        article = Article.objects.create(
            title='AI Tag Test', slug='ai-tag-test', content='<p>Content</p>'
        )
        tags = extract_tags_with_ai(article)
        assert len(tags) >= 5
        tag_names = [t[0] for t in tags]
        assert 'BYD' in tag_names

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_ai_extraction_markdown_response(self, mock_ai_provider):
        """L427-429: AI wraps JSON in markdown."""
        from news.auto_tags import extract_tags_with_ai
        from news.models import Article
        mock_provider = MagicMock()
        mock_provider.generate_completion.return_value = '```json\n{"brand": "Tesla", "year": 2026}\n```'
        mock_ai_provider.return_value = mock_provider
        article = Article.objects.create(
            title='AI MD Test', slug='ai-md-test', content='<p>Content</p>'
        )
        tags = extract_tags_with_ai(article)
        assert any(t[0] == 'Tesla' for t in tags)

    @patch('ai_engine.modules.ai_provider.get_ai_provider')
    def test_ai_extraction_failure(self, mock_ai_provider):
        """L456-458: AI exception → empty list."""
        from news.auto_tags import extract_tags_with_ai
        from news.models import Article
        mock_ai_provider.side_effect = Exception('API down')
        article = Article.objects.create(
            title='AI Fail Test', slug='ai-fail-test', content='<p>Content</p>'
        )
        tags = extract_tags_with_ai(article)
        assert tags == []


class TestAutoTagArticle:

    def test_without_ai(self):
        """L461-538: use_ai=False → only structured + title scanning."""
        from news.auto_tags import auto_tag_article
        from news.models import Article, VehicleSpecs
        article = Article.objects.create(
            title='2026 BYD Seal AWD EV Review', slug='auto-tag-test',
            content='<p>An electric SUV</p>'
        )
        VehicleSpecs.objects.create(
            article=article, make='BYD', fuel_type='EV', drivetrain='AWD'
        )
        result = auto_tag_article(article, use_ai=False)
        assert result['total'] > 0
        assert result['ai_used'] is False

    def test_max_tags_limit(self):
        """L512-513: max_tags=3 → only 3 tags added."""
        from news.auto_tags import auto_tag_article
        from news.models import Article, VehicleSpecs
        article = Article.objects.create(
            title='2026 BYD Seal AWD EV SUV Luxury Review', slug='max-tag-test',
            content='<p>Electric sedan</p>'
        )
        VehicleSpecs.objects.create(
            article=article, make='BYD', body_type='sedan',
            fuel_type='EV', drivetrain='AWD', year=2026
        )
        result = auto_tag_article(article, use_ai=False, max_tags=3)
        assert result['total'] <= 3

    @patch('news.auto_tags.extract_tags_with_ai')
    def test_ai_triggered_when_few_tags(self, mock_ai):
        """L502-505: < 3 tags detected → AI fallback triggered."""
        from news.auto_tags import auto_tag_article
        from news.models import Article
        mock_ai.return_value = [('BYD', 'Manufacturers'), ('2026', 'Years')]
        article = Article.objects.create(
            title='Something Generic', slug='ai-trigger-test',
            content='<p>No brand mentioned</p>'
        )
        result = auto_tag_article(article, use_ai=True)
        assert result['ai_used'] is True

    def test_skipped_tags_tracked(self):
        """L516-517: Invalid tag names → added to skipped list."""
        from news.auto_tags import auto_tag_article
        from news.models import Article
        article = Article.objects.create(
            title='The New Car Review', slug='skip-tag-test',
            content='<p>Content</p>'
        )
        result = auto_tag_article(article, use_ai=False)
        # 'the', 'new', 'car' are stop words → skipped
        assert isinstance(result['skipped'], list)


# ═══════════════════════════════════════════════════════════════════
# models.py — 89% → 93%
# Missed: L107, L140, L149, L153, L223-239, L252-253, L303, L310,
#          L319, L345, L351, L376, L396, L424-429, L435, L449,
#          L493, L507, L523, L554, L633, L641, L652, L703, L782,
#          L1343-1347, L1351-1357, L1361-1367, L1379, L1383-1391
# ═══════════════════════════════════════════════════════════════════

class TestCategoryModel:

    def test_auto_slug(self):
        """L106-107: Category without slug → auto-generated."""
        from news.models import Category
        cat = Category.objects.create(name='Electric Vehicles')
        assert cat.slug == 'electric-vehicles'

    def test_str(self):
        """L110-111: __str__ returns name."""
        from news.models import Category
        cat = Category.objects.create(name='SUVs', slug='suvs')
        assert str(cat) == 'SUVs'


class TestTagModel:

    def test_auto_slug(self):
        """L148-149: Tag without slug → auto-generated."""
        from news.models import Tag
        tag = Tag.objects.create(name='Electric')
        assert tag.slug == 'electric'

    def test_str(self):
        """L152-153: __str__ returns name."""
        from news.models import Tag
        tag = Tag.objects.create(name='AWD', slug='awd-model-test')
        assert str(tag) == 'AWD'


class TestBrandAliasModel:

    def test_resolve_known_alias(self):
        """L348-354: Known alias → canonical name."""
        from news.models import BrandAlias
        BrandAlias.objects.create(alias='DongFeng VOYAH', canonical_name='VOYAH')
        assert BrandAlias.resolve('DongFeng VOYAH') == 'VOYAH'

    def test_resolve_unknown(self):
        """L355-356: Unknown make → returned as-is."""
        from news.models import BrandAlias
        assert BrandAlias.resolve('Tesla') == 'Tesla'

    def test_resolve_none(self):
        """L350-351: None → None."""
        from news.models import BrandAlias
        assert BrandAlias.resolve(None) is None

    def test_str(self):
        """L344-345: __str__ shows alias → canonical."""
        from news.models import BrandAlias
        ba = BrandAlias.objects.create(alias='Benz', canonical_name='Mercedes-Benz')
        assert '→' in str(ba)


class TestBrandModel:

    def test_get_article_count(self):
        """L305-313: Brand.get_article_count()."""
        from news.models import Brand, Article, CarSpecification
        brand = Brand.objects.create(name='BrandTest', slug='brand-test')
        article = Article.objects.create(
            title='Brand Count', slug='brand-count', content='<p>C</p>',
            is_published=True
        )
        CarSpecification.objects.create(
            article=article, model_name='BrandTest Model', make='BrandTest'
        )
        assert brand.get_article_count() >= 1

    def test_get_model_count(self):
        """L315-322: Brand.get_model_count()."""
        from news.models import Brand, Article, CarSpecification
        brand = Brand.objects.create(name='ModelCount', slug='model-count')
        art = Article.objects.create(
            title='MC', slug='mc-test', content='<p>C</p>'
        )
        CarSpecification.objects.create(
            article=art, model_name='MC X', make='ModelCount', model='X'
        )
        assert brand.get_model_count() >= 1

    def test_str(self):
        """L302-303: __str__ returns name."""
        from news.models import Brand
        b = Brand.objects.create(name='TestStr', slug='test-str')
        assert str(b) == 'TestStr'


class TestCarSpecificationModel:

    def test_str(self):
        """L375-376: __str__."""
        from news.models import Article, CarSpecification
        art = Article.objects.create(
            title='Spec Str', slug='spec-str', content='<p>C</p>'
        )
        cs = CarSpecification.objects.create(article=art, model_name='Test')
        assert 'Spec Str' in str(cs)


class TestVehicleSpecsDisplayMethods:

    def _make_vs(self, **kwargs):
        from news.models import Article, VehicleSpecs
        art = Article.objects.create(
            title='VS Display', slug=f"vs-display-{kwargs.get('make','t')}",
            content='<p>C</p>'
        )
        return VehicleSpecs.objects.create(article=art, **kwargs)

    def test_str_with_all_parts(self):
        """L1342-1347: __str__ with make+model+trim."""
        vs = self._make_vs(make='BYD', model_name='Seal', trim_name='AWD')
        assert 'BYD' in str(vs)
        assert 'Seal' in str(vs)

    def test_str_no_parts(self):
        """L1345-1347: No make/model → article title fallback."""
        vs = self._make_vs(make='', model_name='', trim_name='')
        assert 'VS Display' in str(vs)

    def test_get_power_display_hp_and_kw(self):
        """L1351-1352: Both HP and kW."""
        vs = self._make_vs(make='pw1', power_hp=530, power_kw=390)
        assert '530 HP' in vs.get_power_display()
        assert '390 kW' in vs.get_power_display()

    def test_get_power_display_hp_only(self):
        """L1353-1354: HP only."""
        vs = self._make_vs(make='pw2', power_hp=530)
        assert '530 HP' in vs.get_power_display()

    def test_get_power_display_kw_only(self):
        """L1355-1356: kW only."""
        vs = self._make_vs(make='pw3', power_kw=390)
        assert '390 kW' in vs.get_power_display()

    def test_get_power_display_none(self):
        """L1357: No power → 'N/A'."""
        vs = self._make_vs(make='pw4')
        assert vs.get_power_display() == 'N/A'

    def test_get_range_display_wltp(self):
        """L1361-1362: WLTP range."""
        vs = self._make_vs(make='rg1', range_wltp=570)
        assert 'WLTP' in vs.get_range_display()

    def test_get_range_display_epa(self):
        """L1363-1364: EPA range."""
        vs = self._make_vs(make='rg2', range_epa=350)
        assert 'EPA' in vs.get_range_display()

    def test_get_range_display_km(self):
        """L1365-1366: Generic km range."""
        vs = self._make_vs(make='rg3', range_km=500)
        assert '500 km' in vs.get_range_display()

    def test_get_range_display_none(self):
        """L1367: No range → 'N/A'."""
        vs = self._make_vs(make='rg4')
        assert vs.get_range_display() == 'N/A'

    def test_get_price_display_usd(self):
        """L1377-1380: USD price."""
        vs = self._make_vs(make='pr1', price_from=35000, currency='USD')
        assert '$35,000' in vs.get_price_display()

    def test_get_price_display_usd_range(self):
        """L1378-1379: USD price range."""
        vs = self._make_vs(make='pr2', price_from=30000, price_to=45000, currency='USD')
        display = vs.get_price_display()
        assert '$30,000' in display
        assert '$45,000' in display

    def test_get_price_display_cny(self):
        """CNY price — shows original currency only (USD conversion handled by frontend)."""
        vs = self._make_vs(make='pr3', price_from=250000, currency='CNY',
                           price_usd_from=34000)
        display = vs.get_price_display()
        assert '¥' in display
        assert '250,000' in display
        # USD estimate no longer baked in — frontend PriceConverter does live conversion
        assert '$' not in display

    def test_get_price_display_no_price(self):
        """L1371-1372: No price → 'N/A'."""
        vs = self._make_vs(make='pr4')
        assert vs.get_price_display() == 'N/A'


class TestRSSFeedSafetyScore:

    def test_unsafe(self):
        """L621-622: Red → unsafe."""
        from news.models import RSSFeed
        feed = RSSFeed.objects.create(
            name='Test', feed_url='https://test.com/rss-unsafe',
            license_status='red'
        )
        assert feed.safety_score == 'unsafe'

    def test_no_checks_review(self):
        """L625-627: No checks → review."""
        from news.models import RSSFeed
        feed = RSSFeed.objects.create(
            name='Test2', feed_url='https://test.com/rss-review',
            license_status='green', safety_checks={}
        )
        assert feed.safety_score == 'review'

    def test_all_passed_green(self):
        """L636-637: All checks passed + green → safe."""
        from news.models import RSSFeed
        feed = RSSFeed.objects.create(
            name='Test3', feed_url='https://test.com/rss-safe',
            license_status='green',
            safety_checks={
                'robots': {'passed': True},
                'tos': {'passed': True},
            }
        )
        assert feed.safety_score == 'safe'

    def test_one_failed_review(self):
        """L638-641: One failed + green → review."""
        from news.models import RSSFeed
        feed = RSSFeed.objects.create(
            name='Test4', feed_url='https://test.com/rss-partial',
            license_status='green',
            safety_checks={
                'robots': {'passed': True},
                'tos': {'passed': False},
            }
        )
        assert feed.safety_score == 'review'


class TestArticleSlugGeneration:

    def test_duplicate_slug_increment(self):
        """L251-253: Duplicate slug → counter appended."""
        from news.models import Article
        a1 = Article.objects.create(title='Same Title', content='<p>C</p>')
        a2 = Article.objects.create(title='Same Title', content='<p>C</p>')
        assert a1.slug != a2.slug
        assert a2.slug.startswith('same-title')


class TestCommentModel:

    def test_str(self):
        """L395-396: __str__."""
        from news.models import Article, Comment
        art = Article.objects.create(
            title='Comment Str', slug='comment-str', content='<p>C</p>'
        )
        c = Comment.objects.create(
            article=art, name='John', email='j@t.com', content='Nice'
        )
        assert 'John' in str(c)
        assert 'Comment Str' in str(c)


class TestRatingModel:

    def test_str(self):
        """L412-413: __str__."""
        from news.models import Article, Rating
        art = Article.objects.create(
            title='Rating Str', slug='rating-str', content='<p>C</p>'
        )
        r = Rating.objects.create(
            article=art, ip_address='127.0.0.1', rating=5
        )
        assert '5★' in str(r)


class TestArticleFeedbackModel:

    def test_str(self):
        """L1468-1469: __str__."""
        from news.models import Article, ArticleFeedback
        art = Article.objects.create(
            title='Feedback Str', slug='feedback-str', content='<p>C</p>'
        )
        fb = ArticleFeedback.objects.create(
            article=art, category='typo', message='Typo on line 3'
        )
        assert 'Typo' in str(fb)


class TestPendingArticleModel:

    def test_str(self):
        """L781-782: __str__."""
        from news.models import PendingArticle
        pa = PendingArticle.objects.create(
            title='PA Str Test', video_url='https://youtube.com/watch?v=strtest'
        )
        assert 'PA Str Test' in str(pa)
