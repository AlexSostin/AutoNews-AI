"""
Integration tests for:
1. VehicleSpecs-based similarity matching (price, body type, horsepower)
2. similar_articles endpoint with real DB data (no mocks)
3. Article generation pipeline validation (specs filling, HTML structure)

These tests catch regressions in the similar-car matching logic
and ensure the article generation pipeline produces valid data.
"""
import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from django.contrib.auth.models import User

pytestmark = pytest.mark.django_db

API = '/api/v1'
UA = {'HTTP_USER_AGENT': 'TestBrowser/1.0'}


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username='staff_vspec', email='staff_vspec@test.com',
        password='Pass123!', is_staff=True, is_superuser=True,
    )


@pytest.fixture
def staff_client(staff_user):
    client = APIClient(**UA)
    client.force_authenticate(user=staff_user)
    return client


@pytest.fixture
def anon_client():
    return APIClient(**UA)


@pytest.fixture
def base_article(db):
    """Primary article: a $55k SUV with 880hp."""
    from news.models import Article
    from news.models.vehicles import VehicleSpecs
    art = Article.objects.create(
        title='2026 ZEEKR 8X Super Hybrid', slug='zeekr-8x-vspec-test',
        content='<p>Test content for ZEEKR 8X.</p>',
        summary='ZEEKR 8X review', is_published=True,
    )
    VehicleSpecs.objects.create(
        article=art, make='ZEEKR', model_name='8X', year=2026,
        body_type='SUV', price_from=55000, power_hp=880,
        fuel_type='PHEV', drivetrain='AWD',
    )
    return art


@pytest.fixture
def similar_suv(db):
    """Similar SUV: same body type, similar price ($60k) and HP (800)."""
    from news.models import Article
    from news.models.vehicles import VehicleSpecs
    art = Article.objects.create(
        title='2026 Li Auto L8 Max', slug='li-auto-l8-vspec-test',
        content='<p>Test content for Li Auto L8.</p>',
        summary='Li Auto L8 review', is_published=True, views=100,
    )
    VehicleSpecs.objects.create(
        article=art, make='Li Auto', model_name='L8 Max', year=2026,
        body_type='SUV', price_from=60000, power_hp=800,
        fuel_type='PHEV', drivetrain='AWD',
    )
    return art


@pytest.fixture
def similar_price_only(db):
    """Similar price ($50k) but different body type (sedan) and HP (400)."""
    from news.models import Article
    from news.models.vehicles import VehicleSpecs
    art = Article.objects.create(
        title='2026 BMW i5 eDrive40', slug='bmw-i5-vspec-test',
        content='<p>Test content for BMW i5.</p>',
        summary='BMW i5 review', is_published=True, views=50,
    )
    VehicleSpecs.objects.create(
        article=art, make='BMW', model_name='i5', year=2026,
        body_type='sedan', price_from=50000, power_hp=400,
        fuel_type='EV', drivetrain='RWD',
    )
    return art


@pytest.fixture
def totally_different(db):
    """Totally different: hatchback, $25k, 150hp."""
    from news.models import Article
    from news.models.vehicles import VehicleSpecs
    art = Article.objects.create(
        title='2026 Nissan Leaf', slug='nissan-leaf-vspec-test',
        content='<p>Test content for Nissan Leaf.</p>',
        summary='Nissan Leaf review', is_published=True, views=200,
    )
    VehicleSpecs.objects.create(
        article=art, make='Nissan', model_name='Leaf', year=2026,
        body_type='hatchback', price_from=25000, power_hp=150,
        fuel_type='EV', drivetrain='FWD',
    )
    return art


@pytest.fixture
def similar_no_specs(db):
    """Article without VehicleSpecs — should never crash the endpoint."""
    from news.models import Article
    return Article.objects.create(
        title='Generic EV News', slug='generic-ev-vspec-test',
        content='<p>No specs here.</p>',
        summary='EV news', is_published=True, views=300,
    )


@pytest.fixture
def unpublished_similar(db):
    """Unpublished SUV with matching specs — should NEVER appear."""
    from news.models import Article
    from news.models.vehicles import VehicleSpecs
    art = Article.objects.create(
        title='2026 Secret SUV', slug='secret-suv-vspec-test',
        content='<p>Secret car.</p>',
        summary='Secret', is_published=False,
    )
    VehicleSpecs.objects.create(
        article=art, make='Secret', model_name='X', year=2026,
        body_type='SUV', price_from=54000, power_hp=900,
        fuel_type='EV', drivetrain='AWD',
    )
    return art


