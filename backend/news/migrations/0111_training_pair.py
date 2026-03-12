from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Add TrainingPair model for collecting fine-tuning data."""

    dependencies = [
        ('news', '0110_update_embedding_model_to_v2'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrainingPair',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pair_type', models.CharField(
                    choices=[
                        ('generation', 'Article Generation (source → final)'),
                        ('title_ab', 'Title A/B Winner'),
                    ],
                    max_length=20,
                )),
                ('source_type', models.CharField(
                    choices=[('rss', 'RSS Feed'), ('youtube', 'YouTube'), ('manual', 'Manual')],
                    default='rss',
                    max_length=20,
                )),
                ('input_title', models.CharField(blank=True, max_length=500)),
                ('output_title', models.CharField(blank=True, max_length=500)),
                ('input_text', models.TextField(help_text='Source content (pending article / original AI)')),
                ('output_text', models.TextField(help_text='Final content after admin edits')),
                ('quality_signals', models.JSONField(
                    blank=True, default=dict,
                    help_text='Reader quality data: capsule_score, engagement_score, views, etc.',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('article', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='training_pairs',
                    to='news.article',
                )),
            ],
            options={
                'verbose_name': 'Training Pair',
                'verbose_name_plural': 'Training Pairs',
                'indexes': [
                    models.Index(fields=['pair_type', '-created_at'], name='news_traini_pair_ty_idx'),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='trainingpair',
            constraint=models.UniqueConstraint(
                fields=('article', 'pair_type'),
                name='unique_training_pair_per_article',
            ),
        ),
    ]
