# 🚀 Быстрый Старт: SSL + Gunicorn

## 📋 ЧТО СОЗДАНО:

### Файлы для SSL:
- ✅ `setup-ssl.sh` - скрипт для Linux/Mac
- ✅ `setup-ssl.ps1` - скрипт для Windows
- ✅ `docker-compose.prod.yml` - обновлен с Certbot

### Файлы для Gunicorn:
- ✅ `gunicorn.conf.py` - конфигурация
- ✅ `Dockerfile.prod` - production образ
- ✅ `requirements.txt` - добавлен gunicorn==23.0.0

### Документация:
- ✅ `SSL_GUNICORN_GUIDE.md` - ПОЛНОЕ руководство (читать обязательно!)

---

## ⚡ КРАТКАЯ ИНСТРУКЦИЯ:

### Шаг 1: SSL Сертификаты (Windows)

```powershell
cd C:\Projects\Auto_News\backend

# Замените на ваши данные!
.\setup-ssl.ps1 -Domain "yourdomain.com" -Email "admin@yourdomain.com"

# Для тестирования (не тратит лимиты):
.\setup-ssl.ps1 -Domain "yourdomain.com" -Email "admin@yourdomain.com" -Staging
```

**Что нужно ПЕРЕД запуском:**
1. ✅ DNS запись: `yourdomain.com` → IP вашего сервера
2. ✅ DNS запись: `www.yourdomain.com` → IP вашего сервера
3. ✅ Порты 80 и 443 открыты в файрволе

**Проверка DNS:**
```powershell
nslookup yourdomain.com
# Должен вернуть IP вашего сервера
```

### Шаг 2: Production конфигурация

```powershell
# Создайте .env.prod
copy .env.prod.example .env.prod

# Откройте и измените:
notepad .env.prod
```

**ОБЯЗАТЕЛЬНО измените:**
```env
SECRET_KEY=СГЕНЕРИРУЙТЕ_НОВЫЙ_КЛЮЧ  # см. ниже как генерировать
POSTGRES_PASSWORD=НАДЕЖНЫЙ_ПАРОЛЬ_16+_СИМВОЛОВ
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ORIGINS=https://yourdomain.com
NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api/v1
```

**Генерация SECRET_KEY:**
```powershell
docker run --rm python:3.13-slim python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Шаг 3: Запуск Production

```powershell
cd C:\Projects\Auto_News\backend

# Запуск всех сервисов (PostgreSQL + Redis + Django + Next.js + Nginx)
docker-compose -f docker-compose.prod.yml up -d

# Проверка логов
docker-compose -f docker-compose.prod.yml logs -f

# Создание суперпользователя
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

### Шаг 4: Проверка

```powershell
# Проверьте статус
docker-compose -f docker-compose.prod.yml ps

# Все должны быть "Up"

# Откройте в браузере:
# - https://yourdomain.com (frontend)
# - https://api.yourdomain.com/admin/ (Django admin)
# - https://api.yourdomain.com/api/v1/articles/ (API)
```

---

## 🔍 ЧТО ИЗМЕНИЛОСЬ:

### Gunicorn вместо runserver:

**БЫЛО (dev):**
```bash
python manage.py runserver 0.0.0.0:8001
```

**СТАЛО (prod):**
```bash
gunicorn auto_news_site.wsgi:application -c gunicorn.conf.py
```

**Преимущества:**
- ✅ 4+ worker процессов (многопоточность)
- ✅ Автоматический restart при сбоях
- ✅ Оптимизация памяти
- ✅ Production-ready безопасность

### SSL/HTTPS:

**БЫЛО (dev):**
```
http://localhost:8001
http://localhost:3000
```

**СТАЛО (prod):**
```
https://api.yourdomain.com
https://yourdomain.com
```

**Преимущества:**
- 🔒 Шифрование данных
- ✅ Доверие пользователей
- 📈 Лучший SEO
- ✅ Автообновление сертификатов

### Nginx как Reverse Proxy:

**БЫЛО (dev):**
```
Browser → Django (8001)
Browser → Next.js (3000)
```

**СТАЛО (prod):**
```
Browser (443) → Nginx → Django (8001)
Browser (443) → Nginx → Next.js (3000)
```

**Преимущества:**
- ✅ SSL терминация
- ✅ Static files caching
- ✅ Load balancing
- ✅ Security headers
- ✅ Rate limiting

---

## 📊 АРХИТЕКТУРА:

### Development:
```
┌─────────┐     ┌─────────────┐
│ Browser │────▶│ Django:8001 │
└─────────┘     └─────────────┘
     │          ┌──────────────┐
     └─────────▶│ Next.js:3000 │
                └──────────────┘
```

