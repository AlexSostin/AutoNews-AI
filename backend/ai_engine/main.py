import argparse
import os
import sys
import re
import logging
import requests

logger = logging.getLogger(__name__)

# Add ai_engine directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import config first to ensure it's available
try:
    from ai_engine.config import GROQ_API_KEY
except ImportError:
    try:
        from config import GROQ_API_KEY
    except ImportError:
        GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Import modules
try:
    from ai_engine.modules.downloader import download_audio_and_thumbnail
    from ai_engine.modules.transcriber import transcribe_from_youtube
    from ai_engine.modules.analyzer import analyze_transcript
    from ai_engine.modules.article_generator import generate_article
    from ai_engine.modules.publisher import publish_article
    from ai_engine.modules.downloader import extract_video_screenshots
except ImportError:
    from modules.downloader import download_audio_and_thumbnail
    from modules.transcriber import transcribe_from_youtube
    from modules.analyzer import analyze_transcript
    from modules.article_generator import generate_article
    from modules.publisher import publish_article
    from modules.downloader import extract_video_screenshots

# Generic section headers that AI generates as part of article structure.
# These should NEVER be used as article titles.
GENERIC_SECTION_HEADERS = [
    'performance & specs', 'performance and specs',
    'performance & specifications', 'performance and specifications',
    'performance \u0026 specifications', 'performance \u0026amp; specifications',
    'performance \u0026 specs', 'performance \u0026amp; specs',
    'design & interior', 'design and interior',
    'design \u0026 interior', 'design \u0026amp; interior',
    'technology & features', 'technology and features',
    'technology \u0026 features', 'technology \u0026amp; features',
    'driving experience', 'driving impressions',
    'pros & cons', 'pros and cons', 'pros \u0026 cons',
    'conclusion', 'summary', 'overview', 'introduction',
    'us market availability & pricing', 'us market availability',
    'global market & regional availability', 'global market',
    'market availability & pricing', 'pricing & availability',
    'pricing and availability', 'specifications', 'features',
    'details', 'information', 'title:', 'new car review',
    'interior & comfort', 'safety & technology',
    'exterior design', 'interior design',
    'engine & performance', 'powertrain',
    'battery & range', 'charging & range',
]


def _is_generic_header(text: str) -> bool:
    """
    Check if a text is a generic section header that shouldn't be a title.
    Uses fuzzy matching to catch variations.
    """
    clean = text.strip().lower()
    # Remove HTML entities
    clean = clean.replace('&amp;', '&').replace('\u0026amp;', '&').replace('\u0026', '&')
    # Remove leading/trailing punctuation
    clean = re.sub(r'^[\s\-:]+|[\s\-:]+$', '', clean)
    
    # Exact or substring match against known headers
    for header in GENERIC_SECTION_HEADERS:
        if clean == header or (header in clean and len(clean) < 50):
            return True
    
    # Regex patterns for common generic headers
    generic_patterns = [
        r'^(the\s+)?\d{4}\s+(performance|specs|design)',  # "2025 Performance"
        r'^(pros|cons)\s*(\u0026|and|&)',
        r'^(key\s+)?(features|specifications|highlights)$',
        r'^(final\s+)?(verdict|thoughts|conclusion)s?$',
        r'^(driving|ride|road)\s+(experience|test|review)$',
    ]
    for pattern in generic_patterns:
        if re.match(pattern, clean, re.IGNORECASE):
            return True
    
    return False


