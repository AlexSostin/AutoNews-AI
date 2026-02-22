from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('news', '0075_add_deep_specs_automation'),
    ]

    operations = [
        # Add moderation fields to Comment
        migrations.AddField(
            model_name='comment',
            name='moderation_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending Review'),
                    ('auto_approved', 'Auto-Approved'),
                    ('auto_blocked', 'Auto-Blocked'),
                    ('admin_approved', 'Admin Approved'),
                    ('admin_rejected', 'Admin Rejected'),
                ],
                db_index=True,
                default='pending',
                help_text='Moderation system decision',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='comment',
            name='moderation_reason',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Why comment was approved/blocked',
                max_length=255,
            ),
        ),
        # Create CommentModerationLog model
        migrations.CreateModel(
            name='CommentModerationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('decision', models.CharField(choices=[('approved', 'Approved'), ('rejected', 'Rejected')], max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('admin_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='moderation_decisions', to='auth.user')),
                ('comment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='moderation_logs', to='news.comment')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['decision', '-created_at'], name='news_commen_decisio_idx'),
                ],
            },
        ),
    ]
