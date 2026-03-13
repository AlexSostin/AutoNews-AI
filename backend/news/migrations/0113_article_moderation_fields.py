"""
Add content moderation fields to Article model.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('news', '0112_article_fts_gin_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='moderation_status',
            field=models.CharField(
                choices=[
                    ('pending_review', 'Pending Review'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                    ('auto_approved', 'Auto-Approved'),
                ],
                db_index=True,
                default='auto_approved',
                help_text='Moderation status: pending_review (needs human check), approved, rejected, auto_approved (bypassed)',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='article',
            name='moderation_notes',
            field=models.TextField(
                blank=True,
                default='',
                help_text="Reviewer's notes on why article was approved/rejected",
            ),
        ),
        migrations.AddField(
            model_name='article',
            name='moderation_reviewed_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When moderator reviewed this article',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='article',
            name='moderation_reviewed_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Who reviewed this article',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='moderated_articles',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
