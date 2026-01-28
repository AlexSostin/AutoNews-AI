# 🚀 Quick Start with Docker

## Предварительные требования

- Docker Desktop установлен и запущен
- Git (для клонирования репозитория)

## Быстрый запуск

### 1. Клонируйте проект
```bash
git clone <your-repo-url>
cd Auto_News
```

### 2. Настройте переменные окружения
```bash
# Скопируйте пример файла
copy .env.example backend\.env

# Отредактируйте backend\.env и добавьте свои API ключи:
# - GROQ_API_KEY
# - GEMINI_API_KEY
```

### 3. Запустите все сервисы одной командой
```bash
cd backend
docker-compose up -d
```

**Это запустит:**
- ✅ PostgreSQL (порт 5433)
- ✅ Django Backend (порт 8001)
- ✅ Next.js Frontend (порт 3000)

### 4. Создайте суперпользователя (первый запуск)
```bash
docker exec -it autonews_backend python manage.py createsuperuser
```

### 5. Откройте в браузере
- 🌐 Сайт: http://localhost:3000
- 🔧 Админка Django: http://localhost:8001/admin
- 📡 API: http://localhost:8001/api/v1/

## Управление Docker контейнерами

### Просмотр статуса
```bash
docker-compose ps
```

### Просмотр логов
```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Остановка
```bash
docker-compose stop
```

### Перезапуск
```bash
docker-compose restart
```

### Полная остановка с удалением контейнеров
```bash
docker-compose down
```

### Полная очистка (включая данные БД)
```bash
docker-compose down -v
```

## Работа с Django внутри контейнера

### Миграции
```bash
docker exec autonews_backend python manage.py makemigrations
docker exec autonews_backend python manage.py migrate
```

### Django shell
```bash
docker exec -it autonews_backend python manage.py shell
```

### Создание категорий
```bash
docker exec autonews_backend python create_categories.py
```

### Генерация AI статьи
```bash
docker exec -it autonews_backend python ai_engine/main.py
```

## Типичный рабочий процесс

**Утром:**
```bash
cd Auto_News/backend
docker-compose up -d
```

**Во время работы:**
- Редактируете код локально
- Изменения автоматически применяются (volume mapping)
- Смотрите логи: `docker-compose logs -f`

**Вечером:**
```bash
docker-compose stop
```

## Backup и восстановление БД

### Создать backup
```bash
docker exec autonews_postgres pg_dump -U autonews_user autonews > backup_$(date +%Y%m%d).sql
```

### Восстановить из backup
```bash
docker exec -i autonews_postgres psql -U autonews_user autonews < backup_20260117.sql
```

## Troubleshooting

### Контейнер не запускается
```bash
# Проверьте логи
docker-compose logs backend

# Пересоберите образы
docker-compose build --no-cache
docker-compose up -d
```

### База данных не доступна
```bash
# Проверьте здоровье PostgreSQL
docker exec autonews_postgres pg_isready -U autonews_user
```

### Порт уже занят
Измените порты в `docker-compose.yml`:
```yaml
ports:
  - "8002:8001"  # вместо 8001:8001
```

## Полезные команды

### Войти в контейнер bash
```bash
docker exec -it autonews_backend sh
docker exec -it autonews_frontend sh
```

### Просмотр использования ресурсов
```bash
docker stats
```

### Очистка неиспользуемых образов/контейнеров
```bash
docker system prune -a
```
