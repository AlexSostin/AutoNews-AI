import pytest
import datetime
from django.utils import timezone
from news.models.vehicles import VehicleSpecs
from news.models.system import CompetitorPairLog
from news.models import Article
from ai_engine.modules.competitor_lookup import get_competitor_context

@pytest.fixture
def base_competitors(db):
    """Create a set of VehicleSpecs for testing competitor lookup logic."""
    # Subject car will be a $50k Electric SUV, 400 hp
    
    # 1. Direct competitor: $48k, Electric, SUV (Wait, diff is 2k / 50k = 4%, so < 10% -> 3x bonus)
    VehicleSpecs.objects.create(
        make="Tesla", model_name="Model Y", body_type="SUV", fuel_type="Electric",
        price_usd_from=48000, power_hp=390, range_wltp=500
    )
    # 2. Close competitor: $42k, Electric, SUV (diff is 8k / 50k = 16%, so < 20% -> 2x bonus)
    VehicleSpecs.objects.create(
        make="Ford", model_name="Mach-E", body_type="SUV", fuel_type="Electric",
        price_usd_from=42000, power_hp=350, range_wltp=450
    )
    # 3. Same segment, but outside bonus range: $41k, Electric, SUV (diff is 18%, we'll test bounds)
    VehicleSpecs.objects.create(
        make="Hyundai", model_name="Ioniq 5", body_type="SUV", fuel_type="Electric",
        price_usd_from=41000, power_hp=320, range_wltp=480
    )
    # 4. Too expensive (Outside tight limit): $70k (50k * 1.35 = 67.5k max)
    VehicleSpecs.objects.create(
        make="Rivian", model_name="R1S", body_type="SUV", fuel_type="Electric",
        price_usd_from=70000, power_hp=600, range_wltp=500
    )
    # 5. Too cheap (Outside tight limit): $30k (50k * 0.70 = 35k min)
    VehicleSpecs.objects.create(
        make="Chevrolet", model_name="Equinox EV", body_type="SUV", fuel_type="Electric",
        price_usd_from=30000, power_hp=210, range_wltp=400
    )
    # 6. No price specified (Should be kept by benefit of doubt)
    VehicleSpecs.objects.create(
        make="Fisker", model_name="Ocean", body_type="SUV", fuel_type="Electric",
        price_usd_from=None, power_hp=400, range_wltp=560
    )
    # 7. Same make as subject (Should be excluded initially)
    VehicleSpecs.objects.create(
        make="SubjectMake", model_name="OtherModel", body_type="SUV", fuel_type="Electric",
        price_usd_from=49000, power_hp=410, range_wltp=490
    )
    
