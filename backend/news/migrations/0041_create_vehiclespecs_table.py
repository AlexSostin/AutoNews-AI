# Generated manually to create VehicleSpecs table in production
# This is a clean migration containing ONLY VehicleSpecs creation

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0040_articleembedding'),
    ]

    operations = [
        migrations.CreateModel(
            name='VehicleSpecs',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('drivetrain', models.CharField(blank=True, choices=[('FWD', 'Front-Wheel Drive'), ('RWD', 'Rear-Wheel Drive'), ('AWD', 'All-Wheel Drive'), ('4WD', 'Four-Wheel Drive')], help_text='Drive configuration', max_length=10, null=True)),
                ('motor_count', models.IntegerField(blank=True, help_text='Number of electric motors', null=True)),
                ('motor_placement', models.CharField(blank=True, help_text="Motor location (e.g., 'front', 'rear', 'front+rear')", max_length=50, null=True)),
                ('power_hp', models.IntegerField(blank=True, help_text='Power in horsepower', null=True)),
                ('power_kw', models.IntegerField(blank=True, help_text='Power in kilowatts', null=True)),
                ('torque_nm', models.IntegerField(blank=True, help_text='Torque in Newton-meters', null=True)),
                ('acceleration_0_100', models.FloatField(blank=True, help_text='0-100 km/h acceleration time in seconds', null=True)),
                ('top_speed_kmh', models.IntegerField(blank=True, help_text='Top speed in km/h', null=True)),
                ('battery_kwh', models.FloatField(blank=True, help_text='Battery capacity in kWh', null=True)),
                ('range_km', models.IntegerField(blank=True, help_text='Range in kilometers (general)', null=True)),
                ('range_wltp', models.IntegerField(blank=True, help_text='WLTP range in kilometers', null=True)),
                ('range_epa', models.IntegerField(blank=True, help_text='EPA range in kilometers', null=True)),
                ('charging_time_fast', models.CharField(blank=True, help_text="Fast charging time (e.g., '30 min to 80%')", max_length=100, null=True)),
                ('charging_time_slow', models.CharField(blank=True, help_text='Slow/AC charging time', max_length=100, null=True)),
                ('charging_power_max_kw', models.IntegerField(blank=True, help_text='Maximum charging power in kW', null=True)),
                ('transmission', models.CharField(blank=True, choices=[('automatic', 'Automatic'), ('manual', 'Manual'), ('CVT', 'CVT'), ('single-speed', 'Single-Speed'), ('dual-clutch', 'Dual-Clutch')], help_text='Transmission type', max_length=20, null=True)),
                ('transmission_gears', models.IntegerField(blank=True, help_text='Number of gears', null=True)),
                ('body_type', models.CharField(blank=True, choices=[('sedan', 'Sedan'), ('SUV', 'SUV'), ('hatchback', 'Hatchback'), ('coupe', 'Coupe'), ('truck', 'Truck'), ('crossover', 'Crossover'), ('wagon', 'Wagon'), ('van', 'Van')], help_text='Body style', max_length=20, null=True)),
                ('fuel_type', models.CharField(blank=True, choices=[('EV', 'Electric Vehicle'), ('Hybrid', 'Hybrid'), ('PHEV', 'Plug-in Hybrid'), ('Gas', 'Gasoline'), ('Diesel', 'Diesel'), ('Hydrogen', 'Hydrogen')], help_text='Fuel/power source type', max_length=20, null=True)),
                ('seats', models.IntegerField(blank=True, help_text='Number of seats', null=True)),
                ('length_mm', models.IntegerField(blank=True, help_text='Length in millimeters', null=True)),
                ('width_mm', models.IntegerField(blank=True, help_text='Width in millimeters', null=True)),
                ('height_mm', models.IntegerField(blank=True, help_text='Height in millimeters', null=True)),
                ('wheelbase_mm', models.IntegerField(blank=True, help_text='Wheelbase in millimeters', null=True)),
                ('weight_kg', models.IntegerField(blank=True, help_text='Curb weight in kilograms', null=True)),
                ('cargo_liters', models.IntegerField(blank=True, help_text='Cargo/trunk capacity in liters', null=True)),
                ('price_from', models.IntegerField(blank=True, help_text='Starting price', null=True)),
                ('price_to', models.IntegerField(blank=True, help_text='Maximum price', null=True)),
                ('currency', models.CharField(choices=[('USD', 'US Dollar'), ('EUR', 'Euro'), ('CNY', 'Chinese Yuan'), ('RUB', 'Russian Ruble'), ('GBP', 'British Pound'), ('JPY', 'Japanese Yen')], default='USD', help_text='Price currency', max_length=3)),
                ('year', models.IntegerField(blank=True, help_text='Release year', null=True)),
                ('model_year', models.IntegerField(blank=True, help_text='Model year', null=True)),
                ('country_of_origin', models.CharField(blank=True, help_text='Country where manufactured', max_length=100, null=True)),
                ('extracted_at', models.DateTimeField(auto_now=True, help_text='When specs were last extracted/updated')),
                ('confidence_score', models.FloatField(default=0.0, help_text='AI extraction confidence (0.0-1.0)')),
                ('article', models.OneToOneField(help_text='Article this specification belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='vehicle_specs', to='news.article')),
            ],
            options={
                'verbose_name': 'Vehicle Specification',
                'verbose_name_plural': 'Vehicle Specifications',
                'ordering': ['-extracted_at'],
            },
        ),
    ]
