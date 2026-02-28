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
    
    # Generate summary if not provided or if it's junk
    if not summary or len(summary.strip()) < 20 or summary.strip().rstrip(':') in ('Pros', 'Cons', 'Summary', 'Review', 'Verdict'):
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
                
                # Case D: Cloudinary relative paths (similar to rss_youtube.py fix)
                elif not img_path.startswith('/'):
                    from django.core.files.storage import default_storage
                    print(f"  ☁️ Attempting to download from default storage URL for: {img_path}")
                    try:
                        file_url = default_storage.url(img_path)
                        
                        # Fix double https issues if Cloudinary is misconfigured
                        if file_url.count('https://') > 1:
                            file_url = file_url[file_url.rfind('https://'):]
                            
                        resp = requests.get(file_url, timeout=15)
                        
                        # Cloudinary sometimes adds v1/media/ to the URL which breaks for media not in the media/ folder
                        if resp.status_code == 404:
                            print(f"  ⚠️ Storage URL {file_url} returned 404. Trying alternative paths...")
                            alt_url_1 = file_url.replace('/v1/media/', '/')
                            alt_url_2 = file_url.replace('/media/', '/')
                            for alt_url in [alt_url_1, alt_url_2]:
                                resp_alt = requests.get(alt_url, timeout=15)
                                if resp_alt.status_code == 200:
                                    resp = resp_alt
                                    print(f"  ✓ Success with alternative URL: {alt_url}")
                                    break

                        if resp.status_code == 200:
                            content = ContentFile(resp.content)
                            filename = f"image_{i+1}.jpg"
                        else:
                            print(f"  ❌ Download from storage failed with status {resp.status_code}")
                    except Exception as storage_err:
                         print(f"  ❌ Error processing storage URL: {storage_err}")
                
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
        elif not image_path.startswith('/'):
            import requests
            from django.core.files.base import ContentFile
            from django.core.files.storage import default_storage
            print(f"  ☁️ Attempting to download from default storage URL for single image: {image_path}")
            try:
                file_url = default_storage.url(image_path)
                if file_url.count('https://') > 1:
                    file_url = file_url[file_url.rfind('https://'):]
                resp = requests.get(file_url, timeout=15)
                if resp.status_code == 404:
                    alt_url_1 = file_url.replace('/v1/media/', '/')
                    alt_url_2 = file_url.replace('/media/', '/')
                    for alt_url in [alt_url_1, alt_url_2]:
                        resp_alt = requests.get(alt_url, timeout=15)
                        if resp_alt.status_code == 200:
                            resp = resp_alt
                            break
                if resp.status_code == 200:
                    content = ContentFile(resp.content)
                    filename = f"single_image.jpg"
                    article.image.save(filename, content, save=False)
                    print(f"  ✓ Image attached from storage URL")
            except Exception as e:
                print(f"  ❌ Error processing single image storage URL: {e}")
    
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
            from news.models import AutomationSettings
            from django.db.models import F as DbF
            from django.utils import timezone as tz
            auto_settings = AutomationSettings.load()
            
            if not auto_settings.google_indexing_enabled:
                print("  🔍 Google Indexing: disabled in automation settings")
            else:
                from news.management.commands.submit_to_google import submit_url_to_google
                site_url = os.environ.get('SITE_URL', 'https://www.freshmotors.net')
                article_url = f"{site_url}/articles/{article.slug}"
                result = submit_url_to_google(article_url)
                
                if result['success']:
                    print(f"  🔍 Google Indexing API: submitted {article_url}")
                    AutomationSettings.objects.filter(pk=1).update(
                        google_indexing_last_run=tz.now(),
                        google_indexing_last_status=f"✅ {article.title[:60]}",
                        google_indexing_today_count=DbF('google_indexing_today_count') + 1,
                    )
                else:
                    err_msg = result.get('error', 'unknown error')[:80]
                    print(f"  ⚠️ Google Indexing API: {err_msg}")
                    AutomationSettings.objects.filter(pk=1).update(
                        google_indexing_last_run=tz.now(),
                        google_indexing_last_status=f"❌ {err_msg}",
                    )
        except Exception as e:
            print(f"  ⚠️ Google Indexing API not configured: {e}")
    
    return article


