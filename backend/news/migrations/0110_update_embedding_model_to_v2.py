from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Update ArticleEmbedding.model_name default to gemini-embedding-2-preview.
    
    NOTE: Embeddings from v1 (gemini-embedding-001) are incompatible with v2.
    Old embeddings must be deleted and re-generated. Run:
        python manage.py clear_embeddings
        python manage.py index_articles
    """

    dependencies = [
        ('news', '0109_scheduled_publish_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='articleembedding',
            name='model_name',
            field=models.CharField(
                default='models/gemini-embedding-2-preview',
                help_text='Gemini model used to generate this embedding',
                max_length=100,
            ),
        ),
    ]
