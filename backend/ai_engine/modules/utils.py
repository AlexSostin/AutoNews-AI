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


# YouTube noise phrases to strip from video titles before AI sees them
_YOUTUBE_NOISE_PATTERNS = [
    # Common YouTube video type suffixes (case-insensitive)
    r'\bwalk[\s-]*around\b',
    r'\bwalkaround\b',
    r'\bfirst\s+look\b',
    r'\bfirst\s+drive\b',
    r'\btest\s+drive\b',
    r'\bhands[\s-]?on\b',
    r'\bfull\s+review\b',
    r'\breview\b',
    r'\bpov\s+drive\b',
    r'\bpov\b',
    r'\bexterior\s+(?:and|&)\s+interior\b',
    r'\bexterior\s+interior\b',
    r'\b(?:4k|uhd|hdr|60fps)\b',
    r'\bin\s+\d+\s*k\b',      # "in 4k"
    r'\bunboxing\b',
    r'\bfull\s+tour\b',
    r'\bdetailed\s+tour\b',
    r'\bcomplete\s+guide\b',
]

_YOUTUBE_NOISE_RE = re.compile(
    '|'.join(_YOUTUBE_NOISE_PATTERNS),
    re.IGNORECASE
)


def clean_video_title(title):
    """
    Strip YouTube-specific noise from video titles before passing to AI.
    
    Example:
        "2026 BYD SONG DM i walk around" -> "2026 BYD SONG DM i"
        "Tesla Model 3 First Look POV 4K" -> "Tesla Model 3"
    """
    if not title:
        return title
    
    cleaned = _YOUTUBE_NOISE_RE.sub('', title)
    
    # Clean up leftover separators, dangling '&'/'and', and whitespace
    cleaned = re.sub(r'\s*[&]\s*$', '', cleaned)  # trailing &
    cleaned = re.sub(r'\s+and\s*$', '', cleaned, flags=re.IGNORECASE)  # trailing "and"
    cleaned = re.sub(r'\s*[:\-|–—]\s*$', '', cleaned)  # trailing separators
    cleaned = re.sub(r'^\s*[:\-|–—]\s*', '', cleaned)  # leading separators
    cleaned = re.sub(r'\s*[:\-|–—]\s*[:\-|–—]\s*', ' — ', cleaned)  # double separators
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
    
    if cleaned != title.strip():
        print(f"🧹 Title cleaned: \"{title.strip()}\" → \"{cleaned}\"")
    
    return cleaned or title  # fallback to original if everything was stripped


def validate_article_quality(content):
    """
    Validate quality of AI-generated article content.
    
    Returns:
        dict: {'valid': bool, 'issues': list of strings}
    """
    issues = []
    
    # Minimum length check
    if len(content) < 500:
        issues.append("Article too short (< 500 characters)")
    
    # Must have heading
    if '<h2>' not in content:
        issues.append("Missing <h2> heading")
    
    # Must have enough sections
    section_count = content.count('<h2>')
    if section_count < 3:
        issues.append(f"Too few sections (found {section_count}, need at least 3)")
    
    # Check for placeholder text
    placeholders = ['lorem ipsum', 'placeholder', 'xxx', '[insert', 'todo:', 'tbd']
    content_lower = content.lower()
    for placeholder in placeholders:
        if placeholder in content_lower:
            issues.append(f"Found placeholder text: {placeholder}")
    
    # Minimum paragraphs
    paragraph_count = content.count('<p>')
    if paragraph_count < 4:
        issues.append(f"Too few paragraphs (found {paragraph_count}, need at least 4)")
    
    # TRUNCATION CHECK: if content doesn't end with a closing tag, it was cut off
    stripped = content.strip()
    if stripped and not stripped.endswith('>'):
        issues.append("Content appears truncated (no closing HTML tag at end)")
    
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


def clean_html_markup(html_content):
    """
    Очищает и валидирует HTML-разметку с помощью BeautifulSoup4.
    - Автоматически закрывает незакрытые теги (например, <p>)
    - Удаляет артефакты markdown (```html и т.д.)
    - Убирает лишние пустые теги
    """
    from bs4 import BeautifulSoup
    import re
    
    # Сначала удаляем markdown артефакты, если они остались
    cleaned = re.sub(r'```[a-z]*\n?', '', html_content)
    cleaned = cleaned.replace('```', '')
    
    # Парсим через bs4
    soup = BeautifulSoup(cleaned, 'html.parser')
    
    # Удаляем пустые теги
    for tag in soup.find_all(['p', 'h2', 'h3', 'ul', 'li']):
        if not tag.contents or (tag.string and not tag.string.strip()):
            tag.decompose()
            
    # Возвращаем форматированный HTML без <html>, <head>, <body>
    # Если bs4 обернул все в <html><body>, извлекаем только содержимое body
    if soup.body:
        return ''.join(str(tag) for tag in soup.body.children).strip()
    return str(soup).strip()

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
