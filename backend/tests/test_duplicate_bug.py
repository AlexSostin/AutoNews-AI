import pytest
from news.models import Article
from ai_engine.modules.duplicate_checker import check_car_duplicate

@pytest.mark.django_db
def test_duplicate_06_11():
    Article.objects.create(
        title="2025 Avatr 11 EREV: The 1,065 km Range-Extended SUV Disrupting the Premium Market",
        slug="avatr-11",
        is_published=True
    )
    
    # Simulating specs for Avatr 06
    specs = {
        'make': 'Avatr',
        'model': '06',
        'trim': 'EV',
        'title': '2026 Avatr 06 EV Reveal'
    }
    
    result = check_car_duplicate(specs)
    print("Duplicate result:", result)
    assert result is None, "Should not be a duplicate!"
