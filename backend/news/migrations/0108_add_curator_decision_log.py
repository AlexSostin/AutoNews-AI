from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0107_add_seo_description_to_pending_article'),
    ]

    operations = [
        migrations.CreateModel(
            name='CuratorDecisionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('decision', models.CharField(choices=[
                    ('generate', 'Generated Article'),
                    ('merge', 'Merged into Roundup'),
                    ('skip', 'Skipped'),
                    ('save_later', 'Saved for Later'),
                ], max_length=20)),
                ('curator_score', models.IntegerField(default=0, help_text='FreshMotors relevance score at decision time')),
                ('cluster_id', models.CharField(blank=True, default='', help_text='Cluster identifier from curator run', max_length=50)),
                ('brand', models.CharField(blank=True, default='', max_length=100)),
                ('has_specs_data', models.BooleanField(default=False)),
                ('source_count', models.IntegerField(default=1)),
                ('llm_score', models.IntegerField(blank=True, null=True)),
                ('title_text', models.CharField(blank=True, default='', help_text='Title snapshot — avoids JOIN for ML training queries', max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('news_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='curator_decisions', to='news.rssnewsitem')),
                ('generated_article', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='curator_decisions', to='news.article')),
            ],
            options={
                'verbose_name': 'Curator Decision Log',
                'verbose_name_plural': 'Curator Decision Logs',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['decision', '-created_at'], name='news_curato_decisio_idx'),
                ],
            },
        ),
    ]