def validate_title(title: str, video_title: str = None, specs: dict = None) -> str:
    """
    Validates and fixes article title. Returns a good title or constructs one from available data.
    
    Priority:
    1. Use provided title if it's valid (not generic, long enough, contains brand/model info)
    2. Use video_title if available
    3. Construct from specs (Year Make Model Review)
    4. Last resort: generic but unique-ish fallback
    """
    # Check if title is valid
    if title and len(title) > 15 and not _is_generic_header(title):
        # Additional check: title should contain at least some brand/model indicator
        return title.strip()
    
    # Fallback 1: Use video title (cleaned up)
    if video_title and len(video_title) > 10:
        # Clean video title (remove channel name suffixes, etc.)
        clean_vt = re.sub(r'\s*[|\-–]\s*[^|\-–]+$', '', video_title).strip()
        if clean_vt and len(clean_vt) > 10:
            return clean_vt
        return video_title.strip()
    
    # Fallback 2: Construct from specs
    if specs:
        make = specs.get('make', '')
        model = specs.get('model', '')
        year = specs.get('year', '')
        trim = specs.get('trim', '')
        
        if make and make != 'Not specified' and model and model != 'Not specified':
            year_str = f"{year} " if year else ""
            trim_str = f" {trim}" if trim and trim != 'Not specified' else ""
            return f"{year_str}{make} {model}{trim_str} Review"
    
    # Last resort
    return title if (title and len(title) > 5) else "New Car Review"


def extract_title(html_content):
    """
    Extracts the main article title from generated HTML.
    Ignores generic section headers like 'Performance & Specifications'.
    """
    # Find all h2 tags (handle attributes in tags)
    h2_matches = re.findall(r'<h2[^>]*>(.*?)</h2>', html_content, re.IGNORECASE | re.DOTALL)
    
    for title in h2_matches:
        # Strip HTML tags inside the h2 (e.g., <strong>, <em>)
        clean_t = re.sub(r'<[^>]+>', '', title).strip()
        clean_t = clean_t.replace('Title:', '').strip()
        
        # Skip empty or very short
        if len(clean_t) < 10:
            continue
        
        # Skip generic section headers
        if _is_generic_header(clean_t):
            continue
        
        return clean_t
    
    return None  # Return None instead of fallback — let validate_title handle it

def main(youtube_url):
    print(f"Starting pipeline for: {youtube_url}")
    
    # 1. Download
    # audio_path, thumbnail_path = download_audio_and_thumbnail(youtube_url)
    
    # 2. Transcribe
    # transcript = transcribe_audio(audio_path)
    
    # For testing without wasting API credits/Time, let's mock if needed
    # transcript = "Mock transcript..."
    
    # 3. Analyze
    # analysis = analyze_transcript(transcript)
    
    # 4. Generate Article
    # article_html = generate_article(analysis)
    
    # Mocking for demonstration since we don't have API keys set up
    article_html = "<h2>2026 Future Car Review</h2><p>This is a generated article with a mockup image.</p>"
    
    # 5. Publish
    title = extract_title(article_html)
    
    # Pass thumbnail_path if we had real download
    # publish_article(title, article_html, image_path=thumbnail_path)
    
    # Mock publish
    publish_article(title, article_html)
    
    print("Pipeline finished.")

def check_duplicate(youtube_url):
    """
    Проверяет, не генерировали ли мы уже статью с этого видео.
    """
    # Setup Django if not configured
    import django
    if not django.apps.apps.ready:
        import os
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.append(BASE_DIR)
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
        django.setup()
    
    from news.models import Article
    
    existing = Article.objects.filter(youtube_url=youtube_url).first()
    if existing:
        print(f"⚠️  Статья уже существует: {existing.slug} (ID: {existing.id})")
        return existing
    return None


