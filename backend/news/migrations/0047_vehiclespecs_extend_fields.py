from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0046_carspecification_drivetrain'),
    ]

    operations = [
        # New dimension fields
        migrations.AddField(
            model_name='vehiclespecs',
            name='cargo_liters_max',
            field=models.IntegerField(blank=True, help_text='Max cargo with seats folded in liters', null=True),
        ),
        migrations.AddField(
            model_name='vehiclespecs',
            name='ground_clearance_mm',
            field=models.IntegerField(blank=True, help_text='Ground clearance in millimeters', null=True),
        ),
        migrations.AddField(
            model_name='vehiclespecs',
            name='towing_capacity_kg',
            field=models.IntegerField(blank=True, help_text='Maximum towing capacity in kg', null=True),
        ),
        # New range field
        migrations.AddField(
            model_name='vehiclespecs',
            name='range_cltc',
            field=models.IntegerField(blank=True, help_text='CLTC range in kilometers (Chinese standard)', null=True),
        ),
        # Technical details
        migrations.AddField(
            model_name='vehiclespecs',
            name='platform',
            field=models.CharField(blank=True, help_text='Vehicle platform (e.g., SEA, MEB, E-GMP, TNGA)', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='vehiclespecs',
            name='voltage_architecture',
            field=models.IntegerField(blank=True, help_text='Electrical architecture voltage (400, 800, 900)', null=True),
        ),
        migrations.AddField(
            model_name='vehiclespecs',
            name='suspension_type',
            field=models.CharField(blank=True, help_text='Suspension type (e.g., air suspension, adaptive, McPherson)', max_length=200, null=True),
        ),
        # Flexible JSON field
        migrations.AddField(
            model_name='vehiclespecs',
            name='extra_specs',
            field=models.JSONField(blank=True, default=dict, help_text="Additional specs as key-value pairs (e.g., {'panoramic_roof': true, 'lidar': 'Hesai ATX'})"),
        ),
        # Update body_type choices
        migrations.AlterField(
            model_name='vehiclespecs',
            name='body_type',
            field=models.CharField(blank=True, choices=[('sedan', 'Sedan'), ('SUV', 'SUV'), ('hatchback', 'Hatchback'), ('coupe', 'Coupe'), ('truck', 'Truck'), ('crossover', 'Crossover'), ('wagon', 'Wagon'), ('shooting_brake', 'Shooting Brake'), ('van', 'Van'), ('convertible', 'Convertible'), ('pickup', 'Pickup')], help_text='Body style', max_length=20, null=True),
        ),
    ]
