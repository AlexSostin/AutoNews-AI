import json
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from news.models import Article, Category, Tag, CarSpecification
from django.contrib.auth import get_user_model

User = get_user_model()

# Read exported data
with open('/app/sqlite_export.json', 'r') as f:
    data = json.load(f)

print(f"Импортирую {len(data['categories'])} категорий...")
print(f"Импортирую {len(data['tags'])} тегов...")
print(f"Импортирую {len(data['articles'])} статей...")
print(f"Импортирую {len(data['car_specs'])} характеристик авто...")

# Get or create default author
admin_user = User.objects.first()
if not admin_user:
    print("Создаю пользователя admin...")
    admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin')

# Import categories (they might already exist)
for cat_data in data['categories']:
    category, created = Category.objects.get_or_create(
        slug=cat_data['slug'],
        defaults={'name': cat_data['name']}
    )
    if created:
        print(f"Создана категория: {category.name}")

# Import tags
tag_mapping = {}
for tag_data in data['tags']:
    tag, created = Tag.objects.get_or_create(
        slug=tag_data['slug'],
        defaults={'name': tag_data['name']}
    )
    tag_mapping[tag_data['id']] = tag
    if created:
        print(f"Создан тег: {tag.name}")

# Import articles
article_mapping = {}
for art_data in data['articles']:
    # Skip if article with this slug already exists
    if Article.objects.filter(slug=art_data['slug']).exists():
        print(f"Статья {art_data['slug']} уже существует, пропускаю...")
        continue
    
    # Get category
    category = None
    if art_data['category_id']:
        category = Category.objects.get(id=art_data['category_id'])
    
    # Create article
    article = Article.objects.create(
        title=art_data['title'],
        slug=art_data['slug'],
        summary=art_data.get('summary') or '',
        content=art_data['content'],
        # Don't copy image paths - files don't exist
        # image=art_data.get('image') or '',
        youtube_url=art_data.get('youtube_url') or '',
        category=category,
        is_published=bool(art_data.get('is_published', 1)),
        views=art_data.get('views') or 0,
        seo_title=art_data.get('seo_title') or art_data['title'],
        seo_description=art_data.get('seo_description') or '',
    )
    article_mapping[art_data['id']] = article
    print(f"Импортирована статья: {article.title}")

# Import car specifications
for spec_data in data['car_specs']:
    article_id = spec_data['article_id']
    if article_id not in article_mapping:
        # Try to find existing article
        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            print(f"Статья с ID {article_id} не найдена, пропускаю спецификацию...")
            continue
    else:
        article = article_mapping[article_id]
    
    # Skip if car spec for this article already exists
    if CarSpecification.objects.filter(article=article).exists():
        print(f"Спецификация для {article.title} уже существует, пропускаю...")
        continue
    
    CarSpecification.objects.create(
        article=article,
        make=spec_data.get('make') or '',
        model=spec_data.get('model') or '',
        year=spec_data.get('year'),
        engine_type=spec_data.get('engine_type') or '',
        horsepower=spec_data.get('horsepower'),
        torque=spec_data.get('torque') or '',
        transmission=spec_data.get('transmission') or '',
        drivetrain=spec_data.get('drivetrain') or '',
        fuel_economy=spec_data.get('fuel_economy') or '',
        zero_to_sixty=spec_data.get('zero_to_sixty') or '',
        top_speed=spec_data.get('top_speed') or '',
        price=spec_data.get('price') or '',
    )
    print(f"Импортирована спецификация для: {article.title}")

print("\n✅ Импорт завершён!")
print(f"Всего статей в БД: {Article.objects.count()}")
