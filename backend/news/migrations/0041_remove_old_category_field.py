# Generated manually - Step 3: Remove old category field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0040_copy_category_data'),
    ]

    operations = [
        # Remove old ForeignKey field
        migrations.RemoveField(
            model_name='article',
            name='category',
        ),
        # Update related_name on categories field
        migrations.AlterField(
            model_name='article',
            name='categories',
            field=models.ManyToManyField(blank=True, related_name='articles', to='news.category'),
        ),
    ]
