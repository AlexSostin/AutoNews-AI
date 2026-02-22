from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0074_tag_learning_log'),
    ]

    operations = [
        migrations.AddField(
            model_name='automationsettings',
            name='deep_specs_enabled',
            field=models.BooleanField(default=True, help_text='Auto-generate VehicleSpecs cards for published articles'),
        ),
        migrations.AddField(
            model_name='automationsettings',
            name='deep_specs_interval_hours',
            field=models.IntegerField(default=6, help_text='Hours between deep specs backfill runs (4, 6, 12, 24)'),
        ),
        migrations.AddField(
            model_name='automationsettings',
            name='deep_specs_max_per_cycle',
            field=models.IntegerField(default=3, help_text='Max articles to process per cycle'),
        ),
        migrations.AddField(
            model_name='automationsettings',
            name='deep_specs_last_run',
            field=models.DateTimeField(null=True, blank=True, help_text='When deep specs backfill last ran'),
        ),
        migrations.AddField(
            model_name='automationsettings',
            name='deep_specs_last_status',
            field=models.CharField(max_length=500, blank=True, default='', help_text='Last backfill result'),
        ),
        migrations.AddField(
            model_name='automationsettings',
            name='deep_specs_today_count',
            field=models.IntegerField(default=0, help_text='VehicleSpecs cards created today'),
        ),
        migrations.AddField(
            model_name='automationsettings',
            name='deep_specs_lock',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='automationsettings',
            name='deep_specs_lock_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
