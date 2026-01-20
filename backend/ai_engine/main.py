import argparse
import os
import sys
import re

# Add ai_engine directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from modules.downloader import download_audio_and_thumbnail
from modules.transcriber import transcribe_from_youtube
from modules.analyzer import analyze_transcript
from modules.article_generator import generate_article
from modules.publisher import publish_article
from modules.screenshot_maker import extract_screenshots_simple

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


def generate_article_from_youtube(youtube_url):
    """
    Generate article from YouTube URL and return article data.
    Used by Django API.
    
    УЛУЧШЕННАЯ ВЕРСИЯ с:
    - Проверкой дубликатов
    - Автоматической категоризацией
    - Автоматическими тегами
    - Сохранением характеристик авто
    - SEO оптимизацией
    """
    try:
        print(f"🚀 Генерация статьи из: {youtube_url}")
        
        # 0. Проверка дубликатов
        print("🔍 Проверка дубликатов...")
        existing = check_duplicate(youtube_url)
        if existing:
            return {
                'success': False,
                'error': f'Статья уже существует: {existing.title}',
                'article_id': existing.id,
                'duplicate': True
            }
        
        # 1. Получаем транскрипт
        print("📝 Получение транскрипта...")
        transcript = transcribe_from_youtube(youtube_url)
        
        if not transcript or len(transcript) < 50:
            raise Exception("Не удалось получить транскрипт или он слишком короткий")
        
        print(f"✓ Транскрипт получен ({len(transcript)} символов)")
        
        # 2. Анализируем транскрипт
        print("🔍 Анализ транскрипта...")
        analysis = analyze_transcript(transcript)
        
        if not analysis:
            raise Exception("Не удалось проанализировать транскрипт")
        
        print("✓ Анализ завершен")
        
        # 2.5. Определяем категорию и теги (НОВОЕ!)
        print("🏷️  Категоризация и теги...")
        from modules.analyzer import categorize_article, extract_specs_dict
        
        category_name, tag_names = categorize_article(analysis)
        print(f"✓ Категория: {category_name}")
        print(f"✓ Теги: {', '.join(tag_names) if tag_names else 'нет'}")
        
        # 2.6. Извлекаем характеристики для БД (НОВОЕ!)
        specs = extract_specs_dict(analysis)
        print(f"✓ Характеристики: {specs['make']} {specs['model']} {specs['year'] or ''}")
        
        # 3. Генерируем статью
        print("✍️  Генерация статьи с Groq AI...")
        article_html = generate_article(analysis)
        
        if not article_html or len(article_html) < 100:
            raise Exception("Статья не сгенерирована или слишком короткая")
        
        print(f"✓ Статья сгенерирована ({len(article_html)} символов)")
        
        # 4. Извлекаем заголовок
        title = extract_title(article_html)
        
        # 5. Извлекаем 3 скриншота из видео
        print("📸 Извлечение скриншотов из видео...")
        screenshot_paths = []
        try:
            # Директория для сохранения скриншотов
            screenshots_dir = os.path.join(current_dir, 'output', 'screenshots')
            os.makedirs(screenshots_dir, exist_ok=True)
            
            # Извлекаем 3 скриншота из разных моментов видео
            screenshot_paths = extract_screenshots_simple(youtube_url, screenshots_dir, num_screenshots=3)
            
            if screenshot_paths:
                print(f"✓ Извлечено {len(screenshot_paths)} скриншотов")
            else:
                print(f"⚠️  Не удалось извлечь скриншоты")
                
        except Exception as e:
            print(f"⚠️  Ошибка при извлечении скриншотов: {e}")
            screenshot_paths = []
        
        # 6. Создаем краткое описание из анализа
        summary_lines = [line for line in analysis.split('\n') if line.startswith('Summary:')]
        if summary_lines:
            summary = summary_lines[0].replace('Summary:', '').strip()[:300]
        else:
            # Извлекаем из первого параграфа статьи
            import re
            match = re.search(r'<p>(.*?)</p>', article_html, re.DOTALL)
            if match:
                summary = re.sub(r'<[^>]+>', '', match.group(1))[:300]
            else:
                summary = f"Comprehensive review of the {specs['make']} {specs['model']}"
        
        # 7. Публикуем статью с ПОЛНЫМИ метаданными и скриншотами
        print("📤 Публикация статьи...")
        article = publish_article(
            title=title,
            content=article_html,
            summary=summary,
            category_name=category_name,  # Правильная категория
            youtube_url=youtube_url,
            image_paths=screenshot_paths,  # 3 скриншота из видео
            tag_names=tag_names,  # Автоматические теги
            specs=specs  # Характеристики авто
        )
        
        print(f"✅ Статья успешно создана! ID: {article.id}, Slug: {article.slug}")
        
        return {
            'success': True,
            'article_id': article.id,
            'title': title,
            'slug': article.slug,
            'category': category_name,
            'tags': tag_names
        }
        
    except Exception as e:
        print(f"❌ Ошибка при генерации статьи: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Auto News Generator")
    parser.add_argument("url", help="YouTube Video URL")
    args = parser.parse_args()
    
    main(args.url)