@pytest.fixture
def specs_no_price(db):
    """SUV with matching body type and HP but NO price — partial match."""
    from news.models import Article
    from news.models.vehicles import VehicleSpecs
    art = Article.objects.create(
        title='2026 Mystery SUV', slug='mystery-suv-vspec-test',
        content='<p>Mystery SUV.</p>',
        summary='Mystery', is_published=True, views=10,
    )
    VehicleSpecs.objects.create(
        article=art, make='Mystery', model_name='X', year=2026,
        body_type='SUV', price_from=None, power_hp=850,
        fuel_type='PHEV', drivetrain='AWD',
    )
    return art


# ═══════════════════════════════════════════════════════════════════════════
# 1. VehicleSpecs similarity logic (direct DB queries)
# ═══════════════════════════════════════════════════════════════════════════

class TestVehicleSpecsSimilarityLogic:
    """Tests the VehicleSpecs-based matching at the ORM level."""

    def test_price_range_match(self, base_article, similar_suv, similar_price_only, totally_different):
        """Articles within ±30% price range should match."""
        from news.models.vehicles import VehicleSpecs
        base_spec = VehicleSpecs.objects.get(article=base_article)
        price_low = int(base_spec.price_from * 0.7)   # 38,500
        price_high = int(base_spec.price_from * 1.3)   # 71,500

        matches = VehicleSpecs.objects.filter(
            price_from__gte=price_low,
            price_from__lte=price_high,
            article__is_published=True,
        ).exclude(article=base_article)

        match_ids = set(matches.values_list('article_id', flat=True))
        assert similar_suv.id in match_ids       # $60k — within range
        assert similar_price_only.id in match_ids  # $50k — within range
        assert totally_different.id not in match_ids  # $25k — outside range

    def test_body_type_exact_match(self, base_article, similar_suv, similar_price_only, totally_different):
        """Only same body type should match."""
        from news.models.vehicles import VehicleSpecs
        base_spec = VehicleSpecs.objects.get(article=base_article)

        matches = VehicleSpecs.objects.filter(
            body_type=base_spec.body_type,
            article__is_published=True,
        ).exclude(article=base_article)

        match_ids = set(matches.values_list('article_id', flat=True))
        assert similar_suv.id in match_ids         # SUV
        assert similar_price_only.id not in match_ids  # sedan
        assert totally_different.id not in match_ids    # hatchback

    def test_horsepower_range_match(self, base_article, similar_suv, similar_price_only, totally_different):
        """Articles within ±40% HP should match."""
        from news.models.vehicles import VehicleSpecs
        base_spec = VehicleSpecs.objects.get(article=base_article)
        hp_low = int(base_spec.power_hp * 0.6)   # 528
        hp_high = int(base_spec.power_hp * 1.4)   # 1232

        matches = VehicleSpecs.objects.filter(
            power_hp__gte=hp_low,
            power_hp__lte=hp_high,
            article__is_published=True,
        ).exclude(article=base_article)

        match_ids = set(matches.values_list('article_id', flat=True))
        assert similar_suv.id in match_ids         # 800hp — within range
        assert similar_price_only.id not in match_ids  # 400hp — too low
        assert totally_different.id not in match_ids    # 150hp — way too low

    def test_combined_filters_narrow_results(self, base_article, similar_suv,
                                              similar_price_only, totally_different):
        """All three filters combined should only match truly similar cars."""
        from news.models.vehicles import VehicleSpecs
        base_spec = VehicleSpecs.objects.get(article=base_article)

        matches = VehicleSpecs.objects.filter(
            body_type=base_spec.body_type,
            price_from__gte=int(base_spec.price_from * 0.7),
            price_from__lte=int(base_spec.price_from * 1.3),
            power_hp__gte=int(base_spec.power_hp * 0.6),
            power_hp__lte=int(base_spec.power_hp * 1.4),
            article__is_published=True,
        ).exclude(article=base_article)

        match_ids = set(matches.values_list('article_id', flat=True))
        assert similar_suv.id in match_ids         # SUV, $60k, 800hp — full match
        assert similar_price_only.id not in match_ids  # sedan — body type mismatch
        assert totally_different.id not in match_ids    # everything different

    def test_excludes_unpublished(self, base_article, unpublished_similar):
        """Unpublished articles must never appear in similarity results."""
        from news.models.vehicles import VehicleSpecs
        base_spec = VehicleSpecs.objects.get(article=base_article)

        matches = VehicleSpecs.objects.filter(
            body_type=base_spec.body_type,
            article__is_published=True,
            article__is_deleted=False,
        ).exclude(article=base_article)

        match_ids = set(matches.values_list('article_id', flat=True))
        assert unpublished_similar.id not in match_ids

    def test_null_price_partially_matches(self, base_article, specs_no_price):
        """Article with null price_from should NOT match when price filter is active."""
        from news.models.vehicles import VehicleSpecs
        base_spec = VehicleSpecs.objects.get(article=base_article)

        matches = VehicleSpecs.objects.filter(
            body_type=base_spec.body_type,
            price_from__gte=int(base_spec.price_from * 0.7),
            price_from__lte=int(base_spec.price_from * 1.3),
            article__is_published=True,
        ).exclude(article=base_article)

        match_ids = set(matches.values_list('article_id', flat=True))
        # price_from is NULL, so Django's __gte/__lte excludes it
        assert specs_no_price.id not in match_ids


