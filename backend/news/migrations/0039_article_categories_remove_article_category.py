# Safe migration - checks if table exists before creating
from django.db import migrations, models, connection


def check_and_add_categories_field(apps, schema_editor):
    """
    Safely add categories field only if the table doesn't exist.
    """
    # Check if the many-to-many table already exists
    table_name = 'news_article_categories'
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            );
        """, [table_name])
        table_exists = cursor.fetchone()[0]
    
    if table_exists:
        print(f"✓ Table {table_name} already exists, skipping creation")
        return
    
    # Table doesn't exist, create it
    print(f"Creating table {table_name}")
    Article = apps.get_model('news', 'Article')
    Category = apps.get_model('news', 'Category')
    
    # This will create the many-to-many table
    schema_editor.create_model(Article.categories.through)


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0038_remove_article_article_category_created_idx_and_more'),
    ]

    operations = [
        # Use RunPython to safely check and create
        migrations.RunPython(
            check_and_add_categories_field,
            reverse_code=migrations.RunPython.noop,
        ),
        # Add the field to the model (won't create table if it exists)
        migrations.AddField(
            model_name='article',
            name='categories',
            field=models.ManyToManyField(
                blank=True, 
                related_name='articles_new', 
                to='news.category',
                db_table='news_article_categories'  # Explicitly set table name
            ),
        ),
    ]
