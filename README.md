# 🚗 AutoNews - AI-Powered Automotive News Platform

![Django](https://img.shields.io/badge/Django-6.0.1-green)
![Next.js](https://img.shields.io/badge/Next.js-16.1-black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue)
![Python](https://img.shields.io/badge/Python-3.13-blue)

**AutoNews** - современная платформа автомобильных новостей с AI генерацией контента из YouTube видео. Построена на микросервисной архитектуре с Django REST API и Next.js frontend.

## 🌟 Основные возможности

- 🤖 **AI генерация статей** из YouTube видео через Groq API (llama-3.3-70b)
- 📝 Полнофункциональная админ-панель для управления контентом
- 🎨 Современный публичный сайт на Next.js 16 с SSR
- 🔐 JWT аутентификация с защитой API
- 📱 Адаптивный дизайн для всех устройств
- 🔒 Защита от уязвимостей (CSRF, XSS, rate limiting)
- 💬 Комментарии и рейтинги статей
- 📊 SEO оптимизация с dynamic metadata

## 📁 Структура проекта

```
Auto_News/
├── backend/              # Django REST API
│   ├── manage.py
│   ├── .env             # Переменные окружения (не в Git)
│   ├── auto_news_site/  # Настройки Django
│   ├── news/            # Основное приложение
│   ├── ai_engine/       # AI генерация контента
│   └── media/           # Загруженные файлы
│
├── frontend-next/        # Next.js Public Site
│   ├── app/             # App Router (Next.js 16)
│   ├── components/      # React компоненты
│   ├── lib/             # Утилиты и API клиент
│   └── types/           # TypeScript типы
│
└── README.md
```

## 🛠 Технологический стек

### Backend
- **Django 6.0.1** + Django REST Framework 3.15
- **JWT Authentication** (djangorestframework-simplejwt)
- **Rate Limiting** (100 req/hour для анонимов)
- **Security Headers** (HSTS, XSS protection, etc.)
- **Groq API** - AI генерация статей
- **SQLite** (dev) / **PostgreSQL** (prod)

### Frontend
- **Next.js 16.1** (App Router, Server Components, SSR)
- **TypeScript 5.0** - Type safety
- **Tailwind CSS** - Styling
- **Lucide React** - Иконки
- **React Hook Form** - Формы в админке

## 🚀 Быстрый старт

### Системные требования
- Python 3.13+
- Node.js 18+
- Git
- Redis (опционально, есть автоматический fallback)

### ⚠️ Важно: Порядок запуска

**Обязательно запускайте в таком порядке:**
1. ✅ **Сначала**: Django backend на порте 8001
2. ✅ **Затем**: Next.js frontend на порте 3000

Если увидите ошибки соединения, убедитесь что Django работает до запуска Next.js!

### 1. Клонирование и настройка

```bash
# Клонировать репозиторий
git clone https://github.com/AlexSostin/AutoNews-AI.git
cd Auto_News

# Установить Python зависимости
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Применить миграции
python manage.py migrate

# Создать суперпользователя
python manage.py createsuperuser

# Установить Node.js зависимости
cd ../frontend-next
npm install
```

### 2. Настройка переменных окружения

Файл `.env` уже создан в `backend/.env` с настройками для разработки.

**⚠️ Для продакшена** обязательно измените:
```env
DEBUG=False
SECRET_KEY=<новый-секретный-ключ>
ALLOWED_HOSTS=yourdomain.com
CORS_ORIGINS=https://yourdomain.com
```

### 3. Запуск проекта (ВАЖНО: порядок!)

**Откройте 2 терминала:**

#### Терминал 1 - Django Backend API (ЗАПУСТИТЕ ПЕРВЫМ!)
```bash
cd backend
python manage.py runserver 8001
```
✅ Дождитесь сообщения: `Starting ASGI/Daphne... at http://127.0.0.1:8001/`
- Django Admin: http://127.0.0.1:8001/admin/
- API Root: http://127.0.0.1:8001/api/v1/

#### Терминал 2 - Next.js Frontend (ЗАПУСТИТЕ ВТОРЫМ!)
```bash
cd frontend-next
npm run dev
```
✅ Сайт запущен на `http://localhost:3000/`

**💡 Если видите ошибки соединения**: убедитесь что Django работает, затем нажмите кнопку "🔄 Retry Connection" на фронтенде.
- Публичный сайт: http://localhost:3000/
- Админ-панель: http://localhost:3000/admin/

## 🎯 Основные URL-адреса

### Backend (Django)
| Endpoint | Описание |
|----------|----------|
| `/admin/` | Django Admin Panel |
| `/api/v1/articles/` | Список статей (API) |
| `/api/v1/categories/` | Категории |
| `/api/v1/tags/` | Теги |
| `/api/v1/comments/` | Комментарии |
| `/api/v1/auth/login/` | JWT Login |

### Frontend (Next.js)
| URL | Описание |
|-----|----------|
| `/` | Главная страница |
| `/articles/[slug]` | Детальная страница статьи |
| `/categories/[slug]` | Статьи по категории |
| `/admin/` | Админ-панель |
| `/admin/articles` | Управление статьями |

## 📚 Руководства

- [Настройка AI генерации](backend/GEMINI_SETUP.md)
- [Безопасность](backend/SECURITY.md)
- [Исправления безопасности](backend/SECURITY_FIXES.md)

## 🔐 Безопасность

✅ Все критические уязвимости исправлены:
- SECRET_KEY в переменных окружения
- Rate limiting (100 req/h анонимы, 1000 req/h авторизованные)
- CSRF & XSS protection
- Secure headers (HSTS, Content-Type-Nosniff)
- Валидация YouTube URL
- Ограничение загрузки файлов (5MB max)

Подробнее в [SECURITY_FIXES.md](backend/SECURITY_FIXES.md)

## 🚀 Развертывание на продакшене

### 1. Обновите .env
```env
DEBUG=False
SECRET_KEY=<сгенерируйте новый>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ORIGINS=https://yourdomain.com
```

### 2. Настройте PostgreSQL
```bash
pip install psycopg2-binary
```

В .env:
```env
DB_NAME=autonews_db
DB_USER=autonews_user
DB_PASSWORD=<сильный-пароль>
DB_HOST=localhost
DB_PORT=5432
```

### 3. Соберите статические файлы
```bash
python manage.py collectstatic
```

### 4. Используйте Gunicorn
```bash
pip install gunicorn
gunicorn auto_news_site.wsgi:application --bind 0.0.0.0:8001
```

### 5. Настройте Nginx
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🤝 Как использовать AI генерацию

1. Войдите в админ-панель: http://localhost:3000/admin/
2. Перейдите в "Articles"
3. Нажмите "Generate from YouTube"
4. Вставьте YouTube URL
5. AI автоматически создаст статью!

**Требуется:** API ключи в `.env` (Groq или Gemini)

## 📝 Создание контента вручную

1. Django Admin: http://127.0.0.1:8001/admin/
2. Или Next.js Admin: http://localhost:3000/admin/

Создайте:
- Категории (News, Reviews, EVs, etc.)
- Теги
- Статьи с изображениями
- Характеристики автомобилей

## 🐛 Отладка

### Backend не запускается
```bash
# Проверьте миграции
python manage.py migrate

# Проверьте .env файл
cat backend/.env
```

### Frontend показывает ошибки API
```bash
# Убедитесь что Django запущен на порту 8001
curl http://127.0.0.1:8001/api/v1/articles/

# Проверьте CORS настройки в backend/auto_news_site/settings.py
```

### Rate Limiting блокирует запросы
Это нормально для разработки. В `settings.py` измените:
```python
'DEFAULT_THROTTLE_RATES': {
    'anon': '1000/hour',  # Увеличьте для dev
    'user': '10000/hour'
}
```

✅ React админка запустится на **http://localhost:5173/**

### Результат

После запуска обоих серверов у вас будет:

| Сервер | URL | Описание |
|--------|-----|----------|
| Django API | http://127.0.0.1:8001/api/v1/ | REST API для React |
| React Admin | http://localhost:5173/ | Админ панель (React + TypeScript) |
| Public Site | http://127.0.0.1:8001/news/ | Публичный сайт |
| Django Admin | http://127.0.0.1:8001/admin/ | Старая админка Django (backup) |

## ✨ Основные возможности

### 🤖 AI Генерация контента
- Автоматическое создание статей из YouTube видео
- Извлечение субтитров и транскрипция
- Анализ спецификаций автомобилей
- Захват скриншотов (3 кадра на 15%, 50%, 85%)
- Генерация за ~15 секунд

### ⚛️ React Admin Panel
- 🔐 JWT аутентификация с auto-refresh
- 📝 CRUD для статей с YouTube генерацией
- 🏷️ Inline редактирование категорий и тегов
- 💬 Модерация комментариев (approve/delete)
- 📊 Dashboard с live статистикой
- 🎨 Современный UI с градиентами (#667eea → #764ba2)

### 🌐 Public Site
- 9 категорий новостей
- Поиск и фильтрация
- Комментарии с модерацией
- Рейтинги статей
- Адаптивный дизайн
- SEO оптимизация

## 📚 API Endpoints

### Authentication
```
POST /api/v1/token/           # Login (получить токены)
POST /api/v1/token/refresh/   # Обновить access токен
```

### Articles
```
GET    /api/v1/articles/                    # Список статей
POST   /api/v1/articles/                    # Создать статью
GET    /api/v1/articles/{id}/               # Получить статью
PUT    /api/v1/articles/{id}/               # Обновить статью
DELETE /api/v1/articles/{id}/               # Удалить статью
POST   /api/v1/articles/generate_from_youtube/  # Генерация из YouTube
POST   /api/v1/articles/{id}/increment_views/   # Увеличить просмотры
```

### Categories & Tags
```
GET    /api/v1/categories/     # Список категорий
POST   /api/v1/categories/     # Создать категорию
PUT    /api/v1/categories/{id}/
DELETE /api/v1/categories/{id}/

GET    /api/v1/tags/           # Список тегов
POST   /api/v1/tags/
PUT    /api/v1/tags/{id}/
DELETE /api/v1/tags/{id}/
```

### Comments
```
GET    /api/v1/comments/           # Список комментариев
POST   /api/v1/comments/{id}/approve/  # Одобрить комментарий
DELETE /api/v1/comments/{id}/      # Удалить комментарий
```

## 🔧 Настройка окружения

### Backend Setup

1. Создайте виртуальное окружение Python:
```powershell
python -m venv .venv
.venv\Scripts\activate
```

2. Установите зависимости:
```powershell
cd backend
pip install -r requirements.txt
```

3. Настройте Groq API:
```powershell
cd ai_engine
cp config.example.py config.py
# Отредактируйте config.py и добавьте ваш GROQ_API_KEY
```

4. Примените миграции:
```powershell
python manage.py migrate
```

5. Создайте суперпользователя:
```powershell
python manage.py createsuperuser
```

### Frontend Setup

```powershell
cd frontend
npm install
```

## 🎯 Использование

### Создание статьи из YouTube

**Через React Admin:**
1. Откройте http://localhost:5173/
2. Войдите с Django admin credentials
3. Articles → New Article
4. Вставьте YouTube URL и нажмите "Generate"
5. AI создаст статью за ~15 секунд
6. Отредактируйте при необходимости
7. Опубликуйте

**Через API:**
```bash
curl -X POST http://127.0.0.1:8001/api/v1/articles/generate_from_youtube/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

## 📝 Категории

1. News - Автомобильные новости
2. Reviews - Обзоры автомобилей
3. EVs - Электромобили
4. Technology - Автомобильные технологии
5. Industry - Автомобильная индустрия
6. Classics - Классические автомобили
7. Motorsport - Автоспорт
8. Modifications - Тюнинг и модификации
9. Comparisons - Сравнения автомобилей

## 🔐 Безопасность

- JWT токены с коротким lifetime (5 часов access, 1 день refresh)
- CORS настроен только для localhost
- CSRF защита Django
- XSS защита через React
- SQL injection защита через ORM

## 📄 Лицензия

MIT License

## 👨‍💻 Разработка

Проект использует:
- Hot reload для React (Vite HMR)
- Auto-reload для Django (runserver)
- TypeScript для type safety
- ESLint для code quality

---

**Made with ❤️ and AI**
