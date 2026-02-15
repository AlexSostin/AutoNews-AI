"""
Migration: Create Brand model and auto-populate from existing CarSpecification data.

This is a two-phase migration:
1. Create the Brand table schema
2. Auto-populate with unique makes from CarSpecification, applying BrandAlias resolution
"""
from django.db import migrations, models
import django.db.models.deletion


def populate_brands(apps, schema_editor):
    """Auto-create Brand records from existing CarSpecification.make values."""
    CarSpecification = apps.get_model('news', 'CarSpecification')
    BrandAlias = apps.get_model('news', 'BrandAlias')
    Brand = apps.get_model('news', 'Brand')
    
    from django.utils.text import slugify
    
    # Get all unique makes
    makes = (
        CarSpecification.objects
        .exclude(make='')
        .exclude(make='Not specified')
        .values_list('make', flat=True)
        .distinct()
    )
    
    # Build alias lookup
    alias_map = {}
    for alias in BrandAlias.objects.all():
        alias_map[alias.alias.lower()] = alias.canonical_name
    
    # Resolve and deduplicate
    seen = {}  # canonical_lower → Brand name
    for make in makes:
        # Apply alias resolution
        canonical = alias_map.get(make.lower(), make)
        key = canonical.lower()
        if key not in seen:
            seen[key] = canonical
    
    # Create brands
    for key, name in sorted(seen.items()):
        slug = slugify(name)
        if not slug:
            slug = slugify(key)
        if not slug:
            continue
        
        # Ensure unique slug
        base_slug = slug
        counter = 1
        while Brand.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        Brand.objects.create(
            name=name,
            slug=slug,
            is_visible=True,
            sort_order=0,
        )


def reverse_populate(apps, schema_editor):
    """Delete all auto-created brands (safe to reverse)."""
    Brand = apps.get_model('news', 'Brand')
    Brand.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0050_carspec_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='Brand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Display name', max_length=100, unique=True)),
                ('slug', models.SlugField(help_text='URL slug', max_length=120, unique=True)),
                ('logo', models.ImageField(blank=True, help_text='Brand logo', upload_to='brands/')),
                ('country', models.CharField(blank=True, help_text='Country of origin', max_length=50)),
                ('description', models.TextField(blank=True, help_text='Short brand description')),
                ('sort_order', models.IntegerField(default=0, help_text='Manual sort order (0=auto by article count)')),
                ('is_visible', models.BooleanField(default=True, help_text='Show in public catalog')),
                ('parent', models.ForeignKey(
                    blank=True, null=True,
                    help_text='Parent brand (e.g. DongFeng for VOYAH)',
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sub_brands',
                    to='news.brand',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-sort_order', 'name'],
                'verbose_name_plural': 'Brands',
            },
        ),
        migrations.RunPython(populate_brands, reverse_populate),
    ]
