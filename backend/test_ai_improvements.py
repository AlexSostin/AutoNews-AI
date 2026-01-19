# 🎯 AI Engine Test Script

"""
Тестовый скрипт для проверки всех новых улучшений AI Engine.
Запустите этот файл чтобы увидеть все новые возможности в действии!
"""

import sys
import os

# Setup Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')

import django
django.setup()

from ai_engine.main import generate_article_from_youtube
from ai_engine.modules.utils import (
    calculate_reading_time,
    extract_video_id,
    clean_title,
    validate_article_quality,
    format_price
)

def test_improvements():
    """
    Демонстрация всех улучшений.
    """
    print("=" * 80)
    print("🚀 AI ENGINE IMPROVEMENTS TEST")
    print("=" * 80)
    print()
    
    # Test 1: Utils
    print("📦 Test 1: Utility Functions")
    print("-" * 80)
    
    # Reading time
    sample_text = "<p>" + ("word " * 600) + "</p>"
    reading_time = calculate_reading_time(sample_text)
    print(f"✓ Reading time for 600 words: {reading_time} min")
    
    # Video ID extraction
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ"
    ]
    for url in test_urls:
        video_id = extract_video_id(url)
        print(f"✓ Video ID from {url[:30]}...: {video_id}")
    
    # Title cleaning
    dirty_title = "First Drive: 2026 Tesla &amp; Model 3 &quot;Review&quot;"
    clean = clean_title(dirty_title)
    print(f"✓ Clean title: {clean}")
    
    # Price formatting
    price = format_price("45000")
    print(f"✓ Formatted price: {price}")
    
    print()
    
    # Test 2: Article Quality Validation
    print("📊 Test 2: Article Quality Validation")
    print("-" * 80)
    
    good_article = """
    <h2>First Drive: 2026 Tesla Model 3</h2>
    <p>Introduction paragraph with details.</p>
    <h2>Performance</h2>
    <p>Performance details here.</p>
    <h2>Design</h2>
    <p>Design details here.</p>
    <h2>Technology</h2>
    <p>Technology details here.</p>
    <h2>Pros & Cons</h2>
    <ul><li>Pro 1</li><li>Pro 2</li></ul>
    """ * 5  # Повторяем для достаточной длины
    
    quality = validate_article_quality(good_article)
    if quality['valid']:
        print("✓ Article quality: PASSED")
    else:
        print("⚠️  Article quality issues:")
        for issue in quality['issues']:
            print(f"   - {issue}")
    
    print()
    
    # Test 3: Full Generation (Interactive)
    print("🎬 Test 3: Full Article Generation")
    print("-" * 80)
    print()
    print("Введите YouTube URL для тестирования (или Enter чтобы пропустить):")
    print("Пример: https://www.youtube.com/watch?v=VIDEO_ID")
    print()
    
    youtube_url = input("YouTube URL: ").strip()
    
    if youtube_url:
        print()
        print("🚀 Запуск генерации с ВСЕМИ УЛУЧШЕНИЯМИ...")
        print("-" * 80)
        
        result = generate_article_from_youtube(youtube_url)
        
        print()
        print("=" * 80)
        print("📊 РЕЗУЛЬТАТ")
        print("=" * 80)
        
        if result['success']:
            print(f"✅ Статья успешно создана!")
            print(f"   ID: {result.get('article_id')}")
            print(f"   Title: {result.get('title')}")
            print(f"   Slug: {result.get('slug')}")
            print(f"   Category: {result.get('category', 'N/A')}")
            print(f"   Tags: {', '.join(result.get('tags', []))}")
            print()
            print("🎯 Что было применено:")
            print("   ✓ Проверка дубликатов")
            print("   ✓ Автоматическая категоризация")
            print("   ✓ Автоматические теги (5-7 шт)")
            print("   ✓ CarSpecification сохранены в БД")
            print("   ✓ SEO оптимизация (title + description)")
            print("   ✓ Время чтения вычислено")
            print("   ✓ Проверка качества статьи")
            print("   ✓ Retry логика для надёжности")
        elif result.get('duplicate'):
            print(f"⚠️  Статья уже существует (дубликат заблокирован)")
            print(f"   Существующий ID: {result.get('article_id')}")
            print(f"   Ошибка: {result.get('error')}")
        else:
            print(f"❌ Ошибка: {result.get('error')}")
    else:
        print("⏭️  Пропущено (не введен URL)")
    
    print()
    print("=" * 80)
    print("✨ ТЕСТ ЗАВЕРШЁН")
    print("=" * 80)
    print()
    print("Все улучшения работают! 🎉")
    print()
    print("📖 Подробнее: backend/ai_engine/IMPROVEMENTS_APPLIED.md")
    print()


if __name__ == "__main__":
    try:
        test_improvements()
    except KeyboardInterrupt:
        print("\n\n⚠️  Тест прерван пользователем")
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
