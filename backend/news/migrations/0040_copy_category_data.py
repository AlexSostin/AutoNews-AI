# Safe migration - copy data only if old field exists
from django.db import migrations


def copy_category_to_categories(apps, schema_editor):
    """
    Copy single category to categories ManyToMany field.
    Safely handles case where old 'category' field doesn't exist.
    """
    Article = apps.get_model('news', 'Article')
    
    # Check if the old 'category' field exists
    if not hasattr(Article, 'category'):
        print("✓ Old 'category' field doesn't exist, skipping data copy")
        return
    
    # Copy data from old field to new field
    copied_count = 0
    for article in Article.objects.all():
        try:
            if hasattr(article, 'category') and article.category:
                article.categories.add(article.category)
                copied_count += 1
        except AttributeError:
            # Field doesn't exist on this instance, skip
            continue
    
    print(f"✓ Copied {copied_count} category assignments to categories field")


def reverse_copy(apps, schema_editor):
    """Reverse migration: copy first category back to category field"""
    Article = apps.get_model('news', 'Article')
    
    # Check if the old 'category' field exists
    if not hasattr(Article, 'category'):
        print("✓ Old 'category' field doesn't exist, skipping reverse copy")
        return
    
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
