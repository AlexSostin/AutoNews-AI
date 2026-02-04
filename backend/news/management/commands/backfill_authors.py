"""
Backfill author information for existing articles from their PendingArticle sources.
"""
from django.core.management.base import BaseCommand
from news.models import Article, PendingArticle


class Command(BaseCommand):
    help = 'Backfill author information for existing articles from PendingArticle'

    def handle(self, *args, **options):
        # Find all published pending articles with a linked article
        pending_articles = PendingArticle.objects.filter(
            status='published',
            published_article__isnull=False,
            youtube_channel__isnull=False
        ).select_related('youtube_channel', 'published_article')

        updated_count = 0
        skipped_count = 0

        for pending in pending_articles:
            article = pending.published_article
            
            # Skip if article already has author info
            if article.author_name:
                skipped_count += 1
                continue
            
            # Update author info from channel
            article.author_name = pending.youtube_channel.name
            article.author_channel_url = pending.youtube_channel.channel_url
            article.save(update_fields=['author_name', 'author_channel_url'])
            
            updated_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'✓ Updated article #{article.id}: {article.title[:50]} -> {article.author_name}')
            )

        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Backfill complete! Updated: {updated_count}, Skipped: {skipped_count}')
        )
