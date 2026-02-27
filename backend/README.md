# 🚗 FreshMotors Backend — Django REST API

![Django](https://img.shields.io/badge/Django-6.0.1-green)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)
![Redis](https://img.shields.io/badge/Redis-7-red)
![pytest](https://img.shields.io/badge/tests-391%2B_passing-brightgreen)

Backend API для платформы автомобильных новостей FreshMotors. Развёрнут на Railway, фронтенд на Vercel (Next.js 16).

---

## 🚀 Быстрый запуск (Docker)

```bash
# Запуск backend + Redis
docker-compose up -d

# Миграции
docker exec autonews_backend python manage.py migrate

# Суперпользователь
docker exec -it autonews_backend python manage.py createsuperuser

# Тесты
docker exec autonews_backend pytest tests/ -v
```

**Endpoints:**

- 📡 API: <http://localhost:8000/api/v1/>
- 🔧 Django Admin: <http://localhost:8000/admin/>
- ❤️ Health: <http://localhost:8000/api/v1/health/>

---

## 🛠 Технологический стек

| Технология | Назначение |
|-----------|-----------|
| **Django 6.0.1** + DRF 3.15 | REST API framework |
| **PostgreSQL** | Основная БД |
| **Redis** | Кэш, view tracking, sessions, Celery broker |
| **Celery** | Фоновые задачи (обогащение, авто-спеки, автопубликация) |
| **Google Gemini 2.0 Flash** | Основной AI-провайдер |
| **Groq Llama 3.3 70b** | Фоллбэк AI-провайдер |
| **Cloudinary** | CDN для медиа (production) |
| **Pexels API** | Поиск стоковых фотографий |
| **Sentry** | Error tracking |
| **yt-dlp** | Извлечение транскриптов YouTube |
| **pytest** | 391+ тестов |

---

## 📁 Структура

```
backend/
├── auto_news_site/            # Django settings, urls, wsgi/asgi
├── news/                      # Core app
│   ├── models/                # Модели (package: articles, vehicles, system, ...)
│   ├── api_views/             # 20+ DRF ViewSets (разделены по доменам)
│   │   ├── mixins/            # ArticleGenerationMixin, ArticleEnrichmentMixin
│   │   ├── articles.py        # ArticleViewSet
│   │   ├── system.py          # Health, ErrorLog, Notifications
│   │   └── ...                # auth, rss, youtube, vehicles, etc.
│   ├── api_urls.py            # API routing (60+ endpoints)
│   ├── serializers.py         # Сериализация + A/B variant injection
│   ├── error_capture.py       # ErrorCaptureMiddleware (auto-logs 500s)
│   ├── management/commands/   # verify_migrations, reformat_rss_articles
│   └── migrations/            # 88+ миграций
├── ai_engine/                 # AI генерация
│   ├── main.py                # Pipeline orchestrator
│   └── modules/
│       ├── transcriber.py     # YouTube транскрипт
│       ├── analyzer.py        # AI анализ + спеки
│       ├── article_generator.py   # RSS press release expansion
│       ├── entity_validator.py    # Anti-hallucination валидатор
│       ├── deep_specs.py          # Deep vehicle specs обогащение
│       ├── publisher.py       # Публикация в БД
│       ├── article_reviewer.py    # AI Editor
│       ├── auto_publisher.py      # Автопаблишер
│       ├── content_formatter.py   # Форматирование контента
│       └── screenshot_extractor.py # Скриншоты из видео
├── tests/                     # pytest (391+ тестов)
│   ├── conftest.py            # Fixtures
│   ├── test_ab_testing.py     # A/B тестирование (10)
│   ├── test_analytics_api.py  # Аналитика (8)
│   ├── test_auto_publisher.py # Автопаблишер (8)
│   ├── test_automation_api.py # API автоматизации (8)
│   ├── test_models.py         # Модели (12)
│   ├── test_search_api.py     # Поиск (11)
│   ├── test_article_generation.py  # Генерация (6)
│   ├── test_seo_helpers.py    # SEO (8)
│   └── + 20 more test files   # CRUD, auth, brands, cars, comments, etc.
└── Dockerfile
```

---

## 📡 Ключевые API Endpoints

### Контент

```
GET/POST /api/v1/articles/                    # CRUD статей
POST     /api/v1/articles/generate_from_youtube/  # AI генерация
GET      /api/v1/categories/                  # Категории
GET      /api/v1/tags/ | /api/v1/tag-groups/  # Теги и группы
GET      /api/v1/pending-articles/            # Модерация
```

### A/B Testing

```
POST /api/v1/ab/impression/     # Track impression
POST /api/v1/ab/click/          # Track click
GET  /api/v1/ab/tests/          # List tests (admin)
POST /api/v1/ab/pick-winner/    # Manual pick (admin)
POST /api/v1/ab/auto-pick/      # Auto-pick (admin)
```

### Автоматизация

```
GET/PATCH /api/v1/automation/settings/       # Настройки
GET       /api/v1/automation/stats/          # Статистика
POST      /api/v1/automation/trigger/{type}/ # Ручной запуск
```

### Аналитика

```
GET /api/v1/analytics/overview/        # Dashboard
GET /api/v1/analytics/articles/top/    # Топ статьи
GET /api/v1/analytics/views/timeline/  # Timeline
GET /api/v1/analytics/categories/      # По категориям
GET /api/v1/analytics/gsc/             # Google Search Console
GET /api/v1/analytics/ai-stats/        # AI enrichment stats
```

### Полный список в [api_urls.py](news/api_urls.py)

---

## 🔧 Переменные окружения

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=autonews_db
DB_USER=autonews_user
DB_PASSWORD=your-password
DATABASE_URL=postgresql://...        # production

# AI
GEMINI_API_KEY=your-gemini-key
GROQ_API_KEY=your-groq-key

# Redis
REDIS_URL=redis://redis:6379/0

# Media
CLOUDINARY_URL=cloudinary://...      # production

# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Analytics
GSC_KEY_JSON=...

# Images
PEXELS_API_KEY=...

# Monitoring
SENTRY_DSN=...
```

---

## 🧪 Тесты

```bash
# Все тесты
docker exec autonews_backend pytest tests/ -v

# Конкретный файл
docker exec autonews_backend pytest tests/test_ab_testing.py -v

# С покрытием
docker exec autonews_backend pytest tests/ --cov=news --cov-report=term-missing
```

**391+ тестов** покрывающие: API endpoints, модели, автопаблишер, A/B тестирование, поиск, аналитику, SEO, генерацию, error tracking, CRUD, auth, brands, cars, comments, ratings.

---

## 💾 Бэкапы

```bash
# Ручной бэкап
docker exec autonews_postgres pg_dump -U autonews_user autonews > backup_$(date +%Y%m%d).sql

# Восстановление
docker exec -i autonews_postgres psql -U autonews_user autonews < backup.sql
```

Медиа-файлы хранятся в **Cloudinary** и безопасны при редеплое.

---

## 📝 Дополнительная документация

- [docs/AD_SETUP_GUIDE.md](docs/AD_SETUP_GUIDE.md) — настройка рекламы
- [docs/AUTH_SYSTEM.md](docs/AUTH_SYSTEM.md) — система аутентификации
- [docs/GEMINI_SETUP.md](docs/GEMINI_SETUP.md) — настройка Gemini AI
- [docs/PEXELS_SETUP.md](docs/PEXELS_SETUP.md) — настройка Pexels API
- [docs/REDIS_SETUP.md](docs/REDIS_SETUP.md) — настройка Redis
- [docs/SENTRY_SETUP.md](docs/SENTRY_SETUP.md) — настройка Sentry
- [SECURITY.md](SECURITY.md) — безопасность backend

---

**Made with ❤️, AI, and a lot of coffee ☕**
