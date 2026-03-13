"""
Add PostgreSQL Full-Text Search GIN index on Article title + content + summary.
This dramatically speeds up text searches and enables ranked results.
"""
from django.contrib.postgres.search import SearchVector
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0111_training_pair'),
    ]

    operations = [
        # Add GIN index for full-text search on title (weight A) + summary (weight B) + content (weight C)
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS article_fts_gin_idx
                ON news_article
                USING GIN (
                    (
                        setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
                        setweight(to_tsvector('english', COALESCE(summary, '')), 'B') ||
                        setweight(to_tsvector('english', COALESCE(content, '')), 'C')
                    )
                );
            """,
            reverse_sql="DROP INDEX IF EXISTS article_fts_gin_idx;",
        ),
    ]
