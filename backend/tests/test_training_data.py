"""
Tests for the Training Data Collection system.

Covers:
- TrainingPair model creation and constraints
- record_training_pair signal — creates pairs on article edit+publish
- enrich_training_pair_quality signal — updates quality from capsule feedback
- export_training_data management command — JSONL output
"""
import json
import tempfile
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.test import TestCase

from news.models.content import Article, PendingArticle, Category
from news.models.system import TrainingPair, ArticleTitleVariant


@pytest.fixture
def category(db):
    return Category.objects.create(name='Test', slug='test')


@pytest.fixture
def article_with_original(db, category):
    """Published article with content_original (simulating admin edits)."""
    art = Article.objects.create(
        title='2026 BMW iX M60 Review',
        slug='bmw-ix-m60-review',
        content='<p>The 2026 BMW iX is a premium electric SUV with impressive specs.</p>',
        content_original='<p>Original AI draft about the BMW car.</p>',
        is_published=True,
    )
    art.categories.add(category)
    return art


@pytest.fixture
def pending_article(db, category):
    """PendingArticle linked to a published article."""
    pending = PendingArticle.objects.create(
        title='AI Draft: Tesla Model Y 2026',
        content='<p>AI wrote this about Tesla Model Y 2026.</p>',
        excerpt='Test excerpt',
        status='published',
    )
    art = Article.objects.create(
        title='2026 Tesla Model Y Full Review',
        slug='tesla-model-y-2026',
        content='<p>Editor rewrote this article about Tesla Model Y.</p>',
        is_published=True,
    )
    art.categories.add(category)
    pending.published_article = art
    pending.save()
    return pending, art


# =============================================================================
# TrainingPair Model Tests
# =============================================================================

