# Rewritten to use RunSQL with IF NOT EXISTS guards
# so this migration works both on clean databases (CI) and production

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0038_vehiclespecs_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS "article_embeddings" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "embedding_vector" jsonb NOT NULL,
                "model_name" varchar(100) NOT NULL DEFAULT 'models/embedding-001',
                "text_hash" varchar(64) NULL,
                "created_at" timestamp with time zone NOT NULL DEFAULT NOW(),
                "updated_at" timestamp with time zone NOT NULL DEFAULT NOW(),
                "article_id" bigint NOT NULL UNIQUE REFERENCES "news_article" ("id") DEFERRABLE INITIALLY DEFERRED
            );
            CREATE INDEX IF NOT EXISTS "article_emb_article_8fbb22_idx" ON "article_embeddings" ("article_id");
            CREATE INDEX IF NOT EXISTS "article_emb_updated_78b8b7_idx" ON "article_embeddings" ("updated_at");
            CREATE INDEX IF NOT EXISTS "article_emb_text_ha_a4d8fa_idx" ON "article_embeddings" ("text_hash");
            """,
            reverse_sql='DROP TABLE IF EXISTS "article_embeddings";',
            state_operations=[
                migrations.CreateModel(
                    name='ArticleEmbedding',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('embedding_vector', models.JSONField(help_text='768-dimensional embedding vector from Gemini (stored as JSON array)')),
                        ('model_name', models.CharField(default='models/embedding-001', help_text='Gemini model used to generate this embedding', max_length=100)),
                        ('text_hash', models.CharField(blank=True, help_text='SHA256 hash of indexed text (to detect changes)', max_length=64)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('article', models.OneToOneField(help_text='Article this embedding belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='embedding', to='news.article')),
                    ],
                    options={
                        'verbose_name': 'Article Embedding',
                        'verbose_name_plural': 'Article Embeddings',
                        'db_table': 'article_embeddings',
                        'indexes': [
                            models.Index(fields=['article'], name='article_emb_article_8fbb22_idx'),
                            models.Index(fields=['updated_at'], name='article_emb_updated_78b8b7_idx'),
                            models.Index(fields=['text_hash'], name='article_emb_text_ha_a4d8fa_idx'),
                        ],
                    },
                ),
            ],
        ),
    ]
