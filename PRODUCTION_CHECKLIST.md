# 🚀 Production Deployment Checklist

## ✅ Готово к продакшену

### 1. **Безопасность Django**
- ✅ SECRET_KEY вынесен в переменные окружения
- ✅ DEBUG=False по умолчанию (включается только через env)
- ✅ ALLOWED_HOSTS настроен через переменные окружения
- ✅ CORS настроен через переменные окружения
- ✅ Security headers включены (X-Frame-Options, Content-Type-Nosniff, XSS-Filter)
- ✅ HTTPS настройки подготовлены (HSTS, SSL Redirect)

### 2. **База данных**
- ✅ PostgreSQL используется через Docker
- ✅ Credentials вынесены в переменные окружения
- ✅ Volume для персистентности данных
- ✅ Health checks настроены

### 3. **Docker & Контейнеризация**
- ✅ Dockerfile для backend (Django)
- ✅ Dockerfile для frontend (Next.js)
- ✅ Docker Compose для оркестрации
- ✅ Volumes для статики, медиа и БД
- ✅ Networks для изоляции
- ✅ Restart policies настроены

---

## ⚠️ КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ ПЕРЕД ПРОДАКШЕНОМ

### 1. **🔴 SECRET_KEY - ОБЯЗАТЕЛЬНО ИЗМЕНИТЬ!**
```bash
# Сгенерировать новый SECRET_KEY:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
**Текущий дефолтный ключ небезопасен!**

### 2. **🔴 Пароль базы данных**
```yaml
# В docker-compose.yml замените:
POSTGRES_PASSWORD: SecurePass123  # НА НАДЕЖНЫЙ ПАРОЛЬ!
```

### 3. **🔴 Hardcoded URLs в frontend**
Найдены hardcoded URLs, нужно исправить:

#### Файлы с проблемами:
1. **app/articles/[slug]/page.tsx (строка 74, 317)**
   - `http://localhost:3000` → использовать переменную окружения
   - `http://127.0.0.1:8001` → использовать getApiUrl()

2. **app/articles/page.tsx (строки 50, 77, 78)**
   - Жёстко прописаны `http://127.0.0.1:8001/api/v1/`

3. **app/categories/[slug]/page.tsx (строки 9, 24)**
   - Жёстко прописаны `http://127.0.0.1:8001/api/v1/`

4. **next.config.ts (строка 24)**
   - Жёсткий redirect на `http://127.0.0.1:8001`

5. **components/public/ImageGallery.tsx (строка 38)**
   - `http://127.0.0.1:8001` → использовать NEXT_PUBLIC_MEDIA_URL

6. **components/public/ArticleCard.tsx (строка 22)**
   - `http://127.0.0.1:8001` → использовать NEXT_PUBLIC_MEDIA_URL

7. **components/public/TrendingSection.tsx (строка 76)**
   - `http://127.0.0.1:8001` → использовать NEXT_PUBLIC_MEDIA_URL

### 4. **🟡 AI Engine API Keys**
В `ai_engine/config.py` API ключи из .env - убедитесь что файл .env **НЕ** в git:
```bash
# Проверьте .gitignore:
backend/.env
backend/ai_engine/.env
frontend-next/.env.local
```

### 5. **🟡 CORS Configuration**
Текущая настройка:
```python
CORS_ALLOWED_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']
```
**Для продакшена добавьте:**
```python
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'https://yourdomain.com,https://www.yourdomain.com'
).split(',')
```

---

## 📋 TODO для продакшена

### Высокий приоритет

#### 1. **Production Docker Compose**
Создайте `docker-compose.prod.yml`:
```yaml
services:
  backend:
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}  # Из .env.prod
      - ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
    command: >
      sh -c "python manage.py migrate &&
             python manage.py collectstatic --noinput &&
             gunicorn auto_news_site.wsgi:application --bind 0.0.0.0:8001 --workers 4"
  
  frontend:
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api/v1
    command: npm run build && npm start
```

#### 2. **Nginx для Reverse Proxy**
Добавьте Nginx в docker-compose:
```yaml
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl  # SSL сертификаты
      - static_volume:/app/staticfiles
      - media_volume:/app/media
```

#### 3. **SSL/TLS Сертификаты**
- Используйте Let's Encrypt (certbot)
- Или настройте Cloudflare

#### 4. **Замените runserver на Gunicorn**
```dockerfile
# В backend/Dockerfile добавьте:
RUN pip install gunicorn

# В docker-compose.prod.yml:
command: gunicorn auto_news_site.wsgi:application --bind 0.0.0.0:8001 --workers 4
```

