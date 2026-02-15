from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0048_vehiclespecs_multi_trim'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrandAlias',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alias', models.CharField(help_text="The name variation (what AI might produce, e.g. 'DongFeng VOYAH')", max_length=100, unique=True)),
                ('canonical_name', models.CharField(help_text="The correct brand name (e.g. 'VOYAH')", max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'Brand Aliases',
                'ordering': ['canonical_name', 'alias'],
            },
        ),
    ]
