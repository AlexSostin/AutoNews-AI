from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0045_sitesettings_show_browse_by_brand'),
    ]

    operations = [
        migrations.AddField(
            model_name='carspecification',
            name='drivetrain',
            field=models.CharField(blank=True, help_text='AWD, FWD, RWD, 4WD', max_length=50),
        ),
    ]
