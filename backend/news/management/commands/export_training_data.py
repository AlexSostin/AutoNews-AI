"""Export collected training data as JSONL for Gemini fine-tuning.

Usage:
    python manage.py export_training_data                  # all types
    python manage.py export_training_data --type generation  # article pairs only
    python manage.py export_training_data --type titles      # A/B winners only
    python manage.py export_training_data --output /tmp/training.jsonl

Output format (Gemini-compatible JSONL):
    {"text_input": "...", "output": "..."}
"""
import json
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Export training data as JSONL for Gemini fine-tuning'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            choices=['generation', 'titles', 'all'],
            default='all',
            help='Type of training data to export (default: all)',
        )
        parser.add_argument(
            '--output', '-o',
            default='training_data.jsonl',
            help='Output file path (default: training_data.jsonl)',
        )
        parser.add_argument(
            '--min-quality',
            type=float,
            default=0.0,
            help='Minimum capsule_score to include (0.0-1.0)',
        )

    def handle(self, *args, **options):
        data_type = options['type']
        output_path = options['output']
        min_quality = options['min_quality']
        total = 0

        with open(output_path, 'w', encoding='utf-8') as f:
            if data_type in ('generation', 'all'):
                total += self._export_generation_pairs(f, min_quality)

            if data_type in ('titles', 'all'):
                total += self._export_title_winners(f)

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Exported {total} training examples → {output_path}'
        ))

        if total < 20:
            self.stdout.write(self.style.WARNING(
                f'⚠️  Only {total} examples — Gemini fine-tuning needs at least 20 (recommended: 100+)'
            ))

    def _export_generation_pairs(self, f, min_quality):
        """Export article generation pairs as JSONL."""
        from news.models.system import TrainingPair

        pairs = TrainingPair.objects.filter(pair_type='generation').order_by('-created_at')
        count = 0

        for pair in pairs:
            # Filter by quality if specified
            capsule_score = (pair.quality_signals or {}).get('capsule_score')
            if min_quality > 0 and capsule_score is not None and capsule_score < min_quality:
                continue

            text_input = (
                f"Write a professional automotive article based on this content:\n\n"
                f"Title: {pair.input_title}\n\n"
                f"{pair.input_text[:8000]}"
            )
            output = (
                f"Title: {pair.output_title}\n\n"
                f"{pair.output_text[:8000]}"
            )

            line = json.dumps({
                'text_input': text_input,
                'output': output,
            }, ensure_ascii=False)
            f.write(line + '\n')
            count += 1

        self.stdout.write(f'  📝 Generation pairs: {count}')
        return count

    def _export_title_winners(self, f):
        """Export A/B test winner titles as JSONL."""
        from news.models.system import ArticleTitleVariant
        from news.models.content import Article

        # Get all winners with their losing counterparts
        winners = ArticleTitleVariant.objects.filter(
            is_winner=True
        ).select_related('article')

        count = 0
        for winner in winners:
            # Get original article title and losing variants
            losers = ArticleTitleVariant.objects.filter(
                article_id=winner.article_id,
                is_winner=False,
            ).values_list('title', flat=True)

            if not losers:
                continue

            # Input = article summary/content snippet for context
            article = winner.article
            context = (article.summary or article.content[:500]) if article else ''

            text_input = (
                f"Generate the best click-through title for this automotive article:\n\n"
                f"{context[:2000]}\n\n"
                f"Previous titles that underperformed:\n"
                + '\n'.join(f'- {t}' for t in losers)
            )

            line = json.dumps({
                'text_input': text_input,
                'output': winner.title,
            }, ensure_ascii=False)
            f.write(line + '\n')
            count += 1

        self.stdout.write(f'  🏆 A/B title winners: {count}')
        return count
