# 💡 FreshMotors — Идеи и Планы

> Записная книжка для будущих улучшений. Добавляй идеи с датой!

---

## 📅 13 Марта 2026

### 🔬 Архитектурный аудит стека
>
> **Статус:** 💡 Аудит завершён, рекомендации записаны

После обновления `PROJECT_ARCHITECTURE.md` (2335+ тестов, 95 файлов, 46 AI модулей, 112+ эндпоинтов) провёл полный анализ стека. Ниже — конкретные действия, отсортированные по приоритету.

---

### 🔴 Критично — нужно сделать

#### 1. Backup Strategy (PostgreSQL)
> Сейчас: ничего. Railway может подвести, данные потеряются.

- [ ] **Automated daily pg_dump** → Cloudflare R2 (бесплатно 10 GB) или S3
- [ ] Celery Beat задача: `pg_dump` → сжатие → upload (ночью, 3 AM)
- [ ] Retention: 7 последних + 4 weekly
- [ ] Тест восстановления раз в месяц

**Сложность:** 🟢 Просто | **Время:** 2-3 часа | **Риск без этого:** 🔴 Критичный

#### 2. Celery Beat вместо threading.Timer
> Сейчас: RSS сканер на `threading.Timer` — умирает с процессом, нет retry, нет мониторинга.

- [ ] Заменить `threading.Timer` в `scheduler.py` на Celery periodic tasks
- [ ] Все периодические задачи (RSS scan, YouTube scan, auto-publish, daily reports) через `CELERY_BEAT_SCHEDULE`
- [ ] Мониторинг задач через `django-celery-results`
- [ ] Celery worker уже есть + Redis broker уже есть → минимальные изменения

**Сложность:** 🟡 Средне | **Время:** 4-6 часов | **Риск без этого:** 🟡 Нестабильность планировщика

#### 3. Sitemap + IndexNow
> Сейчас: команда `submit_to_google` есть, но нет автоматического sitemap.xml.

- [ ] Django `contrib.sitemaps` — автогенерация sitemap.xml (статьи, категории, бренды)
- [ ] **IndexNow** webhook при публикации → мгновенная индексация в Bing/Yandex
- [ ] Добавить `<lastmod>` в sitemap для приоритета свежего контента
- [ ] Разбивка на sitemap index (>50k URL → несколько файлов)

**Сложность:** 🟢 Просто | **Время:** 2-3 часа | **Риск без этого:** 🟡 SEO теряет потенциал

---

### 🟡 Важно — стоит сделать

#### 4. Консолидация дублирующих модулей
> 3 скорера, 2 SEO модуля, 2 spec-экстрактора с почти одинаковыми именами.

| Дубль | Файлы | Решение |
|-------|-------|---------|
| **Scoring** | `quality_scorer.py` + `ml_quality_scorer.py` + `scoring.py` | Объединить в `quality_scorer.py` (основной) + `ml_quality_scorer.py` (ML). `scoring.py` → удалить или alias |
| **SEO** | `seo.py` + `seo_helpers.py` | Merge: `seo.py` (A/B title generation) + `seo_helpers.py` (keyword extraction) → один `seo.py` |
| **Spec extraction** | `ai_engine/modules/specs_extractor.py` + `news/spec_extractor.py` | Определить "главный", второй → import-обёртка |
| **Content generation** | `content_generator.py` + `article_generator.py` | Проверить пересечение, `content_generator.py` скорее всего legacy |

- [ ] Фаза 1: Аудит — проверить какие модули реально вызываются в production
- [ ] Фаза 2: Объединение `seo.py` + `seo_helpers.py` (наименее рисковано)
- [ ] Фаза 3: Spec extractors — объединить тесты, потом код
- [ ] Фаза 4: Scoring — проверить кто вызывает `scoring.py`

**Сложность:** 🟡 Средне | **Время:** 2-3 часа на фазу | **Риск:** 🟢 Низкий (рефакторинг)

#### 5. Full-Text Search (PostgreSQL FTS или Meilisearch)
> Сейчас: поиск через `icontains` — медленно, нет fuzzy matching, нет autocomplete.

**Вариант A — PostgreSQL FTS (проще):**
- [ ] `SearchVector` + `SearchQuery` + `SearchRank` на `Article.title` + `Article.content`
- [ ] GIN index для скорости
- [ ] Не нужен внешний сервис, 0 затрат

