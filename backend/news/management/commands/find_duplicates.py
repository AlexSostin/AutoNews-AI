"""
Management command to find duplicate articles based on car specs (make + model).
Shows groups of articles that cover the same car, so you can decide which to keep.
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from news.models import Article, CarSpecification


class Command(BaseCommand):
    help = 'Find duplicate articles based on car make + model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-count',
            type=int,
            default=2,
            help='Minimum number of articles to be considered a duplicate group (default: 2)',
        )

    def handle(self, *args, **options):
        min_count = options['min_count']
        
        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n=== Scanning for Duplicate Articles ===\n'
        ))
        
        # Find make+model combinations that appear more than once
        duplicates = (
            CarSpecification.objects
            .exclude(make='')
            .exclude(make='Not specified')
            .exclude(model='')
            .exclude(model='Not specified')
            .values('make', 'model')
            .annotate(count=Count('id'))
            .filter(count__gte=min_count)
            .order_by('-count')
        )
        
        if not duplicates:
            self.stdout.write(self.style.SUCCESS(
                '  ✅ No duplicate articles found!\n'
            ))
            return
        
        total_dupes = 0
        
        for group in duplicates:
            make = group['make']
            model = group['model']
            count = group['count']
            total_dupes += count - 1  # First one is the "original"
            
            self.stdout.write(self.style.WARNING(
                f'\n  🔍 {make} {model} — {count} articles:'
            ))
            
            # Get all articles for this make+model
            specs = CarSpecification.objects.filter(
                make=make, model=model
            ).select_related('article').order_by('article__created_at')
            
            for i, spec in enumerate(specs):
                article = spec.article
                trim_info = f" ({spec.trim})" if spec.trim and spec.trim != 'Not specified' else ""
                status = "📄" if i == 0 else "⚠️ "
                
                views = getattr(article, 'views', 0)
                
                self.stdout.write(
                    f'    {status} #{article.id}: "{article.title}"{trim_info}'
                    f'\n        Created: {article.created_at.strftime("%Y-%m-%d")} | '
                    f'Views: {views} | '
                    f'Published: {"✅" if article.is_published else "❌"}'
                    f'\n        URL: /articles/{article.slug}'
                )
        
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n=== Summary ==='
        ))
        self.stdout.write(
            f'  Duplicate groups: {len(duplicates)}\n'
            f'  Extra articles (potential duplicates): {total_dupes}\n'
            f'\n  💡 Review each group and delete duplicates via admin panel.\n'
            f'  Keep the article with more views or better content.\n'
        )