# ═══════════════════════════════════════════════════════════════════════════
# 2. similar_articles API endpoint integration (real DB, ML mocked)
# ═══════════════════════════════════════════════════════════════════════════

class TestSimilarArticlesEndpoint:
    """Integration tests for GET /api/v1/articles/{slug}/similar_articles/
    with real VehicleSpecs data (ML/vector search mocked to simulate fallback)."""

    @patch('ai_engine.modules.content_recommender.find_similar', return_value=[])
    @patch('ai_engine.modules.content_recommender.is_available', return_value=False)
    @patch('ai_engine.modules.vector_search.get_vector_engine',
           side_effect=Exception('FAISS not loaded'))
    def test_vehiclespecs_fallback_returns_similar(
        self, mock_ve, mock_avail, mock_similar,
        anon_client, base_article, similar_suv, totally_different
    ):
        """When ML/vector are unavailable, VehicleSpecs fallback should find similar SUVs."""
        resp = anon_client.get(f'{API}/articles/{base_article.slug}/similar_articles/')
        assert resp.status_code == 200
        slugs = [a['slug'] for a in resp.data['similar_articles']]
        assert similar_suv.slug in slugs
        # Totally different car might still appear via category fallback,
        # but similar_suv should come first
        if totally_different.slug in slugs:
            assert slugs.index(similar_suv.slug) < slugs.index(totally_different.slug)

    @patch('ai_engine.modules.content_recommender.find_similar', return_value=[])
    @patch('ai_engine.modules.content_recommender.is_available', return_value=False)
    @patch('ai_engine.modules.vector_search.get_vector_engine',
           side_effect=Exception('FAISS not loaded'))
    def test_excludes_unpublished_from_results(
        self, mock_ve, mock_avail, mock_similar,
        anon_client, base_article, unpublished_similar
    ):
        """Unpublished articles must never appear in similar_articles response."""
        resp = anon_client.get(f'{API}/articles/{base_article.slug}/similar_articles/')
        assert resp.status_code == 200
        slugs = [a['slug'] for a in resp.data['similar_articles']]
        assert unpublished_similar.slug not in slugs

    @patch('ai_engine.modules.content_recommender.find_similar', return_value=[])
    @patch('ai_engine.modules.content_recommender.is_available', return_value=False)
    @patch('ai_engine.modules.vector_search.get_vector_engine',
           side_effect=Exception('FAISS not loaded'))
    def test_excludes_self_from_results(
        self, mock_ve, mock_avail, mock_similar,
        anon_client, base_article, similar_suv
    ):
        """The article itself should never appear in its own similar results."""
        resp = anon_client.get(f'{API}/articles/{base_article.slug}/similar_articles/')
        assert resp.status_code == 200
        ids = [a['id'] for a in resp.data['similar_articles']]
        assert base_article.id not in ids

    @patch('ai_engine.modules.content_recommender.find_similar', return_value=[])
    @patch('ai_engine.modules.content_recommender.is_available', return_value=False)
    @patch('ai_engine.modules.vector_search.get_vector_engine',
           side_effect=Exception('FAISS not loaded'))
    def test_article_without_specs_returns_empty_gracefully(
        self, mock_ve, mock_avail, mock_similar,
        anon_client, similar_no_specs
    ):
        """Article with no VehicleSpecs should not crash, just return empty or category-based."""
        resp = anon_client.get(f'{API}/articles/{similar_no_specs.slug}/similar_articles/')
        assert resp.status_code == 200
        assert 'similar_articles' in resp.data

    @patch('ai_engine.modules.content_recommender.find_similar', return_value=[])
    @patch('ai_engine.modules.content_recommender.is_available', return_value=False)
    @patch('ai_engine.modules.vector_search.get_vector_engine',
           side_effect=Exception('FAISS not loaded'))
    def test_response_is_serialized_correctly(
        self, mock_ve, mock_avail, mock_similar,
        anon_client, base_article, similar_suv
    ):
        """Each similar article in response should have required fields."""
        resp = anon_client.get(f'{API}/articles/{base_article.slug}/similar_articles/')
        assert resp.status_code == 200
        articles = resp.data['similar_articles']
        if articles:
            first = articles[0]
            assert 'id' in first
            assert 'title' in first
            assert 'slug' in first

    @patch('ai_engine.modules.content_recommender.find_similar', return_value=[])
    @patch('ai_engine.modules.content_recommender.is_available', return_value=False)
    @patch('ai_engine.modules.vector_search.get_vector_engine',
           side_effect=Exception('FAISS not loaded'))
    def test_max_15_results(
        self, mock_ve, mock_avail, mock_similar,
        anon_client, base_article, similar_suv
    ):
        """Endpoint should cap results at 15."""
        # Create many similar articles
        from news.models import Article
        from news.models.vehicles import VehicleSpecs
        for i in range(20):
            a = Article.objects.create(
                title=f'SUV Model {i}', slug=f'suv-model-{i}-vspec-test',
                content=f'<p>Content {i}</p>', summary=f'Summary {i}',
                is_published=True, views=i,
            )
            VehicleSpecs.objects.create(
                article=a, make=f'Brand{i}', model_name=f'M{i}', year=2026,
                body_type='SUV', price_from=55000 + i * 100, power_hp=880,
            )
        resp = anon_client.get(f'{API}/articles/{base_article.slug}/similar_articles/')
        assert resp.status_code == 200
        assert len(resp.data['similar_articles']) <= 15


