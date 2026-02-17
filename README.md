# 🚗 FreshMotors — AI-Powered Automotive News Platform

![Django](https://img.shields.io/badge/Django-6.0.1-green)
![Next.js](https://img.shields.io/badge/Next.js-16.1-black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![Redis](https://img.shields.io/badge/Redis-Cache-red)

**FreshMotors** — полнофункциональная платформа автомобильных новостей с AI генерацией контента из YouTube видео. Построена на Django REST API + Next.js 16 с полностью кастомной наследной архитектурой и развёрнута на Railway (backend) + Vercel (frontend).

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

### 📊 Аналитика и мониторинг
- **Google Analytics 4**: Отслеживание просмотров, scroll depth (25/50/75/100%), read time
- **Google Search Console**: Интеграция с GSC для данных по кликам/показам
- **Redis view tracking**: Высокопроизводительный подсчёт просмотров с батч-синхронизацией в БД
- **Dashboard**: Метрики роста, популярные статьи, статистика категорий

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
- **RSS агрегатор**: Мониторинг RSS лент брендов с дедупликацией
- **Модерация**: Комментарии, фидбэки с resolve/reopen
- **Brand менеджмент**: Каталог брендов с алиасами, логотипами, мержем
- **Подписчики**: Управление newsletter подписками
- **Аналитика**: Дашборд с графиками и метриками
- **Настройки**: Site settings, account settings, email preferences

### 🔐 Безопасность
- **JWT аутентификация** с auto-refresh токенов
- **Google OAuth 2.0** — социальный логин
- **Email верификация** — смена email через 6-значный код
- **Rate limiting**: 100 req/h анонимы, 1000 req/h авторизованные, + per-endpoint лимиты
- **CSRF/XSS/HSTS** protection, secure headers
- **Anti-spam**: IP rate limiting на feedback и комментарии

---

## 🛠 Технологический стек

### Backend
| Технология | Назначение |
|-----------|-----------|
| **Django 6.0.1** + DRF 3.15 | REST API framework |
| **PostgreSQL** | Основная БД (production) |
| **Redis** | Кэширование, view tracking, Celery broker |
| **Celery** | Фоновые задачи (обогащение, авто-спеки) |
| **Google Gemini 2.0** | Основной AI-провайдер |
| **Groq (Llama 3.3 70b)** | Фоллбэк AI-провайдер |
| **Cloudinary** | Хостинг медиа-файлов (production) |
| **Sentry** | Error tracking и мониторинг |
| **yt-dlp** | Извлечение транскриптов YouTube |

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
| **GitHub Actions** | CI/CD автодеплой |
| **Cloudinary** | CDN для изображений |

---

## 📁 Структура проекта

```
AutoNews-AI/
├── backend/                    # Django REST API
│   ├── auto_news_site/         # Django settings, urls, wsgi
│   ├── news/                   # Core app (models, views, serializers)
│   │   ├── models.py           # Article, Category, Tag, Brand, RSS, Feedback...
│   │   ├── api_views.py        # DRF ViewSets
│   │   ├── api_urls.py         # API routing
│   │   ├── admin.py            # Django Admin
│   │   ├── signals.py          # Auto notifications, spec extraction
│   │   └── cars_views.py       # Brand catalog API
│   ├── ai_engine/              # AI article generation
│   │   ├── main.py             # Pipeline orchestrator
│   │   └── modules/            # Transcriber, analyzer, publisher, reviewer
│   └── Dockerfile
│
├── frontend-next/              # Next.js 16 (App Router)
│   ├── app/
│   │   ├── (public)/           # Public pages (articles, brands, profile)
│   │   └── admin/              # Admin dashboard (20+ pages)
│   ├── components/             # Reusable components
│   │   ├── admin/              # AdminHeader, Sidebar, etc.
│   │   └── public/             # ViewTracker, FeedbackButton, etc.
│   ├── lib/                    # API client, auth, analytics, utils
│   └── types/                  # TypeScript types
│
├── docker-compose.yml          # Backend + Redis containers
├── DEPLOYMENT.md               # Deployment guide
├── PROJECT_ARCHITECTURE.md     # Architecture overview
└── SECURITY.md                 # Security documentation
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

### 4. Открыть
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
GET    /api/v1/comments/                      # Комментарии
GET    /api/v1/feedback/                      # Feedback (admin)
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
GET  /api/v1/analytics/gsc/            # Google Search Console data
```

### RSS & YouTube
```
GET  /api/v1/youtube-channels/         # YouTube каналы
GET  /api/v1/rss-feeds/                # RSS ленты
GET  /api/v1/rss-news-items/           # RSS новости
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
```

---

## 📝 Лицензия

MIT License

---

**Made with ❤️, AI, and a lot of coffee ☕**
