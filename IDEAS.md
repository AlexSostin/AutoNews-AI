# 💡 FreshMotors — Идеи и Планы

> Записная книжка для будущих улучшений. Добавляй идеи с датой!

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

- [x] **CI/CD пайплайн** — GitHub Actions: 391 pytest тестов (PostgreSQL + Redis), E2E Playwright, frontend lint + type check + build
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

- [x] **CI/CD пайплайн** — GitHub Actions с 391 pytest тестами + frontend checks
- [ ] **Staging environment** — второй environment на Railway для тестов перед деплоем
- [x] **E2E тесты** — Playwright: 14 тестов (homepage, articles, SEO, performance, mobile)

### 📈 Аналитика сайта
>
> **Статус:** 💤 На будущее

- [ ] **Конверсия просмотр → подписка** — отслеживать какие статьи лучше конвертируют
- [ ] **Популярные модели** — какие марки и модели привлекают больше трафика
- [ ] **Geo-аналитика в дашборде** — вытянуть страны из GSC API (хотя GA4 уже это показывает)
- [ ] **A/B insight дашборд** — визуализация результатов A/B тестов в админке

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