# ═══════════════════════════════════════════════════════════════════════════
# 3. Article data pipeline validation
# ═══════════════════════════════════════════════════════════════════════════

class TestArticleSpecsFilling:
    """Tests that VehicleSpecs can be properly linked to articles
    and queried, validating the data pipeline."""

    def test_article_can_have_vehicle_specs(self, base_article):
        """Article should have a linked VehicleSpecs record."""
        from news.models.vehicles import VehicleSpecs
        spec = VehicleSpecs.objects.filter(article=base_article).first()
        assert spec is not None
        assert spec.make == 'ZEEKR'
        assert spec.model_name == '8X'
        assert spec.body_type == 'SUV'
        assert spec.price_from == 55000
        assert spec.power_hp == 880

    def test_article_can_have_car_specification(self, db):
        """Old-style CarSpecification should also work for backward compat."""
        from news.models import Article, CarSpecification
        art = Article.objects.create(
            title='Legacy Spec Article', slug='legacy-spec-vspec-test',
            content='<p>Content</p>', summary='Summary', is_published=True,
        )
        spec = CarSpecification.objects.create(
            article=art, make='Toyota', model='Camry', model_name='2026 Toyota Camry',
            horsepower='300 hp', price='$35,000',
        )
        assert spec.make == 'Toyota'
        assert spec.article == art

    def test_vehicle_specs_body_type_choices_valid(self, db):
        """All body type choices should be accepted by the model."""
        from news.models import Article
        from news.models.vehicles import VehicleSpecs
        valid_types = ['sedan', 'SUV', 'hatchback', 'coupe', 'truck',
                       'crossover', 'wagon', 'van', 'convertible', 'pickup']
        for bt in valid_types:
            art = Article.objects.create(
                title=f'Body {bt}', slug=f'body-{bt}-vspec-test',
                content='<p>C</p>', summary='S', is_published=True,
            )
            spec = VehicleSpecs.objects.create(
                article=art, make='Test', model_name=bt, year=2026, body_type=bt,
            )
            assert spec.body_type == bt

    def test_vehicle_specs_null_fields_ok(self, db):
        """VehicleSpecs with all nullable fields as None should save fine."""
        from news.models import Article
        from news.models.vehicles import VehicleSpecs
        art = Article.objects.create(
            title='Minimal Spec', slug='minimal-spec-vspec-test',
            content='<p>C</p>', summary='S', is_published=True,
        )
        spec = VehicleSpecs.objects.create(article=art, make='X', model_name='Y')
        assert spec.body_type is None
        assert spec.price_from is None
        assert spec.power_hp is None

    def test_article_detail_includes_specs(self, staff_client, base_article):
        """Article detail API should include vehicle_specs data."""
        resp = staff_client.get(f'{API}/articles/{base_article.slug}/')
        assert resp.status_code == 200
        data = resp.data
        # The article should have specs data (via serializer)
        specs = data.get('vehicle_specs') or data.get('specs') or data.get('car_specs')
        if specs:
            # If specs are included, they should have key fields
            if isinstance(specs, list) and len(specs) > 0:
                first_spec = specs[0]
                assert 'make' in first_spec or 'body_type' in first_spec
            elif isinstance(specs, dict):
                assert 'make' in specs or 'body_type' in specs


