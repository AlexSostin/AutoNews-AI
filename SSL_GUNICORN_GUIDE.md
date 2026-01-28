# ================================================
# ПОЛНОЕ РУКОВОДСТВО: SSL и Gunicorn для продакшена
# ================================================

## 📋 СОДЕРЖАНИЕ
1. SSL Сертификаты (Let's Encrypt)
2. Настройка Gunicorn
3. Тестирование
4. Мониторинг и устранение неполадок

---

## 🔐 ЧАСТЬ 1: SSL СЕРТИФИКАТЫ

### Что такое SSL/TLS?
SSL (Secure Sockets Layer) / TLS (Transport Layer Security) - протоколы шифрования данных между клиентом и сервером. HTTPS = HTTP + SSL/TLS.

**Зачем нужен:**
- 🔒 Шифрование данных (пароли, личная информация)
- ✅ Доверие пользователей (зеленый замок в браузере)
- 📈 Лучший SEO рейтинг (Google требует HTTPS)
- 🚫 Защита от MITM атак

### Варианты получения SSL:

#### Вариант 1: Let's Encrypt (РЕКОМЕНДУЕТСЯ)
**Плюсы:**
- ✅ Бесплатно
- ✅ Автообновление каждые 90 дней
- ✅ Доверенный всеми браузерами
- ✅ Простая автоматизация

**Минусы:**
- ⚠️ Сертификат действует 90 дней (но автообновляется)
- ⚠️ Нужен публичный домен

**Установка (Windows PowerShell):**

```powershell
# 1. Убедитесь что DNS записи указывают на ваш сервер
# A record: yourdomain.com → IP_ВАШЕГО_СЕРВЕРА
# A record: www.yourdomain.com → IP_ВАШЕГО_СЕРВЕРА

# 2. Перейдите в папку backend
cd C:\Projects\Auto_News\backend

# 3. Запустите скрипт установки
.\setup-ssl.ps1 -Domain "yourdomain.com" -Email "admin@yourdomain.com"

# Для тестирования (не тратит лимиты Let's Encrypt):
.\setup-ssl.ps1 -Domain "yourdomain.com" -Email "admin@yourdomain.com" -Staging
```

**Что делает скрипт:**
1. Создает временный Nginx для ACME challenge
2. Запрашивает сертификат у Let's Encrypt
3. Копирует сертификаты в `nginx/ssl/`
4. Обновляет nginx.conf с вашим доменом
5. Готов к production запуску!

**Ручная установка (если скрипт не работает):**

```powershell
# Создайте директории
mkdir nginx\ssl
mkdir certbot\conf
mkdir certbot\www

# Запустите временный веб-сервер для верификации
docker run -d --name nginx_temp -p 80:80 `
    -v ${PWD}\certbot\www:/var/www/certbot `
    nginx:alpine

# Получите сертификат
docker run --rm `
    -v ${PWD}\certbot\conf:/etc/letsencrypt `
    -v ${PWD}\certbot\www:/var/www/certbot `
    certbot/certbot certonly --webroot `
    -w /var/www/certbot `
    -d yourdomain.com `
    -d www.yourdomain.com `
    --email admin@yourdomain.com `
    --agree-tos --no-eff-email

# Остановите временный сервер
docker stop nginx_temp
docker rm nginx_temp

# Скопируйте сертификаты
copy certbot\conf\live\yourdomain.com\fullchain.pem nginx\ssl\
copy certbot\conf\live\yourdomain.com\privkey.pem nginx\ssl\
```

#### Вариант 2: Cloudflare (для проксированных сайтов)

Если используете Cloudflare:
1. В Cloudflare Dashboard → SSL/TLS → Origin Server
2. Create Certificate → Generate
3. Скопируйте сертификат и ключ в `nginx/ssl/`
4. Cloudflare автоматически терминирует SSL перед вашим сервером

**Плюсы:**
- ✅ Бесплатный SSL
- ✅ DDoS защита
- ✅ CDN
- ✅ Сертификат на 15 лет

**Минусы:**
- ⚠️ Трафик идет через Cloudflare
- ⚠️ Нужен Cloudflare аккаунт

#### Вариант 3: Коммерческий SSL (GoDaddy, Namecheap и т.д.)

1. Купите SSL сертификат (~$10-100/год)
2. Получите файлы: certificate.crt и private.key
3. Скопируйте в `nginx/ssl/`:
   - fullchain.pem = certificate.crt
   - privkey.pem = private.key

### Проверка SSL после установки:

```powershell
# Проверьте что файлы существуют
ls nginx\ssl\

# Должны быть:
# - fullchain.pem (публичный сертификат + цепочка)
# - privkey.pem (приватный ключ)

# Проверьте содержимое сертификата
docker run --rm -v ${PWD}\nginx\ssl:/ssl alpine/openssl `
    x509 -in /ssl/fullchain.pem -text -noout

# Проверьте срок действия
docker run --rm -v ${PWD}\nginx\ssl:/ssl alpine/openssl `
    x509 -in /ssl/fullchain.pem -noout -dates
```

### Автообновление SSL (включено в docker-compose.prod.yml):

Certbot контейнер автоматически обновляет сертификаты:
- Проверяет каждые 12 часов
- Обновляет за 30 дней до истечения
- Nginx автоматически перезагружает конфиг каждые 6 часов

**Ручное обновление:**
```powershell
docker-compose -f docker-compose.prod.yml run --rm certbot renew
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

---

## ⚡ ЧАСТЬ 2: GUNICORN (Production WSGI Server)

### Что такое Gunicorn?

**Gunicorn** (Green Unicorn) - production-ready WSGI HTTP сервер для Python.

### Зачем нужен? (почему не runserver)

| Характеристика | runserver | Gunicorn |
|---------------|-----------|----------|
| Назначение | Development | Production |
| Производительность | Медленно | Быстро (многопоточность) |
| Стабильность | ⚠️ Падает при ошибках | ✅ Restart workers |
| Безопасность | ❌ Уязвимости | ✅ Защищен |
| Workers | 1 поток | 4+ потоков |
| Подходит для прода | ❌ НЕТ | ✅ ДА |

**runserver** - это ТОЛЬКО для разработки! Django документация прямо запрещает использовать его в продакшене.

### Установка Gunicorn:

Уже добавлен в `Dockerfile.prod`:
```dockerfile
RUN pip install --no-cache-dir gunicorn
```

### Конфигурация (gunicorn.conf.py):

Создан файл `backend/gunicorn.conf.py` с оптимальными настройками:

```python
# Основные параметры:
bind = "0.0.0.0:8001"                           # Адрес и порт
workers = multiprocessing.cpu_count() * 2 + 1  # Кол-во процессов
timeout = 120                                    # Таймаут запроса
```

**Количество workers:**
- Формула: `(CPU cores * 2) + 1`
- Для 2 CPU: 5 workers
- Для 4 CPU: 9 workers
- Для 8 CPU: 17 workers

**Worker classes:**
- `sync` (по умолчанию) - стандартные синхронные workers
- `gevent` - асинхронные workers (для WebSockets)
- `eventlet` - асинхронные workers
- `gthread` - thread-based workers

### Команды запуска:

**Простой запуск:**
```bash
gunicorn auto_news_site.wsgi:application --bind 0.0.0.0:8001 --workers 4
```

**С конфиг файлом (РЕКОМЕНДУЕТСЯ):**
```bash
gunicorn auto_news_site.wsgi:application -c gunicorn.conf.py
```

**Через docker-compose (уже настроено):**
```yaml
command: >
  sh -c "python manage.py migrate &&
         python manage.py collectstatic --noinput &&
         gunicorn auto_news_site.wsgi:application -c gunicorn.conf.py"
```

### Логирование:

Gunicorn пишет логи в stdout/stderr, Docker собирает их:

```powershell
# Просмотр логов
docker-compose -f docker-compose.prod.yml logs backend

# Следить за логами в реальном времени
docker-compose -f docker-compose.prod.yml logs -f backend

# Фильтр по ошибкам
docker-compose -f docker-compose.prod.yml logs backend | Select-String "ERROR"
```

### Управление workers:

**Restart workers (без даунтайма):**
```powershell
docker-compose -f docker-compose.prod.yml exec backend kill -HUP 1
```

**Graceful shutdown:**
```powershell
docker-compose -f docker-compose.prod.yml exec backend kill -TERM 1
```

### Оптимизация производительности:

**1. Настройка workers:**
```python
# gunicorn.conf.py
workers = 4                    # Базовое значение
max_requests = 1000            # Перезапуск после 1000 запросов (защита от утечек памяти)
max_requests_jitter = 50       # Рандомизация перезапуска
timeout = 120                  # Таймаут для долгих запросов
```

**2. Keep-Alive:**
```python
keepalive = 5  # Держать соединения 5 секунд
```

**3. Memory limits (в docker-compose.prod.yml):**
```yaml
backend:
  deploy:
    resources:
      limits:
        memory: 2G
      reservations:
        memory: 512M
```

### Мониторинг:

**Проверка работающих процессов:**
```powershell
docker-compose -f docker-compose.prod.yml exec backend ps aux
```

**Статистика использования:**
```powershell
docker stats autonews_backend_prod
```

**Health check:**
```powershell
curl http://localhost:8001/health/
```

---

## 🧪 ЧАСТЬ 3: ТЕСТИРОВАНИЕ

### 1. Локальное тестирование (до деплоя):

```powershell
cd C:\Projects\Auto_News\backend

# Создайте .env.prod
copy .env.prod.example .env.prod
# Отредактируйте .env.prod

# Запустите production stack локально
docker-compose -f docker-compose.prod.yml up -d

# Проверьте логи
docker-compose -f docker-compose.prod.yml logs -f

# Тесты:
# 1. Backend API: http://localhost:8001/api/v1/articles/
# 2. Frontend: http://localhost:3000
# 3. Admin: http://localhost:8001/admin/
```

### 2. Тестирование SSL (после деплоя):

**Проверка сертификата:**
```powershell
# SSL Labs (полный анализ безопасности)
# Откройте: https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com

# Быстрая проверка в браузере
curl -I https://yourdomain.com

# Детальная информация
docker run --rm alpine/openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

**Ожидаемый результат:**
- ✅ A+ рейтинг на SSL Labs
- ✅ TLS 1.2 и 1.3
- ✅ Зеленый замок в браузере
- ✅ Срок действия ~90 дней

### 3. Load Testing (нагрузочное тестирование):

**Установите Apache Bench:**
```powershell
# Windows: скачайте Apache httpd
# Или используйте Docker:

# Тест 1: 1000 запросов, 10 одновременных
docker run --rm --network host jordi/ab `
    -n 1000 -c 10 https://yourdomain.com/

# Тест 2: API endpoint
docker run --rm --network host jordi/ab `
    -n 500 -c 5 https://api.yourdomain.com/api/v1/articles/
```

**Ожидаемые результаты:**
- Время отклика: < 200ms для статики
- Время отклика: < 500ms для API
- 0% ошибок

### 4. Security Testing:

```powershell
# Проверка заголовков безопасности
curl -I https://yourdomain.com | Select-String "Strict-Transport-Security|X-Frame-Options|X-Content-Type-Options"

# Должно быть:
# Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
```

---

## 🔧 ЧАСТЬ 4: TROUBLESHOOTING

### Проблема: "Connection refused" при запуске

**Причина:** Backend не запустился или Gunicorn не слушает порт.

**Решение:**
```powershell
# Проверьте логи
docker-compose -f docker-compose.prod.yml logs backend

# Проверьте что порт открыт внутри контейнера
docker-compose -f docker-compose.prod.yml exec backend netstat -tuln | grep 8001

# Проверьте статус процесса
docker-compose -f docker-compose.prod.yml exec backend ps aux | grep gunicorn
```

### Проблема: SSL сертификат не получается

**Причина 1:** DNS не указывает на сервер
```powershell
# Проверьте DNS
nslookup yourdomain.com

# Должен вернуть IP вашего сервера
```

**Причина 2:** Порт 80 закрыт файрволом
```powershell
# Windows: откройте порт 80
New-NetFirewallRule -DisplayName "HTTP" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow

# Linux:
sudo ufw allow 80
```

**Причина 3:** Превышен лимит Let's Encrypt
- Используйте `--staging` режим для тестов
- Лимит: 5 сертификатов в неделю на домен

### Проблема: Gunicorn workers падают

**Причина:** Недостаточно памяти или ошибки в коде.

**Решение:**
```powershell
# Увеличьте таймаут
# В gunicorn.conf.py:
timeout = 300  # 5 минут

# Уменьшите workers
workers = 2

# Проверьте память
docker stats autonews_backend_prod

# Проверьте логи на ошибки
docker-compose -f docker-compose.prod.yml logs backend | Select-String "ERROR"
```

### Проблема: Медленная работа сайта

**Диагностика:**
```powershell
# 1. Проверьте нагрузку на CPU
docker stats

# 2. Проверьте запросы к БД (в Django shell)
docker-compose -f docker-compose.prod.yml exec backend python manage.py shell
>>> from django.db import connection
>>> len(connection.queries)  # Количество запросов

# 3. Включите кэширование (Redis уже настроен)
```

**Оптимизация:**
1. Добавьте индексы в БД
2. Включите Redis кэш
3. Используйте CDN для статики
4. Оптимизируйте запросы (select_related, prefetch_related)

### Проблема: 502 Bad Gateway

**Причина:** Nginx не может подключиться к backend.

**Решение:**
```powershell
# Проверьте что backend работает
docker-compose -f docker-compose.prod.yml ps

# Проверьте связь между контейнерами
docker-compose -f docker-compose.prod.yml exec nginx ping backend

# Проверьте конфиг Nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# Перезапустите Nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

---

## ✅ ЧЕКЛИСТ ПЕРЕД ЗАПУСКОМ:

- [ ] DNS записи настроены (A record → IP сервера)
- [ ] Порты 80, 443 открыты в файрволе
- [ ] SSL сертификаты установлены (`nginx/ssl/` не пустая)
- [ ] `.env.prod` создан с реальными значениями
- [ ] SECRET_KEY сгенерирован новый
- [ ] Пароль БД изменен на надежный
- [ ] ALLOWED_HOSTS содержит ваши домены
- [ ] gunicorn.conf.py настроен
- [ ] nginx.conf содержит ваш домен (не yourdomain.com)
- [ ] Протестировано локально
- [ ] Созданы бэкапы данных

---

## 🚀 ФИНАЛЬНЫЙ ЗАПУСК:

```powershell
# 1. Перейдите в папку backend
cd C:\Projects\Auto_News\backend

# 2. Остановите dev версию (если запущена)
docker-compose down

# 3. Создайте .env.prod (если еще не создали)
copy .env.prod.example .env.prod
# ОТРЕДАКТИРУЙТЕ .env.prod!

# 4. Установите SSL сертификаты
.\setup-ssl.ps1 -Domain "yourdomain.com" -Email "admin@yourdomain.com"

# 5. Запустите production stack
docker-compose -f docker-compose.prod.yml up -d

# 6. Проверьте логи
docker-compose -f docker-compose.prod.yml logs -f

# 7. Запустите миграции (если нужно)
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# 8. Создайте суперпользователя
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# 9. Проверьте сайт
# - https://yourdomain.com
# - https://api.yourdomain.com/admin/
# - https://api.yourdomain.com/api/v1/articles/
```

---

## 📚 ПОЛЕЗНЫЕ КОМАНДЫ:

```powershell
# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f

# Рестарт сервисов
docker-compose -f docker-compose.prod.yml restart

# Остановка
docker-compose -f docker-compose.prod.yml stop

# Полная остановка с удалением контейнеров
docker-compose -f docker-compose.prod.yml down

# Обновление после изменений в коде
docker-compose -f docker-compose.prod.yml up -d --build

# Бэкап базы данных
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U autonews_prod_user autonews_prod > backup.sql

# Восстановление базы данных
cat backup.sql | docker-compose -f docker-compose.prod.yml exec -T postgres psql -U autonews_prod_user autonews_prod
```

---

## 📞 ПОДДЕРЖКА

Если что-то не работает:

1. **Проверьте логи:** `docker-compose -f docker-compose.prod.yml logs -f`
2. **Проверьте статус:** `docker-compose -f docker-compose.prod.yml ps`
3. **Проверьте сеть:** `docker network inspect backend_autonews_network_prod`
4. **Проверьте конфиги:** файлы nginx.conf, gunicorn.conf.py, .env.prod

**Частые ошибки:**
- "Permission denied" → права доступа к файлам/директориям
- "Connection refused" → сервис не запущен или порт неправильный
- "502 Bad Gateway" → backend недоступен для nginx
- "Certificate error" → неправильные пути к сертификатам

**Документация:**
- Gunicorn: https://docs.gunicorn.org/
- Let's Encrypt: https://letsencrypt.org/docs/
- Nginx: https://nginx.org/en/docs/
- Django Deployment: https://docs.djangoproject.com/en/5.0/howto/deployment/

---

**Создано:** 2026-01-19  
**Проект:** AutoNews  
**Версия:** Production 1.0