**Вариант B — Meilisearch (лучше UX):**
- [ ] Instant search, typo-tolerance, faceted filtering
- [ ] Meilisearch Cloud (бесплатный tier) или self-host
- [ ] Отдельный индекс — не нагружает PostgreSQL

**Рекомендация:** Начать с **Вариант A** (1-2 часа), позже мигрировать на B.

**Сложность:** 🟢/🟡 | **Время:** 2-4 часа | **Влияние:** 🟢 UX + SEO

#### 6. APM / Performance Monitoring
> Сейчас: только Sentry для ошибок. Нет метрик скорости запросов, AI latency, DB performance.

- [ ] **Sentry Performance** (уже есть Sentry DSN — просто включить `traces_sample_rate`)
- [ ] Или **django-silk** для dev — профилирование SQL запросов, N+1 detection
- [ ] AI latency tracking уже есть в `provider_tracker.py` → вывести на dashboard

**Сложность:** 🟢 Просто | **Время:** 30 минут | **Влияние:** 🟡 Видимость проблем

---

### 🟢 Nice to have — можно позже

#### 7. AI Cost Dashboard
> Данные уже собираются в `provider_tracker.py`. Нужно только вывести.

- [ ] Новая страница в админке: `/admin/ai-costs/`
- [ ] Расход по дням: Gemini calls, Groq calls, total tokens
- [ ] Стоимость: Gemini ($0.075/1M input) vs Groq ($0.059/1M input)
- [ ] Прогноз месячных затрат

#### 8. Cleanup Management Commands
> 57 команд — половина одноразовые `fix_*` и `backfill_*` скрипты.

- [ ] Переместить одноразовые в `/scripts/` или удалить:
  - `fix_brand_names.py`, `fix_fuel_types.py`, `fix_rss_logos.py`, `fix_tag_groups.py`, `fix_video_embeds.py`
  - `backfill_authors.py`, `backfill_sources.py`, `backfill_seo_descriptions.py`
- [ ] Оставить production-used: `scan_rss_feeds`, `scan_youtube`, `sync_views`, `clean_summaries`, `telegram_daily_alert`, `verify_migrations`

#### 9. PWA + Web Push
> Уже указано в Ideas 25 февраля. Докопировать:

- [ ] `next-pwa` plugin + `manifest.json`
- [ ] Service Worker с cache-first для статей
- [ ] Web Push для breaking news (Telegram уже есть — добавить параллельно)

#### 10. Internal Linking (SEO)
> Уже указано в Ideas 25 февраля. Уточнение:

- [ ] `seo_linker.py` уже существует в модулях! Проверить его статус.
- [ ] Автоматически добавлять 2-3 ссылки на связанные статьи при генерации
- [ ] Использовать `content_recommender.py` TF-IDF для поиска связанных статей

---

### 📊 Актуальная статистика (13 марта 2026)

| Метрика | Значение |
|---------|----------|
| Python тесты | 2335+ (95 файлов) |
| E2E Playwright | 45 тестов (6 spec файлов) |
| API endpoints | 112+ |
| Admin pages | 34+ |
| AI modules | 46 |
| Management commands | 57+ |
| AI providers | Gemini (complex) + Groq (lightweight via `get_light_provider()`) |
| Django | 6.0.3 / DRF 3.15.2 |
| Next.js | 16.1.3 |
| Python | 3.13.12 |

---

## 📅 4 Марта 2026

### ✅ Реализовано сегодня

> **Статус:** ✅ Завершено

- [x] **Infinite Scroll — полный контент** — `next_article` API теперь использует `ArticleDetailSerializer` (вместо `ArticleListSerializer`). Исправлен пустой контент у 2-5 статей в скролле.
- [x] **Browse All button при раннем Skip** — кнопка теперь показывается при любом `phase === 'done'`, не только при `articles.length >= MAX_ARTICLES`. Устранён тупик при раннем пропуске.
- [x] **Scroll Anchoring в футере** — при загрузке новой статьи пока пользователь в футере (рейтинг/комментарии) — viewport не съезжает. Реализован через `getBoundingClientRect` + `requestAnimationFrame`.
- [x] **NewArticleToast** — если пользователь >50% в футере и сработал sentinel — показывается тост вместо preview-карточки. Кнопки: Show (прыжок к новой статье) / Dismiss.
- [x] **BackToTop Smart Button** — одиночный клик = начало текущей статьи (по `data-article-slug`), двойной = самый верх. Custom event `article-active-slug` для связи без prop drilling.
- [x] **Analytics 500 fix** — `AnalyticsExtraStatsAPIView` теперь возвращает частичный ответ при ошибке вместо краша. Каждый блок обёрнут в отдельный try/except.
- [x] **Docker backend fix** — `RUNNING_IN_DOCKER=1` в `docker-compose.yml` предотвращает загрузку `.env.local` внутри контейнера (DB_HOST 127.0.0.1 vs postgres).

