from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0044_add_verified_to_carspecification'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='show_browse_by_brand',
            field=models.BooleanField(default=True, help_text="Show 'Browse by Brand' section on homepage"),
        ),
    ]