@pytest.mark.django_db
class TestCompetitorLookup:
    
    def test_price_bounds_and_exclusion(self, base_competitors):
        """Test that cars outside the 0.7 - 1.35x bounds are strictly excluded."""
        block, comps = get_competitor_context(
            make="SubjectMake", model_name="SubjectModel",
            fuel_type="Electric", body_type="SUV",
            power_hp=400, price_usd=50000, max_competitors=10
        )
        
        makes = [c["make"] for c in comps]
        
        # Rivian ($70k > 1.35x) and Chevy ($30k < 0.7x) should be excluded
        assert "Rivian" not in makes
        assert "Chevrolet" not in makes
        
        # Unpriced car (Fisker) is filtered out in Step 4 if valid priced cars exist,
        # so it won't be in the final list here.
        assert "Fisker" not in makes
        
        # SubjectMake may be kept if eligible, but we enforce brand diversity.
        # It's an array of makes, SubjectMake might be in there if there's space.
        # But wait, SubjectMake ("SubjectMake") matches the subject make ("SubjectMake")!
        # Step 1 explicitly excludes the exact subject make + model match.
        # Here we have "SubjectMake OtherModel" vs "SubjectMake SubjectModel".
        # It SHOULD be included in candidate pool, but Step 7 (brand diversity) might exclude it
        # IF we picked another car first. But we only have a few cars.
        
        # Direct ones should be present
        assert "Tesla" in makes
        assert "Ford" in makes
        assert "Hyundai" in makes

    def test_price_bonus_weighting(self, db):
        """Test that the weighting algorithm actually prefers 3x and 2x bonus cars statistically."""
        # Create identical cars except for price (all same body, fuel, specs length)
        # We'll run it 100 times picking 1 car and verify distributions.
        VehicleSpecs.objects.create(make="A", model_name="M", price_usd_from=100000, body_type="Sedan", fuel_type="Gas", power_hp=300) # Exact match (0% diff -> 3x)
        VehicleSpecs.objects.create(make="B", model_name="M", price_usd_from=85000, body_type="Sedan", fuel_type="Gas", power_hp=300)  # 15% diff -> 2x
        VehicleSpecs.objects.create(make="C", model_name="M", price_usd_from=75000, body_type="Sedan", fuel_type="Gas", power_hp=300)  # 25% diff -> 1x
        
        counts = {"A": 0, "B": 0, "C": 0}
        
        for _ in range(500):
            block, comps = get_competitor_context(
                make="Subj", model_name="M", fuel_type="Gas", body_type="Sedan",
                power_hp=300, price_usd=100000, max_competitors=1
            )
            # Pick only 1 to see who wins the random.choices weighted draw
            if comps:
                counts[comps[0]["make"]] += 1
                
        # With weights ~ 3.0 (A), 2.0 (B), 1.0 (C)
        # A should win roughly 50% (3/6), B 33% (2/6), C 16% (1/6)
        # We just assert A > B > C by a safe margin
        assert counts["A"] > counts["B"]
        assert counts["B"] > counts["C"]

    def test_cooldown_filter(self, db):
        """Test that cars used >= 2 times in 7 days are excluded."""
        VehicleSpecs.objects.create(make="Tesla", model_name="Model 3", price_usd_from=40000, body_type="Sedan", fuel_type="Electric")
        VehicleSpecs.objects.create(make="Polestar", model_name="2", price_usd_from=45000, body_type="Sedan", fuel_type="Electric")
        
        article = Article.objects.create(title="Test")
        
        # Use Tesla twice today
        CompetitorPairLog.objects.create(article=article, subject_make="X", subject_model="Y", competitor_make="Tesla", competitor_model="Model 3")
        CompetitorPairLog.objects.create(article=article, subject_make="X", subject_model="Y", competitor_make="Tesla", competitor_model="Model 3")
        
        # Use Polestar once today
        CompetitorPairLog.objects.create(article=article, subject_make="X", subject_model="Y", competitor_make="Polestar", competitor_model="2")

        block, comps = get_competitor_context(
            make="X", model_name="Y", fuel_type="Electric", body_type="Sedan",
            price_usd=42000, max_competitors=2
        )
        
        makes = [c["make"] for c in comps]
        assert "Tesla" not in makes  # Excluded by cooldown
        assert "Polestar" in makes   # Kept

    def test_empty_database_safe(self, db):
        """Test that get_competitor_context is safe and returns empty string if no pool."""
        block, comps = get_competitor_context(make="Zeekr", model_name="9X")
        assert block == ""
        assert comps == []

    def test_engagement_score_logic(self, db):
        """Test that engagement ML scores (avg_engagement) are factored in without crashing."""
        VehicleSpecs.objects.create(make="Popular", model_name="Car", price_usd_from=20000, body_type="Hatchback")
        VehicleSpecs.objects.create(make="Boring", model_name="Car", price_usd_from=20000, body_type="Hatchback")
        
        article = Article.objects.create(title="Test2")
        
        # Popular car has great historical engagement
        CompetitorPairLog.objects.create(article=article, subject_make="X", subject_model="Y", competitor_make="Popular", competitor_model="Car", engagement_score_at_log=5.0)
        # Boring car has terrible engagement
        CompetitorPairLog.objects.create(article=article, subject_make="X", subject_model="Y", competitor_make="Boring", competitor_model="Car", engagement_score_at_log=0.1)

        block, comps = get_competitor_context(
            make="X", model_name="Z", body_type="Hatchback", price_usd=20000, max_competitors=2
        )
        
        # Both should be present since max_competitors is 2, just checking no crash
        # and checking that scores map logic runs
        makes = [c["make"] for c in comps]
        assert "Popular" in makes
        assert "Boring" in makes
