from django.core.management.base import BaseCommand
from news.models import Article, Tag
from ai_engine.modules.smart_tagger import assign_tags

class Command(BaseCommand):
    help = 'Tests the Smart Tagger on the most recent article'

    def handle(self, *args, **options):
        article = Article.objects.order_by('-created_at').first()
        if not article:
            self.stdout.write(self.style.ERROR("No articles found in DB."))
            return

        self.stdout.write(self.style.HTTP_INFO(f"Testing Smart Tagger on: {article.title}"))
        
        # Test the module
        tag_ids = assign_tags(article.title, article.content)
        
        if not tag_ids:
            self.stdout.write(self.style.ERROR("Smart Tagger returned empty list or failed."))
            return

        tags = Tag.objects.filter(id__in=tag_ids)
        self.stdout.write(self.style.SUCCESS(f"Extracted {len(tags)} tags!"))
        for t in tags:
            self.stdout.write(f" - {t.name} (Group: {t.group.name if t.group else 'None'})")
        
        # We don't save to the DB in this test script, just output the results
