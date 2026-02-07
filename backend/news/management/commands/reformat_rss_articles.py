"""
Django management command to reformat old RSS pending articles.

Converts plain text content to HTML with proper formatting:
- Wraps paragraphs in <p> tags
- Converts URLs to clickable links
- Adds source attribution footer

Usage:
    python manage.py reformat_rss_articles
    python manage.py reformat_rss_articles --dry-run
"""
from django.core.management.base import BaseCommand
from news.models import PendingArticle
from ai_engine.modules.rss_aggregator import RSSAggregator
import re


class Command(BaseCommand):
    help = 'Reformat old RSS pending articles with HTML formatting'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test mode - show what would be updated without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reformat all RSS articles, even if they already have HTML tags',
        )

    def is_plain_text(self, content: str) -> bool:
        """
        Check if content is plain text (no HTML tags).
        
        Returns True if content has no <p>, <h1>, <h2>, etc. tags.
        """
        # Check for common HTML tags
        html_tags = ['<p>', '<h1>', '<h2>', '<h3>', '<div>', '<article>']
        return not any(tag in content for tag in html_tags)

    def handle(self, *args, **options):
        aggregator = RSSAggregator()
        
        # Find all RSS pending articles
        rss_articles = PendingArticle.objects.filter(
            rss_feed__isnull=False,
            status='pending'
        ).select_related('rss_feed')
        
        if not rss_articles.exists():
            self.stdout.write(self.style.WARNING('No RSS pending articles found'))
            return
        
        self.stdout.write(f'\n📝 Found {rss_articles.count()} RSS pending articles')
        
        # Filter for plain text articles (unless --force is used)
        if options['force']:
            articles_to_update = list(rss_articles)
            self.stdout.write(f'🔄 Force mode: will reformat ALL {len(articles_to_update)} articles\n')
        else:
            articles_to_update = []
            for article in rss_articles:
                if self.is_plain_text(article.content):
                    articles_to_update.append(article)
            
            if not articles_to_update:
                self.stdout.write(self.style.SUCCESS('\n✅ All articles already have HTML formatting!'))
                self.stdout.write('Use --force to reformat all articles anyway.\n')
                return
            
            self.stdout.write(f'🔍 Found {len(articles_to_update)} articles with plain text content\n')
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('[DRY RUN MODE - No changes will be made]\n'))
            for article in articles_to_update[:5]:  # Show first 5
                self.stdout.write(f'  • {article.title[:70]}')
            if len(articles_to_update) > 5:
                self.stdout.write(f'  ... and {len(articles_to_update) - 5} more')
            return
        
        # Update articles
        updated_count = 0
        
        for article in articles_to_update:
            try:
                # Check if content has markdown (###) - convert to HTML first
                has_markdown = '###' in article.content and '<h2>' not in article.content
                if has_markdown:
                    try:
                        import markdown
                        self.stdout.write(f'  Converting markdown to HTML: {article.title[:50]}')
                        article.content = markdown.markdown(article.content, extensions=['fenced_code', 'tables'])
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  ⚠ Markdown conversion failed: {e}'))
                
                # Check if content already has proper HTML structure (from AI or markdown conversion)
                has_html_structure = any(tag in article.content for tag in ['<h2>', '<h3>', '<ul>', '<ol>'])
                
                if has_html_structure:
                    # Content already has HTML structure - just clean publisher mentions
                    # Extract plain text for excerpt only
                    plain_text_for_excerpt = re.sub(r'<[^>]+>', '', article.content).strip()
                    plain_text_for_excerpt = aggregator.clean_publisher_mentions(plain_text_for_excerpt)
                    excerpt = plain_text_for_excerpt[:500] if len(plain_text_for_excerpt) > 500 else plain_text_for_excerpt
                    
                    # Keep HTML content as-is, just clean publisher mentions in text nodes
                    html_content = article.content
                else:
                    # Plain text content - convert to HTML
                    text = re.sub(r'<[^>]+>', '', article.content)
                    text = text.strip()
                    text = aggregator.clean_publisher_mentions(text)
                    excerpt = text[:500] if len(text) > 500 else text
                    html_content = aggregator.convert_plain_text_to_html(text)
                
                # Add source attribution (only once!)
                if article.source_url and article.rss_feed:
                    source_name = article.rss_feed.name or 'Source'
                    html_content += f'\n<p class="source-attribution" style="margin-top: 2rem; padding: 1rem; background: #f3f4f6; border-left: 4px solid #3b82f6; font-size: 0.875rem;">\n    <strong>Source:</strong> {source_name}. \n    <a href="{article.source_url}" target="_blank" rel="noopener noreferrer" style="color: #3b82f6; text-decoration: underline;">View original article</a>\n</p>'
                
                # Update article content AND excerpt
                article.content = html_content
                article.excerpt = excerpt
                article.save(update_fields=['content', 'excerpt'])
                
                updated_count += 1
                self.stdout.write(f'  ✓ Updated: {article.title[:70]}')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error updating {article.title[:50]}: {e}'))
        
        self.stdout.write(f'\n✅ Successfully updated {updated_count} articles!\n')