def _generate_article_content(youtube_url, task_id=None, provider='groq', video_title=None):
    """
    Internal function to generate article content without saving to DB.
    Returns dictionary with all article data.
    """
    def send_progress(step, progress, message):
        """Send progress update via WebSocket"""
        if not task_id:
            print(f"[{progress}%] {message}")
            return
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"generation_{task_id}",
                    {
                        "type": "send_progress",
                        "step": step,
                        "progress": progress,
                        "message": message
                    }
                )
        except Exception as e:
            print(f"WebSocket progress error: {e}")

    try:
        provider_name = "Groq" if provider == 'groq' else "Google Gemini"
        send_progress(1, 5, f"🚀 Начинаем генерацию с {provider_name}...")
        print(f"🚀 Генерация контента из: {youtube_url} используя {provider_name}")
        
        # 0. Получаем заголовок видео и информацию о канале
        author_name = ''
        author_channel_url = ''
        try:
            oembed_url = f"https://www.youtube.com/oembed?url={youtube_url}&format=json"
            resp = requests.get(oembed_url, timeout=5)
            if resp.status_code == 200:
                oembed_data = resp.json()
                if not video_title:
                    video_title = oembed_data.get('title')
                    print(f"🎥 Fetched Video Title: {video_title}")
                author_name = oembed_data.get('author_name', '')
                author_channel_url = oembed_data.get('author_url', '')
                print(f"👤 Channel: {author_name} ({author_channel_url})")
        except Exception as e:
            print(f"⚠️ Could not fetch video metadata: {e}")

        # 1. Получаем транскрипт
        send_progress(2, 20, "📝 Получение субтитров с YouTube...")
        print("📝 Получение транскрипта...")
        transcript = transcribe_from_youtube(youtube_url)
        
        if not transcript or len(transcript) < 5 or transcript.startswith("ERROR:"):
            error_msg = transcript if transcript and transcript.startswith("ERROR:") else "Failed to retrieve transcript or it is too short"
            send_progress(2, 100, f"❌ {error_msg}")
            raise Exception(error_msg)
        
        send_progress(2, 30, f"✓ Transcript received ({len(transcript)} chars)")
        
        # 2. Analyze transcript
        send_progress(3, 40, f"🔍 Analyzing transcript with {provider_name} AI...")
        print("🔍 Analyzing transcript...")
        analysis = analyze_transcript(transcript, video_title=video_title, provider=provider)
        
        if not analysis:
            send_progress(3, 100, "❌ Analysis failed")
            raise Exception("Failed to analyze transcript")
        
        send_progress(3, 50, "✓ Analysis complete")
        
        # 2.5. Categorize and Tags
        send_progress(4, 55, "🏷️ Categorizing...")
        from modules.analyzer import categorize_article, extract_specs_dict
        
        category_name, tag_names = categorize_article(analysis)
        
        # 2.6. Extract Specs
        specs = extract_specs_dict(analysis)
        send_progress(4, 60, f"✓ {specs['make']} {specs['model']}")
        
        # 2.65. DUPLICATE CHECK — skip if article already exists for same car
        if specs.get('make') and specs['make'] != 'Not specified' and specs.get('model') and specs['model'] != 'Not specified':
            try:
                from news.models import CarSpecification
                existing = CarSpecification.objects.filter(
                    make__iexact=specs['make'],
                    model__iexact=specs['model'],
                    article__is_published=True,
                )
                # Also match trim if available
                trim = specs.get('trim', 'Not specified')
                if trim and trim != 'Not specified':
                    existing_same_trim = existing.filter(trim__iexact=trim)
                    if existing_same_trim.exists():
                        existing_article = existing_same_trim.first().article
                        msg = (f"⚠️ Duplicate detected: {specs['make']} {specs['model']} {trim} "
                               f"already exists (Article #{existing_article.id}: \"{existing_article.title}\")")
                        print(msg)
                        send_progress(4, 100, f"⚠️ Skipped — duplicate of article #{existing_article.id}")
                        return {'status': 'skipped', 'reason': 'duplicate', 'existing_article_id': existing_article.id,
                                'message': msg}
                else:
                    # No trim info — check if any article exists for this make+model
                    if existing.exists():
                        existing_article = existing.first().article
                        msg = (f"⚠️ Duplicate detected: {specs['make']} {specs['model']} "
                               f"already exists (Article #{existing_article.id}: \"{existing_article.title}\")")
                        print(msg)
                        send_progress(4, 100, f"⚠️ Skipped — duplicate of article #{existing_article.id}")
                        return {'status': 'skipped', 'reason': 'duplicate', 'existing_article_id': existing_article.id,
                                'message': msg}
            except Exception as e:
                print(f"⚠️ Duplicate check failed (continuing anyway): {e}")
        
        # 2.7 WEB SEARCH ENRICHMENT
        web_context = ""
        try:
            from ai_engine.modules.searcher import get_web_context
            send_progress(4, 62, "🌐 Searching web for facts...")
            
            # Helper to clean model name if it's "Chin L"
            if "Chin" in specs.get('model', '') and "Qin" not in specs.get('model', ''):
                specs['model'] = specs['model'].replace("Chin", "Qin")
                
            web_context = get_web_context(specs)
            if web_context:
                print(f"✓ Web search successful")
        except Exception as e:
            print(f"⚠️ Web search failed: {e}")
        
        # 2.8 SPECS ENRICHMENT — fill gaps using web data
        if web_context:
            try:
                from ai_engine.modules.specs_enricher import enrich_specs_from_web
                send_progress(4, 63, "🔍 Cross-referencing specs...")
                specs = enrich_specs_from_web(specs, web_context)
                
                # Build enriched analysis to give the generator better data
                enriched_lines = []
                for key in ['make', 'model', 'trim', 'year', 'engine', 'torque', 
                           'acceleration', 'top_speed', 'drivetrain', 'battery', 'range', 'price']:
                    val = specs.get(key, 'Not specified')
                    if val and val != 'Not specified':
                        enriched_lines.append(f"{key.replace('_', ' ').title()}: {val}")
                hp = specs.get('horsepower')
                if hp:
                    enriched_lines.append(f"Horsepower: {hp} hp")
                
                if enriched_lines:
                    analysis += f"\n\n[ENRICHED SPECS FROM WEB]:\n" + '\n'.join(enriched_lines)
            except Exception as e:
                print(f"⚠️ Specs enrichment failed (continuing): {e}")
        
        # 3. Generate Article
        send_progress(5, 65, f"✍️ Generating article with {provider_name}...")
        print(f"✍️  Generating article...")
        
        # Pass web context to generator
        article_html = generate_article(analysis, provider=provider, web_context=web_context)
        
        if not article_html or len(article_html) < 100:
            send_progress(5, 100, "❌ Article generation failed")
            raise Exception("Article content is empty or too short")
        
        send_progress(5, 75, "✓ Статья сгенерирована")
        
        # 4. Определяем заголовок (Title) — multi-layer validation
        title = None
        
        # Priority 1: SEO Title from Analysis
        if specs.get('seo_title') and len(specs['seo_title']) > 5:
            candidate = specs['seo_title'].replace('"', '').replace("'", "")
            if not _is_generic_header(candidate):
                title = candidate
                print(f"📌 Using SEO Title from Analysis: {title}")
            
        # Priority 2: Extract from HTML <h2> (first non-generic header)
        if not title:
            extracted = extract_title(article_html)
            if extracted:
                title = extracted
                print(f"📌 Extracted Title from HTML: {title}")
        
        # Priority 3: Construct from Specs (if Make/Model exist)
        if not title and specs.get('make') and specs.get('model') and specs['make'] != 'Not specified':
            year = specs.get('year', '')
            year_str = f"{year} " if year else ""
            trim = specs.get('trim', '')
            trim_str = f" {trim}" if trim and trim != 'Not specified' else ""
            title = f"{year_str}{specs['make']} {specs['model']}{trim_str} Review"
            print(f"📌 Constructed Title from Specs: {title}")
            
        # Final validation — catches anything that slipped through
        title = validate_title(title, video_title=video_title, specs=specs)
        print(f"✅ Final validated title: {title}")
        
        # 5. Извлекаем 3 скриншота из видео
        send_progress(6, 80, "📸 Извлечение скриншотов...")
        print("📸 Извлечение скриншотов...")
        screenshot_paths = []
        try:
            screenshots_dir = os.path.join(current_dir, 'output', 'screenshots')
            os.makedirs(screenshots_dir, exist_ok=True)
            local_paths = extract_video_screenshots(youtube_url, output_dir=screenshots_dir, count=3)
            
            if local_paths:
                # Upload to Cloudinary immediately
                import cloudinary
                import cloudinary.uploader
                import shutil
                from django.conf import settings
                
                print(f"☁️ Uploading {len(local_paths)} screenshots to Cloudinary...")
                for path in local_paths:
                    if os.path.exists(path):
                        uploaded = False
                        try:
                            # Try Cloudinary first
                            if os.getenv('CLOUDINARY_URL'):
                                upload_result = cloudinary.uploader.upload(
                                    path, 
                                    folder="pending_articles",
                                    resource_type="image"
                                )
                                secure_url = upload_result.get('secure_url')
                                if secure_url:
                                    screenshot_paths.append(secure_url)
                                    print(f"  ✓ Uploaded: {secure_url}")
                                    uploaded = True
                        except Exception as cloud_err:
                            print(f"  ⚠️ Cloudinary upload failed for {path}: {cloud_err}")
                        
                        # Fallback to local media if not uploaded
                        if not uploaded:
                            try:
                                # Copy to MEDIA_ROOT
                                media_dir = os.path.join(settings.MEDIA_ROOT, 'screenshots')
                                os.makedirs(media_dir, exist_ok=True)
                                filename = os.path.basename(path)
                                dest_path = os.path.join(media_dir, filename)
                                shutil.copy2(path, dest_path)
                                # Store relative URL for DB and frontend
                                relative_url = os.path.join(settings.MEDIA_URL, 'screenshots', filename)
                                screenshot_paths.append(relative_url)
                                print(f"  ✓ Copied to media: {dest_path} -> {relative_url}")
                            except Exception as copy_err:
                                print(f"  ❌ Failed to copy to media: {copy_err}")
                                screenshot_paths.append(path) # Last resort
                    else:
                        screenshot_paths.append(path)
                        
                send_progress(6, 85, f"✓ Извлечено и загружено {len(screenshot_paths)} скриншотов")
            else:
                send_progress(6, 85, "⚠️ Скриншоты не найдены")
        except Exception as e:
            print(f"⚠️  Ошибка при извлечении/загрузке скриншотов: {e}")
            screenshot_paths = []
        
        # 6. Создаем краткое описание
        send_progress(7, 90, "📝 Создание описания...")
        import html
        
        # Try to extract summary from AI analysis if available
        summary = ""
        if isinstance(analysis, str) and 'Summary:' in analysis:
            summary = analysis.split('Summary:')[-1].split('\n')[0].strip()
        elif isinstance(analysis, dict) and analysis.get('summary'):
            summary = analysis.get('summary')
            
        if not summary:
            # Scrape from HTML, but skip the first heading (it's often redundant)
            # and thoroughly clean tags and unescape content
            temp_content = article_html
            # Skip first h2 if it exists
            if '</h2>' in temp_content:
                temp_content = temp_content.split('</h2>', 1)[-1]
            
            import re
            match = re.search(r'<p>(.*?)</p>', temp_content, re.DOTALL)
            if match:
                raw_text = match.group(1)
                # Unescape first to catch &lt;h2&gt; etc.
                clean_text = html.unescape(raw_text)
                # Strip any remaining tags
                summary = re.sub(r'<[^>]+>', '', clean_text).strip()[:300]
            else:
                # Absolute fallback from whole content
                clean_all = re.sub(r'<[^>]+>', '', html.unescape(temp_content))
                summary = clean_all.strip()[:300]
                
        if not summary:
            summary = f"Comprehensive review of the {specs.get('make', '')} {specs.get('model', '')}"
        
        # 6.5. Генерация SEO keywords
        from modules.seo_helpers import generate_seo_keywords
        seo_keywords = ''
        if isinstance(analysis, dict):
            seo_keywords = generate_seo_keywords(analysis, title)
        
        return {
            'success': True,
            'title': title,
            'content': article_html,
            'summary': summary,
            'category_name': category_name,
            'tag_names': tag_names,
            'specs': specs,
            'meta_keywords': seo_keywords,
            'image_paths': screenshot_paths,
            'analysis': analysis,
            'video_title': video_title,
            'author_name': author_name,
            'author_channel_url': author_channel_url
        }
        
    except Exception as e:
        print(f"❌ Error in _generate_article_content: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }

def generate_article_from_youtube(youtube_url, task_id=None, provider='groq', is_published=True):
    """Generate and publish immediately (LEGACY/MANUAL flow)"""
    
    # 0. Check duplicate first
    existing = check_duplicate(youtube_url)
    if existing:
        return {
            'success': False,
            'error': f'Статья уже существует: {existing.title}',
            'article_id': existing.id,
            'duplicate': True
        }
        
    result = _generate_article_content(youtube_url, task_id, provider)
    
    if not result['success']:
        return result
        
    # Publish to DB
    print(f"📤 Публикация статьи... (Published: {is_published})")
    article = publish_article(
        title=result['title'],
        content=result['content'],
        summary=result['summary'],
        category_name=result['category_name'],
        youtube_url=youtube_url,
        image_paths=result['image_paths'],
        tag_names=result['tag_names'],
        specs=result['specs'],
        is_published=is_published,
        meta_keywords=result['meta_keywords'],
        author_name=result.get('author_name', ''),
        author_channel_url=result.get('author_channel_url', '')
    )
    
    print(f"✅ Статья успешно создана! ID: {article.id}, Slug: {article.slug}")
    
    return {
        'success': True,
        'article_id': article.id,
        'title': result['title'],
        'slug': article.slug,
        'category': result['category_name'],
        'tags': result['tag_names']
    }

def create_pending_article(youtube_url, channel_id, video_title, video_id, provider='groq'):
    """Generate article and save as PendingArticle (NEW flow)"""
    
    # Setup Django
    import django
    if not django.apps.apps.ready:
        import os
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.append(BASE_DIR)
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
        django.setup()
        
    from news.models import PendingArticle, YouTubeChannel, Category, Article
    
    # 1. Check if article exists (only non-deleted)
    existing = Article.objects.filter(youtube_url=youtube_url, is_deleted=False).exists()
    if existing:
        print(f"Skipping {youtube_url} - already exists")
        return {'success': False, 'reason': 'exists', 'error': 'Article already exists in the database'}
        
    # 2. Check if already pending (exclude rejected or published-but-deleted)
    # We allow generation if the existing PendingArticle is 'rejected' 
    # or if it's 'published' but the resulting article was later deleted.
    pending_exists = PendingArticle.objects.filter(video_id=video_id, status__in=['pending', 'approved']).exists()
    if pending_exists:
        print(f"Skipping {youtube_url} - already pending")
        return {'success': False, 'reason': 'pending', 'error': 'Article is already in the pending queue'}
    
    # 3. Generate content
    result = _generate_article_content(youtube_url, task_id=None, provider=provider, video_title=video_title)
    
    if not result['success']:
        return result

    # 4. Get Channel and Category
    try:
        channel = YouTubeChannel.objects.get(id=channel_id)
        default_category = channel.default_category
    except YouTubeChannel.DoesNotExist:
        channel = None
        default_category = None
        
    # Find category by name if no default
    if not default_category and result['category_name']:
         try:
             default_category = Category.objects.get(name__iexact=result['category_name'])
         except Category.DoesNotExist:
             pass

    # 5. Create PendingArticle
    # Ensure video_id and video_title are present (DB requirements)
    final_video_title = result.get('video_title') or video_title or "Untitled YouTube Video"
    
    if not video_id:
        # Try to extract from URL
        import re
        id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', youtube_url)
        video_id = id_match.group(1) if id_match else f"ext_{int(timezone.now().timestamp())}"

    pending = PendingArticle.objects.create(
        youtube_channel=channel,
        video_url=youtube_url,
        video_id=video_id,
        video_title=final_video_title[:500],
        title=result['title'],
        content=result['content'],
        excerpt=result['summary'],
        suggested_category=default_category,
        images=result['image_paths'],  # JSON field
        featured_image=result['image_paths'][0] if result['image_paths'] else '',
        
        # Save structured data for draft safety
        specs=result['specs'],
        tags=result['tag_names'],
        
        status='pending'
    )
    
    print(f"✅ Created PendingArticle: {pending.title}")
    return {'success': True, 'pending_id': pending.id}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Auto News Generator")
    parser.add_argument("url", help="YouTube Video URL")
    args = parser.parse_args()
    
    main(args.url)
