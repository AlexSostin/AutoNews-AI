"""
VehicleSpecs: add multi-trim support.
- article: OneToOneField → ForeignKey (nullable, SET_NULL)
- Add make, model_name, trim_name fields
- Backfill make/model_name from linked CarSpecification
- Add unique_together constraint
"""
from django.db import migrations, models
import django.db.models.deletion


def backfill_make_model(apps, schema_editor):
    """Copy make/model from CarSpecification into VehicleSpecs."""
    VehicleSpecs = apps.get_model('news', 'VehicleSpecs')
    CarSpecification = apps.get_model('news', 'CarSpecification')

    for vs in VehicleSpecs.objects.filter(article__isnull=False):
        try:
            cs = CarSpecification.objects.get(article_id=vs.article_id)
            if cs.make and cs.make != 'Not specified':
                vs.make = cs.make
            if cs.model and cs.model != 'Not specified':
                vs.model_name = cs.model
            if cs.trim and cs.trim != 'Not specified':
                vs.trim_name = cs.trim
            vs.save(update_fields=['make', 'model_name', 'trim_name'])
        except CarSpecification.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0047_vehiclespecs_extend_fields'),
    ]

    operations = [
        # 1. Add new fields
        migrations.AddField(
            model_name='vehiclespecs',
            name='make',
            field=models.CharField(blank=True, default='', help_text='Car brand (e.g. Zeekr, BMW, Tesla)', max_length=100),
        ),
        migrations.AddField(
            model_name='vehiclespecs',
            name='model_name',
            field=models.CharField(blank=True, default='', help_text='Model name (e.g. 007 GT, iX3, Model 3)', max_length=100),
        ),
        migrations.AddField(
            model_name='vehiclespecs',
            name='trim_name',
            field=models.CharField(blank=True, default='', help_text='Trim variant (e.g. AWD 100 kWh, Long Range, Performance)', max_length=100),
        ),

        # 2. Change article from OneToOne to ForeignKey (nullable)
        migrations.AlterField(
            model_name='vehiclespecs',
            name='article',
            field=models.ForeignKey(
                blank=True,
                help_text='Source article (optional)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='vehicle_specs_set',
                to='news.article',
            ),
        ),

        # 3. Backfill make/model from CarSpecification
        migrations.RunPython(backfill_make_model, migrations.RunPython.noop),

        # 4. Update ordering
        migrations.AlterModelOptions(
            name='vehiclespecs',
            options={
                'ordering': ['make', 'model_name', 'trim_name'],
                'verbose_name': 'Vehicle Specification',
                'verbose_name_plural': 'Vehicle Specifications',
            },
        ),

        # 5. Add unique constraint (make + model_name + trim_name)
        migrations.AlterUniqueTogether(
            name='vehiclespecs',
            unique_together={('make', 'model_name', 'trim_name')},
        ),
    ]
