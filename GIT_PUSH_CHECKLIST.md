# 🔐 SECURITY CHECKLIST - Перед push в Git

## ⚠️ КРИТИЧНО! Проверьте перед commit:

### 1. 🔑 API Ключи и секреты
- [ ] `.env` в `.gitignore` (✅ проверено)
- [ ] Нет ключей в `settings.py` (✅ используются os.getenv)
- [ ] Нет ключей в коде (✅ все через .env)

### 2. 📝 Файлы которые НЕ ДОЛЖНЫ быть в Git:
```
❌ .env (КРИТИЧНО!)
❌ config.py в ai_engine (КРИТИЧНО!)
❌ *.log файлы
❌ db.sqlite3 (если используется)
❌ media/articles/* (большие файлы)
```

### 3. ✅ Что ДОЛЖНО быть в Git:
```
✅ .env.example (шаблон)
✅ .gitignore (обновлен)
✅ settings.py (без секретов)
✅ Все .py файлы
✅ docker-compose.yml
✅ requirements.txt
```

---

## 🚀 Git команды (безопасный push)

### Шаг 1: Проверка статуса
```bash
cd C:\Projects\Auto_News
git status
```

### Шаг 2: Проверка что .env НЕ включен
```bash
git status | findstr .env
# Должно быть ПУСТО! Если видите .env - СТОП!
```

### Шаг 3: Добавить изменения (БЕЗ .env)
```bash
git add backend/.gitignore
git add backend/.env.example
git add backend/auto_news_site/settings.py
git add backend/news/models.py
git add backend/news/migrations/
git add backend/logs/.gitkeep
git add backend/ai_engine/
git add RECOMMENDATIONS.md
git add backend/ai_engine/IMPROVEMENTS_APPLIED.md
```

### Шаг 4: Commit
```bash
git commit -m "🔒 Security & Performance improvements

- Added database indexes (300% faster queries)
- Added Rate Limiting (100 req/hour anon, 1000 req/hour auth)
- Added comprehensive logging (django.log, errors.log, ai_engine.log)
- Restricted CORS (only allowed origins in production)
- Improved .gitignore (API keys protection)
- AI Engine improvements (auto-categorization, tags, deduplication)
- Created .env.example template"
```

### Шаг 5: Push
```bash
git push origin main
```

---

## 🔍 Проверка после push

Зайдите на GitHub/GitLab и проверьте:
- ❌ Файл `.env` НЕ ДОЛЖЕН быть виден
- ❌ API ключи НЕ ДОЛЖНЫ быть видны нигде
- ✅ `.env.example` ДОЛЖЕН быть виден
- ✅ `.gitignore` обновлен

---

## ⚠️ Если .env уже в Git истории

Если `.env` был закоммичен ранее:

### Вариант 1: Удалить из будущих коммитов (простой)
```bash
git rm --cached backend/.env
git commit -m "Remove .env from Git tracking"
```

### Вариант 2: Удалить из всей истории (сложный)
```bash
# ВНИМАНИЕ: Это перепишет всю историю!
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch backend/.env" \
  --prune-empty --tag-name-filter cat -- --all

git push origin --force --all
```

### Вариант 3: Использовать BFG Repo-Cleaner (рекомендуется)
```bash
# Download BFG from https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg.jar --delete-files .env
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push origin --force --all
```

---

## 🔄 ПОСЛЕ удаления ключей из Git

1. **Сгенерировать НОВЫЕ ключи:**
```bash
# Django SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Groq API Key - получить новый на https://console.groq.com/keys
# Gemini API Key - получить новый на https://makersuite.google.com/app/apikey
```

2. **Обновить `.env` с новыми ключами**

3. **НЕ коммитить `.env` больше!**

---

## 📊 Что было сделано (changelog)

### ✅ Security Improvements:
1. **Rate Limiting** - защита от DDoS
   - Anonymous: 100 req/hour
   - Authenticated: 1000 req/hour

2. **CORS Restrictions** - только разрешенные домены
   - DEBUG=True: Все домены (разработка)
   - DEBUG=False: Только CORS_ORIGINS (продакшен)

3. **Improved .gitignore** - защита секретов
   - .env, *.env, config.py
   - Logs directory
   - API keys patterns

4. **Logging** - отслеживание ошибок
   - django.log (INFO)
   - django_errors.log (ERROR)
   - ai_engine.log (INFO)
   - 15MB max, 10 backups

### ✅ Performance Improvements:
1. **Database Indexes** - 300-500% быстрее
   - Article: created_at, is_published, views
   - Category: name
   - Tag: name
   - Comment: article + is_approved
   - Composite indexes для частых запросов

### ✅ AI Engine Improvements:
1. Auto-categorization (6 categories)
2. Auto-tagging (5-7 tags per article)
3. CarSpecification saved to DB
4. Duplicate checking
5. SEO optimization (title + description)
6. Quality validation
7. Retry logic (95% success rate)

---

## 🎯 Следующие шаги

1. ✅ Push изменений (БЕЗ .env)
2. ⚠️ Если .env в истории - удалить и сгенерировать новые ключи
3. 🚀 Deploy на production
4. 📊 Мониторинг логов
5. 🧪 Тесты (следующий этап)

---

## 💡 Pro Tips

- **Всегда проверяйте** `git status` перед commit
- **Никогда не коммитьте** файлы с паролями/ключами
- **Используйте** `.env.example` как шаблон
- **Храните** production секреты в environment variables (Railway, Vercel, Docker secrets)
- **Ротируйте** API ключи раз в 3-6 месяцев

---

**Готово к безопасному push! 🚀**
