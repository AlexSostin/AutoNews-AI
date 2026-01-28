"""
Вспомогательные утилиты для AI Engine
"""

import re
from functools import wraps
import time


def retry_on_failure(max_retries=3, delay=5, exceptions=(Exception,)):
    """
    Декоратор для автоматического повтора при сбоях.
    
    Args:
        max_retries: Максимальное количество попыток
        delay: Задержка между попытками (секунды)
        exceptions: Кортеж исключений для перехвата
    
    Пример:
        @retry_on_failure(max_retries=3, delay=10)
        def download_file(url):
            # код который может упасть
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        print(f"⚠️  Attempt {attempt + 1}/{max_retries} failed: {e}")
                        print(f"   Retrying in {delay} seconds...")
                        time.sleep(delay)
                    else:
                        print(f"❌ All {max_retries} attempts failed!")
                        raise last_exception
            
            # Shouldn't reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


def strip_html_tags(html_content):
    """Удаляет все HTML теги из текста."""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', html_content)


def calculate_reading_time(content):
    """
    Вычисляет время чтения статьи (200 слов/минута).
    
    Args:
        content: HTML контент статьи
    
    Returns:
        int: Время чтения в минутах (минимум 1)
    """
    text = strip_html_tags(content)
    word_count = len(text.split())
    reading_time = max(1, word_count // 200)
    
    return reading_time


def extract_video_id(youtube_url):
    """
    Извлекает video ID из YouTube URL.
    
    Поддерживает форматы:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    """
    patterns = [
        r'(?:v=|/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed/)([0-9A-Za-z_-]{11})',
        r'youtu\.be/([0-9A-Za-z_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    
    return None


def clean_title(title):
    """
    Очищает заголовок от HTML entities и лишних символов.
    
    Example:
        "First Drive: 2026 Tesla &amp; Model 3" 
        -> "First Drive: 2026 Tesla & Model 3"
    """
    import html
    
    # Декодируем HTML entities
    title = html.unescape(title)
    
    # Убираем лишние пробелы
    title = ' '.join(title.split())
    
    # Убираем кавычки в начале/конце
    title = title.strip('"\'')
    
    return title


def validate_article_quality(content):
    """
    Проверяет качество сгенерированной статьи.
    
    Returns:
        dict: {'valid': bool, 'issues': list of strings}
    """
    issues = []
    
    # Проверка минимальной длины
    if len(content) < 500:
        issues.append("Статья слишком короткая (< 500 символов)")
    
    # Проверка наличия заголовка
    if '<h2>' not in content:
        issues.append("Отсутствует заголовок <h2>")
    
    # Проверка структуры (должно быть несколько секций)
    section_count = content.count('<h2>')
    if section_count < 3:
        issues.append(f"Недостаточно секций (найдено {section_count}, нужно минимум 3)")
    
    # Проверка на placeholder текст
    placeholders = ['lorem ipsum', 'placeholder', 'xxx', '[insert', 'todo:', 'tbd']
    content_lower = content.lower()
    for placeholder in placeholders:
        if placeholder in content_lower:
            issues.append(f"Найден placeholder текст: {placeholder}")
    
    # Проверка на минимум параграфов
    paragraph_count = content.count('<p>')
    if paragraph_count < 4:
        issues.append(f"Мало параграфов (найдено {paragraph_count}, нужно минимум 4)")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues
    }


def format_price(price_str):
    """
    Форматирует цену в стандартный вид.
    
    Examples:
        "45000" -> "$45,000"
        "€50000" -> "€50,000"
        "1500000 RUB" -> "₽1,500,000"
    """
    import re
    
    # Извлекаем число
    numbers = re.findall(r'\d+', price_str)
    if not numbers:
        return price_str
    
    price = int(''.join(numbers))
    
    # Определяем валюту
    if '$' in price_str or 'USD' in price_str.upper():
        currency = '$'
    elif '€' in price_str or 'EUR' in price_str.upper():
        currency = '€'
    elif '₽' in price_str or 'RUB' in price_str.upper():
        currency = '₽'
    elif '£' in price_str or 'GBP' in price_str.upper():
        currency = '£'
    else:
        currency = '$'  # Default
    
    # Форматируем с разделителями
    formatted = f"{price:,}".replace(',', ' ')
    
    return f"{currency}{formatted}"


def generate_meta_keywords(title, content, max_keywords=10):
    """
    Генерирует ключевые слова из заголовка и контента.
    
    Returns:
        str: Comma-separated keywords
    """
    import re
    from collections import Counter
    
    # Объединяем title и content
    text = title + ' ' + strip_html_tags(content)
    
    # Список стоп-слов
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                  'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                  'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
                  'can', 'could', 'may', 'might', 'must', 'this', 'that', 'these', 'those'}
    
    # Извлекаем слова
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Фильтруем стоп-слова
    words = [w for w in words if w not in stop_words]
    
    # Считаем частоту
    word_freq = Counter(words)
    
    # Берем топ-N
    top_words = [word for word, count in word_freq.most_common(max_keywords)]
    
    return ', '.join(top_words)


if __name__ == "__main__":
    # Тесты
    print("Testing utils...")
    
    # Test reading time
    sample_text = "word " * 600  # 600 слов
    print(f"Reading time for 600 words: {calculate_reading_time(sample_text)} min")
    
    # Test video ID extraction
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ"
    ]
    for url in urls:
        print(f"Video ID from {url}: {extract_video_id(url)}")
    
    # Test title cleaning
    dirty_title = "First Drive: 2026 Tesla &amp; Model 3 &quot;Review&quot;"
    print(f"Clean title: {clean_title(dirty_title)}")
    
    print("✓ All tests passed!")
