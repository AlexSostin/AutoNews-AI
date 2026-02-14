"""
Fix articles that have youtube_url but no video embed in their content.
Adds the YouTube iframe at the beginning of the article content.
"""
import re
from django.core.management.base import BaseCommand
from news.models import Article


class Command(BaseCommand):
    help = 'Add missing YouTube video embeds to articles'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show changes without saving')
        parser.add_argument('--article-id', type=int, help='Fix specific article by ID')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        article_id = options.get('article_id')

        # Find articles with youtube_url but no iframe in content
        articles = Article.objects.filter(
            youtube_url__isnull=False,
        ).exclude(youtube_url='')

        if article_id:
            articles = articles.filter(id=article_id)

        fixed = 0
        for article in articles:
            # Skip if already has iframe
            if '<iframe' in (article.content or ''):
                continue

            # Extract video ID from youtube_url
            video_id = self._extract_video_id(article.youtube_url)
            if not video_id:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️ [{article.id}] Could not extract video ID from: {article.youtube_url}'
                ))
                continue

            # Build embed HTML
            embed_html = (
                f'<div class="video-container" style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;margin-bottom:24px">'
                f'<iframe src="https://www.youtube.com/embed/{video_id}" '
                f'style="position:absolute;top:0;left:0;width:100%;height:100%" '
                f'frameborder="0" allowfullscreen loading="lazy"></iframe></div>\n'
            )

            # Also save youtube_video_id if missing
            save_fields = ['content']
            if not article.youtube_video_id:
                article.youtube_video_id = video_id
                save_fields.append('youtube_video_id')

            # Insert embed after first <h2> tag (title)
            content = article.content or ''
            h2_match = re.search(r'</h2>', content)
            if h2_match:
                insert_pos = h2_match.end()
                new_content = content[:insert_pos] + '\n' + embed_html + content[insert_pos:]
            else:
                new_content = embed_html + content

            self.stdout.write(
                f'  ✅ [{article.id}] {article.title[:60]} — video_id={video_id}'
            )

            if not dry_run:
                article.content = new_content
                article.save(update_fields=save_fields)

            fixed += 1

        action = "Would fix" if dry_run else "Fixed"
        self.stdout.write(self.style.SUCCESS(f'\n{action} {fixed} articles'))

    def _extract_video_id(self, url):
        """Extract YouTube video ID from various URL formats."""
        if not url:
            return None
        patterns = [
            r'(?:v=|\/embed\/|\/v\/|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
