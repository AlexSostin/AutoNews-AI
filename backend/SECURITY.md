# Security Recommendations 🔒

## ⚠️ Критические проблемы (исправить перед продакшеном)

### 1. SECRET_KEY
**Проблема:** SECRET_KEY открыт в коде
**Решение:**
```bash
# Создайте .env файл
echo "SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')" > .env
```

В `settings.py`:
```python
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-me')
```

### 2. DEBUG Mode
**Проблема:** DEBUG = True раскрывает traceback и внутреннюю структуру
**Решение:**
```python
DEBUG = os.getenv('DEBUG', 'False') == 'True'
```

### 3. ALLOWED_HOSTS
**Проблема:** ALLOWED_HOSTS = [] разрешает любые хосты
**Решение:**
```python
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
```

### 4. База данных
**Проблема:** SQLite не подходит для production
**Решение:** Используйте PostgreSQL:
```bash
pip install psycopg2-binary
```

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}
```

### 5. CORS настройки
**Проблема:** Жестко закодированные origins
**Решение:**
```python
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
```

## ✅ Что уже настроено правильно

- ✅ CORS middleware установлен
- ✅ CSRF protection включен
- ✅ X-Frame-Options защита включена
- ✅ JWT authentication настроен
- ✅ IsAuthenticatedOrReadOnly по умолчанию
- ✅ Использование ORM (защита от SQL injection)

## 🟡 Рекомендации для улучшения

### 1. Установите дополнительные заголовки безопасности
```python
# Защита от MIME-sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True

# HTTPS
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### 2. Rate Limiting
Установите django-ratelimit для защиты от брутфорса:
```bash
pip install django-ratelimit
```

### 3. Обновите зависимости
```bash
pip install --upgrade django djangorestframework
pip list --outdated
```

### 4. Логирование
Настройте логирование подозрительных действий:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs/security.log',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
```

### 5. Ограничение размера загружаемых файлов
```python
# settings.py
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
```

### 6. API Rate Limiting
В `api_views.py` добавьте:
```python
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
```

### 7. Валидация YouTube URL
В `api_views.py` добавьте валидацию:
```python
import re

def is_valid_youtube_url(url):
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
    return re.match(youtube_regex, url) is not None
```

### 8. Санитизация HTML контента
Если разрешаете пользователям создавать контент:
```bash
pip install bleach
```

```python
import bleach

def sanitize_html(html_content):
    allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'h2', 'h3', 'ul', 'ol', 'li', 'a']
    allowed_attrs = {'a': ['href', 'title']}
    return bleach.clean(html_content, tags=allowed_tags, attributes=allowed_attrs)
```

## 📋 Чеклист перед продакшеном

- [ ] SECRET_KEY в переменных окружения
- [ ] DEBUG = False
- [ ] ALLOWED_HOSTS настроен
- [ ] PostgreSQL вместо SQLite
- [ ] HTTPS настроен
- [ ] Secure cookies включены
- [ ] Rate limiting настроен
- [ ] Логирование настроено
- [ ] Backup базы данных настроен
- [ ] Мониторинг ошибок (Sentry)
- [ ] Firewall настроен
- [ ] Обновлены все зависимости
- [ ] Регулярные security аудиты

## 🔐 Дополнительно

### Создайте .env.example
```env
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_NAME=autonews_db
DB_USER=autonews_user
DB_PASSWORD=strong-password-here
DB_HOST=localhost
DB_PORT=5432
CORS_ORIGINS=https://yourdomain.com
```

### Добавьте в .gitignore
```
.env
*.pyc
__pycache__/
db.sqlite3
media/
staticfiles/
*.log
```
