from django.core.management.base import BaseCommand
from news.models import Category

class Command(BaseCommand):
    help = 'Creates default categories from AI analyzer logic'

    def handle(self, *args, **kwargs):
        categories = [
            # (Name, Slug, Description)
            ('News', 'news', 'Latest automotive news, announcements, and reveals'),
            ('Reviews', 'reviews', 'In-depth car reviews and test drives'),
            ('EVs', 'evs', 'Electric vehicles, hybrids, and green technology'),
            ('Technology', 'technology', 'New automotive tech, software, and autonomous systems'),
            ('Industry', 'industry', 'Automobile industry analysis, production, and sales'),
            ('Comparisons', 'comparisons', 'Head-to-head model comparisons'),
        ]

        for name, slug, description in categories:
            cat, created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {name}'))
            else:
                self.stdout.write(f'Category already exists: {name}')
