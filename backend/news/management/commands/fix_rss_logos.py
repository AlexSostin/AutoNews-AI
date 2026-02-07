"""
Management command to fix broken RSS feed logos.
"""
from django.core.management.base import BaseCommand
from news.models import RSSFeed


class Command(BaseCommand):
    help = 'Fix broken RSS feed logo URLs'

    def handle(self, *args, **options):
        # Working logo URLs
        logo_fixes = {
            'Electrek Tesla': 'https://electrek.co/wp-content/themes/electrek/images/electrek-logo.svg',
            'Teslarati': 'https://www.teslarati.com/wp-content/uploads/2021/01/teslarati-logo-2021.png',
            'BMWBLOG': 'https://www.bmwblog.com/wp-content/themes/bmwblog/images/logo.svg',
            'Ford Media Center': 'https://upload.wikimedia.org/wikipedia/commons/3/3e/Ford_logo_flat.svg',
            'Toyota USA Newsroom': 'https://upload.wikimedia.org/wikipedia/commons/e/e7/Toyota.svg',
        }

        updated = 0
        for feed_name, new_logo_url in logo_fixes.items():
            try:
                feed = RSSFeed.objects.get(name=feed_name)
                old_url = feed.logo_url
                feed.logo_url = new_logo_url
                feed.save()
                
                self.stdout.write(self.style.SUCCESS(f'✓ Updated {feed_name}'))
                self.stdout.write(f'  Old: {old_url}')
                self.stdout.write(f'  New: {new_logo_url}')
                updated += 1
            except RSSFeed.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'⚠ Feed not found: {feed_name}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error updating {feed_name}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'\n✅ Updated {updated} RSS feed logos'))