---

## 📅 27 Февраля 2026

### ✅ Реализовано сегодня
>
> **Статус:** ✅ Завершено

- [x] **Entity Mismatch Fix** — исправлена критическая ошибка путаницы названий авто в AI-генерации:
  - Функция `clean_source_title` — очистка RSS заголовков от метаданных (цены, дальность, emoji, «overview», pipe-separated суффиксы)
  - Исправлен `_extract_model_name` — расширены суффиксы, cleanup для цен, единиц измерения, emoji
  - Интеграция `clean_source_title` в `extract_entities` для правильного entity anchoring
  - Теперь AI правильно использует «LEOPARD 5» вместо «LEOPARD 5 1310km range starting price $37,900 overview China 🇨🇳 🚗»
- [x] **AI Buttons Review** — разбор функционала 3-х AI кнопок в админке:
  - ✨ Reformat with AI — очистка и SEO-оптимизация HTML через Gemini
  - ⚡ Re-enrich Specs — повторное обогащение спецификаций
  - 🔄 Regenerate — повторная генерация из YouTube/RSS с entity anchoring
- [x] **Health Dashboard Error Tracking** — доработки мониторинга ошибок:
  - Исправлен `errors-summary` endpoint (500 → 200)
  - Resolve All — теперь работает в один клик
- [x] **Документация обновлена** — все MD файлы актуализированы:
  - `models.py` → `models/` package, `api_views.py` → `api_views/` с mixins
  - Добавлены: entity_validator, article_generator, deep_specs, error_capture
  - Тесты: 75 → 391+, миграции: 69 → 88+
  - Новые разделы: Health Dashboard, Error Tracking API, AI Content API, TinyMCE

---

## 📅 22 Февраля 2026

### ✅ Реализовано сегодня
>
> **Статус:** ✅ Завершено

- [x] **Smart Auto-Publish (Circuit Breaker)** — интеллектуальная система повторных попыток:
  - MAX_RETRIES = 3, после 3 провалов → статус `auto_failed`
  - Экспоненциальный backoff: 30 мин → 2 часа → перманент
  - Приоритизация свежих статей (меньше попыток = выше приоритет)
  - Если 5 подряд провалов → пауза автопубликации на 1 час
- [x] **Draft/Publish Toggle** — переключатель в Automation Settings:
  - Draft mode (📝) — статьи как черновики, ты проверяешь
  - Direct publish (🚀) — сразу в публикацию
  - По умолчанию: Draft mode ON
- [x] **ML Learning System** — сбор обучающих данных при ревью:
  - `AutoPublishLog` расширен: `human_approved`/`human_rejected` decisions
  - `review_time_seconds` — сколько времени потрачено на ревью
  - `reviewer_notes` — комментарий ревьюера
  - Django signal `log_human_review_decision` — автоматически записывает одобрения
  - Записываются: quality score, длина текста, наличие картинки/спеков/тегов, источник, категория
- [x] **Tag Learning System** — обучение на выборе тегов пользователем:
  - `TagLearningLog` модель: `title_keywords` → `final_tags` маппинг
  - `tag_suggester.py` — 3-стратегийный движок:
    1. Keyword → tag (body types, powertrain, word-boundary regex)
    2. Brand detection (Manufacturers, word-boundary для составных имён)
    3. Historical pattern matching (взвешенный overlap из TagLearningLog)
  - Django signal `learn_tag_choices` — записывает теги при публикации
  - 65 существующих статей backfilled как обучающие данные
  - Fix: word-boundary regex предотвращает false positives (SEAT ≠ 6-seater, EV ≠ REV)
