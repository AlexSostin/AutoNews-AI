# 🔐 Анализ безопасности проекта AutoNews

**Дата анализа**: 21 января 2026  
**Окружение**: Railway.app (Production)  
**Статус**: ⚠️ Требуются улучшения

---

## 📊 Общая оценка безопасности

| Категория | Оценка | Статус |
|-----------|--------|--------|
| Аутентификация | 8/10 | ✅ Хорошо |
| Авторизация | 7/10 | ⚠️ Требует внимания |
| CORS & HTTPS | 9/10 | ✅ Отлично |
| Секреты | 8/10 | ✅ Хорошо |
| Rate Limiting | 6/10 | ⚠️ Недостаточно |
| Input Validation | 7/10 | ⚠️ Требует внимания |
| Логирование | 5/10 | ❌ Критично |
| Инфраструктура | 8/10 | ✅ Хорошо |

**Итоговая оценка: 7.3/10** ⚠️

---

## ✅ Что хорошо реализовано

### 1. HTTPS & Secure Headers
```python
# settings.py - ОТЛИЧНО
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 год
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```
✅ Все критичные заголовки настроены правильно

### 2. JWT Authentication
```python
# JWT токены с expiration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ]
}
```
✅ Используется безопасная JWT-аутентификация

### 3. CORS Configuration
```python
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Только в dev режиме
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ORIGINS', '...').split(',')
CORS_ALLOW_CREDENTIALS = True
```
✅ CORS настроен правильно, whitelist доменов

### 4. Environment Variables
- ✅ SECRET_KEY не хардкоден
- ✅ DEBUG = False в продакшене
- ✅ Пароли БД в переменных окружения
- ✅ .env в .gitignore

### 5. Rate Limiting (частично)
```python
@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
def generate_from_youtube(self, request):
    ...
```
✅ Rate limiting на критичных эндпоинтах

---

## ❌ Критические проблемы

### 🔴 1. DEBUG Принты в Production коде
**Файл**: `backend/news/api_views.py` (строки 223-283)

```python
# ❌ ОПАСНО - логи в production
print(f"DEBUG: Received rating_value: {rating_value}")
print(f"DEBUG: Request data: {request.data}")
print(f"DEBUG: IP address: {ip_address}")
print(f"DEBUG: Fingerprint: {fingerprint}")
```

**Риски**:
- Утечка чувствительных данных в логи
- Логи могут содержать IP адреса, fingerprints, user data
- Violation GDPR/Privacy regulations

**Исправление**:
```python
# ✅ ПРАВИЛЬНО
import logging
logger = logging.getLogger(__name__)

if settings.DEBUG:
    logger.debug(f"Received rating_value: {rating_value}")
```

---

### 🟠 2. Отсутствует Rate Limiting на критичных эндпоинтах

**Уязвимые эндпоинты**:
- `/api/v1/token/` - login (нет защиты от brute-force)
- `/api/v1/users/register/` - регистрация (возможен spam)
- `/api/v1/articles/` - GET запросы (DDoS)
- `/api/v1/comments/` - создание комментариев (spam)

**Текущее состояние**:
```python
# ❌ НЕТ rate limiting на логине
path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
```

**Исправление**:
```python
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit

# ✅ Добавить rate limiting
@ratelimit(key='ip', rate='5/15m', method='POST', block=True)
class RateLimitedTokenObtainPairView(TokenObtainPairView):
    pass

urlpatterns = [
    path('token/', RateLimitedTokenObtainPairView.as_view()),
]
```

---

### 🟠 3. Недостаточная валидация YouTube URL

**Файл**: `backend/news/api_views.py:40`

```python
def is_valid_youtube_url(url):
    youtube_regex = r'^(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/...'
    return bool(re.match(youtube_regex, url))
```

**Проблемы**:
- Нет проверки длины URL
- Нет защиты от редиректов
- Нет валидации video ID

**Исправление**:
```python
def is_valid_youtube_url(url):
    if not url or len(url) > 200:  # ✅ Проверка длины
        return False
    if not isinstance(url, str):
        return False
    # Разрешены только youtube.com и youtu.be
    if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
        return False
    youtube_regex = r'^https://(www\.)?(youtube\.com|youtu\.be)/.*$'
    return bool(re.match(youtube_regex, url))
```

---

### 🟠 4. Middleware проверяет auth без timeout fallback

**Файл**: `frontend-next/middleware.ts:33`

```typescript
// ⚠️ Если backend недоступен - middleware зависает
const response = await fetch(`${apiUrl}/users/me/`, {
    signal: AbortSignal.timeout(5000),  // ✅ Timeout есть, но нет fallback
});
```

**Проблема**:
```typescript
} catch (error) {
    console.error('[Middleware] Auth check failed:', error);
    // ❌ НЕ редиректим - это может дать доступ без авторизации!
}
```

**Исправление**:
```typescript
} catch (error) {
    console.error('[Middleware] Auth check failed:', error);
    // ✅ При ошибке - безопасный редирект
    const response = NextResponse.redirect(new URL('/login', request.url));
    response.cookies.delete('access_token');
    response.cookies.delete('refresh_token');
    return response;
}
```

---

### 🟡 5. Отсутствие Content Security Policy (CSP)

**Текущее состояние**: CSP не настроен

**Риски**:
- XSS атаки
- Загрузка скриптов с недоверенных источников
- Clickjacking (частично защищено через X_FRAME_OPTIONS)

