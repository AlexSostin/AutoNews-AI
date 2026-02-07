# Generated manually - Step 1: Add new field without removing old one
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0038_remove_article_article_category_created_idx_and_more'),
    ]

    operations = [
        # Add new ManyToMany field (old category field still exists)
        migrations.AddField(
            model_name='article',
            name='categories',
            field=models.ManyToManyField(blank=True, related_name='articles_new', to='news.category'),
        ),
    ]
