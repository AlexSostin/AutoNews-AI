# Rewritten to use RunSQL with IF NOT EXISTS / IF EXISTS guards
# so this migration works both on clean databases (CI) and production
# (where some tables already exist but VehicleSpecs does not)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0037_pendingarticle_content_hash_and_more'),
    ]

    operations = [
        # 1. Create VehicleSpecs table (IF NOT EXISTS)
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS "news_vehiclespecs" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "drivetrain" varchar(10) NULL,
                "motor_count" integer NULL,
                "motor_placement" varchar(50) NULL,
                "power_hp" integer NULL,
                "power_kw" integer NULL,
                "torque_nm" integer NULL,
                "acceleration_0_100" double precision NULL,
                "top_speed_kmh" integer NULL,
                "battery_kwh" double precision NULL,
                "range_km" integer NULL,
                "range_wltp" integer NULL,
                "range_epa" integer NULL,
                "charging_time_fast" varchar(100) NULL,
                "charging_time_slow" varchar(100) NULL,
                "charging_power_max_kw" integer NULL,
                "transmission" varchar(20) NULL,
                "transmission_gears" integer NULL,
                "body_type" varchar(20) NULL,
                "fuel_type" varchar(20) NULL,
                "seats" integer NULL,
                "length_mm" integer NULL,
                "width_mm" integer NULL,
                "height_mm" integer NULL,
                "wheelbase_mm" integer NULL,
                "weight_kg" integer NULL,
                "cargo_liters" integer NULL,
                "price_from" integer NULL,
                "price_to" integer NULL,
                "currency" varchar(3) NOT NULL DEFAULT 'USD',
                "year" integer NULL,
                "model_year" integer NULL,
                "country_of_origin" varchar(100) NULL,
                "extracted_at" timestamp with time zone NOT NULL DEFAULT NOW(),
                "confidence_score" double precision NOT NULL DEFAULT 0.0,
                "article_id" bigint NOT NULL UNIQUE REFERENCES "news_article" ("id") DEFERRABLE INITIALLY DEFERRED
            );
            """,
            reverse_sql='DROP TABLE IF EXISTS "news_vehiclespecs";',
            state_operations=[
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
            ],
        ),

        # 2. Remove old category index (IF EXISTS)
        migrations.RunSQL(
            sql='DROP INDEX IF EXISTS "article_category_created_idx";',
            reverse_sql=migrations.RunSQL.noop,
            state_operations=[
                migrations.RemoveIndex(
                    model_name='article',
                    name='article_category_created_idx',
                ),
            ],
        ),

        # 3. Add categories M2M table (IF NOT EXISTS)
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS "news_article_categories" (
                "id" bigserial NOT NULL PRIMARY KEY,
                "article_id" bigint NOT NULL REFERENCES "news_article" ("id") DEFERRABLE INITIALLY DEFERRED,
                "category_id" bigint NOT NULL REFERENCES "news_category" ("id") DEFERRABLE INITIALLY DEFERRED
            );
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'news_article_categories_article_id_category_id_uniq'
                ) THEN
                    ALTER TABLE "news_article_categories"
                        ADD CONSTRAINT "news_article_categories_article_id_category_id_uniq"
                        UNIQUE ("article_id", "category_id");
                END IF;
            END $$;
            """,
            reverse_sql='DROP TABLE IF EXISTS "news_article_categories";',
            state_operations=[
                migrations.AddField(
                    model_name='article',
                    name='categories',
                    field=models.ManyToManyField(blank=True, related_name='articles', to='news.category'),
                ),
            ],
        ),

        # 4. Remove old category FK column (IF EXISTS)
        migrations.RunSQL(
            sql='ALTER TABLE "news_article" DROP COLUMN IF EXISTS "category_id";',
            reverse_sql=migrations.RunSQL.noop,
            state_operations=[
                migrations.RemoveField(
                    model_name='article',
                    name='category',
                ),
            ],
        ),
    ]
