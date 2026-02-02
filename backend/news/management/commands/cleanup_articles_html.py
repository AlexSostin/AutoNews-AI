from django.core.management.base import BaseCommand
from news.models import Article
import markdown
import re

class Command(BaseCommand):
    help = 'Clean up HTML formatting for all existing articles'

    def ensure_html_only(self, content):
        if not content:
            return content
        
        # If it already has list tags, it's likely fine
        if "<li>" in content and "<ul>" in content:
            return content

        # Fix "mashed" lists and other common markdown patterns
        if "*" in content or "-" in content or "#" in content or "**" in content:
            # Pre-processing for lists
            content = re.sub(r'\s+[\*\-]\s+', r'\n\n* ', content)
            
            # Convert to HTML
            html_content = markdown.markdown(content, extensions=['extra', 'sane_lists'])
            return html_content

        return content

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🧹 Starting HTML cleanup for all articles...'))
        articles = Article.objects.filter(is_deleted=False)
        count = 0
        
        for article in articles:
            updated = False
            
            # Clean main content
            new_content = self.ensure_html_only(article.content)
            if new_content != article.content:
                article.content = new_content
                updated = True
            
            if updated:
                # We use save() to ensure all signal/save logic applies
                # New image optimization logic will skip already optimized images
                article.save()
                count += 1
                self.stdout.write(self.style.SUCCESS(f'✅ Updated: {article.title}'))
                
        self.stdout.write(self.style.SUCCESS(f'\n✨ Done! Cleaned up {count} articles.'))
