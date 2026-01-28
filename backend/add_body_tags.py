from news.models import Tag

# Body types (Типы кузова)
body_types = [
    ('Sedan', 'sedan'),
    ('Hatchback', 'hatchback'),
    ('Wagon', 'wagon'),
    ('Crossover', 'crossover'),
    ('Coupe', 'coupe'),
    ('Convertible', 'convertible'),
    ('Pickup', 'pickup'),
    ('Minivan', 'minivan'),
    ('Sports Car', 'sports-car'),
    ('Van', 'van'),
    ('Roadster', 'roadster'),
]

# Engine/Fuel types (Типы двигателей)
engine_types = [
    ('Electric', 'electric'),
    ('Hybrid', 'hybrid'),
    ('PHEV', 'phev'),
    ('Gasoline', 'gasoline'),
    ('Diesel', 'diesel'),
    ('Hydrogen', 'hydrogen'),
]

# Additional useful tags
additional_tags = [
    ('Luxury', 'luxury'),
    ('Performance', 'performance'),
    ('Off-Road', 'off-road'),
    ('Family', 'family'),
    ('Budget', 'budget'),
    ('Premium', 'premium'),
    ('Compact', 'compact'),
    ('Full-Size', 'full-size'),
    ('Mid-Size', 'mid-size'),
    ('AWD', 'awd'),
    ('4WD', '4wd'),
    ('FWD', 'fwd'),
    ('RWD', 'rwd'),
]

print("Adding body type tags...")
for name, slug in body_types:
    tag, created = Tag.objects.get_or_create(slug=slug, defaults={'name': name})
    if created:
        print(f"✓ Created: {name}")
    else:
        print(f"- Already exists: {name}")

print("\nAdding engine type tags...")
for name, slug in engine_types:
    tag, created = Tag.objects.get_or_create(slug=slug, defaults={'name': name})
    if created:
        print(f"✓ Created: {name}")
    else:
        print(f"- Already exists: {name}")

print("\nAdding additional tags...")
for name, slug in additional_tags:
    tag, created = Tag.objects.get_or_create(slug=slug, defaults={'name': name})
    if created:
        print(f"✓ Created: {name}")
    else:
        print(f"- Already exists: {name}")

print("\n" + "="*50)
print(f"Total tags in database: {Tag.objects.count()}")
print("="*50)