### Production:
```
┌─────────┐
│ Browser │
└────┬────┘
     │ HTTPS (443)
     ▼
┌─────────────────┐
│  Nginx:80,443   │─────SSL Termination
└────┬────┬───────┘
     │    │
     │    └──────▶┌──────────────┐
     │            │ Next.js:3000 │
     │            └──────────────┘
     │
     └───────────▶┌─────────────────┐
                  │ Gunicorn:8001   │
                  │ (4 workers)     │
                  └────┬────────────┘
                       │
                  ┌────▼─────┐
                  │PostgreSQL│
                  └──────────┘
```

---

## 🛠️ УПРАВЛЕНИЕ:

### Команды production:

```powershell
# Запуск
docker-compose -f docker-compose.prod.yml up -d

# Остановка
docker-compose -f docker-compose.prod.yml stop

# Перезапуск
docker-compose -f docker-compose.prod.yml restart

# Логи
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f nginx

# Обновление кода
docker-compose -f docker-compose.prod.yml up -d --build

# Миграции БД
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Django shell
docker-compose -f docker-compose.prod.yml exec backend python manage.py shell

# Создать суперпользователя
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# Бэкап БД
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U autonews_prod_user autonews_prod > backup_$(date +%Y%m%d).sql
```

### Мониторинг:

```powershell
# Статус контейнеров
docker-compose -f docker-compose.prod.yml ps

# Использование ресурсов
docker stats

# Проверка Gunicorn workers
docker-compose -f docker-compose.prod.yml exec backend ps aux | grep gunicorn

# Проверка Nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# Health check
curl https://api.yourdomain.com/health/
```

---

## ⚠️ ВАЖНЫЕ ЗАМЕЧАНИЯ:

### 1. Безопасность:

- ❌ **НИКОГДА** не коммитьте `.env.prod` в git
- ❌ **НИКОГДА** не используйте дефолтные пароли
- ✅ Используйте сложные пароли (16+ символов)
- ✅ Регулярно обновляйте зависимости
- ✅ Включите мониторинг (Sentry, Prometheus)

### 2. Бэкапы:

**База данных (каждый день):**
```powershell
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U autonews_prod_user autonews_prod > backup_$(Get-Date -Format "yyyyMMdd").sql
```

**Media файлы (каждую неделю):**
```powershell
docker cp autonews_backend_prod:/app/media ./media_backup_$(Get-Date -Format "yyyyMMdd")
```

### 3. SSL Сертификаты:

- ✅ Обновляются автоматически каждые 12 часов
- ✅ Действительны 90 дней
- ⚠️ Проверяйте срок: `docker-compose -f docker-compose.prod.yml logs certbot`

### 4. Производительность:

**Оптимальные настройки для разных нагрузок:**

**Малая (< 1000 пользователей/день):**
```python
# gunicorn.conf.py
workers = 2
```

**Средняя (1000-10000 пользователей/день):**
```python
# gunicorn.conf.py
workers = 4
```

**Высокая (> 10000 пользователей/день):**
```python
# gunicorn.conf.py
workers = 8
# + добавьте Redis кэш
# + добавьте CDN
```

---

## 📚 ДОПОЛНИТЕЛЬНО:

### Читать обязательно:
- 📖 [SSL_GUNICORN_GUIDE.md](SSL_GUNICORN_GUIDE.md) - ПОЛНОЕ руководство
- 📖 [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) - чеклист перед запуском

### Полезные ссылки:
- Gunicorn Docs: https://docs.gunicorn.org/
- Let's Encrypt: https://letsencrypt.org/
- Django Deployment: https://docs.djangoproject.com/en/5.0/howto/deployment/
- Nginx: https://nginx.org/en/docs/

---

## ✅ ИТОГОВЫЙ ЧЕКЛИСТ:

- [ ] DNS настроен
- [ ] Порты 80, 443 открыты
- [ ] SSL сертификат получен (setup-ssl.ps1)
- [ ] .env.prod создан и настроен
- [ ] SECRET_KEY сгенерирован
- [ ] Пароли изменены
- [ ] gunicorn.conf.py проверен
- [ ] nginx.conf обновлен с доменом
- [ ] docker-compose.prod.yml проверен
- [ ] Production stack запущен
- [ ] Логи проверены (без ошибок)
- [ ] Сайт открывается через HTTPS
- [ ] Django admin доступен
- [ ] API работает
- [ ] Настроены бэкапы

---

**Готово! 🎉**

После выполнения всех шагов ваш сайт будет работать в production режиме с:
- ✅ HTTPS/SSL
- ✅ Gunicorn (4 workers)
- ✅ Nginx reverse proxy
- ✅ PostgreSQL
- ✅ Redis кэш
- ✅ Автообновление SSL
