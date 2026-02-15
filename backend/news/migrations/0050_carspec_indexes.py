from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0049_brandalias'),
    ]

    operations = [
        migrations.AlterField(
            model_name='carspecification',
            name='make',
            field=models.CharField(blank=True, db_index=True, help_text='Car Brand', max_length=100),
        ),
        migrations.AlterField(
            model_name='carspecification',
            name='model',
            field=models.CharField(blank=True, db_index=True, help_text='Base Model', max_length=100),
        ),
    ]
