"""
Django management command to clean markdown remnants from published articles.

Fixes:
- *** (bold+italic) → <strong><em>...</em></strong>
- ** (bold) → <strong>...</strong>
- * list items → <ul><li>...</li></ul>

Only modifies articles that actually contain markdown remnants.
Always run with --dry-run first to preview changes.

Usage:
    python manage.py cleanup_markdown_remnants --dry-run
    python manage.py cleanup_markdown_remnants
"""
from django.core.management.base import BaseCommand
from news.models import Article
import re


class Command(BaseCommand):
    help = 'Clean markdown remnants (**, ***, * lists) from published article content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without modifying the database',
        )
        parser.add_argument(
            '--article-id',
            type=int,
            help='Fix a specific article by ID (for testing)',
        )

    def has_markdown_remnants(self, content):
        """
        Check if content has markdown patterns that should be HTML.
        """
        if not content:
            return False
        # **text** or ***text*** (markdown bold/italic)
        if re.search(r'\*\*\*(.+?)\*\*\*', content):
            return True
        if re.search(r'\*\*(.+?)\*\*', content):
            return True
        # Markdown list markers: lines starting with * or -  followed by text
        # but NOT inside already valid <ul>/<li> blocks
        if re.search(r'^\*\s+', content, re.MULTILINE):
            return True
        return False

    def convert_markdown_lists(self, content):
        """
        Convert markdown-style list items (* text) to proper <ul><li> HTML.
        Handles consecutive list items and wraps them in a single <ul>.
        Does NOT touch lines that are already inside <ul> tags.
        """
        lines = content.split('\n')
        result = []
        in_list = False
        inside_html_ul = False
        
        for line in lines:
            stripped = line.strip()
            
            # Track if we're inside an HTML <ul> block (don't touch those)
            if '<ul>' in stripped:
                inside_html_ul = True
            if '</ul>' in stripped:
                inside_html_ul = False
                
            # Check if this is a markdown list item (not inside an HTML list)
            md_match = re.match(r'^\*\s+(.+)$', stripped)
            
            if md_match and not inside_html_ul:
                item_content = md_match.group(1)
                if not in_list:
                    # Start a new list
                    result.append('<ul>')
                    in_list = True
                result.append(f'    <li>{item_content}</li>')
            else:
                if in_list:
                    # Close the list
                    result.append('</ul>')
                    in_list = False
                result.append(line)
        
        # Close any unclosed list at the end
        if in_list:
            result.append('</ul>')
        
        return '\n'.join(result)

    def clean_markdown(self, content):
        """
        Convert all markdown remnants to HTML tags.
        Order: lists first, then bold/italic.
        """
        original = content
        changes = []
        
        # Step 1: Convert markdown list items to <ul><li>
        has_md_lists = bool(re.search(r'^\*\s+', content, re.MULTILINE))
        if has_md_lists:
            content = self.convert_markdown_lists(content)
            list_count = content.count('<li>') - original.count('<li>')
            if list_count > 0:
                changes.append(f'{list_count} list items')
        
        # Step 2: Convert bold/italic markers
        # ***bold italic*** → <strong><em>...</em></strong>
        content = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', content)
        # **bold** → <strong>...</strong>
        content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
        
        if original != content:
            bold_italic_new = len(re.findall(r'<strong><em>', content)) - len(re.findall(r'<strong><em>', original))
            bold_new = len(re.findall(r'<strong>', content)) - len(re.findall(r'<strong>', original)) - bold_italic_new
            if bold_italic_new > 0:
                changes.append(f'{bold_italic_new} bold+italic')
            if bold_new > 0:
                changes.append(f'{bold_new} bold')
        
        return content, changes

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        article_id = options.get('article_id')

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN MODE - No changes will be made]\n'))

        # Get articles to check
        if article_id:
            articles = Article.objects.filter(id=article_id)
            if not articles.exists():
                self.stdout.write(self.style.ERROR(f'Article with ID {article_id} not found'))
                return
        else:
            # Only published articles with content
            articles = Article.objects.filter(
                is_published=True,
                content__isnull=False
            ).exclude(content='')

        self.stdout.write(f'\n🔍 Scanning {articles.count()} articles for markdown remnants...\n')

        affected = []
        for article in articles.iterator():
            if self.has_markdown_remnants(article.content):
                affected.append(article)

        if not affected:
            self.stdout.write(self.style.SUCCESS('\n✅ No markdown remnants found! All articles are clean.'))
            return

        self.stdout.write(f'\n⚠️  Found {len(affected)} articles with markdown remnants:\n')

        updated_count = 0
        for article in affected:
            cleaned_content, changes = self.clean_markdown(article.content)
            changes_str = ', '.join(changes) if changes else 'cleaned'

            if dry_run:
                self.stdout.write(f'  📄 [{article.id}] {article.title[:60]}')
                self.stdout.write(f'      → Would fix: {changes_str}')
                # Show a preview
                for match in re.finditer(r'(\*\s+\S.{0,50}|\*\*\*?.{0,50}\*\*\*?)', article.content):
                    preview = match.group(0)[:70]
                    self.stdout.write(f'      → Found: {preview}')
                    break
            else:
                try:
                    article.content = cleaned_content
                    article.save(update_fields=['content'])
                    updated_count += 1
                    self.stdout.write(f'  ✓ [{article.id}] {article.title[:60]} ({changes_str})')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'  ✗ [{article.id}] {article.title[:50]}: {e}'
                    ))

        if dry_run:
            self.stdout.write(f'\n📊 {len(affected)} articles would be updated.')
            self.stdout.write('Run without --dry-run to apply changes.\n')
        else:
            self.stdout.write(f'\n✅ Successfully cleaned {updated_count} articles!\n')
