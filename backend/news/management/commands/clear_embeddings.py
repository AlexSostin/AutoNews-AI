"""
Management command to clear all article embeddings before model migration.

Run BEFORE switching to a new Gemini Embedding model version,
since embedding spaces between versions are incompatible.

Usage:
    python manage.py clear_embeddings              # Preview what will be cleared
    python manage.py clear_embeddings --confirm    # Actually delete embeddings

After clearing, re-index with:
    python manage.py index_articles --rebuild
"""

from django.core.management.base import BaseCommand
from news.models import ArticleEmbedding


class Command(BaseCommand):
    help = (
        'Clear all ArticleEmbedding rows and flush FAISS/Redis cache. '
        'Required when upgrading to an incompatible embedding model version.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Actually delete embeddings (without this flag, only shows what would be deleted)',
        )

    def handle(self, *args, **options):
        confirm = options['confirm']

        count = ArticleEmbedding.objects.count()
        self.stdout.write(f'📊 Found {count} ArticleEmbedding rows in database')

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✅ Nothing to clear — database already empty'))
        elif not confirm:
            self.stdout.write(self.style.WARNING(
                f'⚠️  DRY RUN: Would delete {count} embeddings.\n'
                f'   Run with --confirm to actually delete.'
            ))
            return
        else:
            # Delete all embeddings from PostgreSQL
            deleted, _ = ArticleEmbedding.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'🗑️  Deleted {deleted} embeddings from PostgreSQL'))

        # Flush FAISS Redis cache
        try:
            from django.core.cache import cache
            from ai_engine.modules.vector_search import FAISS_REDIS_KEY, EMBEDDING_CACHE_PREFIX
            cache.delete(FAISS_REDIS_KEY)
            self.stdout.write('🧹 Flushed FAISS Redis cache')

            # Also clear any cached query embeddings
            # Note: cache.delete_pattern requires django-redis and is optional
            try:
                cache.delete_pattern(f'{EMBEDDING_CACHE_PREFIX}*')
                self.stdout.write('🧹 Flushed embedding query cache')
            except (AttributeError, Exception):
                self.stdout.write(self.style.WARNING('   (Could not clear query cache — delete_pattern not supported)'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️  Could not flush Redis cache: {e}'))

        # Delete FAISS disk index
        try:
            import shutil
            from pathlib import Path
            index_path = Path('data/vector_db/faiss_index')
            if index_path.exists():
                shutil.rmtree(index_path)
                self.stdout.write('🧹 Deleted FAISS disk index')
            else:
                self.stdout.write('   (No FAISS disk index found)')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️  Could not delete FAISS disk index: {e}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ All embeddings cleared!'))
        self.stdout.write(self.style.SUCCESS(
            '🚀 Now run: python manage.py index_articles --rebuild'
        ))
        self.stdout.write(self.style.WARNING(
            '   Note: New model is gemini-embedding-2-preview (multimodal, 8K context)'
        ))