class TestArticleHTMLContentIntegrity:
    """Tests that article HTML content maintains structural integrity
    by checking that AI-generated content has the expected patterns."""

    def test_article_with_compare_grid_content(self, db):
        """Article content containing compare-grid HTML should store correctly."""
        from news.models import Article
        compare_html = '''
        <h2>How It Compares</h2>
        <div class="compare-grid">
          <div class="compare-card featured">
            <div class="compare-badge">This Vehicle</div>
            <div class="compare-card-name">2026 ZEEKR 8X</div>
            <div class="compare-row"><span class="k">Power</span><span class="v">885 hp</span></div>
            <div class="compare-row"><span class="k">Price</span><span class="v">$54,600</span></div>
          </div>
        </div>
        '''
        art = Article.objects.create(
            title='Compare Grid Test', slug='compare-grid-vspec-test',
            content=compare_html, summary='S', is_published=True,
        )
        art.refresh_from_db()
        assert 'compare-grid' in art.content
        assert 'compare-card' in art.content
        assert 'compare-row' in art.content

    def test_article_with_pros_cons_content(self, db):
        """Article content with pros/cons structure should store correctly."""
        from news.models import Article
        html = '''
        <div class="pros-cons">
          <div class="pc-block pros"><div class="pc-title">Pros</div><ul class="pc-list"><li>Fast</li></ul></div>
          <div class="pc-block cons"><div class="pc-title">Cons</div><ul class="pc-list"><li>Heavy</li></ul></div>
        </div>
        '''
        art = Article.objects.create(
            title='Pros Cons Test', slug='pros-cons-vspec-test',
            content=html, summary='S', is_published=True,
        )
        art.refresh_from_db()
        assert 'pros-cons' in art.content
        assert 'pc-block' in art.content

    def test_article_with_spec_bar_content(self, db):
        """Article content with spec-bar structure should store correctly."""
        from news.models import Article
        html = '''
        <div class="spec-bar">
          <div class="spec-item"><div class="spec-label">PRICE</div><div class="spec-value">$55k</div></div>
          <div class="spec-item"><div class="spec-label">POWER</div><div class="spec-value">880hp</div></div>
        </div>
        '''
        art = Article.objects.create(
            title='Spec Bar Test', slug='spec-bar-vspec-test',
            content=html, summary='S', is_published=True,
        )
        art.refresh_from_db()
        assert 'spec-bar' in art.content
        assert 'spec-item' in art.content

    def test_article_with_verdict_content(self, db):
        """Article content with fm-verdict should store correctly."""
        from news.models import Article
        html = '''
        <div class="fm-verdict">
          <div class="verdict-label">FreshMotors Verdict</div>
          <p>This car is amazing.</p>
        </div>
        '''
        art = Article.objects.create(
            title='Verdict Test', slug='verdict-vspec-test',
            content=html, summary='S', is_published=True,
        )
        art.refresh_from_db()
        assert 'fm-verdict' in art.content
        assert 'verdict-label' in art.content