class TestTrainingPairModel(TestCase):

    def setUp(self):
        self.article = Article.objects.create(
            title='Test Article', slug='test-tp', content='Content',
            is_published=True,
        )

    def test_create_generation_pair(self):
        pair = TrainingPair.objects.create(
            article=self.article,
            pair_type='generation',
            source_type='rss',
            input_title='AI Title',
            output_title='Human Title',
            input_text='AI draft content',
            output_text='Human edited content',
        )
        assert pair.pk is not None
        assert str(pair) == '[generation] Human Title'
        assert pair.quality_signals == {}

    def test_unique_constraint_per_article_pair_type(self):
        TrainingPair.objects.create(
            article=self.article, pair_type='generation',
            input_text='a', output_text='b',
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            TrainingPair.objects.create(
                article=self.article, pair_type='generation',
                input_text='c', output_text='d',
            )

    def test_different_pair_types_allowed(self):
        TrainingPair.objects.create(
            article=self.article, pair_type='generation',
            input_text='a', output_text='b',
        )
        pair2 = TrainingPair.objects.create(
            article=self.article, pair_type='title_ab',
            input_text='c', output_text='d',
        )
        assert pair2.pk is not None
        assert TrainingPair.objects.filter(article=self.article).count() == 2


# =============================================================================
# Signal Tests — record_training_pair
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestRecordTrainingPairSignal:

    def test_records_pair_from_content_original(self):
        """When article has content_original ≠ content, pair is created."""
        art = Article.objects.create(
            title='Signal Test',
            slug='signal-test',
            content='<p>Final human version</p>',
            content_original='<p>Original AI version</p>',
            is_published=False,
        )
        # Publish (triggers the signal as an update)
        art.is_published = True
        art.save()

        import time
        time.sleep(0.5)  # Wait for background thread

        pair = TrainingPair.objects.filter(article=art, pair_type='generation').first()
        assert pair is not None
        assert 'Original AI version' in pair.input_text
        assert 'Final human version' in pair.output_text

    def test_no_pair_when_content_unchanged(self):
        """No pair created when content == content_original."""
        art = Article.objects.create(
            title='Same Content', slug='same-content',
            content='<p>Same text</p>',
            content_original='<p>Same text</p>',
            is_published=False,
        )
        art.is_published = True
        art.save()

        import time
        time.sleep(0.5)

        assert not TrainingPair.objects.filter(article=art).exists()

    def test_no_pair_when_no_source(self):
        """No pair created when no content_original and no PendingArticle."""
        art = Article.objects.create(
            title='No Source', slug='no-source',
            content='<p>Some content</p>',
            is_published=False,
        )
        art.is_published = True
        art.save()

        import time
        time.sleep(0.5)

        assert not TrainingPair.objects.filter(article=art).exists()

    def test_skips_on_create(self):
        """No pair on initial Article.objects.create."""
        art = Article.objects.create(
            title='Fresh', slug='fresh',
            content='<p>Content</p>',
            content_original='<p>AI content</p>',
            is_published=True,
        )
        import time
        time.sleep(0.5)
        # Signal skips created=True
        assert not TrainingPair.objects.filter(article=art).exists()

    def test_records_pair_from_pending_article(self):
        """When article has linked PendingArticle, uses its content."""
        pending = PendingArticle.objects.create(
            title='AI: Audi Q6 e-tron',
            content='<p>AI draft about Audi Q6 e-tron</p>',
            status='published',
        )
        art = Article.objects.create(
            title='2026 Audi Q6 e-tron Review',
            slug='audi-q6-etron',
            content='<p>Human-edited Audi article</p>',
            is_published=False,
        )
        pending.published_article = art
        pending.save()

        art.is_published = True
        art.save()

        import time
        time.sleep(0.5)

        pair = TrainingPair.objects.filter(article=art).first()
        assert pair is not None
        assert 'AI draft about Audi' in pair.input_text
        assert 'AI: Audi Q6 e-tron' == pair.input_title


# =============================================================================
# Signal Tests — enrich_training_pair_quality
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestEnrichTrainingPairQuality:

    def test_enriches_quality_on_capsule_feedback(self):
        """Capsule feedback updates quality_signals on existing pair."""
        from news.models.interactions import ArticleCapsuleFeedback

        art = Article.objects.create(
            title='Quality Test', slug='quality-test',
            content='Content', is_published=True, views=42,
            engagement_score=7.5,
        )
        # Create a training pair manually
        pair = TrainingPair.objects.create(
            article=art, pair_type='generation',
            input_text='ai', output_text='human',
        )

        # Submit positive capsule feedback
        ArticleCapsuleFeedback.objects.create(
            article=art, feedback_type='well_written',
            ip_address='1.2.3.4',
        )
        import time
        time.sleep(0.5)

        pair.refresh_from_db()
        signals = pair.quality_signals
        assert signals.get('capsule_positive') == 1
        assert signals.get('capsule_negative') == 0
        assert signals.get('capsule_score') == 1.0
        assert signals.get('views') == 42

    def test_no_error_when_no_training_pair(self):
        """Capsule feedback on article without training pair does nothing."""
        from news.models.interactions import ArticleCapsuleFeedback

        art = Article.objects.create(
            title='No Pair', slug='no-pair',
            content='Content', is_published=True,
        )
        # Should not raise
        ArticleCapsuleFeedback.objects.create(
            article=art, feedback_type='accurate_specs',
            ip_address='1.2.3.5',
        )
        import time
        time.sleep(0.5)
        assert not TrainingPair.objects.filter(article=art).exists()


# =============================================================================
# Export Command Tests
# =============================================================================

class TestExportTrainingData(TestCase):

    def test_export_generation_pairs(self):
        art = Article.objects.create(
            title='Export Test', slug='export-test',
            content='Final', summary='Summary', is_published=True,
        )
        TrainingPair.objects.create(
            article=art, pair_type='generation',
            input_title='AI Title', output_title='Human Title',
            input_text='AI content', output_text='Human content',
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            out_path = f.name

        out = StringIO()
        call_command('export_training_data', '--type', 'generation', '--output', out_path, stdout=out)

        with open(out_path, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 1
        data = json.loads(lines[0])
        assert 'text_input' in data
        assert 'output' in data
        assert 'AI content' in data['text_input']
        assert 'Human content' in data['output']

    def test_export_title_winners(self):
        art = Article.objects.create(
            title='AB Test', slug='ab-test',
            content='Content', summary='Test summary', is_published=True,
        )
        ArticleTitleVariant.objects.create(
            article=art, variant='A', title='Losing Title',
            impressions=150, clicks=5,
        )
        ArticleTitleVariant.objects.create(
            article=art, variant='B', title='Winning Title',
            impressions=150, clicks=15, is_winner=True,
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            out_path = f.name

        out = StringIO()
        call_command('export_training_data', '--type', 'titles', '--output', out_path, stdout=out)

        with open(out_path, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 1
        data = json.loads(lines[0])
        assert 'Winning Title' in data['output']
        assert 'Losing Title' in data['text_input']

    def test_export_empty(self):
        """Export with no data produces empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            out_path = f.name

        out = StringIO()
        call_command('export_training_data', '--output', out_path, stdout=out)

        with open(out_path, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 0
        assert '0 training examples' in out.getvalue()

    def test_min_quality_filter(self):
        """--min-quality filters out low-quality pairs."""
        art = Article.objects.create(
            title='Filter Test', slug='filter-test',
            content='Content', is_published=True,
        )
        TrainingPair.objects.create(
            article=art, pair_type='generation',
            input_text='ai', output_text='human',
            quality_signals={'capsule_score': 0.3},
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            out_path = f.name

        out = StringIO()
        call_command(
            'export_training_data', '--type', 'generation',
            '--min-quality', '0.5', '--output', out_path, stdout=out,
        )

        with open(out_path, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 0  # Filtered out due to low quality
