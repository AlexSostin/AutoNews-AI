"""
Management command to update site settings from AutoNews to Fresh Motors
"""
from django.core.management.base import BaseCommand
from news.models import SiteSettings


class Command(BaseCommand):
    help = 'Update site settings to Fresh Motors branding'

    def handle(self, *args, **options):
        settings = SiteSettings.objects.first()
        
        if not settings:
            self.stdout.write(self.style.ERROR('No SiteSettings found!'))
            return
        
        # Update branding
        updates = {
            'about_page_title': 'About Fresh Motors',
            'about_page_content': '',  # Clear custom content to show default design
            'hero_title': 'Welcome to Fresh Motors',
            'hero_subtitle': 'Your premier source for automotive news, reviews, and insights',
            'footer_text': '© 2026 Fresh Motors. All rights reserved.',
        }
        
        for field, value in updates.items():
            old_value = getattr(settings, field)
            setattr(settings, field, value)
            self.stdout.write(
                self.style.SUCCESS(f'✅ Updated {field}:')
            )
            self.stdout.write(f'   Old: {old_value}')
            self.stdout.write(f'   New: {value}')
        
        settings.save()
        self.stdout.write(self.style.SUCCESS('\n🎉 Site settings updated successfully!'))
