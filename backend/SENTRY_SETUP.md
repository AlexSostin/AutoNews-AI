# Sentry Setup - Отслеживание ошибок

## Регистрация на Sentry

1. Перейди на https://sentry.io/signup/
2. Создай бесплатный аккаунт (5000 событий/месяц бесплатно)
3. Создай 2 проекта:
   - **autonews-backend** (платформа: Django)
   - **autonews-frontend** (платформа: Next.js)

## Настройка Backend (Django)

1. Скопируй DSN из Sentry проекта `autonews-backend`
2. Добавь в `backend/.env`:
```bash
SENTRY_DSN=https://xxxxxxxxxx@xxxxxxxxxx.ingest.sentry.io/xxxxxxxxxx
ENVIRONMENT=production
```

3. Перезапусти backend контейнер:
```bash
cd backend
docker-compose restart backend
```

## Настройка Frontend (Next.js)

1. Скопируй DSN из Sentry проекта `autonews-frontend`
2. Создай `frontend-next/.env.local`:
```bash
NEXT_PUBLIC_SENTRY_DSN=https://xxxxxxxxxx@xxxxxxxxxx.ingest.sentry.io/xxxxxxxxxx
SENTRY_ORG=your-org-name
SENTRY_PROJECT=autonews-frontend
```

3. Перезапусти frontend контейнер:
```bash
cd backend
docker-compose restart frontend
```

## Проверка работы

### Тестовая ошибка в Backend:
```python
# Открой любой view и добавь:
raise Exception("Test Sentry Backend Error")
```

### Тестовая ошибка в Frontend:
```typescript
// Добавь в любой компонент:
throw new Error("Test Sentry Frontend Error");
```

После генерации ошибки проверь дашборд Sentry - ошибка должна появиться в течение минуты.

## Что отслеживается

### Backend:
- ✅ 500 ошибки (Internal Server Error)
- ✅ Необработанные исключения
- ✅ SQL запросы (медленные)
- ✅ API эндпоинты с ошибками
- ✅ Стектрейс с номерами строк

### Frontend:
- ✅ JavaScript ошибки
- ✅ React компонент ошибки
- ✅ API запросы с ошибками
- ✅ Браузер и ОС пользователя
- ✅ URL страницы где произошла ошибка
- ✅ Session Replay (видео действий пользователя до ошибки)

## Дашборд Sentry

В веб-панели Sentry ты увидишь:
- Количество ошибок
- Какие пользователи затронуты
- В каком браузере/ОС произошла ошибка
- Полный стектрейс
- История действий пользователя (breadcrumbs)
- Session replay (запись экрана)

## Email уведомления

Sentry автоматически отправляет email когда:
- Новая ошибка появилась
- Ошибка возникает слишком часто
- Ошибка появилась в production после деплоя

## Production настройки

Для production измени в `settings.py`:
```python
traces_sample_rate=0.1,  # Только 10% запросов отслеживаем (экономия квоты)
profiles_sample_rate=0.1,
```

Для development можно поставить `1.0` (100%) чтобы видеть все ошибки.
