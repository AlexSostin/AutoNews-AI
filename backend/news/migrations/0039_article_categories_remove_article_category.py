# Safe migration - handles existing news_article_categories table
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0038_remove_article_article_category_created_idx_and_more'),
    ]

    operations = [
        # Use SeparateDatabaseAndState to handle existing table
        migrations.SeparateDatabaseAndState(
            # Database operations (empty - table already exists in production)
            database_operations=[],
            
            # State operations (update Django's model state)
            state_operations=[
                migrations.AddField(
                    model_name='article',
                    name='categories',
                    field=models.ManyToManyField(
                        blank=True,
                        related_name='articles_new',
                        to='news.category'
                    ),
                ),
            ],
        ),
    ]
