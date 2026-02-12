# Safe migration: handles both clean DB (CI) and production (column may already exist)
from django.db import migrations, models


def add_is_visible_if_not_exists(apps, schema_editor):
    """Add is_visible column only if it doesn't already exist (for production)"""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'news_category' AND column_name = 'is_visible'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE news_category
                ADD COLUMN is_visible BOOLEAN DEFAULT TRUE NOT NULL
            """)


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0040_articleembedding'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Database: use RunPython that checks IF NOT EXISTS
            database_operations=[
                migrations.RunPython(add_is_visible_if_not_exists, migrations.RunPython.noop),
            ],
            # State: tell Django this field now exists on the model
            state_operations=[
                migrations.AddField(
                    model_name='category',
                    name='is_visible',
                    field=models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text='Show this category in public navigation and lists',
                    ),
                ),
            ],
        ),
    ]
