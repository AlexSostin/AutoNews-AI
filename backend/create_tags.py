import os
import sys
import django

# Setup Django Environment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from news.models import Tag
from django.utils.text import slugify

def create_tags():
    print("🚗 Populating Body Type Tags...")
    
    body_types = [
        "Sedan", "SUV", "Crossover", "Hatchback", "Coupe", 
        "Convertible", "Wagon", "Pickup Truck", "Minivan", 
        "Electric", "Hybrid", "Supercar", "Luxury", "Off-Road"
    ]
    
    created_count = 0
    for name in body_types:
        tag, created = Tag.objects.get_or_create(
            name=name,
            defaults={'slug': slugify(name)}
        )
        if created:
            print(f"  ✓ Created: {name}")
            created_count += 1
        else:
            print(f"  - Exists: {name}")
            
    print(f"\n✨ Done! Created {created_count} new tags.")

if __name__ == "__main__":
    create_tags()
