# Generated migration for YouTube monitoring system

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('news', '0019_add_subscriber'),
    ]

    operations = [
        migrations.CreateModel(
            name='YouTubeChannel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Channel name for display', max_length=200)),
                ('channel_url', models.URLField(help_text='YouTube channel URL (e.g., https://www.youtube.com/@ChannelName)')),
                ('channel_id', models.CharField(blank=True, help_text='YouTube channel ID (auto-extracted)', max_length=100)),
                ('is_enabled', models.BooleanField(default=True, help_text='Enable monitoring for this channel')),
                ('auto_publish', models.BooleanField(default=False, help_text='Automatically publish articles (skip review)')),
                ('last_checked', models.DateTimeField(blank=True, null=True)),
                ('last_video_id', models.CharField(blank=True, help_text='Last processed video ID', max_length=50)),
                ('videos_processed', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('default_category', models.ForeignKey(blank=True, help_text='Default category for articles from this channel', null=True, on_delete=django.db.models.deletion.SET_NULL, to='news.category')),
            ],
            options={
                'verbose_name': 'YouTube Channel',
                'verbose_name_plural': 'YouTube Channels',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='AutoPublishSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_enabled', models.BooleanField(default=False, help_text='Enable automatic scanning')),
                ('frequency', models.CharField(choices=[('once', 'Once a day'), ('twice', 'Twice a day'), ('four', 'Four times a day'), ('manual', 'Manual only')], default='twice', max_length=20)),
                ('scan_time_1', models.TimeField(default='09:00', help_text='First scan time')),
                ('scan_time_2', models.TimeField(default='18:00', help_text='Second scan time')),
                ('scan_time_3', models.TimeField(blank=True, help_text='Third scan time', null=True)),
                ('scan_time_4', models.TimeField(blank=True, help_text='Fourth scan time', null=True)),
                ('last_scan', models.DateTimeField(blank=True, null=True)),
                ('last_scan_result', models.TextField(blank=True)),
                ('total_scans', models.IntegerField(default=0)),
                ('total_articles_generated', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Auto-Publish Schedule',
                'verbose_name_plural': 'Auto-Publish Schedule',
            },
        ),
        migrations.CreateModel(
            name='PendingArticle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('video_url', models.URLField(help_text='Source YouTube video URL')),
                ('video_id', models.CharField(max_length=50)),
                ('video_title', models.CharField(max_length=500)),
                ('title', models.CharField(max_length=500)),
                ('content', models.TextField()),
                ('excerpt', models.TextField(blank=True)),
                ('images', models.JSONField(blank=True, default=list)),
                ('featured_image', models.URLField(blank=True)),
                ('status', models.CharField(choices=[('pending', 'Pending Review'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('published', 'Published')], default='pending', max_length=20)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('review_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('published_article', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='source_pending', to='news.article')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('suggested_category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='news.category')),
                ('youtube_channel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pending_articles', to='news.youtubechannel')),
            ],
            options={
                'verbose_name': 'Pending Article',
                'verbose_name_plural': 'Pending Articles',
                'ordering': ['-created_at'],
            },
        ),
    ]
