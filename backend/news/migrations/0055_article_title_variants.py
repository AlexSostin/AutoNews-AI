from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0054_add_article_feedback'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArticleTitleVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('variant', models.CharField(choices=[('A', 'Variant A (Original)'), ('B', 'Variant B'), ('C', 'Variant C')], max_length=1)),
                ('title', models.CharField(max_length=500)),
                ('impressions', models.PositiveIntegerField(default=0, help_text='Number of times shown')),
                ('clicks', models.PositiveIntegerField(default=0, help_text='Number of click-throughs')),
                ('is_winner', models.BooleanField(default=False, help_text='Winning variant (applied as main title)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='title_variants', to='news.article')),
            ],
            options={
                'verbose_name': 'Title A/B Variant',
                'verbose_name_plural': 'Title A/B Variants',
                'ordering': ['variant'],
                'unique_together': {('article', 'variant')},
            },
        ),
    ]
