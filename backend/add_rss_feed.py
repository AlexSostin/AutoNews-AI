#!/usr/bin/env python
"""
Quick script to add Car and Driver RSS feed to database
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from news.models import RSSFeed, Category

# Get or create category
category, _ = Category.objects.get_or_create(
    name='Electric Vehicles',
    defaults={'slug': 'electric-vehicles', 'description': 'EV and hybrid news'}
)

# Create RSS feed
feed, created = RSSFeed.objects.get_or_create(
    feed_url='https://www.caranddriver.com/rss/all.xml',
    defaults={
        'name': 'Car and Driver',
        'website_url': 'https://www.caranddriver.com',
        'source_type': 'media',
        'is_enabled': True,
        'auto_publish': False,
        'default_category': category,
        'logo_url': 'https://hips.hearstapps.com/hmg-prod/images/cd-logo-1200x630-1581109928.png',
        'description': 'Car and Driver automotive news and reviews'
    }
)

if created:
    print(f'✓ Created RSS Feed: {feed.name} (ID: {feed.id})')
else:
    print(f'✓ RSS Feed already exists: {feed.name} (ID: {feed.id})')
    
print(f'Feed URL: {feed.feed_url}')
print(f'Category: {feed.default_category.name if feed.default_category else "None"}')
print(f'Status: {"Enabled" if feed.is_enabled else "Disabled"}')