- [x] **Cloudinary Image Crash Fix** — `process_img()` теперь проверяет URL до доступа к файлу
- [x] **Auto-Publish Failures Cleanup** — удалены 570 битых AutoPublishLog записей

### 🧠 Tag Learning Roadmap
>
> **Статус:** 🟡 В процессе (Фаза 1 готова)

| Фаза | Что | Когда | Статус |
|------|-----|-------|--------|
| **Фаза 1** | Keyword matching + historical overlap | Сейчас | ✅ Готово |
| **Фаза 2** | TF-IDF + cosine similarity вместо простого overlap | ~200 статей | 💤 |
| **Фаза 3** | ML классификатор (Random Forest / XGBoost) | ~500 статей | 💤 |
| **Фаза 4** | Автокоррекция AI-тегов перед показом в админке | ~1000 статей | 💤 |
| **Фаза 5** | Embedding-based matching (sentence-transformers) | Когда угодно | 💤 |

### 🤖 AI Review Roadmap (будущее)
>
> **Статус:** 💤 На будущее

- [ ] **AI Quality Gate** — второй LLM проверяет статью перед драфтом:
  - Релевантность (автомобили или нет?)
  - Мусорный контент (off-topic, clickbait)
  - Спекулятивные данные ("US Market Analysis" в статье про китайский авто)
- [ ] **Content Classifier** — обучить на human_approved/rejected данных:
  - Какие темы пользователь одобряет
  - Какие источники надёжные
  - Оптимальная длина текста
- [ ] **Auto-Tag Correction** — после 500+ одобренных статей:
  - Автоматически исправлять AI-теги до показа в админке
  - На основе TagLearningLog patterns

---

## 📅 21 Февраля 2026

### ✅ Реализовано вчера (20 Февраля)
>
> **Статус:** ✅ Завершено

- [x] **Тесты: publisher.py** — 24 теста, покрытие 51% → 55%
- [x] **Тесты: scheduler.py** — 15 тестов, покрытие 20% → 56%
- [x] **Багфикс: CarSpecification** — убрано поле `year` из `publisher.py` (спеки не сохранялись)
- [x] **Багфикс: невидимые статьи** — `cache_signals.py` теперь чистит `@cache_page` ключи
- [x] **Перф: SiteSettings** — добавлен `@cache_page(300)` (5 мин кеш)
- [x] **Перф: robots.txt** — добавлен `@cache_page(86400)` (24ч кеш, было 2.25s TTFB)
- [x] **Перф: Article list** — кеш увеличен 30s → 300s
- [x] **Перф: Homepage ISR** — revalidate 30s → 120s
- [x] **Перф: Изображения** — включена оптимизация Next.js (WebP + resize)
- [x] **CI fix** — E2E тесты теперь `continue-on-error` (не блокируют деплой)

---

## 📅 20 Февраля 2026

### ✅ Реализовано
>
> **Статус:** ✅ Завершено

- [x] **CI/CD пайплайн** — GitHub Actions: 2335+ pytest тестов (PostgreSQL + Redis), E2E Playwright (45 тестов), frontend lint + type check + build
- [x] **A/B тестирование заголовков** — бэкенд: модель, variant serving, tracking, auto/manual winner selection. 5 API endpoints.
- [x] **Система автоматизации** — auto-publisher с quality scoring, safety gating, daily limits, decision logging
- [x] **AI Image Generation** — Gemini image gen + Pexels photo search
- [x] **Ad Placements** — модель и API для управления рекламными блоками
- [x] **Admin User Management** — CRUD пользователей, сброс паролей
- [x] **Bot Protection** — User-Agent middleware
- [x] **Performance Caching** — Redis cache на Settings, robots.txt, article list; Next.js image optimization

### ✅ A/B Testing Frontend
>
> **Статус:** ✅ Завершено

- [x] **Frontend tracking** — sendBeacon для impressions/clicks с `ab_variant_id` (`ABImpressionTracker.tsx`)
- [x] **Использование `display_title`** — публичные компоненты отображают A/B варианты (`ABTitle.tsx`)
- [x] **Cookie seed** — установка `ab_seed` cookie при первом визите (`ABSeedProvider.tsx`)

---

## 📅 17 Февраля 2026

### 📊 Аналитика AI Генерации
>
> **Статус:** 🟡 В процессе (сбор данных)

