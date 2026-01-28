import os
import sys
import django

# Setup Django Environment only if not already configured
try:
    from django.apps import apps
    if not apps.ready:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.append(BASE_DIR)
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
        django.setup()
except:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.append(BASE_DIR)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
    django.setup()

from news.models import Article, Category, Tag, CarSpecification
from django.core.files import File
from django.utils.text import slugify
import re

def publish_article(title, content, category_name="Reviews", image_path=None, image_paths=None, youtube_url=None, summary=None, tag_names=None, specs=None, meta_keywords=None):
    """
    Publishes the article to the Django database with full metadata.
    
    Args:
        image_path: Single image path (backwards compatibility)
        image_paths: List of up to 3 image paths [screenshot1, screenshot2, screenshot3]
        meta_keywords: Comma-separated SEO keywords
    """
    print(f"📤 Publishing article: {title}")
    
    # Get or Create Category
    category, created = Category.objects.get_or_create(
        name=category_name,
        defaults={'slug': slugify(category_name)}
    )
    if created:
        print(f"  ✓ Created new category: {category_name}")
    
    # Generate summary if not provided
    if not summary:
        # Extract first paragraph from content
        summary = extract_summary(content)
    
    # Trim summary to 300 chars
    if len(summary) > 300:
        summary = summary[:297] + "..."
    
    # Generate SEO fields
    seo_title = generate_seo_title(title)
    seo_description = summary[:160]  # Meta description limit
    
    # Create Article
    article = Article(
        title=title,
        summary=summary,
        content=content,
        category=category,
        youtube_url=youtube_url or '',
        is_published=True,
        seo_title=seo_title,
        seo_description=seo_description,
        meta_keywords=meta_keywords or ''
    )
    
    # Add images (support for 3 screenshots from video)
    if image_paths and isinstance(image_paths, list):
        print(f"  📸 Processing {len(image_paths)} image paths: {image_paths}")
        # Multiple screenshots from video
        for i, img_path in enumerate(image_paths[:3]):  # Max 3 images
            if img_path:
                print(f"  📸 Checking image {i+1}: {img_path}")
                print(f"      exists: {os.path.exists(img_path)}")
                if os.path.exists(img_path):
                    file_size = os.path.getsize(img_path)
                    print(f"      size: {file_size} bytes")
                    filename = os.path.basename(img_path)
                    with open(img_path, 'rb') as f:
                        file_content = File(f, name=filename)
                        if i == 0:
                            article.image.save(filename, file_content, save=False)
                        elif i == 1:
                            article.image_2.save(filename, file_content, save=False)
                        elif i == 2:
                            article.image_3.save(filename, file_content, save=False)
                    print(f"  ✓ Screenshot {i+1} saved to storage: {filename}")
                else:
                    print(f"  ⚠️ Image file not found: {img_path}")
            else:
                print(f"  ⚠️ Image path {i+1} is None")
    elif image_path and os.path.exists(image_path):
        # Single image (backwards compatibility)
        filename = os.path.basename(image_path)
        with open(image_path, 'rb') as f:
            file_content = File(f, name=filename)
            article.image.save(filename, file_content, save=False)
            print(f"  ✓ Image attached: {filename}")
    
    article.save()
    print(f"  ✓ Article saved with slug: {article.slug}")
    
    # Add tags
    if tag_names:
        added_tags = []
        for tag_name in tag_names:
            tag, created = Tag.objects.get_or_create(
                name=tag_name,
                defaults={'slug': slugify(tag_name)}
            )
            article.tags.add(tag)
            added_tags.append(tag_name)
        
        if added_tags:
            print(f"  ✓ Tags added: {', '.join(added_tags)}")
    
    # Save car specifications
    if specs and specs.get('make') != 'Not specified':
        try:
            car_spec = CarSpecification.objects.create(
                article=article,
                make=specs.get('make', ''),
                model=specs.get('model', ''),
                year=specs.get('year'),
                engine_type=specs.get('engine', ''),
                horsepower=specs.get('horsepower'),
                torque=specs.get('torque', ''),
                zero_to_sixty=specs.get('acceleration', ''),
                top_speed=specs.get('top_speed', ''),
                price=specs.get('price', ''),
            )
            print(f"  ✓ Car specs saved: {specs['make']} {specs['model']}")
        except Exception as e:
            print(f"  ⚠️  Failed to save specs: {e}")
    
    print(f"✅ Article published successfully! ID: {article.id}")
    return article


def extract_summary(content):
    """Извлекает первый параграф из HTML контента для summary."""
    # Удаляем заголовок
    content = re.sub(r'<h2>.*?</h2>', '', content, count=1, flags=re.DOTALL)
    
    # Ищем первый <p> тег
    match = re.search(r'<p>(.*?)</p>', content, re.DOTALL)
    if match:
        summary = match.group(1)
        # Очищаем от HTML тегов
        summary = re.sub(r'<[^>]+>', '', summary)
        return summary.strip()
    
    return "AI-generated automotive article with detailed analysis and specifications."


def generate_seo_title(title):
    """Генерирует SEO-оптимизированный title (до 60 символов)."""
    # Если title уже короткий, используем как есть
    if len(title) <= 60:
        return title
    
    # Извлекаем основную информацию: марку, модель, год
    match = re.search(r'(\d{4})\s+(\w+)\s+(\w+)', title)
    if match:
        year, make, model = match.groups()
        return f"{year} {make} {model} Review & Specs"
    
    # Если не нашли паттерн, обрезаем title
    return title[:57] + "..."
