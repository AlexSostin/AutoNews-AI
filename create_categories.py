import os
import sys
import django

# Setup Django
sys.path.append('c:/Projects/Auto_News')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from news.models import Category

# Create categories
categories = [
    ('News', 'news'),
    ('Reviews', 'reviews'),
    ('EVs', 'evs'),
    ('Technology', 'technology'),
    ('Industry', 'industry'),
    ('Classics', 'classics'),
    ('Motorsport', 'motorsport'),
    ('Modifications', 'modifications'),
    ('Comparisons', 'comparisons'),
]

for name, slug in categories:
    cat, created = Category.objects.get_or_create(name=name, defaults={'slug': slug})
    if created:
        print(f'✅ Created: {name}')
    else:
        print(f'✓ Already exists: {name}')

print('\n🎉 All categories ready!')
