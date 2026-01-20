# 🚀 Railway Deployment Guide - Auto News

## 📋 Что уже готово ✅

### Безопасность (100% готова):
- ✅ `SECRET_KEY` из переменных окружения
- ✅ `DEBUG=False` по умолчанию
- ✅ `ALLOWED_HOSTS` настроен
- ✅ HTTPS редирект (SECURE_SSL_REDIRECT=True)
- ✅ Безопасные cookies (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE)
- ✅ HSTS с годовым сроком
- ✅ CORS ограничен (только разрешённые домены)
- ✅ SecurityMiddleware активирован
- ✅ XFrameOptionsMiddleware против clickjacking
- ✅ CsrfViewMiddleware защита
- ✅ .gitignore настроен (никаких секретов в git)
- ✅ Sentry для отслеживания ошибок
- ✅ Rate limiting (100 req/hour для анонимных, 1000 для авторизованных)
- ✅ Лимит загрузки файлов (5MB)

---

## 🎯 ПОШАГОВАЯ ИНСТРУКЦИЯ

### ШАГ 1: Создать проекты в Railway

1. Зайти на [Railway.app](https://railway.app)
2. Создать **New Project** → **Empty Project**
3. Добавить 3 сервиса:
   - **PostgreSQL** (Database)
   - **Backend** (Django)
   - **Frontend** (Next.js)

---

### ШАГ 2: Настроить PostgreSQL

1. Нажать **+ New** → **Database** → **PostgreSQL**
2. Railway автоматически создаст базу данных
3. Скопировать переменную `DATABASE_URL` (она появится автоматически)
4. **ВАЖНО**: Запомнить эту переменную для Backend

---

### ШАГ 3: Настроить Backend (Django)

#### 3.1 Подключить репозиторий:
1. Нажать **+ New** → **GitHub Repo**
2. Выбрать ваш репозиторий `Auto_News`
3. В **Root Directory** указать: `backend`

#### 3.2 Установить переменные окружения:

Перейти в **Variables** и добавить:

```env
# 🔐 КРИТИЧЕСКИ ВАЖНО - Ваш новый SECRET_KEY:
SECRET_KEY=0j1$0a!+e$530aflz3kc9g(*_9*=i+^lz2cuggcdv-9mk)0_9r

# 🚨 ОБЯЗАТЕЛЬНО False в production:
DEBUG=False

# 🌐 Домены (после получите их от Railway):
ALLOWED_HOSTS=.railway.app

# 🗄️ База данных (скопируйте из PostgreSQL сервиса):
DATABASE_URL=postgresql://postgres:...@postgres.railway.internal:5432/railway

# 🔗 CORS (замените на реальный URL фронтенда):
CORS_ALLOWED_ORIGINS=https://your-frontend.up.railway.app

# 🤖 API ключи:
GROQ_API_KEY=ваш_ключ_от_groq

# 📊 Sentry:
SENTRY_DSN=https://87d896ae25bc56da5e80115c2c1364da@o4510742370648064.ingest.de.sentry.io/4510742712746064
ENVIRONMENT=production
```

#### 3.3 Настроить порт:
В **Settings** → **Networking**:
- **Port**: `8001`

#### 3.4 Deploy команды (Railway определит автоматически из Dockerfile):
Если нужно переопределить, в **Settings** → **Deploy**:
```bash
# Build Command:
pip install -r requirements.txt

# Start Command:
python manage.py collectstatic --noinput && python manage.py migrate --noinput && daphne -b 0.0.0.0 -p 8001 auto_news_site.asgi:application
```

---

### ШАГ 4: Настроить Frontend (Next.js)

#### 4.1 Подключить репозиторий:
1. Нажать **+ New** → **GitHub Repo**
2. Выбрать тот же репозиторий `Auto_News`
3. В **Root Directory** указать: `frontend-next`

#### 4.2 Установить переменные окружения:

Перейти в **Variables** и добавить:

```env
# 🌐 Node окружение:
NODE_ENV=production

# 🔗 API URL (замените на реальный URL бэкенда):
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app/api/v1

# 🔗 Для серверного рендеринга (внутренний адрес в Railway):
NEXT_PUBLIC_API_URL_SERVER=http://backend:8001/api/v1
API_INTERNAL_URL=http://backend:8001/api/v1

# 📁 Media URL (изображения):
NEXT_PUBLIC_MEDIA_URL=https://your-backend.up.railway.app

# 🌍 URL сайта:
NEXT_PUBLIC_SITE_URL=https://your-frontend.up.railway.app

# 📊 Sentry:
NEXT_PUBLIC_SENTRY_DSN=https://87d896ae25bc56da5e80115c2c1364da@o4510742370648064.ingest.de.sentry.io/4510742712746064
```

#### 4.3 Настроить порт:
В **Settings** → **Networking**:
- **Port**: `3000`

---

### ШАГ 5: Получить URLs и обновить переменные

После деплоя Railway предоставит URLs:
- Backend: `https://auto-news-backend-production.up.railway.app`
- Frontend: `https://auto-news-frontend-production.up.railway.app`

**ВАЖНО**: Обновить переменные окружения с реальными URLs:

#### Backend:
```env
ALLOWED_HOSTS=auto-news-backend-production.up.railway.app,.railway.app
CORS_ALLOWED_ORIGINS=https://auto-news-frontend-production.up.railway.app
```

#### Frontend:
```env
NEXT_PUBLIC_API_URL=https://auto-news-backend-production.up.railway.app/api/v1
NEXT_PUBLIC_MEDIA_URL=https://auto-news-backend-production.up.railway.app
NEXT_PUBLIC_SITE_URL=https://auto-news-frontend-production.up.railway.app
```

---

### ШАГ 6: Создать суперпользователя

1. Зайти в **Backend сервис**
2. Открыть **Console** (Terminal)
3. Выполнить:
```bash
python manage.py createsuperuser
```

Ввести:
- Username: `admin`
- Email: `ваш@email.com`
- Password: `сильный_пароль_123!`

---

### ШАГ 7: Проверить работу

#### Тест 1: Backend API
```bash
curl https://your-backend.up.railway.app/api/v1/articles/
```
Должен вернуть JSON с артиклями.

#### Тест 2: Django Admin
Открыть: `https://your-backend.up.railway.app/admin/`
Войти с созданным суперпользователем.

#### Тест 3: Frontend
Открыть: `https://your-frontend.up.railway.app`
Должен загрузиться сайт.

#### Тест 4: Sentry
1. Открыть [Sentry Dashboard](https://o4510742370648064.sentry.io/issues/)
2. Вызвать ошибку на сайте (например, открыть несуществующую страницу)
3. Проверить, что ошибка появилась в Sentry

---

## 🆘 ЧАСТЫЕ ПРОБЛЕМЫ

### ❌ "DisallowedHost at /"
**Причина**: Неправильный ALLOWED_HOSTS  
**Решение**: Добавить Railway URL в ALLOWED_HOSTS:
```env
ALLOWED_HOSTS=.railway.app,your-domain.railway.app
```

### ❌ "CORS error"
**Причина**: Frontend URL не в CORS_ALLOWED_ORIGINS  
**Решение**: Добавить точный URL фронтенда:
```env
CORS_ALLOWED_ORIGINS=https://your-frontend.up.railway.app
```

### ❌ "Database connection error"
**Причина**: Неправильный DATABASE_URL  
**Решение**: Скопировать DATABASE_URL из PostgreSQL сервиса в Backend переменные.

### ❌ "Static files not found"
**Причина**: collectstatic не выполнился  
**Решение**: Проверить логи деплоя, убедиться что команда выполнилась:
```bash
python manage.py collectstatic --noinput
```

---

## 💰 СТОИМОСТЬ

Railway Hobby Plan:
- **$5/месяц** - включает $5 кредитов
- **Usage-based billing** после исчерпания кредитов
- **Примерно $10-15/месяц** для вашего проекта:
  - PostgreSQL: ~$3-5
  - Backend: ~$3-5
  - Frontend: ~$3-5

**Первый месяц**: $5 (trial credits)

---

## 📊 МОНИТОРИНГ

### 1. Railway Dashboard:
- CPU Usage
- Memory Usage
- Bandwidth
- Deployment logs

### 2. Sentry Dashboard:
- [Issues](https://o4510742370648064.sentry.io/issues/)
- Performance
- Session Replay

---

## 🔄 ОБНОВЛЕНИЕ КОДА

После изменений в коде:

1. **Commit и Push в GitHub**:
```bash
git add .
git commit -m "Update: описание изменений"
git push origin main
```

2. **Railway автоматически**:
- Заметит изменения в GitHub
- Пересоберёт проект
- Задеплоит новую версию

**Время деплоя**: 2-5 минут

---

## 🌐 ПОДКЛЮЧЕНИЕ ДОМЕНА (опционально)

Когда купите домен:

1. В Railway сервисе → **Settings** → **Networking** → **Custom Domain**
2. Добавить домен: `example.com`
3. Railway покажет CNAME record
4. У регистратора домена (Namecheap, Porkbun) добавить CNAME:
   ```
   Type: CNAME
   Name: @
   Value: <railway-provided-value>
   ```

5. Обновить переменные окружения:
```env
# Backend:
ALLOWED_HOSTS=.railway.app,example.com

# Frontend:
NEXT_PUBLIC_SITE_URL=https://example.com
```

---

## ✅ ФИНАЛЬНЫЙ ЧЕКЛИСТ

Перед тем как считать деплой завершённым:

- [ ] PostgreSQL сервис работает
- [ ] Backend деплоится без ошибок
- [ ] Frontend деплоится без ошибок
- [ ] Все переменные окружения установлены
- [ ] ALLOWED_HOSTS обновлён с Railway URLs
- [ ] CORS_ALLOWED_ORIGINS обновлён с Railway URLs
- [ ] Суперпользователь создан
- [ ] Django Admin открывается
- [ ] Авторизация работает
- [ ] API возвращает данные
- [ ] Фронтенд загружается и показывает статьи
- [ ] Sentry получает ошибки
- [ ] Статические файлы (CSS/JS) загружаются
- [ ] Изображения отображаются

---

## 📞 ПОДДЕРЖКА

Если что-то пошло не так:

1. **Railway Logs**: В каждом сервисе есть вкладка "Logs"
2. **Sentry Errors**: [Dashboard](https://o4510742370648064.sentry.io/issues/)
3. **Railway Discord**: [Community](https://discord.gg/railway)
4. **Документация**: [Railway Docs](https://docs.railway.app)

---

**🎉 Удачи с деплоем! Всё готово к production!**
