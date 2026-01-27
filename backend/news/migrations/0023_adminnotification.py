# Generated migration for AdminNotification model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0022_add_email_preferences'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[
                    ('comment', 'New Comment'),
                    ('subscriber', 'New Subscriber'),
                    ('article', 'New Article'),
                    ('video_pending', 'Video Pending Review'),
                    ('video_error', 'Video Processing Error'),
                    ('ai_error', 'AI Generation Error'),
                    ('system', 'System Alert'),
                    ('info', 'Information'),
                ], default='info', max_length=20)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('link', models.CharField(blank=True, help_text='Optional link to related item', max_length=500)),
                ('priority', models.CharField(choices=[
                    ('low', 'Low'),
                    ('normal', 'Normal'),
                    ('high', 'High'),
                ], default='normal', max_length=10)),
                ('is_read', models.BooleanField(db_index=True, default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'verbose_name': 'Admin Notification',
                'verbose_name_plural': 'Admin Notifications',
                'ordering': ['-created_at'],
            },
        ),
    ]
