# Generated manually
from django.db import migrations, models


def add_is_visible_if_not_exists(apps, schema_editor):
    """Add is_visible column only if it doesn't already exist"""
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
            cursor.execute("""
                CREATE INDEX news_category_is_visible_idx ON news_category (is_visible)
            """)


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0040_articleembedding'),
    ]

    operations = [
        migrations.RunPython(add_is_visible_if_not_exists, migrations.RunPython.noop),
    ]
