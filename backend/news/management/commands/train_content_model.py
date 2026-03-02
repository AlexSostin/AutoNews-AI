"""
Train the Content Recommender ML model.

Builds TF-IDF model from all published articles for:
- Tag prediction
- Category prediction
- Similar articles

Usage: python manage.py train_content_model [--force]
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Train the Content Recommender TF-IDF model from published articles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild even if data has not changed',
        )

    def handle(self, *args, **options):
        from ai_engine.modules.content_recommender import build, get_model_info

        self.stdout.write('🧠 Training Content Recommender model...\n')

        result = build(force=options['force'])

        if result.get('skipped'):
            self.stdout.write(self.style.WARNING(
                '⏭️  Data unchanged — model rebuild skipped. Use --force to rebuild anyway.'
            ))
            return

        if not result.get('success'):
            self.stdout.write(self.style.ERROR(
                f'❌ Build failed: {result.get("reason", "Unknown error")}'
            ))
            return

        self.stdout.write(self.style.SUCCESS(
            f'✅ Model trained successfully!\n'
            f'   📊 Articles: {result["article_count"]}\n'
            f'   📝 Features: {result["vocabulary_size"]}\n'
            f'   🏷️  Tags: {result["unique_tags"]}\n'
            f'   📂 Categories: {result["unique_categories"]}\n'
            f'   💾 Saved to: {result["model_path"]}'
        ))

        # Quick sanity check
        info = get_model_info()
        self.stdout.write(f'   📦 Model size: {info.get("model_size_kb", "?")} KB')
