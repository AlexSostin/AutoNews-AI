# Generated manually - Step 2: Copy data from category to categories
from django.db import migrations


def copy_category_to_categories(apps, schema_editor):
    """Copy single category to categories ManyToMany field"""
    Article = apps.get_model('news', 'Article')
    for article in Article.objects.all():
        if article.category:
            article.categories.add(article.category)


def reverse_copy(apps, schema_editor):
    """Reverse migration: copy first category back to category field"""
    Article = apps.get_model('news', 'Article')
    for article in Article.objects.all():
        first_category = article.categories.first()
        if first_category:
            article.category = first_category
            article.save()


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0039_article_categories_remove_article_category'),
    ]

    operations = [
        migrations.RunPython(copy_category_to_categories, reverse_copy),
    ]
