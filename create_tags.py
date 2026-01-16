#!/usr/bin/env python
"""Script to create common automotive tags"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from news.models import Tag

# Common automotive tags
tags = [
    # Brands
    "Tesla", "BMW", "Mercedes-Benz", "Audi", "Porsche", "Toyota", "Honda",
    "Ford", "Chevrolet", "Volkswagen", "Nissan", "Hyundai", "Kia", "Mazda",
    "Volvo", "Jaguar", "Land Rover", "Lexus", "Genesis", "Rivian", "Lucid",
    
    # Vehicle Types
    "Sedan", "SUV", "Truck", "Coupe", "Convertible", "Hatchback", "Wagon",
    "Minivan", "Crossover", "Sports Car", "Supercar", "Hypercar",
    
    # Powertrain
    "Electric", "Hybrid", "Plug-in Hybrid", "Gasoline", "Diesel", "Hydrogen",
    "Battery", "EV", "ICE", "AWD", "4WD", "FWD", "RWD",
    
    # Technology
    "Autonomous", "Self-Driving", "Autopilot", "ADAS", "Safety", "AI",
    "Connected Car", "Infotainment", "CarPlay", "Android Auto",
    
    # Features
    "Performance", "Luxury", "Off-Road", "Towing", "Fuel Economy",
    "Fast Charging", "Range", "Interior", "Design", "Aerodynamics",
    
    # Categories
    "Review", "First Drive", "Test Drive", "Comparison", "Launch",
    "Concept", "Production", "Recall", "Update", "News", "Rumor",
    
    # Year Tags
    "2024", "2025", "2026", "2027", "2028",
    
    # Topics
    "Charging", "Infrastructure", "Policy", "Regulation", "Sales",
    "Market", "Industry", "Technology", "Innovation", "Sustainability",
    "Environment", "Carbon Neutral", "Zero Emission",
]

created_count = 0
existing_count = 0

for tag_name in tags:
    tag, created = Tag.objects.get_or_create(name=tag_name)
    if created:
        created_count += 1
        print(f"✅ Created: {tag_name}")
    else:
        existing_count += 1
        print(f"⏭️  Already exists: {tag_name}")

print(f"\n📊 Summary:")
print(f"   ✅ Created: {created_count}")
print(f"   ⏭️  Existed: {existing_count}")
print(f"   📝 Total tags in database: {Tag.objects.count()}")
