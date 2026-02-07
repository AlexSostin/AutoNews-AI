"""
Management command to assign default categories to articles without categories.

This is needed after migrating from ForeignKey to ManyToMany categories field.
"""
from django.core.management.base import BaseCommand
from news.models import Article, Category, Tag


class Command(BaseCommand):
    help = 'Assign categories to articles based on their tags or default category'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--default-category',
            type=str,
            default='news',
            help='Default category slug to assign (default: news)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        default_slug = options['default_category']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get default category
        try:
            default_category = Category.objects.get(slug=default_slug)
        except Category.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Default category "{default_slug}" not found'))
            return
        
        # Category mapping based on tags
        category_keywords = {
            'evs': ['electric', 'ev', 'battery', 'charging', 'tesla', 'rivian', 'lucid'],
            'luxury': ['luxury', 'premium', 'mercedes', 'bmw', 'audi', 'porsche', 'bentley', 'rolls-royce'],
            'reviews': ['review', 'test', 'drive', 'comparison'],
            'technology': ['technology', 'autonomous', 'self-driving', 'software', 'ai', 'tech'],
        }
        
        # Get all categories
        categories = {cat.slug: cat for cat in Category.objects.all()}
        
        # Find articles without categories
        articles_without_cats = Article.objects.filter(categories__isnull=True).distinct()
        total_count = articles_without_cats.count()
        
        self.stdout.write(f'\nFound {total_count} articles without categories')
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('All articles already have categories!'))
            return
        
        assigned_counts = {slug: 0 for slug in categories.keys()}
        
        for article in articles_without_cats:
            assigned_category = None
            
            # Try to assign based on tags
            article_tags = article.tags.all()
            tag_names = ' '.join([tag.name.lower() for tag in article_tags])
            
            # Check each category's keywords
            for cat_slug, keywords in category_keywords.items():
                if cat_slug in categories:
                    for keyword in keywords:
                        if keyword in tag_names or keyword in article.title.lower():
                            assigned_category = categories[cat_slug]
                            break
                    if assigned_category:
                        break
            
            # If no match found, use default category
            if not assigned_category:
                assigned_category = default_category
            
            if not dry_run:
                article.categories.add(assigned_category)
            
            assigned_counts[assigned_category.slug] = assigned_counts.get(assigned_category.slug, 0) + 1
            
            self.stdout.write(f'  Article "{article.title[:50]}" → {assigned_category.name}')
        
        # Summary
        self.stdout.write(f'\n{"=" * 60}')
        self.stdout.write('Summary:')
        for slug, count in assigned_counts.items():
            if count > 0:
                self.stdout.write(f'  {categories[slug].name}: {count} articles')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN COMPLETE - Run without --dry-run to apply changes'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully assigned categories to {total_count} articles!'))
