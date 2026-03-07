from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0101_add_rss_is_favorite'),
    ]

    operations = [
        migrations.AddField(
            model_name='rssnewsitem',
            name='llm_score',
            field=models.SmallIntegerField(
                null=True,
                blank=True,
                db_index=True,
                help_text='LLM relevance score 0-100 (gpt-4o-mini). Null = not yet scored.',
            ),
        ),
        migrations.AddField(
            model_name='rssnewsitem',
            name='llm_score_reason',
            field=models.CharField(
                max_length=200,
                blank=True,
                default='',
                help_text='Short reason from LLM scorer (e.g. "BYD battery reveal").',
            ),
        ),
        migrations.AddField(
            model_name='rssnewsitem',
            name='source_count',
            field=models.PositiveSmallIntegerField(
                default=1,
                db_index=True,
                help_text='Number of different RSS sources covering the same story. >3 = hot topic.',
            ),
        ),
    ]
