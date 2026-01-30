import argparse
import os
import sys
import re
import requests

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

def extract_title(html_content):
    match = re.search(r'<h2>(.*?)</h2>', html_content)
    if match:
        return match.group(1)
    return "New Car Review" 

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
        
        # 0. Получаем заголовок видео, если его нет
        if not video_title:
             try:
                 # Quick fetch using requests (avoid full client init if possible, or use client)
                 # Better to use YouTubeClient properly
                 from modules.youtube_client import YouTubeClient
                 yt = YouTubeClient()
                 # Simple request to get title via oEmbed or scrap (oEmbed is reliable and free)
                 oembed_url = f"https://www.youtube.com/oembed?url={youtube_url}&format=json"
                 resp = requests.get(oembed_url, timeout=5)
                 if resp.status_code == 200:
                     video_title = resp.json().get('title')
                     print(f"🎥 Fetched Video Title: {video_title}")
             except Exception as e:
                 print(f"⚠️ Could not fetch video title: {e}")

        # 1. Получаем транскрипт
        send_progress(2, 20, "📝 Получение субтитров с YouTube...")
        print("📝 Получение транскрипта...")
        transcript = transcribe_from_youtube(youtube_url)
        
        if not transcript or len(transcript) < 5:
            send_progress(2, 100, "❌ Failed to retrieve transcript")
            raise Exception("Failed to retrieve transcript or it is too short")
        
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
        
        # 3. Generate Article
        send_progress(5, 65, f"✍️ Generating article with {provider_name}...")
        print(f"✍️  Generating article...")
        
        # Pass web context to generator
        article_html = generate_article(analysis, provider=provider, web_context=web_context)
        
        if not article_html or len(article_html) < 100:
            send_progress(5, 100, "❌ Article generation failed")
            raise Exception("Article content is empty or too short")
        
        send_progress(5, 75, "✓ Статья сгенерирована")
        
        # 4. Определяем заголовок (Title)
        title = "New Car Review"
        
        # Priority 1: SEO Title from Analysis
        if specs.get('seo_title') and len(specs['seo_title']) > 5:
            title = specs['seo_title'].replace('"', '').replace("'", "")
            print(f"📌 Using SEO Title form Analysis: {title}")
            
        # Priority 2: Construct from Specs (if Make/Model exist)
        elif specs.get('make') and specs.get('model') and specs['make'] != 'Not specified':
            year = specs.get('year', '')
            year_str = f"{year} " if year else ""
            title = f"{year_str}{specs['make']} {specs['model']} Review"
            print(f"📌 Constructed Title from Specs: {title}")
            
        # Priority 3: Extract from HTML <h2>
        else:
            extracted = extract_title(article_html)
            if extracted and len(extracted) > 5:
                title = extracted
                print(f"📌 Extracted Title from HTML: {title}")
        
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
        summary_lines = [line for line in analysis.split('\n') if line.startswith('Summary:')]
        if summary_lines:
            summary = summary_lines[0].replace('Summary:', '').strip()[:300]
        else:
            import re
            match = re.search(r'<p>(.*?)</p>', article_html, re.DOTALL)
            if match:
                summary = re.sub(r'<[^>]+>', '', match.group(1))[:300]
            else:
                summary = f"Comprehensive review of the {specs['make']} {specs['model']}"
        
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
            'analysis': analysis
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
        meta_keywords=result['meta_keywords']
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
    
    # 1. Check if article exists
    existing = Article.objects.filter(youtube_url=youtube_url).exists()
    if existing:
        print(f"Skipping {youtube_url} - already exists")
        return {'success': False, 'reason': 'exists', 'error': 'Article already exists in the database'}
        
    # 2. Check if already pending
    if PendingArticle.objects.filter(video_id=video_id).exists():
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
    pending = PendingArticle.objects.create(
        youtube_channel=channel,
        video_url=youtube_url,
        video_id=video_id,
        video_title=video_title,
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
