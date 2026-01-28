# 🚀 Quick Start - Railway Deployment

## ⚡ БЫСТРЫЙ СТАРТ (5 минут)

### 1️⃣ PostgreSQL в Railway
1. Открыть [Railway](https://railway.app)
2. New Project → Add PostgreSQL
3. Скопировать `DATABASE_URL` (автоматически создастся)

---

### 2️⃣ Backend Service

**GitHub Repo**: Выбрать `Auto_News` → Root Directory: `backend`

**Variables** (скопировать все):
```env
SECRET_KEY=0j1$0a!+e$530aflz3kc9g(*_9*=i+^lz2cuggcdv-9mk)0_9r
DEBUG=False
ALLOWED_HOSTS=.railway.app
DATABASE_URL=<вставить из PostgreSQL>
CORS_ALLOWED_ORIGINS=<будет после создания фронтенда>
GROQ_API_KEY=<ваш ключ>
SENTRY_DSN=https://87d896ae25bc56da5e80115c2c1364da@o4510742370648064.ingest.de.sentry.io/4510742712746064
ENVIRONMENT=production
```

**Port**: `8001`

---

### 3️⃣ Frontend Service

**GitHub Repo**: Выбрать `Auto_News` → Root Directory: `frontend-next`

**Variables**:
```env
NODE_ENV=production
NEXT_PUBLIC_API_URL=<backend URL>/api/v1
NEXT_PUBLIC_API_URL_SERVER=http://backend:8001/api/v1
API_INTERNAL_URL=http://backend:8001/api/v1
NEXT_PUBLIC_MEDIA_URL=<backend URL>
NEXT_PUBLIC_SITE_URL=<frontend URL>
NEXT_PUBLIC_SENTRY_DSN=https://87d896ae25bc56da5e80115c2c1364da@o4510742370648064.ingest.de.sentry.io/4510742712746064
```

**Port**: `3000`

---

### 4️⃣ Получить URLs и обновить

После деплоя Railway даст URLs:
- Backend: `https://xxx.up.railway.app`
- Frontend: `https://yyy.up.railway.app`

**Обновить переменные:**

Backend:
```env
ALLOWED_HOSTS=xxx.up.railway.app,.railway.app
CORS_ALLOWED_ORIGINS=https://yyy.up.railway.app
```

Frontend:
```env
NEXT_PUBLIC_API_URL=https://xxx.up.railway.app/api/v1
NEXT_PUBLIC_MEDIA_URL=https://xxx.up.railway.app
NEXT_PUBLIC_SITE_URL=https://yyy.up.railway.app
```

---

### 5️⃣ Создать суперпользователя

Backend → Console:
```bash
python manage.py createsuperuser
```

---

## ✅ ГОТОВО!

Проверить:
- Frontend: `https://yyy.up.railway.app`
- Admin: `https://xxx.up.railway.app/admin/`
- API: `https://xxx.up.railway.app/api/v1/articles/`

---

## 📚 Полные инструкции:
- [RAILWAY_DEPLOY_GUIDE.md](RAILWAY_DEPLOY_GUIDE.md) - детальный гайд
- [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md) - чек-лист безопасности
- [SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md) - отчёт о безопасности

**💰 Цена**: ~$10-15/месяц
