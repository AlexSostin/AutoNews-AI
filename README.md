# 🚗 FreshMotors — AI-Powered Automotive News Platform

![Django](https://img.shields.io/badge/Django-6.0.1-green)
![Next.js](https://img.shields.io/badge/Next.js-16.1-black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![Redis](https://img.shields.io/badge/Redis-Cache-red)
![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF)

**FreshMotors** — полнофункциональная платформа автомобильных новостей с AI генерацией контента из YouTube видео и RSS лент. Построена на Django REST API + Next.js 16 с полностью кастомной наследной архитектурой и развёрнута на Railway (backend) + Vercel (frontend).

🌐 **Live**: [freshmotors.net](https://freshmotors.net)

---

## 🌟 Ключевые возможности

### 🤖 AI-движок генерации контента
- **Dual-провайдер**: Google Gemini 2.0 Flash (основной) + Groq Llama 3 (фоллбэк)
- **AI-редактор**: Автоматическая проверка и улучшение сгенерированных статей
- **Извлечение скриншотов**: 3 кадра из видео (15%, 50%, 85%)
- **Анализ спецификаций**: Автоматическое извлечение характеристик авто из видео
- **Тайминг пайплайна**: Замеры каждого шага генерации (сохраняются в `generation_metadata`)
- **AI Editor diff**: Отслеживание изменений AI-редактора (добавлено/удалено символов)
- **AI Image Generation**: Генерация изображений через Gemini + поиск через Pexels API

### 🤖 Система автоматизации
- **Auto-Publisher**: Автоматическая публикация статей из RSS лент с quality scoring
- **Safety Gating**: Оценка безопасности RSS источников перед автопубликацией
- **Контроль лимитов**: Ежедневные лимиты публикации, минимальное качество, require image
- **Decision Logging**: Полное логирование решений автопаблишера
- **Панель управления**: Настройки автоматизации, статистика, ручной триггер задач

### 📊 Аналитика и мониторинг
- **Google Analytics 4**: Отслеживание просмотров, scroll depth (25/50/75/100%), read time
- **Google Search Console**: Интеграция с GSC для данных по кликам/показам
- **Redis view tracking**: Высокопроизводительный подсчёт просмотров с батч-синхронизацией в БД
- **Dashboard**: Метрики роста, популярные статьи, статистика категорий
- **AI Stats**: Обогащение покрытие (vehicle specs, A/B titles, tags, car specs, images)

### 🧪 A/B Тестирование
- **Варианты заголовков**: AI генерирует 2-3 варианта заголовка для статьи
- **Детерминированное назначение**: Cookie-based seed для консистентности по сессиям
- **Трекинг**: Impression/click отслеживание через API
- **Автовыбор победителя**: По CTR после достижения порога impressions
- **Ручной выбор**: Админ может вручную выбрать победителя

### 🌐 Публичный сайт
- **SSR/SSG**: Server-side rendering и static generation с Next.js 16
- **Каталог брендов**: Страницы брендов и моделей с автоматическим обогащением
- **SEO**: Dynamic metadata, canonical tags, JSON-LD structured data, sitemap.xml
- **Мультиязычность**: Контент на английском с мультивалютным конвертером цен
- **Комментарии**: Threaded comments с модерацией и рейтингами (1–5 звёзд)
- **Избранное**: Сохранение статей для зарегистрированных пользователей
- **Feedback**: Кнопка "Found an error?" для репорта ошибок/галлюцинаций AI
- **Адаптивный дизайн**: Mobile-first, все breakpoints

### ⚛️ Админ-панель (Next.js)
- **Управление контентом**: CRUD статей, категорий, тегов, car specs
- **YouTube генерация**: Генерация статей из YouTube URL
- **Batch генерация**: Одновременная генерация до 5 статей
- **RSS агрегатор**: Мониторинг RSS лент брендов с дедупликацией и safety scoring
- **Pending Articles**: Модерация сгенерированных статей перед публикацией
- **Модерация**: Комментарии, фидбэки с resolve/reopen
- **Brand менеджмент**: Каталог брендов с алиасами, логотипами, мержем
- **Подписчики**: Управление newsletter подписками
- **Аналитика**: Дашборд с графиками, метрики, AI Stats, GSC
- **A/B Testing**: Управление A/B тестами заголовков
- **Рекламные места**: Управление AdSense и кастомными рекламными блоками
- **Автоматизация**: Настройки автопаблишера, статистика, ручные триггеры
- **Управление пользователями**: CRUD пользователей, сброс паролей
- **Настройки**: Site settings, account settings, уведомления

### 🔐 Безопасность
- **JWT аутентификация** с auto-refresh токенов
- **Google OAuth 2.0** — социальный логин
- **Email верификация** — смена email через 6-значный код
- **Rate limiting**: 100 req/h анонимы, 1000 req/h авторизованные, + per-endpoint лимиты
- **CSRF/XSS/HSTS** protection, secure headers
- **Anti-spam**: IP rate limiting на feedback и комментарии
- **Bot Protection**: User-Agent middleware для блокировки автоматических запросов

### ✅ CI/CD
- **GitHub Actions**: Автоматические pytest тесты (75 тестов) при каждом пуше
- **Backend тесты**: PostgreSQL + Redis в CI, pytest с полным покрытием
- **Frontend checks**: Lint, type checking, build verification
- **Auto-deploy**: Railway (backend) + Vercel (frontend) из GitHub

---

## 🛠 Технологический стек

### Backend
| Технология | Назначение |
|-----------|-----------|
| **Django 6.0.1** + DRF 3.15 | REST API framework |
| **PostgreSQL** | Основная БД (production) |
| **Redis** | Кэширование, view tracking, Celery broker |
| **Celery** | Фоновые задачи (обогащение, авто-спеки, автопубликация) |
| **Google Gemini 2.0** | Основной AI-провайдер |
| **Groq (Llama 3.3 70b)** | Фоллбэк AI-провайдер |
| **Cloudinary** | Хостинг медиа-файлов (production) |
| **Sentry** | Error tracking и мониторинг |
| **yt-dlp** | Извлечение транскриптов YouTube |
| **Pexels API** | Поиск стоковых фотографий |
| **pytest** | Тестовый фреймворк (75 тестов) |

### Frontend
| Технология | Назначение |
|-----------|-----------|
| **Next.js 16.1** | App Router, SSR, SSG |
| **TypeScript 5.0** | Type safety |
| **Tailwind CSS** | Styling |
| **Lucide React** | Иконки |
| **Google Analytics 4** | Трекинг пользователей |

### Инфраструктура
| Технология | Назначение |
|-----------|-----------|
| **Docker Compose** | Локальная разработка (backend + redis) |
| **Railway** | Хостинг backend (production) |
| **Vercel** | Хостинг frontend (production) |
| **GitHub Actions** | CI (pytest, lint, build) + CD автодеплой |
| **Cloudinary** | CDN для изображений |

---

## 📁 Структура проекта

```
AutoNews-AI/
├── .github/workflows/         # CI/CD
│   └── ci.yml                 # GitHub Actions: pytest + frontend checks
├── backend/                   # Django REST API
│   ├── auto_news_site/        # Django settings, urls, wsgi
│   ├── news/                  # Core app
│   │   ├── models.py          # Article, Category, Tag, Brand, RSS, A/B, Ads...
│   │   ├── api_views.py       # 30+ DRF ViewSets
│   │   ├── api_urls.py        # API routing
│   │   ├── serializers.py     # Data serialization (with AB variant injection)
│   │   ├── ab_testing_views.py # A/B test tracking & admin endpoints
│   │   ├── cars_views.py      # Brand catalog API
│   │   └── search_analytics_views.py # Search + Analytics endpoints
│   ├── ai_engine/             # AI article generation
│   │   ├── main.py            # Pipeline orchestrator
│   │   └── modules/           # Transcriber, analyzer, publisher, reviewer, auto_publisher
│   ├── tests/                 # Pytest test suite (75 tests)
│   └── Dockerfile
│
├── frontend-next/             # Next.js 16 (App Router)
│   ├── app/
│   │   ├── (public)/          # Public pages (articles, brands, profile)
│   │   └── admin/             # Admin dashboard (25+ pages)
│   ├── components/            # Reusable components
│   └── lib/                   # API client, auth, analytics, utils
│
├── docker-compose.yml         # Backend + Redis containers
├── DEPLOYMENT.md              # Deployment guide
├── PROJECT_ARCHITECTURE.md    # Architecture overview
└── SECURITY.md                # Security documentation
```

---

## 🚀 Быстрый старт

### Системные требования
- Python 3.13+
- Node.js 18+
- Docker & Docker Compose
- Redis (через Docker или установленный)

### 1. Клонирование
```bash
git clone https://github.com/AlexSostin/AutoNews-AI.git
cd AutoNews-AI
```

### 2. Backend (Docker)
```bash
# Запуск backend + Redis
docker-compose up -d

# Применить миграции
docker exec autonews_backend python3 manage.py migrate

# Создать суперпользователя
docker exec -it autonews_backend python3 manage.py createsuperuser
```

### 3. Frontend
```bash
cd frontend-next
npm install
npm run dev
```

### 4. Запуск тестов
```bash
docker exec autonews_backend pytest tests/ -v
```

### 5. Открыть
- 🌐 Публичный сайт: http://localhost:3000
- ⚙️ Админ-панель: http://localhost:3000/admin
- 📡 API: http://localhost:8000/api/v1/

---

## 📡 Основные API Endpoints

### Аутентификация
```
POST /api/v1/token/                    # JWT Login
POST /api/v1/token/refresh/            # Refresh token
GET  /api/v1/auth/user/                # Current user info
PATCH /api/v1/auth/user/               # Update profile
POST /api/v1/auth/password/change/     # Change password
POST /api/v1/auth/email/request-change/ # Email change (verification)
```

### Контент
```
GET    /api/v1/articles/                      # Список статей
POST   /api/v1/articles/generate_from_youtube/ # AI генерация
POST   /api/v1/articles/{slug}/feedback/      # User feedback
GET    /api/v1/categories/                    # Категории
GET    /api/v1/tags/                          # Теги
GET    /api/v1/tag-groups/                    # Группы тегов
GET    /api/v1/comments/                      # Комментарии
GET    /api/v1/feedback/                      # Feedback (admin)
GET    /api/v1/pending-articles/              # Pending articles (admin)
```

### Каталог автомобилей
```
GET  /api/v1/cars/brands/                       # Все бренды
GET  /api/v1/cars/brands/{slug}/                # Детали бренда
GET  /api/v1/cars/brands/{slug}/models/{slug}/  # Детали модели
GET  /api/v1/car-specifications/                # Car specs
GET  /api/v1/vehicle-specs/                     # Vehicle specs
```

### Аналитика
```
GET  /api/v1/analytics/overview/       # Dashboard overview
GET  /api/v1/analytics/articles/top/   # Top articles
GET  /api/v1/analytics/views/timeline/ # Views timeline
GET  /api/v1/analytics/categories/     # Category distribution
GET  /api/v1/analytics/gsc/            # Google Search Console data
GET  /api/v1/analytics/ai-stats/       # AI enrichment statistics
```

### A/B Testing
```
POST /api/v1/ab/impression/     # Track impression (public)
POST /api/v1/ab/click/          # Track click (public)
GET  /api/v1/ab/tests/          # List all tests (admin)
POST /api/v1/ab/pick-winner/    # Manual winner pick (admin)
POST /api/v1/ab/auto-pick/      # Auto-pick eligible (admin)
```

### Автоматизация
```
GET/PATCH /api/v1/automation/settings/        # Automation settings
GET       /api/v1/automation/stats/           # Stats & decision log
POST      /api/v1/automation/trigger/{type}/  # Manual trigger
```

### RSS & YouTube
```
GET  /api/v1/youtube-channels/         # YouTube каналы
GET  /api/v1/rss-feeds/                # RSS ленты
GET  /api/v1/rss-news-items/           # RSS новости
```

### AI Image
```
POST /api/v1/articles/{id}/generate-ai-image/  # AI image generation
POST /api/v1/articles/{id}/search-photos/       # Pexels photo search
POST /api/v1/articles/{id}/save-external-image/ # Save external image
```

### Реклама & Прочее
```
GET  /api/v1/ad-placements/         # Ad placements
GET  /api/v1/subscribers/           # Newsletter subscribers
GET  /api/v1/admin/users/           # User management (admin)
GET  /api/v1/health/                # Health check
```

---

## 🔧 Переменные окружения

Основные переменные в `backend/.env`:

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=autonews_db
DB_USER=autonews_user
DB_PASSWORD=your-password

# AI Providers
GEMINI_API_KEY=your-gemini-key
GROQ_API_KEY=your-groq-key

# Redis
REDIS_URL=redis://redis:6379/0

# Media (Production)
CLOUDINARY_URL=cloudinary://...

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Analytics
GSC_KEY_JSON=your-gsc-credentials

# Images
PEXELS_API_KEY=your-pexels-key
```

---

## 📝 Лицензия

MIT License

---

**Made with ❤️, AI, and a lot of coffee ☕**