**Исправление** (добавить в settings.py):
```python
SECURE_CONTENT_SECURITY_POLICY = {
    'default-src': ["'self'"],
    'script-src': ["'self'", "'unsafe-inline'", 'https://cdn.jsdelivr.net'],
    'style-src': ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com'],
    'img-src': ["'self'", 'data:', 'https:'],
    'font-src': ["'self'", 'https://fonts.gstatic.com'],
    'connect-src': ["'self'", 'https://heroic-healing-production-2365.up.railway.app'],
    'frame-ancestors': ["'none'"],
}
```

---

### 🟡 6. Слабая защита от CSRF на API

**Текущее состояние**:
```python
# settings.py
'django.middleware.csrf.CsrfViewMiddleware',  # Включен
```

**Проблема**: JWT API не требует CSRF токенов, но:
```python
# ⚠️ Есть IsStaffOrReadOnly без проверки происхождения запроса
class ArticleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrReadOnly]
```

**Рекомендация**:
- Для API с JWT - CSRF токены не обязательны ✅
- Но нужно проверять Referer/Origin headers для чувствительных операций

---

### 🟡 7. Пароль в entrypoint.sh читается из env без валидации

**Файл**: `backend/entrypoint.sh:15`

```bash
password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin')  # ❌ Дефолтный 'admin'
```

**Проблема**:
- Если не задан DJANGO_SUPERUSER_PASSWORD → пароль = 'admin'
- Слабый пароль в production

**Исправление**:
```python
password = os.getenv('DJANGO_SUPERUSER_PASSWORD')
if not password or len(password) < 12:
    raise ValueError("DJANGO_SUPERUSER_PASSWORD must be set and >= 12 chars")
```

---

### 🟡 8. Отсутствует логирование попыток входа

**Текущее состояние**: Нет логов для:
- Неудачных попыток входа
- Создания пользователей
- Изменения прав доступа
- Удаления критичных данных

**Исправление**:
```python
# Добавить в settings.py
LOGGING = {
    'handlers': {
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 30,  # 30 дней
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
```

---

## 🔧 Рекомендации по приоритетам

### Немедленно (P0 - Критично):
1. ❌ **Удалить все `print()` из production кода** → заменить на `logging`
2. ❌ **Добавить rate limiting на `/api/v1/token/`** (brute-force защита)
3. ❌ **Исправить middleware fallback** - редирект при ошибке auth
4. ❌ **Установить надежный DJANGO_SUPERUSER_PASSWORD** (мин 16+ символов)

### В ближайшее время (P1 - Высокий):
5. ⚠️ **Добавить rate limiting на регистрацию** (`/users/register/`)
6. ⚠️ **Настроить security logging** (логи попыток входа)
7. ⚠️ **Добавить CSP headers**
8. ⚠️ **Улучшить валидацию YouTube URL**

### Желательно (P2 - Средний):
9. 📝 **Добавить rate limiting на GET запросы** (защита от scraping)
10. 📝 **Настроить WAF на Railway** (если доступно)
11. 📝 **Добавить 2FA для админов**
12. 📝 **Регулярные security audits** (dependency check)

---

## 🛡️ Дополнительные меры безопасности

### 1. Database Security
```python
# ✅ УЖЕ ЕСТЬ
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'sslmode': 'require',  # ✅ SSL для БД
        }
    }
}
```

### 2. Dependency Scanning
```bash
# Регулярно проверять уязвимости
pip install safety
safety check --json

# Или использовать GitHub Dependabot
```

### 3. Secrets Rotation
- 🔄 Ротация SECRET_KEY каждые 90 дней
- 🔄 Ротация DJANGO_SUPERUSER_PASSWORD каждые 90 дней
- 🔄 Ротация JWT secrets каждые 6 месяцев

### 4. Backup & Recovery
```bash
# Настроить автоматические бэкапы БД в Railway
# Retention: минимум 7 дней
```

### 5. Monitoring & Alerts
```python
# ✅ УЖЕ НАСТРОЕНО
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
# Sentry будет отлавливать ошибки
```

---

## 📋 Чеклист перед production

- [x] SECRET_KEY уникальный и сложный
- [x] DEBUG = False
- [x] ALLOWED_HOSTS настроен
- [x] HTTPS enabled с HSTS
- [x] CSRF protection enabled
- [ ] Rate limiting на всех auth endpoints
- [x] JWT tokens с коротким expiration
- [ ] Security logging настроено
- [ ] CSP headers настроены
- [x] CORS правильно настроен
- [x] Database SSL enabled
- [x] Sentry error tracking
- [ ] Dependency vulnerabilities проверены
- [x] .env файлы в .gitignore
- [ ] Регулярные security audits запланированы

**Выполнено: 11/15 (73%)**

---

## 🚨 Критичные действия СЕЙЧАС

### 1. Удалить DEBUG принты (5 минут)
```bash
# Найти все print() в production коде
grep -r "print(f\"DEBUG:" backend/news/
```

### 2. Добавить rate limiting на логин (10 минут)
См. секцию "Проблема 2" выше

### 3. Исправить middleware error handling (5 минут)
См. секцию "Проблема 4" выше

### 4. Проверить Railway environment variables:
- ✅ DJANGO_SUPERUSER_PASSWORD - длина >= 16 символов
- ✅ SECRET_KEY - уникальный, не дефолтный
- ✅ CORS_ORIGINS - только доверенные домены

---

## 📞 Контакты

**При обнаружении уязвимости**:
- Email: security@autonews.ai (настроить)
- Response time: 24 часа

---

## 📝 Версия отчета

- **Версия**: 1.0
- **Дата**: 21 января 2026
- **Автор**: GitHub Copilot Security Audit
- **Следующий аудит**: Февраль 2026

