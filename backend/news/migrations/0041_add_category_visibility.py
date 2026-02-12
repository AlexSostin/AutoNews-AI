# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0040_articleembedding'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='is_visible',
            field=models.BooleanField(db_index=True, default=True, help_text='Show this category in public navigation and lists'),
        ),
    ]
