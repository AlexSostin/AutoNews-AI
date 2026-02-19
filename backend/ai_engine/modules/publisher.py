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

def publish_article(title, content, category_name="Reviews", image_path=None, image_paths=None, youtube_url=None, summary=None, tag_names=None, specs=None, meta_keywords=None, is_published=True, author_name="", author_channel_url="", generation_metadata=None):
    """
    Publishes the article to the Django database with full metadata.
    
    Args:
        image_path: Single image path (backwards compatibility)
        image_paths: List of up to 3 image paths [screenshot1, screenshot2, screenshot3]
        meta_keywords: Comma-separated SEO keywords
        is_published: Whether to publish immediately (True) or save as draft (False)
        author_name: Original content creator name
        author_channel_url: Original creator channel URL
    """
    print(f"📤 Publishing article: {title} (Published: {is_published})")
    
    # Get or Create Category
    cat_slug = slugify(category_name)
    category, created = Category.objects.get_or_create(
        slug=cat_slug,
        defaults={'name': category_name}
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
    
    # Create Article (category is M2M, added after save)
    article = Article(
        title=title,
        summary=summary,
        content=content,
        content_original=content,
        youtube_url=youtube_url or '',
        is_published=is_published,
        seo_title=seo_title,
        seo_description=seo_description,
        meta_keywords=meta_keywords or '',
        author_name=author_name,
        author_channel_url=author_channel_url,
        generation_metadata=generation_metadata
    )
    
    # Add images (support for 3 screenshots from video)
    if image_paths and isinstance(image_paths, list):
        print(f"  📸 Processing {len(image_paths)} image paths")
        import requests
        from django.core.files.base import ContentFile
        
        # Multiple screenshots from video
        for i, img_path in enumerate(image_paths[:3]):  # Max 3 images
            if not img_path:
                print(f"  ⚠️ Image path {i+1} is None")
                continue

            try:
                content = None
                filename = None
                cloudinary_url = None
                
                # Case A: Already on Cloudinary - reuse directly
                if 'cloudinary.com' in img_path:
                    print(f"  ♻️ Reusing Cloudinary URL for image {i+1}: {img_path}")
                    cloudinary_url = img_path
                
                # Case B: Non-Cloudinary URL (Pexels, etc)
                elif img_path.startswith('http'):
                    print(f"  ⬇️ Downloading image from URL: {img_path}")
                    resp = requests.get(img_path)
                    if resp.status_code == 200:
                        content = ContentFile(resp.content)
                        filename = f"image_{i+1}.jpg"
                    else:
                        print(f"  ❌ Failed to download: {resp.status_code}")
                
                # Case C: Local File (Relative or Absolute)
                elif img_path.startswith('/media/'):
                    from django.conf import settings
                    full_path = os.path.join(settings.BASE_DIR, img_path.lstrip('/'))
                    if os.path.exists(full_path):
                        print(f"  📂 Reading relative media: {full_path}")
                        with open(full_path, 'rb') as f:
                            file_content = f.read()
                            content = ContentFile(file_content)
                            filename = os.path.basename(img_path)
                    else:
                        print(f"  ⚠️ Relative media file not found: {full_path}")
                
                elif os.path.exists(img_path):
                    print(f"  📂 Reading absolute local image: {img_path}")
                    with open(img_path, 'rb') as f:
                        file_content = f.read()
                        content = ContentFile(file_content)
                        filename = os.path.basename(img_path)
                
                else:
                    print(f"  ⚠️ Image file not found: {img_path}")
                    
                # Save if we got cloudinary URL or content
                if cloudinary_url:
                    if i == 0:
                        article.image = cloudinary_url
                    elif i == 1:
                        article.image_2 = cloudinary_url
                    elif i == 2:
                        article.image_3 = cloudinary_url
                    print(f"  ✓ Image {i+1} assigned from Cloudinary")
                elif content and filename:
                    if i == 0:
                        article.image.save(filename, content, save=False)
                    elif i == 1:
                        article.image_2.save(filename, content, save=False)
                    elif i == 2:
                        article.image_3.save(filename, content, save=False)
                    print(f"  ✓ Image {i+1} attached: {filename}")
                    
            except Exception as e:
                print(f"  ❌ Error processing image {img_path}: {e}")

    elif image_path:
        # Single image (backwards compatibility)
        if image_path.startswith('http'):
             # ... Logic for single URL if needed ...
             pass
        elif os.path.exists(image_path):
            filename = os.path.basename(image_path)
            with open(image_path, 'rb') as f:
                file_content = File(f, name=filename)
                article.image.save(filename, file_content, save=False)
                print(f"  ✓ Image attached: {filename}")
    
    article.save()
    print(f"  ✓ Article saved with slug: {article.slug}")
    
    # Add category (M2M - must be done after save)
    article.categories.add(category)
    print(f"  ✓ Category assigned: {category_name}")
    
    # Add tags
    if tag_names:
        added_tags = []
        for tag_name in tag_names:
            slug = slugify(tag_name)
            tag, created = Tag.objects.get_or_create(
                slug=slug,
                defaults={'name': tag_name}
            )
            article.tags.add(tag)
            added_tags.append(tag_name)
        
        if added_tags:
            print(f"  ✓ Tags added: {', '.join(added_tags)}")
    
    # Smart brand/model tagging from specs
    if specs:
        _add_spec_based_tags(article, specs)
    
    # Save car specifications
    if specs and specs.get('make') != 'Not specified':
        try:
            car_spec, _ = CarSpecification.objects.update_or_create(
                article=article,
                defaults={
                    'model_name': f"{specs.get('make', '')} {specs.get('model', '')} {specs.get('trim', '')}".strip(),
                    'make': specs.get('make', ''),
                    'model': specs.get('model', ''),
                    'trim': specs.get('trim', ''),
                    'year': specs.get('year'),
                    'engine': specs.get('engine', ''),
                    'horsepower': specs.get('horsepower'),
                    'torque': specs.get('torque', ''),
                    'zero_to_sixty': specs.get('zero_to_sixty', specs.get('acceleration', '')),
                    'top_speed': specs.get('top_speed', ''),
                    'drivetrain': specs.get('drivetrain', ''),
                    'price': specs.get('price', ''),
                }
            )
            print(f"  ✓ Car specs saved: {specs['make']} {specs['model']}")
        except Exception as e:
            print(f"  ⚠️  Failed to save specs: {e}")
    
    print(f"✅ Article published successfully! ID: {article.id}")
    
    # Auto-submit to Google Indexing API for instant indexing
    if is_published:
        try:
            from news.management.commands.submit_to_google import submit_url_to_google
            site_url = os.environ.get('SITE_URL', 'https://www.freshmotors.net')
            article_url = f"{site_url}/articles/{article.slug}"
            result = submit_url_to_google(article_url)
            if result['success']:
                print(f"  🔍 Google Indexing API: submitted {article_url}")
            else:
                print(f"  ⚠️ Google Indexing API: {result.get('error', 'unknown error')[:80]}")
        except Exception as e:
            print(f"  ⚠️ Google Indexing API not configured: {e}")
    
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


def _add_spec_based_tags(article, specs):
    """
    Add tags based on specs data (make/model).
    Only adds tags that already exist in the database — never creates new ones.
    This ensures the brand is always properly tagged even if the AI misses it.
    """
    added = []
    
    # Add manufacturer tag
    make = specs.get('make', 'Not specified')
    if make and make != 'Not specified':
        make_slug = slugify(make)
        try:
            tag = Tag.objects.get(slug=make_slug)
            if not article.tags.filter(pk=tag.pk).exists():
                article.tags.add(tag)
                added.append(f"make:{tag.name}")
        except Tag.DoesNotExist:
            pass  # Brand not in DB, skip
    
    # Add model tag
    model = specs.get('model', 'Not specified')
    if model and model != 'Not specified':
        model_slug = slugify(model)
        try:
            tag = Tag.objects.get(slug=model_slug)
            if not article.tags.filter(pk=tag.pk).exists():
                article.tags.add(tag)
                added.append(f"model:{tag.name}")
        except Tag.DoesNotExist:
            pass  # Model not in DB, skip
    
    if added:
        print(f"  ✓ Spec-based tags added: {', '.join(added)}")

