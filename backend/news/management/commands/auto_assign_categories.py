"""
Management command to auto-assign categories to articles without categories.
"""
from django.core.management.base import BaseCommand
from news.models import Article, Category
import re


class Command(BaseCommand):
    help = 'Auto-assign categories to articles based on content analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be assigned without actually assigning',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write('\n🔍 Finding articles without categories...\n')
        
        # Get articles without categories
        articles_without_categories = Article.objects.filter(
            categories__isnull=True,
            status='published'
        ).distinct()
        
        total = articles_without_categories.count()
        self.stdout.write(f'📊 Found {total} articles without categories\n')
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ All articles have categories!'))
            return
        
        # Get all categories
        categories = {cat.name.lower(): cat for cat in Category.objects.all()}
        
        # Category keywords mapping (matching production categories)
        category_keywords = {
            'evs': ['electric', 'ev', 'battery', 'charging', 'tesla', 'rivian', 'lucid', 'byd', 'plug-in', 'phev', 'hybrid'],
            'reviews': ['review', 'test drive', 'first drive', 'road test', 'tested', 'verdict', 'pros', 'cons'],
            'technology': ['technology', 'tech', 'autonomous', 'self-driving', 'ai', 'software', 'infotainment', 'connectivity', 'adas', 'sensor'],
            'comparisons': ['vs', 'versus', 'comparison', 'compare', 'compared', 'better than', 'face-off'],
            'motorsport': ['racing', 'race', 'motorsport', 'f1', 'formula', 'nascar', 'rally', 'track', 'championship', 'prix'],
            'industry': ['sales', 'market', 'production', 'manufacturing', 'factory', 'plant', 'earnings', 'revenue', 'ceo', 'executive'],
            'modifications': ['tuning', 'modified', 'custom', 'aftermarket', 'upgrade', 'performance parts', 'mod', 'tuned'],
            'classics': ['classic', 'vintage', 'retro', 'heritage', 'restoration', 'restored', 'collector', 'historic'],
            'news': ['recall', 'safety', 'nhtsa', 'crash test', 'rating', 'award', 'announcement', 'unveiled', 'debut', 'launch'],
        }
        
        assigned_count = 0
        
        for article in articles_without_categories:
            # Combine title and content for analysis
            text = f"{article.title} {article.content}".lower()
            
            # Find matching categories
            matches = []
            for cat_name, keywords in category_keywords.items():
                if cat_name.lower() in categories:
                    score = sum(1 for keyword in keywords if keyword in text)
                    if score > 0:
                        matches.append((cat_name, score))
            
            # Sort by score and take top match
            if matches:
                matches.sort(key=lambda x: x[1], reverse=True)
                best_match = matches[0][0]
                category = categories[best_match.lower()]
                
                if dry_run:
                    self.stdout.write(
                        f"  Would assign '{category.name}' to: {article.title[:60]}"
                    )
                else:
                    article.categories.add(category)
                    assigned_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Assigned '{category.name}' to: {article.title[:60]}")
                    )
            else:
                # Default to "News" if no match
                default_cat = categories.get('news')
                if default_cat:
                    if dry_run:
                        self.stdout.write(
                            f"  Would assign 'News' (default) to: {article.title[:60]}"
                        )
                    else:
                        article.categories.add(default_cat)
                        assigned_count += 1
                        self.stdout.write(
                            f"  ✓ Assigned 'News' (default) to: {article.title[:60]}"
                        )
        
        if dry_run:
            self.stdout.write('\n' + self.style.WARNING('🔍 DRY RUN - No categories assigned'))
        else:
            self.stdout.write('\n' + self.style.SUCCESS(f'✅ Successfully assigned categories to {assigned_count} articles!'))
