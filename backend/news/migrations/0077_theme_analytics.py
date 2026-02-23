from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0076_comment_moderation'),
    ]

    operations = [
        migrations.CreateModel(
            name='ThemeAnalytics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('theme', models.CharField(db_index=True, help_text="Theme ID e.g. 'default', 'midnight-green', 'deep-ocean'", max_length=30)),
                ('session_hash', models.CharField(blank=True, default='', help_text='Anonymized session identifier', max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['theme', '-created_at'], name='news_themea_theme_idx'),
                ],
            },
        ),
    ]
