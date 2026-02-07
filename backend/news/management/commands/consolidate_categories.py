"""
Management command to consolidate article categories.

Merges:
- "Electric Vehicles" -> "EVs"
- "Industry" -> "News"

Deletes:
- "Comparisons"
"""
from django.core.management.base import BaseCommand
from news.models import Category, Article


class Command(BaseCommand):
    help = 'Consolidate article categories from 8 to 5 core categories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get categories
        try:
            evs = Category.objects.get(slug='evs')
            electric_vehicles = Category.objects.get(slug='electric-vehicles')
            news = Category.objects.get(slug='news')
            industry = Category.objects.get(slug='industry')
            comparisons = Category.objects.get(slug='comparisons')
        except Category.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f'Category not found: {e}'))
            return
        
        # 1. Merge "Electric Vehicles" -> "EVs"
        ev_articles = Article.objects.filter(categories=electric_vehicles)
        ev_count = ev_articles.count()
        
        self.stdout.write(f'\n1. Merging "Electric Vehicles" -> "EVs"')
        self.stdout.write(f'   Found {ev_count} articles with "Electric Vehicles" category')
        
        if not dry_run and ev_count > 0:
            for article in ev_articles:
                article.categories.add(evs)
                article.categories.remove(electric_vehicles)
            self.stdout.write(self.style.SUCCESS(f'   ✓ Migrated {ev_count} articles'))
        
        # 2. Merge "Industry" -> "News"
        industry_articles = Article.objects.filter(categories=industry)
        industry_count = industry_articles.count()
        
        self.stdout.write(f'\n2. Merging "Industry" -> "News"')
        self.stdout.write(f'   Found {industry_count} articles with "Industry" category')
        
        if not dry_run and industry_count > 0:
            for article in industry_articles:
                article.categories.add(news)
                article.categories.remove(industry)
            self.stdout.write(self.style.SUCCESS(f'   ✓ Migrated {industry_count} articles'))
        
        # 3. Remove "Comparisons" category from articles
        comparison_articles = Article.objects.filter(categories=comparisons)
        comparison_count = comparison_articles.count()
        
        self.stdout.write(f'\n3. Removing "Comparisons" category')
        self.stdout.write(f'   Found {comparison_count} articles with "Comparisons" category')
        
        if not dry_run and comparison_count > 0:
            for article in comparison_articles:
                article.categories.remove(comparisons)
                # Ensure article has at least one category
                if article.categories.count() == 0:
                    article.categories.add(news)  # Default to News
                    self.stdout.write(f'   → Article "{article.title}" had no categories, added "News"')
            self.stdout.write(self.style.SUCCESS(f'   ✓ Removed "Comparisons" from {comparison_count} articles'))
        
        # 4. Delete old categories
        if not dry_run:
            self.stdout.write(f'\n4. Deleting old categories')
            electric_vehicles.delete()
            self.stdout.write(self.style.SUCCESS('   ✓ Deleted "Electric Vehicles"'))
            industry.delete()
            self.stdout.write(self.style.SUCCESS('   ✓ Deleted "Industry"'))
            comparisons.delete()
            self.stdout.write(self.style.SUCCESS('   ✓ Deleted "Comparisons"'))
        else:
            self.stdout.write(f'\n4. Would delete: "Electric Vehicles", "Industry", "Comparisons"')
        
        # 5. Show final category list
        self.stdout.write(f'\n5. Final categories:')
        final_categories = Category.objects.all().order_by('name')
        for cat in final_categories:
            article_count = cat.articles.count()
            self.stdout.write(f'   - {cat.name} ({cat.slug}): {article_count} articles')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN COMPLETE - Run without --dry-run to apply changes'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Category consolidation complete!'))
