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


def _generate_article_content(youtube_url, task_id=None, provider='gemini', video_title=None):
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
        import time as _time
        _t_start = _time.time()
        _timings = {}
        
        provider_name = "Groq" if provider == 'groq' else "Google Gemini"
        send_progress(1, 5, f"🚀 Starting generation with {provider_name}...")
        print(f"🚀 Starting generation from: {youtube_url} using {provider_name}")
        
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
        _t_step = _time.time()
        send_progress(2, 20, "📝 Fetching subtitles from YouTube...")
        print("📝 Fetching transcript...")
        transcript = transcribe_from_youtube(youtube_url)
        _timings['transcript'] = round(_time.time() - _t_step, 1)
        
        if not transcript or len(transcript) < 5 or transcript.startswith("ERROR:"):
            error_msg = transcript if transcript and transcript.startswith("ERROR:") else "Failed to retrieve transcript or it is too short"
            send_progress(2, 100, f"❌ {error_msg}")
            raise Exception(error_msg)
        
        send_progress(2, 30, f"✓ Transcript received ({len(transcript)} chars)")
        
        # 2. Analyze transcript
        _t_step = _time.time()
        send_progress(3, 40, f"🔍 Analyzing transcript with {provider_name} AI...")
        print("🔍 Analyzing transcript...")
        analysis = analyze_transcript(transcript, video_title=video_title, provider=provider)
        
        if not analysis:
            send_progress(3, 100, "❌ Analysis failed")
            raise Exception("Failed to analyze transcript")
        
        _timings['analysis'] = round(_time.time() - _t_step, 1)
        send_progress(3, 50, "✓ Analysis complete")
        
        # 2.5. Categorize and Tags
        send_progress(4, 55, "🏷️ Categorizing...")
        from modules.analyzer import categorize_article, extract_specs_dict
        
        category_name, tag_names = categorize_article(analysis)
        
        # 2.6. Extract Specs
        specs = extract_specs_dict(analysis)
        send_progress(4, 60, f"✓ {specs['make']} {specs['model']}")
        
        # 2.6.1 AUTO-ADD YEAR TAG if not already present
        year = specs.get('year')
        if year:
            year_str = str(year)
            # Check if any year tag is already present
            has_year_tag = any(t.isdigit() and len(t) == 4 for t in tag_names)
            if not has_year_tag:
                tag_names.append(year_str)
                print(f"🏷️ Auto-added year tag: {year_str}")
        
        # 2.6.2 AUTO-ADD DRIVETRAIN TAG from enriched specs
        drivetrain = specs.get('drivetrain')
        if drivetrain and drivetrain not in ('Not specified', '', None):
            dt_upper = drivetrain.upper()
            has_dt_tag = any(t.upper() in ('AWD', 'FWD', 'RWD', '4WD') for t in tag_names)
            if not has_dt_tag and dt_upper in ('AWD', 'FWD', 'RWD', '4WD'):
                tag_names.append(dt_upper)
                print(f"🏷️ Auto-added drivetrain tag: {dt_upper}")
        
        # 2.6.3 AUTO-ADD MODEL TAG from DB if not already present
        try:
            from news.models import Tag
            model_name = specs.get('model')
            make_name = specs.get('make')
            if model_name and model_name != 'Not specified':
                # Check if any Models-group tag matches
                has_model_tag = False
                model_tags = Tag.objects.filter(group__name='Models').values_list('name', flat=True)
                tag_names_lower = [t.lower() for t in tag_names]
                for mt in model_tags:
                    if mt.lower() in tag_names_lower:
                        has_model_tag = True
                        break
                if not has_model_tag:
                    # Try to find a matching Model tag in DB
                    for mt in model_tags:
                        if model_name.lower() in mt.lower() or mt.lower() in model_name.lower():
                            tag_names.append(mt)
                            print(f"🏷️ Auto-added model tag: {mt}")
                            break
        except Exception as e:
            print(f"⚠️ Model tag auto-add failed: {e}")
        
        # 2.65. DUPLICATE CHECK — skip if article already exists for same car
        if specs.get('make') and specs['make'] != 'Not specified' and specs.get('model') and specs['model'] != 'Not specified':
            try:
                from news.models import CarSpecification, PendingArticle as PA
                
                # Check published articles
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
                        return {'success': False, 'status': 'skipped', 'reason': 'duplicate',
                                'existing_article_id': existing_article.id, 'error': msg}
                else:
                    # No trim info — check if any article exists for this make+model
                    if existing.exists():
                        existing_article = existing.first().article
                        msg = (f"⚠️ Duplicate detected: {specs['make']} {specs['model']} "
                               f"already exists (Article #{existing_article.id}: \"{existing_article.title}\")")
                        print(msg)
                        send_progress(4, 100, f"⚠️ Skipped — duplicate of article #{existing_article.id}")
                        return {'success': False, 'status': 'skipped', 'reason': 'duplicate',
                                'existing_article_id': existing_article.id, 'error': msg}
                
                # Also check PendingArticle for same car (not yet published)
                pending_same_car = PA.objects.filter(
                    status='pending',
                    title__icontains=specs['model'],
                )
                if specs.get('make'):
                    pending_same_car = pending_same_car.filter(title__icontains=specs['make'])
                if pending_same_car.exists():
                    pending_art = pending_same_car.first()
                    msg = (f"⚠️ Duplicate detected: {specs['make']} {specs['model']} "
                           f"already pending (PendingArticle #{pending_art.id}: \"{pending_art.title}\")")
                    print(msg)
                    send_progress(4, 100, f"⚠️ Skipped — same car already pending #{pending_art.id}")
                    return {'success': False, 'status': 'skipped', 'reason': 'duplicate_pending',
                            'existing_pending_id': pending_art.id, 'error': msg}
                            
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
        
        # 2.9 POST-ENRICHMENT: auto-add drivetrain tag if enricher found it
        drivetrain = specs.get('drivetrain')
        if drivetrain and drivetrain not in ('Not specified', '', None):
            dt_upper = drivetrain.upper()
            has_dt_tag = any(t.upper() in ('AWD', 'FWD', 'RWD', '4WD') for t in tag_names)
            if not has_dt_tag and dt_upper in ('AWD', 'FWD', 'RWD', '4WD'):
                tag_names.append(dt_upper)
                print(f"🏷️ Auto-added drivetrain tag (post-enrichment): {dt_upper}")
        
        # 2.10 AUTO-ADD SEGMENT TAG based on price
        try:
            from modules.analyzer import extract_price_usd
            price_usd = extract_price_usd(analysis)
            if price_usd and price_usd > 0:
                # Check if any price-based segment already assigned
                price_segments = {'Budget', 'Premium', 'Luxury'}
                has_price_segment = any(t in price_segments for t in tag_names)
                if not has_price_segment:
                    if price_usd < 25000:
                        tag_names.append('Budget')
                        print(f"🏷️ Auto-added segment: Budget (${price_usd:,.0f})")
                    elif 50000 <= price_usd < 80000:
                        tag_names.append('Premium')
                        print(f"🏷️ Auto-added segment: Premium (${price_usd:,.0f})")
                    elif price_usd >= 80000:
                        tag_names.append('Luxury')
                        print(f"🏷️ Auto-added segment: Luxury (${price_usd:,.0f})")
        except Exception as e:
            print(f"⚠️ Price segment auto-add failed: {e}")
        
        # 3. Generate Article
        _t_step = _time.time()
        send_progress(5, 65, f"✍️ Generating article with {provider_name}...")
        print(f"✍️  Generating article...")
        
        # Pass web context to generator
        article_html = generate_article(analysis, provider=provider, web_context=web_context)
        
        if not article_html or len(article_html) < 100:
            send_progress(5, 100, "❌ Article generation failed")
            raise Exception("Article content is empty or too short")
        
        # Stamp the article with AI provider info (hidden from readers, visible in admin)
        from datetime import datetime
        gen_stamp = f"<!-- Generated by: {provider_name} | {datetime.now().strftime('%Y-%m-%d %H:%M')} -->"
        article_html = article_html.strip() + f"\n\n{gen_stamp}\n"
        
        _timings['generation'] = round(_time.time() - _t_step, 1)
        send_progress(5, 75, "✓ Article generated")
        
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
        _t_step = _time.time()
        send_progress(6, 80, "📸 Extracting screenshots...")
        print("📸 Extracting screenshots...")
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
                        
                send_progress(6, 85, f"✓ Extracted and uploaded {len(screenshot_paths)} screenshots")
            else:
                send_progress(6, 85, "⚠️ No screenshots found")
        except Exception as e:
            print(f"⚠️  Ошибка при извлечении/загрузке скриншотов: {e}")
            screenshot_paths = []
        
        # 6. Создаем краткое описание
        _timings['screenshots'] = round(_time.time() - _t_step, 1)
        send_progress(7, 90, "📝 Creating description...")
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
        
        # 7. AI Editor — second pass quality check
        _t_step = _time.time()
        send_progress(8, 92, "🧠 AI Editor: quality check...")
        content_original = article_html  # Save original before review
        ai_editor_diff = None
        try:
            from modules.article_reviewer import review_article
            article_html = review_article(article_html, specs, provider)
            if article_html != content_original:
                send_progress(8, 95, "✅ AI Editor: article improved")
                ai_editor_diff = {
                    'changed': True,
                    'original_chars': len(content_original),
                    'reviewed_chars': len(article_html),
                    'diff_chars': len(article_html) - len(content_original),
                }
            else:
                send_progress(8, 95, "✅ AI Editor: no changes needed")
                ai_editor_diff = {'changed': False}
        except Exception as e:
            print(f"⚠️ AI Editor failed, using original: {e}")
            send_progress(8, 95, "⚠️ AI Editor: skipped")
            ai_editor_diff = {'changed': False, 'error': str(e)}
        _timings['ai_editor'] = round(_time.time() - _t_step, 1)
        
        # Build generation metadata
        _timings['total'] = round(_time.time() - _t_start, 1)
        generation_metadata = {
            'provider': provider,
            'timings': _timings,
            'ai_editor': ai_editor_diff,
        }
        print(f"📊 Generation timing: {_timings}")
        
        return {
            'success': True,
            'title': title,
            'content': article_html,
            'content_original': content_original,
            'summary': summary,
            'category_name': category_name,
            'tag_names': tag_names,
            'specs': specs,
            'meta_keywords': seo_keywords,
            'image_paths': screenshot_paths,
            'analysis': analysis,
            'web_context': web_context,
            'video_title': video_title,
            'author_name': author_name,
            'author_channel_url': author_channel_url,
            'generation_metadata': generation_metadata
        }
        
    except Exception as e:
        print(f"❌ Error in _generate_article_content: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }

def generate_title_variants(article, provider='gemini'):
    """Generate A/B title variants for an article using AI.
    Creates 3 variants: A (original), B and C (AI-generated alternatives).
    Returns the created variants or empty list on failure."""
    try:
        from news.models import ArticleTitleVariant
        
        # Skip if variants already exist
        if ArticleTitleVariant.objects.filter(article=article).exists():
            print(f"📊 A/B variants already exist for article #{article.id}")
            return []
        
        # Generate alternatives using AI
        from modules.ai_provider import get_ai_provider
        ai = get_ai_provider(provider)
        
        prompt = f"""You are an SEO expert and headline writer for an automotive news website.

Given this article title: "{article.title}"

Generate exactly 2 alternative headline variants that:
- Are roughly the same length (±20%)
- Highlight different angles or benefits (performance, price, tech, etc.)
- Are engaging, click-worthy, but NOT clickbait
- Maintain factual accuracy
- Include the car make/model name

Reply with ONLY the two alternative titles, one per line. No numbering, no explanations, no quotes."""

        result = ai.generate_completion(prompt, temperature=0.9, max_tokens=200)
        
        lines = [l.strip().strip('"').strip("'") for l in result.strip().split('\n') if l.strip()]
        # Filter out lines that look like numbering or explanations
        lines = [l for l in lines if len(l) > 10 and not l.startswith(('1.', '2.', '-', '*', '#'))]
        # Remove leading numbers like "1) " or "2) "
        import re
        lines = [re.sub(r'^\d+[\)\.]\s*', '', l) for l in lines]
        
        alt_titles = lines[:2]  # Max 2 alternatives
        
        if not alt_titles:
            print(f"⚠️ AI returned no valid title alternatives")
            return []
        
        # Create variant A (original)
        variants = []
        variants.append(ArticleTitleVariant.objects.create(
            article=article,
            variant='A',
            title=article.title
        ))
        
        # Create variant B
        if len(alt_titles) >= 1:
            variants.append(ArticleTitleVariant.objects.create(
                article=article,
                variant='B',
                title=alt_titles[0][:500]
            ))
        
        # Create variant C
        if len(alt_titles) >= 2:
            variants.append(ArticleTitleVariant.objects.create(
                article=article,
                variant='C',
                title=alt_titles[1][:500]
            ))
        
        print(f"📊 Created {len(variants)} A/B title variants:")
        for v in variants:
            print(f"   [{v.variant}] {v.title}")
        
        return variants
        
    except Exception as e:
        print(f"⚠️ A/B title variant generation failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def generate_article_from_youtube(youtube_url, task_id=None, provider='gemini', is_published=True):
    """Generate and publish immediately (LEGACY/MANUAL flow)"""
    
    # 0. Check duplicate first
    existing = check_duplicate(youtube_url)
    if existing:
        return {
            'success': False,
            'error': f'Article already exists: {existing.title}',
            'article_id': existing.id,
            'duplicate': True
        }
        
    result = _generate_article_content(youtube_url, task_id, provider)
    
    if not result['success']:
        return result
        
    # Publish to DB
    print(f"📤 Publishing article... (Published: {is_published})")
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
        author_channel_url=result.get('author_channel_url', ''),
        generation_metadata=result.get('generation_metadata')
    )
    
    print(f"✅ Article created! ID: {article.id}, Slug: {article.slug}")
    
    # Generate A/B title variants
    generate_title_variants(article, provider=provider)
    
    # Deep specs enrichment — auto-fill VehicleSpecs card (/cars/{brand}/{model})
    try:
        from ai_engine.modules.deep_specs import generate_deep_vehicle_specs
        generate_deep_vehicle_specs(
            article,
            specs=result.get('specs'),
            web_context=result.get('web_context', ''),
            provider=provider
        )
    except Exception as e:
        print(f"⚠️ Deep specs enrichment failed: {e}")
    
    return {
        'success': True,
        'article_id': article.id,
        'title': result['title'],
        'slug': article.slug,
        'category': result['category_name'],
        'tags': result['tag_names']
    }


def create_pending_article(youtube_url, channel_id, video_title, video_id, provider='gemini'):
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
