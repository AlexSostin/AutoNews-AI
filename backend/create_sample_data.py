import os
import django
from django.core.files.base import ContentFile
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from news.models import Article, Category, Tag

def create_sample_data():
    print("Creating sample data...")

    # Categories
    cat_news, _ = Category.objects.get_or_create(name="News")
    cat_reviews, _ = Category.objects.get_or_create(name="Reviews")
    cat_evs, _ = Category.objects.get_or_create(name="EVs")

    # Tags
    tag_tesla, _ = Tag.objects.get_or_create(name="Tesla")
    tag_concept, _ = Tag.objects.get_or_create(name="Concept")
    tag_suv, _ = Tag.objects.get_or_create(name="SUV")

    # Articles
    # 1. Tesla Article
    if not Article.objects.filter(title="Tesla Model Y 2026: What We Know").exists():
        a1 = Article.objects.create(
            title="Tesla Model Y 2026: What We Know",
            summary="The refresh of the world's best-selling car is just around the corner, featuring the new 'Juniper' design language.",
            content="""
            <p>The 2026 Tesla Model Y, codenamed Juniper, represents a significant update to the electric SUV that has taken the world by storm.</p>
            <h2>New Design</h2>
            <p>Borrowing heavily from the Model 3 Highland refresh, the new Model Y features slimmer headlights, a removed front bumper fog light housing for better aerodynamics, and a new rear light bar.</p>
            <h2>Interior</h2>
            <p>Inside, the stalks are gone, replaced by steering wheel buttons. The screen is brighter, and the rear passengers now get their own 8-inch display.</p>
            """,
            category=cat_evs,
            is_published=True,
            seo_title="2026 Tesla Model Y Juniper Refresh Details",
            seo_description="Everything we know about the 2026 Tesla Model Y Juniper refresh."
        )
        a1.tags.add(tag_tesla, tag_suv)
        print("Created Tesla article.")

    # 2. Scout Article
    if not Article.objects.filter(title="Volkswagen Scout Revival").exists():
        a2 = Article.objects.create(
            title="Volkswagen Scout Revival",
            summary="VW is bringing back the legendary Scout nameplate for a new line of rugged electric off-roaders.",
            content="""
            <p>Volkswagen is reviving the Scout brand purely for electric vehicles. The new Terra pickup and Traveler SUV are set to challenge Rivian and Ford.</p>
            """,
            category=cat_news,
            is_published=True
        )
        a2.tags.add(tag_concept, tag_suv)
        print("Created Scout article.")

    print("Sample data creation complete.")

if __name__ == "__main__":
    create_sample_data()