- [ ] **Процент заполнения спеков** — считать сколько полей в CarSpecification заполнены vs пустые. Показывать в дашборде.
- [ ] **Время от генерации до публикации** — штамп `Generated by` уже даёт время генерации, сравнить с `published_at`
- [ ] **Степень редактирования контента** — сохранять оригинальный HTML при генерации, потом сравнивать с опубликованным (% изменений)
- [x] **Сбор данных** — добавить поле `content_original` в Article для хранения исходного AI-контента

### 🤖 Умная генерация
>
> **Статус:** 💤 На будущее

- [ ] **Авто-доработка спеков** — если после генерации заполнено <70% спеков, запускать повторный поиск по конкретным пропущенным полям
- [ ] **Выбор провайдера по марке** — если данные покажут что Gemini лучше для китайских EV, а Groq для европейских, автоматически выбирать
- [ ] **Самокоррекция промптов** — если 80% статей не получают drivetrain, усиливать промпт

### 🌐 Инфраструктура
>
> **Статус:** ✅ Частично реализовано

- [x] **CI/CD пайплайн** — GitHub Actions с 2335+ pytest тестами + frontend checks
- [ ] **Staging environment** — второй environment на Railway для тестов перед деплоем
- [x] **E2E тесты** — Playwright: 45 тестов (admin, analytics, article-ux, auth, basic, search)

### 📈 Аналитика сайта
>
> **Статус:** 💤 На будущее

- [ ] **Конверсия просмотр → подписка** — отслеживать какие статьи лучше конвертируют
- [ ] **Популярные модели** — какие марки и модели привлекают больше трафика
- [ ] **Geo-аналитика в дашборде** — вытянуть страны из GSC API (хотя GA4 уже это показывает)
- [x] **A/B insight дашборд** — `/admin/ab-testing` — показывает варианты заголовков, CTR comparison bar chart, impressions/clicks, кнопку Pick Winner, бейдж Leading. ✅ Полностью реализован.

---

## 📅 25 Февраля 2026

### 🚀 Future Roadmap: AI & Content Intelligence
>
> **Статус:** 💡 Новые Идеи

- [ ] **Automated Fact-Checking Pipeline:** Интеграция с Google Custom Search API или Tavily API, чтобы перед публикацией статьи AI сверял сгенерированные характеристики с 3 независимыми источниками (доказывая US Market/Pricing claims).
- [ ] **Dynamic Internal Linking (SEO):** AI-агент, который сканирует новую статью и автоматически вставляет 2-3 релевантные гиперссылки на старые статьи FreshMotors (например, связывая Zeekr 007 с обзором Zeekr 001).
- [ ] **Auto-Generated Video Summaries:** Использование FFmpeg + OpenAI TTS + статических изображений автомобиля для автоматической генерации 30-секундных YouTube Shorts или TikTok Reels для каждой статьи платформы.
- [ ] **Competitor Sentiment Analysis:** Оценка тональности обзоров (Sentiment Score: 1-100) на конкурентов в новостях и автоматическое выведение "Рейтинга доверия прессы" в `VehicleSpecsViewSet`.
- [ ] **Voice Search & Conversational UI:** Внедрение AI чат-бота «FreshMotors Assistant» на фронтенд (Next.js), который позволяет пользователям задавать вопросы: *"Какая самая дешевая электрическая машина с запасом хода больше 500 км?"* (с поиском по базе `Article` и `CarSpecification`).

### ⚙️ Future Roadmap: Platform Ecosystem
>
> **Статус:** 💡 Новые Идеи

- [ ] **User Personalization Engine:** Рекомендательная система на главной странице "Specially for You" на основе того, какие тэги/категории пользователь читает дольше всего (Tracking Reading Time).
- [ ] **Real-time Price Alerts:** Разрешить зарегистрированным пользователям нажимать "Уведомить о цене" на страницах автомобилей. Если `currency_service.py` или AI сканирует обновление цены, отправлять Email.
- [ ] **Gamification & Badges:** Система наград для комментаторов и активных читателей (например, "EV Expert", "First to Comment"), чтобы поднять вовлеченность.
- [ ] **Mobile App PWA:** Настройка Next.js `manifest.json` и Service Workers для установки сайта как Native App на iOS/Android с поддержкой Web Push Notifications для важных новостей.

<!-- Добавляй новые записи ниже, каждую с заголовком ## 📅 [Дата] -->
