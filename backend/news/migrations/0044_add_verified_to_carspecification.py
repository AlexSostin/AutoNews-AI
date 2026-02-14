from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0043_alter_articleembedding_model_name_rssnewsitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='carspecification',
            name='is_verified',
            field=models.BooleanField(default=False, help_text='Manually verified by editor'),
        ),
        migrations.AddField(
            model_name='carspecification',
            name='verified_at',
            field=models.DateTimeField(blank=True, null=True, help_text='When specs were verified'),
        ),
    ]