#### 5. **Переменные окружения**
Создайте `.env.prod`:
```bash
# Django
SECRET_KEY=<НОВЫЙ_БЕЗОПАСНЫЙ_КЛЮЧ>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,api.yourdomain.com

# Database
POSTGRES_DB=autonews_prod
POSTGRES_USER=autonews_prod_user
POSTGRES_PASSWORD=<СЛОЖНЫЙ_ПАРОЛЬ>
DB_HOST=postgres
DB_PORT=5432

# CORS
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# AI Engine
GEMINI_API_KEY=<ВАШ_КЛЮЧ>
GROQ_API_KEY=<ВАШ_КЛЮЧ>
AI_PROVIDER=groq

# Redis (для production)
REDIS_URL=redis://redis:6379/1
```

### Средний приоритет

#### 6. **Redis для кэша и WebSockets**
```yaml
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
```

#### 7. **Мониторинг и логи**
- Добавьте сервис для логов (ELK stack или Loki)
- Настройте health checks
- Используйте Sentry для отслеживания ошибок

#### 8. **Backup стратегия**
```bash
# Backup PostgreSQL
docker exec autonews_postgres pg_dump -U autonews_user autonews > backup.sql

# Backup media files
docker cp autonews_backend:/app/media ./media_backup
```

#### 9. **Rate Limiting**
Добавьте в Django:
```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day'
    }
}
```

#### 10. **Static/Media CDN**
- Настройте S3 или CloudFront для статики
- Или используйте Django-storages

### Низкий приоритет

#### 11. **CI/CD Pipeline**
- GitHub Actions / GitLab CI
- Автоматические тесты
- Автодеплой

#### 12. **Тесты**
```bash
# Добавьте тесты для критичных частей
python manage.py test
```

---

## 🔒 Дополнительные меры безопасности

### 1. **Файрвол**
```bash
# Только нужные порты открыты:
80 (HTTP), 443 (HTTPS) - публично
5432 (PostgreSQL), 6379 (Redis) - только внутри Docker network
```

### 2. **Database Security**
- ✅ Пароли в переменных окружения
- ⚠️ Используйте сложные пароли (16+ символов)
- ⚠️ Ограничьте подключения к БД только с backend контейнера

### 3. **Django Security Middleware**
Уже настроено:
- SecurityMiddleware
- CsrfViewMiddleware
- XFrameOptionsMiddleware

### 4. **Environment Variables**
⚠️ **НИКОГДА не коммитьте:**
- `.env`
- `.env.prod`
- `config.py` с API ключами

Убедитесь в `.gitignore`:
```gitignore
.env
.env.*
*.env
config.py
!config.example.py
```

---

## 📊 Текущий статус безопасности

| Элемент | Статус | Комментарий |
|---------|--------|-------------|
| SECRET_KEY | 🟡 | Вынесен в env, но дефолтное значение небезопасно |
| DEBUG | ✅ | False по умолчанию |
| ALLOWED_HOSTS | ✅ | Настроен через env |
| Database Credentials | 🟡 | В env, но пароль простой |
| CORS | ✅ | Настроен |
| HTTPS | 🟠 | Настройки есть, но не активно |
| SSL Certificates | ❌ | Нет |
| Nginx/Reverse Proxy | ❌ | Нет |
| Gunicorn | ❌ | Используется runserver |
| Redis | ❌ | Нет (используется InMemory) |
| Monitoring | ❌ | Нет |
| Backups | ❌ | Не настроены |
| Rate Limiting | ❌ | Нет |
| Hardcoded URLs | 🔴 | Есть в frontend |

**Легенда:**
- ✅ Готово
- 🟡 Нужны улучшения
- 🟠 Частично готово
- 🔴 Критично
- ❌ Отсутствует

---

## 🚀 Быстрый старт для продакшена

### Шаг 1: Исправьте критические проблемы
```bash
# 1. Сгенерируйте новый SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 2. Создайте .env.prod со всеми переменными
cp .env.example .env.prod
# Отредактируйте .env.prod - вставьте новый SECRET_KEY, пароли и т.д.

# 3. Исправьте hardcoded URLs в frontend (список выше)
```

### Шаг 2: Настройте production docker-compose
```bash
# Создайте docker-compose.prod.yml
# Замените runserver на gunicorn
# Добавьте nginx
```

### Шаг 3: Deploy
```bash
# Запустите в production режиме
docker-compose -f docker-compose.prod.yml up -d

# Проверьте логи
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 📞 Поддержка

После исправления всех 🔴 критических проблем проект будет готов к деплою.
Рекомендуется также исправить 🟡 проблемы перед выходом в продакшен.
