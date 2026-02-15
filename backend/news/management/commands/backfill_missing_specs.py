"""
Backfill CarSpecification for articles that don't have one,
or refresh ALL existing specs with AI re-analysis.
Uses shared spec_extractor module for AI extraction and normalization.
Also optionally deletes duplicate articles.
"""
from django.core.management.base import BaseCommand
from news.models import Article, CarSpecification
from news.spec_extractor import (
    extract_specs_from_content, save_specs_for_article, SKIP_ARTICLE_IDS,
)


class Command(BaseCommand):
    help = 'Create/update CarSpecification for articles using AI extraction'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would happen')
        parser.add_argument('--refresh-all', action='store_true',
                          help='Re-analyze ALL articles, updating existing specs')
        parser.add_argument('--article-id', nargs='+', type=int,
                          help='Process only specific article IDs')
        parser.add_argument('--delete-dupes', nargs='+', type=int, help='Article IDs to delete')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        refresh_all = options['refresh_all']

        # Step 1: Delete duplicate articles if specified
        delete_ids = options.get('delete_dupes') or []
        if delete_ids:
            for aid in delete_ids:
                try:
                    article = Article.objects.get(id=aid)
                    self.stdout.write(f'🗑️  Deleting [{aid}] "{article.title[:60]}"')
                    if not dry_run:
                        article.delete()
                except Article.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'  Article {aid} not found'))

        # Step 2: Find target articles
        article_ids = options.get('article_id')
        if article_ids:
            # Force-process specific articles (even if they already have specs)
            articles = (
                Article.objects
                .filter(id__in=article_ids, is_published=True)
                .order_by('id')
            )
            self.stdout.write(f'\n🎯 Processing {articles.count()} specific article(s): {article_ids}')
        elif refresh_all:
            articles = (
                Article.objects
                .filter(is_published=True)
                .exclude(id__in=SKIP_ARTICLE_IDS)
                .order_by('id')
            )
            self.stdout.write(f'\n🔄 REFRESH ALL mode: processing {articles.count()} articles')
        else:
            articles_with_specs = set(
                CarSpecification.objects.values_list('article_id', flat=True)
            )
            articles = (
                Article.objects
                .filter(is_published=True)
                .exclude(id__in=articles_with_specs)
                .exclude(id__in=SKIP_ARTICLE_IDS)
                .order_by('id')
            )
            self.stdout.write(f'\n📊 Found {articles.count()} articles without CarSpecification')

        total = articles.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ Nothing to process!'))
            return

        created = 0
        updated = 0

        for article in articles:
            try:
                self.stdout.write(f'\n🔍 [{article.id}] "{article.title[:60]}"')

                specs = extract_specs_from_content(article)
                if not specs:
                    self.stdout.write(self.style.WARNING('  ⚠️ Could not extract specs'))
                    continue

                make = specs.get('make', '')
                model = specs.get('model', '')
                if not make or make == 'Not specified':
                    self.stdout.write(self.style.WARNING(f'  ⚠️ No make extracted, skipping'))
                    continue

                self.stdout.write(
                    f'  → {make} {model} | engine={specs.get("engine","?")} | '
                    f'hp={specs.get("horsepower","?")} | drivetrain={specs.get("drivetrain","?")} | '
                    f'price={specs.get("price","?")}'
                )

                if not dry_run:
                    existing = CarSpecification.objects.filter(article=article).exists()
                    result = save_specs_for_article(article, specs)
                    if result:
                        if existing:
                            self.stdout.write(f'  ✅ Updated spec')
                            updated += 1
                        else:
                            self.stdout.write(f'  ✅ Created new spec')
                            created += 1
                    else:
                        self.stdout.write(self.style.WARNING(f'  ⚠️ Could not save specs'))
                else:
                    existing = CarSpecification.objects.filter(article=article).exists()
                    if existing:
                        self.stdout.write(f'  [DRY] Would update')
                        updated += 1
                    else:
                        self.stdout.write(f'  [DRY] Would create')
                        created += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'  ❌ Error processing [{article.id}]: {e}'))
                continue

        action_verb = 'Would' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ {action_verb} Created {created}, Updated {updated} CarSpecification records'
        ))