def extract_summary(content):
    """Extract first meaningful paragraph from HTML content for summary."""
    # Remove all headings
    cleaned = re.sub(r'<h[1-6][^>]*>.*?</h[1-6]>', '', content, flags=re.DOTALL)
    
    # Find all <p> tags
    paragraphs = re.findall(r'<p>(.*?)</p>', cleaned, re.DOTALL)
    
    for p_content in paragraphs:
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', '', p_content).strip()
        # Skip short/junk paragraphs
        if len(text) < 15:
            continue
        # Skip paragraphs that are just labels
        if text.rstrip(':') in ('Pros', 'Cons', 'Summary', 'Verdict', 'Pricing'):
            continue
        return text
    
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
    Add tags based on specs data (make/model/drivetrain/engine/year/body type).
    Only adds tags that already exist in the database — never creates new ones.
    This ensures proper tagging even if the AI misses some categories.
    """
    added = []
    
    def _try_add_tag(slug_value, label=""):
        """Try to find and add a tag by slug. Returns True if added."""
        if not slug_value or slug_value in ('Not specified', 'N/A', 'Unknown', ''):
            return False
        tag_slug = slugify(slug_value)
        try:
            tag = Tag.objects.get(slug=tag_slug)
            if not article.tags.filter(pk=tag.pk).exists():
                article.tags.add(tag)
                added.append(f"{label}:{tag.name}" if label else tag.name)
                return True
        except Tag.DoesNotExist:
            pass
        return False
    
    # 1. Manufacturer tag
    make = specs.get('make', '')
    _try_add_tag(make, 'make')
    
    # 2. Model tag (try "Make Model" combo first, then just model)
    model = specs.get('model', '')
    if model and model != 'Not specified':
        if make:
            _try_add_tag(f"{make} {model}", 'model')
        _try_add_tag(model, 'model')
    
    # 3. Year tag
    year = specs.get('year', '')
    if not year:
        # Try to extract year from title
        import re
        year_match = re.search(r'20\d{2}', article.title)
        if year_match:
            year = year_match.group(0)
    _try_add_tag(str(year), 'year')
    
    # 4. Drivetrain tag (AWD, FWD, RWD, 4WD)
    drivetrain = specs.get('drivetrain', '')
    _try_add_tag(drivetrain, 'drivetrain')
    
    # 5. Fuel/powertrain type tags
    engine = specs.get('engine', '')
    fuel_types_to_check = []
    
    # Detect from engine/powertrain field
    engine_lower = (engine or '').lower()
    title_lower = article.title.lower()
    content_lower = (article.content[:2000] if article.content else '').lower()
    combined = f"{engine_lower} {title_lower} {content_lower}"
    
    if any(kw in combined for kw in ['electric', 'ev', 'kwh battery', 'battery electric', 'bev']):
        fuel_types_to_check.append('Electric')
        fuel_types_to_check.append('EV')
        fuel_types_to_check.append('BEV')
    if any(kw in combined for kw in ['hybrid', 'phev', 'plug-in']):
        fuel_types_to_check.append('Hybrid')
        fuel_types_to_check.append('PHEV')
        fuel_types_to_check.append('Plug-in Hybrid')
    if any(kw in combined for kw in ['diesel', 'tdi', 'cdi', 'dci']):
        fuel_types_to_check.append('Diesel')
    if any(kw in combined for kw in ['turbo', 'turbocharged']):
        fuel_types_to_check.append('Turbocharged')
    if any(kw in combined for kw in ['hydrogen', 'fuel cell', 'fcev']):
        fuel_types_to_check.append('Hydrogen')
    if any(kw in combined for kw in ['gasoline', 'petrol', 'v6', 'v8', 'v12', 'inline-4', 'i4']):
        fuel_types_to_check.append('Gasoline')
    
    for ft in fuel_types_to_check:
        _try_add_tag(ft, 'fuel')
    
    # 6. Body type tags
    body_types_to_check = []
    if any(kw in combined for kw in ['suv', 'crossover']):
        body_types_to_check.extend(['SUV', 'Crossover'])
    if any(kw in combined for kw in ['sedan', 'saloon']):
        body_types_to_check.append('Sedan')
    if any(kw in combined for kw in ['hatchback', 'hatch']):
        body_types_to_check.append('Hatchback')
    if any(kw in combined for kw in ['coupe', 'coupé']):
        body_types_to_check.append('Coupe')
    if any(kw in combined for kw in ['convertible', 'cabriolet', 'roadster', 'spider']):
        body_types_to_check.extend(['Convertible', 'Roadster'])
    if any(kw in combined for kw in ['truck', 'pickup']):
        body_types_to_check.extend(['Truck', 'Pickup'])
    if any(kw in combined for kw in ['van', 'minivan', 'mpv']):
        body_types_to_check.extend(['Van', 'Minivan', 'MPV'])
    if any(kw in combined for kw in ['wagon', 'estate', 'shooting brake']):
        body_types_to_check.extend(['Wagon', 'Estate'])
    if any(kw in combined for kw in ['supercar', 'hypercar']):
        body_types_to_check.extend(['Supercar', 'Hypercar'])
    
    for bt in body_types_to_check:
        _try_add_tag(bt, 'body')
    
    # 7. Tech & Features tags
    tech_to_check = []
    if any(kw in combined for kw in ['autonomous', 'self-driving', 'autopilot', 'adas']):
        tech_to_check.extend(['Autonomous Driving', 'ADAS'])
    if any(kw in combined for kw in ['lidar', 'radar']):
        tech_to_check.append('LiDAR')
    if any(kw in combined for kw in ['air suspension']):
        tech_to_check.append('Air Suspension')
    if any(kw in combined for kw in ['4-wheel steering', 'rear-wheel steering', 'four-wheel steering']):
        tech_to_check.append('4-Wheel Steering')
    if any(kw in combined for kw in ['heads-up display', 'head-up display', 'hud']):
        tech_to_check.append('Heads-Up Display')
    if any(kw in combined for kw in ['panoramic roof', 'glass roof', 'sunroof']):
        tech_to_check.append('Panoramic Roof')
    if any(kw in combined for kw in ['wireless charging', 'inductive charging']):
        tech_to_check.append('Wireless Charging')
    
    for tech in tech_to_check:
        _try_add_tag(tech, 'tech')
    
    if added:
        print(f"  ✓ Spec-based tags added: {', '.join(added)}")

