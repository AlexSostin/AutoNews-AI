# FreshMotors — Project Architecture

This document provides a comprehensive overview of the FreshMotors platform architecture, technology stack, and core workflows.

**Last Updated**: 13 March 2026

---

## 🚀 Technology Stack

### Backend

- **Framework**: Django 6.0.3 / Django REST Framework 3.15.2
- **Language**: Python 3.13
- **Database**: PostgreSQL (Production via Railway, Local via Docker)
- **Cache / Queue**: Redis (view tracking, caching, Celery broker, sessions)
- **Task Queue**: Celery Beat (9 periodic tasks: GSC sync, currency update, RSS/YouTube scan, auto-publish, scheduled publish, deep specs backfill, A/B lifecycle, stale error cleanup)
- **AI Providers**: Google Gemini 2.0 Flash (primary — complex tasks), Groq Llama 3.3 70b (lightweight tasks via `get_light_provider()`, fallback to Gemini)
- **Media**: Cloudinary (production CDN), local storage (dev)
- **APIs**: YouTube Data API v3, Google Search Console API, Google OAuth 2.0, Pexels API
- **Monitoring**: Sentry (error tracking)
- **Testing**: pytest (2335+ tests, 95 files), Playwright E2E (45 tests, 6 spec files), GitHub Actions CI

### Frontend

- **Framework**: Next.js 16.1.3 (App Router, Server Components, SSR/SSG)
- **Language**: TypeScript 5.0
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Analytics**: Google Analytics 4 (article views, scroll depth, read time)
- **State**: React hooks, Local Storage, Context API

### Infrastructure

- **Containerization**: Docker Compose (backend + Redis + Celery worker + Celery beat)
- **Backend Hosting**: Railway (PostgreSQL + Redis + Django)
- **Frontend Hosting**: Vercel (Next.js auto-deploy from GitHub)
- **CI/CD**: GitHub Actions (pytest + lint + build) → Railway auto-deploy, Vercel auto-deploy
- **Domain**: freshmotors.net (Vercel) + api.freshmotors.net (Railway)

---

## 📂 Project Structure

### Root Directory

```text
AutoNews-AI/
├── .github/workflows/    # CI/CD pipeline
│   └── ci.yml            # Pytest + frontend checks
├── backend/              # Django Application
├── frontend-next/        # Next.js Application
├── docker-compose.yml    # Backend + Redis containers
├── DEPLOYMENT.md         # Deployment guide
├── DOCKER_GUIDE.md       # Docker quick start
├── PROJECT_ARCHITECTURE.md
├── SECURITY.md
├── IDEAS.md              # Roadmap & ideas
└── README.md
```

### Backend Structure (`/backend`)

| Directory / File | Purpose |
|-----------------|---------|
| `auto_news_site/` | Django settings, URL routing, WSGI/ASGI config, `celery.py` (app factory) |
| `news/models/` | DB schema package: `__init__.py` re-exports all models. Split into: `articles.py`, `categories_tags.py`, `vehicles.py`, `pending_articles.py`, `user_accounts.py`, `system.py` (BackendErrorLog, FrontendEventLog, AdminActionLog, Notification) |
| `news/api_views/` | 30+ DRF ViewSets split by domain: `articles.py`, `auth.py`, `system.py`, `rss_feeds.py`, `youtube.py`, `vehicles.py`, `images.py`, `feedback.py`, `system_graph.py`, `webauthn_views.py`, `ai_costs.py`, `moderation.py`, etc. |
| `news/api_views/mixins/` | Mixin classes for ArticleViewSet: `ArticleGenerationMixin` (YouTube, RSS, reformat, regenerate), `ArticleEnrichmentMixin` (re-enrich specs), `ArticleEngagementMixin` (comments, ratings, favorites) |
| `news/api_urls.py` | Router registrations and URL patterns (112+ endpoints) |
| `news/serializers.py` | Data serialization layer (with A/B variant injection for public users) |
| `news/signals.py` | Auto-notifications, car spec extraction triggers, tag learning signal, human review ML logging |
| `news/error_capture.py` | ErrorCaptureMiddleware — auto-logs 500 errors to BackendErrorLog |
| `news/management/commands/` | 58+ custom commands: `verify_migrations`, `scan_rss_feeds`, `scan_youtube`, `sync_views`, `clean_summaries`, `backfill_car_specs`, `extract_all_specs`, `discover_rss_feeds`, `check_rss_license`, `telegram_daily_alert`, `train_content_model`, `train_quality_model`, `export_training_data`, `backup_database` (pg_dump + R2), etc. |
| `news/tasks.py` | 9 Celery `@shared_task` functions — replaces threading.Timer scheduler |
| `news/indexnow.py` | IndexNow API — instant search engine notification on article publish |
| `news/admin.py` | Django Admin registrations |
| `ai_engine/main.py` | AI pipeline orchestrator (transcript → analysis → generation → screenshots → AI editor) |
| `ai_engine/modules/transcriber.py` | YouTube transcript retrieval (yt-dlp + oEmbed fallback) |
| `ai_engine/modules/analyzer.py` | LLM content analysis and car specs extraction (categorization via Groq) |
| `ai_engine/modules/article_generator.py` | RSS press release expansion into full articles |
| `ai_engine/modules/entity_validator.py` | Anti-hallucination: entity extraction, validation, auto-fix, entity anchoring for prompts |
| `ai_engine/modules/deep_specs.py` | Deep vehicle specs enrichment via AI + web search |
| `ai_engine/modules/publisher.py` | Article persistence to database |
| `ai_engine/modules/article_reviewer.py` | AI Editor — reviews and improves generated articles |
| `ai_engine/modules/auto_publisher.py` | Automated publishing engine with quality scoring, safety gating, circuit breaker (MAX_RETRIES, backoff), draft/publish toggle |
| `ai_engine/modules/tag_suggester.py` | Tag learning system: keyword extraction, brand detection, historical pattern matching |
| `ai_engine/modules/screenshot_maker.py` | Video frame capture (ffmpeg) |
| `ai_engine/modules/content_formatter.py` | Content formatting and image distribution |
| `ai_engine/modules/spec_refill.py` | Auto-refill missing car spec fields via AI |
| `ai_engine/modules/specs_enricher.py` | Post-publish spec enrichment pipeline |
| `ai_engine/modules/feed_discovery.py` | Auto-discover RSS feeds for brands |
| `ai_engine/modules/license_checker.py` | RSS feed license/copyright validation (via Groq) |
| `ai_engine/modules/provider_tracker.py` | AI provider usage tracking and fallback |
| `ai_engine/modules/quality_scorer.py` | Content quality scoring for auto-publishing |
| `ai_engine/modules/seo_helpers.py` | SEO keyword extraction and meta generation |
| `ai_engine/modules/seo.py` | A/B title variant generation (via Groq) |
| `ai_engine/modules/youtube_client.py` | YouTube channel monitoring and batch scanning |
| `ai_engine/modules/content_recommender.py` | TF-IDF ML engine: tag/category prediction, similar articles, semantic search, newsletter selection, regex vehicle spec extraction |
| `ai_engine/modules/content_sanitizer.py` | HTML sanitization and content cleanup |
| `ai_engine/modules/rss_curator.py` | Smart RSS clustering: scan, cluster, score, preference ranking, merge into roundup articles |
| `ai_engine/modules/currency_service.py` | Multi-currency price conversion (USD, CNY, EUR, GBP, etc.) |
| `ai_engine/modules/fact_checker.py` | AI fact-checking of generated content |
| `ai_engine/modules/telegram_publisher.py` | Automated Telegram channel posting |
| `ai_engine/modules/translator.py` | Russian → English AI translation with SEO enhancement |
| `ai_engine/modules/duplicate_checker.py` | Cross-article deduplication engine |
| `ai_engine/modules/correction_memory.py` | Stores AI correction patterns for future prompts |
| `ai_engine/modules/ai_provider.py` | AI provider factory: `get_ai_provider()` (Gemini) + `get_light_provider()` (Groq → Gemini fallback) |
| `news/auto_tags.py` | AI-powered tag extraction from articles (via Groq) |
| `news/spec_extractor.py` | Vehicle spec extraction from article content (via Groq) |
| `news/rss_intelligence.py` | RSS feed classification and embedding generation (via Groq) |
| `news/cache_signals.py` | Auto-invalidation of Redis + @cache_page on model changes |
| `tests/` | pytest test suite (2335+ tests across 95 test files) |

### Frontend Structure (`/frontend-next`)

| Directory / File | Purpose |
|-----------------|---------|
| `app/(public)/` | Public pages: articles, categories, brands, profile, login |
| `app/admin/` | Admin pages: 34+ management screens (incl. health dashboard) |
| `app/admin/automation/` | Automation control panel |
| `app/admin/publish-queue/` | Publish Queue — batch scheduler with staggered times, queue stats |
| `app/admin/ab-testing/` | A/B testing management |
| `app/admin/ads/` | Ad placement management |
| `app/admin/users/` | User management |
| `app/admin/health/` | Health dashboard — backend/frontend error monitoring |
| `components/admin/` | Sidebar, AdminHeader, modals, ArticleContentEditor (TinyMCE) |
| `components/public/` | Public UX: `ViewTracker`, `FeedbackButton`, `ShareButtons`, `RatingStars`, `ReadingProgressBar`, `BackToTop` (smart scroll), `InfiniteArticleScroll`, `ArticleUnit`, `NextArticlePreview`, `NewArticleToast`, `CommentSection`, `RelatedCarousel`, `ABImpressionTracker` |
| `lib/api.ts` | Axios client with auth interceptors |
| `lib/auth.ts` | JWT auth helpers, Google OAuth |
| `lib/analytics.ts` | GA4 event tracking functions |
| `lib/authenticatedFetch.ts` | Fetch wrapper with JWT token |
| `types/` | TypeScript interfaces |

---

## 🔧 Core Workflows

### 1. AI Article Generation Pipeline

1. **Trigger**: Manual YouTube URL in admin, or batch scan of monitored channels
2. **Transcription**: `transcriber.py` fetches subtitles via yt-dlp (with cookies bypass)
3. **Analysis**: Gemini analyzes transcript → extracts car specs, pros/cons, key points. Groq handles categorization
4. **Content Generation**: LLM generates full HTML article with SEO optimization
5. **Screenshots**: ffmpeg captures 3 frames at 15%, 50%, 85% of video
6. **AI Editor**: `article_reviewer.py` reviews and polishes the generated article
7. **Timing**: Each step is timed and saved in `generation_metadata` JSON field
8. **Publishing**: Article saved to DB (directly or as PendingArticle for review)

### 2. Auto-Publisher System

1. **RSS Scan**: Scheduler periodically scans monitored RSS feeds
2. **Deduplication**: Title similarity + content hash prevents duplicates
3. **Safety Gating**: Each RSS source has a safety score (`human_reviewed`, `has_copyright_notice`, etc.)
4. **Quality Scoring**: Pending articles scored by content quality, image presence, completeness
5. **Circuit Breaker**: MAX_RETRIES=3, exponential backoff (30min → 2h), auto_failed status after 3 failures
6. **Draft/Publish Toggle**: `auto_publish_as_draft` setting — drafts require manual approval, or direct publish
7. **Auto-Publish**: Articles above quality threshold published up to daily limit
8. **Decision Logging**: Every decision logged in `AutoPublishLog` (published, drafted, skipped, failed)
9. **ML Learning**: When user approves/rejects drafts, signal logs features for future ML training
10. **Tag Suggestion**: `tag_suggester.py` suggests tags via keyword matching + historical patterns
11. **Publish Queue**: Batch scheduler UI — select drafts, set start time + interval, auto-assign staggered `scheduled_publish_at` times

### 2b. RSS Curator Enhancements

- **Auto-Tags**: `_extract_auto_tags()` detects brands (50+), fuel types (Electric, Hybrid, Hydrogen), body types (SUV, Sedan, Truck, Coupe) from title + content
- **SEO Description**: Auto-generated from article summary during generation
- **Image Fallback**: Auto-searches Pexels/web for relevant photos when RSS source lacks images

### 3. A/B Testing System

1. **Variant Creation**: AI generates 2-3 title variants per article
2. **Variant Serving**: `ArticleListSerializer`/`ArticleDetailSerializer` inject `display_title` + `ab_variant_id` based on cookie seed
3. **Tracking**: Frontend sends `sendBeacon` for impressions and clicks
4. **Winner Selection**: Auto-picked when threshold met (default: 100 impressions) + ≥0.5% CTR difference
5. **Manual Override**: Admin can manually pick winner at any time

### 4. Auto-Enrichment

- **Car Specs**: Auto-extracted from article content on save (signal-triggered)
- **Brand Catalog**: Brands auto-created from car specs with logo, country, aliases
- **Drivetrain Tags**: Auto-tagged (EV, PHEV, Hybrid, ICE) based on spec analysis
- **Price Segments**: Auto-tagged (Budget, Mid-Range, Premium, Luxury, Supercar)

### 8. Caching & Performance

- **Redis Cache**: `@cache_page` on article list (300s), article detail (60s), trending (15min), popular (1h), settings (300s), robots.txt (24h)
- **Cache Invalidation**: `cache_signals.py` auto-clears Redis + `@cache_page` keys on Article/Category/Tag/Rating changes
- **Next.js ISR**: Homepage revalidates every 120s, categories/brands every 3600s
- **Image Optimization**: Next.js auto-converts to WebP, responsive resizing

### 5. Analytics & Tracking

- **GA4 Events**: `article_view`, `article_read` (scroll milestones), `read_time` (on unload)
- **Redis View Counter**: Incremented per page view, batch-synced to PostgreSQL via management command
- **GSC Integration**: Pulls clicks, impressions, CTR, position for all pages
- **AI Stats**: Enrichment coverage (vehicle specs, A/B titles, tags, car specs, images), top tags by views, source breakdown (YouTube/RSS/translated)
- **Generation Metadata**: Per-article timing breakdown and AI Editor diff stats

### 6. User Feedback Loop

- **Feedback Button**: Public users can report errors (factual, hallucination, typo, outdated)
- **Rate Limited**: 1 report per IP per article per day
- **Admin Panel**: Feedback management with resolve/reopen/delete actions

### 7. RSS Aggregation

- **Feed Monitoring**: Celery Beat periodic task (every 30 min) — checks `AutomationSettings` for enabled/disabled state
- **Safety Scoring**: Each feed rated for trustworthiness (human reviewed, copyright, contact info)
- **Deduplication**: Title similarity + content hash to prevent duplicates
- **Workflow**: New → Read → Generating → Generated (or Dismissed)
- **Progress Persistence**: `/rss-feeds/scan_progress/` endpoint in Redis. Admin page re-attaches polling on mount if scan is mid-flight (survive page navigation)
- **Connection Safety**: Celery tasks call `close_old_connections()` in `finally` block after each cycle

---

## 📰 Infinite Scroll (Article Detail)

- **`[slug]/page.tsx`**: SSR fetches initial article (with `fetchWithRetry` — 2 retries, 3s timeout) → passes to `InfiniteArticleScroll`. On SSR failure falls through to `ClientArticleDetail` (CSR fallback).
- **`InfiniteArticleScroll.tsx`**: Orchestrates article feed. IntersectionObserver sentinel triggers `next-article` API fetch. Posts `article-active-slug` custom event on article switch.
- **`ArticleUnit.tsx`**: Renders each article. Fires `onBecameActive` when scrolled into view (updates URL via `window.history.replaceState({...state, slug})` — preserves Next.js `__NA`/`__N` internal flags, fires GA4 `page_view`).
- **`NextArticlePreview.tsx`**: Preview card shown before loading next article (countdown + skip).
- **`NewArticleToast.tsx`**: Toast shown when user is 50%+ in the page footer while next article is fetching — avoids interrupting footer interactions.
- **`BackToTop.tsx`**: Smart scroll button — single click scrolls to current article top (resolved via `data-article-slug` attr + custom event), double click scrolls to page top.
- **Backend**: `next_article` action in `ArticleEngagementMixin` uses `ArticleDetailSerializer` (full content) — priority: same model → same make → ML similar → same category → popular.

---

## 🧪 Testing & CI

### Test Suite (2335+ tests, 95 files)

| File | Tests | What it covers |
|------|-------|----------------|
| `test_boundary_mutations.py` | 80 | Boundary conditions, mutation testing |
| `test_batch2_max.py` | 68 | auto_tags, models (max coverage) |
| `test_ai_engine_core.py` | 63 | AI engine core functionality |
| `test_five_modules_max.py` | 58 | utils, spec_refill, translator, specs_enricher, specs_extractor |
| `test_zone_bd.py` | 53 | Zone B+D modules |
| `test_api_views_remaining.py` | 53 | Remaining API view coverage |
| `test_deep_specs_max.py` | 51 | Deep specs enrichment |
| `test_zone_e.py` | 49 | Zone E modules |
| `test_license_checker_max.py` | 49 | License checker (max coverage) |
| `test_batch6_max.py` | 45 | Batch 6 coverage push |
| `test_new_features.py` | 43 | Newest features |
| `test_batch3_max.py` | 43 | Batch 3 models |
| `test_api_views_batch36.py` | 42 | API views batch |
| `test_batch1_max.py` | 41 | Batch 1 coverage push |
| `test_spec_extractor.py` | 39 | Spec extraction from content |
| `test_critical_generators.py` | 38 | Article generator, RSS aggregator |
| `test_zone_c.py` | 36 | Analyzer, article generator, translator, license checker |
| `test_article_ai_deep_api.py` | 36 | Deep AI API endpoints |
| `test_ai_modules.py` | 35 | AI module unit tests |
| `test_zone_a.py` | 34 | Zone A modules |
| `test_user_auth_api.py` | 34 | User auth API |
| `test_medium_priority.py` | 34 | Medium-priority modules |
| `test_main_max.py` | 33 | ai_engine/main.py (max coverage) |
| `test_content_sanitizer.py` | 33 | HTML sanitization |
| `test_ai_main.py` | 33 | AI main pipeline |
| `test_scheduler.py` | 31 | RSS scan, YouTube scan, auto-publish scheduling |
| `test_main_critical.py` | 31 | ai_engine/main.py critical paths |
| `test_rss_aggregator.py` | 30 | RSS parsing, hashing, similarity, dedup |
| `test_content_recommender.py` | 30 | TF-IDF ML engine, vehicle spec regex |
| `test_tier1_utils.py` | 29 | Tier-1 utility functions |
| `test_pending_feedback_api.py` | 29 | Pending articles, feedback API |
| `test_rss_enhancements.py` | 28 | Auto-tags, publish queue, batch schedule |
| `test_rss_curator.py` | 28 | Scan, cluster, score, preference ranking |
| `test_article_quality.py` | 28 | Article quality validation |
| `test_article_ai_api.py` | 28 | Article AI API endpoints |
| `test_publisher_max.py` | 26 | Publisher (max coverage) |
| `test_main_deep.py` | 26 | Deep pipeline tests |
| `test_signals.py` | 25 | Post-save signals, cache invalidation |
| `test_car_spec_dedup.py` | 25 | Car spec deduplication |
| `test_publisher.py` | 24 | Article persistence, specs, tags, categories |
| `test_article_crud_api.py` | 24 | CRUD operations, permissions |
| `test_newsletter_ads_api.py` | 23 | Newsletter, ad placement |
| `test_system_health.py` | 22 | Error logging, middleware, resolve |
| `test_hypothesis_properties.py` | 22 | Property-based testing |
| `test_entity_validator.py` | 22 | Anti-hallucination entity validation |
| `test_batch5_max.py` | 22 | Batch 5 coverage push |
| + 50 more files | 800+ | Models, auth, webauthn, telegram, SEO, security, management commands |

### CI Pipeline (`.github/workflows/ci.yml`)

- **Backend**: PostgreSQL + Redis services → `pytest tests/ -v` (2335+ tests)
- **Frontend**: `npm run lint` + `npx tsc --noEmit` + `npm run build`
- **E2E**: Playwright → 45 tests across 6 spec files (admin, analytics, article-ux, auth, basic, search)
- **Security**: `safety check` for Python dependency vulnerabilities
- **Trigger**: Push to main, pull requests

---

## 🤖 AI Provider Load Balancing

`get_light_provider()` in `ai_provider.py` routes lightweight tasks to **Groq** (fast, cheap), falling back to **Gemini** if Groq is unavailable.

| Provider | Tasks |
|----------|-------|
| **Gemini** (quality) | Article generation, transcript analysis, deep specs, fact-checking, translation, AI editing, user-facing features |
| **Groq** (speed) | Tag extraction, article categorization, license checking, SEO title variants, summary cleaning, RSS classification, spec extraction |

---

## 🐛 Production Error Fixes (March 2026)

| Error | Root Cause | Fix |
|-------|-----------|-----|
| React #419 (SSR Suspense fallback) | Railway API timeout caused SSR fetch to fail and React to log #419 in Sentry | `fetchWithRetry()` in `articles/[slug]/page.tsx` — 2 retries, 3s timeout |
| `Cannot assign to read-only property pushState` | Direct `window.history.pushState()` conflicts with Next.js App Router hydration | Replaced with `window.history.replaceState({...state, slug})` — spreads existing state to preserve `__NA`/`__N` flags |
| `Failed to load chunk` (ChunkLoadError) | Stale JS chunks in browser after new deploy | `ErrorBoundary` auto-reloads on `ChunkLoadError` or `Loading chunk` errors |
| `FATAL: too many clients already` (PostgreSQL) | Scheduler threads held DB connections open (no cleanup after scan) | Added `close_old_connections()` in `finally` block of `_run_rss_scan()`; `CONN_MAX_AGE=0` always |

---

## 🔒 Security & Authentication

- **JWT Tokens**: Access (8h) + Refresh (7d) via SimpleJWT with rotation
- **Google OAuth 2.0**: Social login with automatic account linking
- **WebAuthn / Passkeys**: FIDO2 passwordless auth — register, authenticate, verify-pending (post-password), list/delete credentials. Cross-origin safe via Redis cache tokens
- **2FA (TOTP)**: Time-based one-time passwords for admin accounts
- **Email Verification**: 6-digit code for email changes
- **Password Reset**: Token-based with email delivery
- **Rate Limiting**: Per-IP and per-user throttles on all sensitive endpoints
- **Bot Protection**: User-Agent middleware blocking automated requests
- **CORS**: Whitelisted origins only (freshmotors.net, localhost)
- **Security Headers**: HSTS, X-Content-Type-Options, X-Frame-Options, CSP

---

## ⚡ Celery Beat — Background Task Scheduler

Replaces the old `threading.Timer` scheduler with a production-grade Celery Beat setup. Redis serves as both broker and result backend.

| Task | Schedule | Description |
|------|----------|-------------|
| `gsc_sync` | Every 6h | Google Search Console data sync |
| `currency_update` | Daily 3:30 AM | Exchange rates + USD price update |
| `rss_scan` | Every 30 min | RSS feeds scan (checks AutomationSettings) |
| `youtube_scan` | Every 30 min | YouTube channels (daytime-only mode) |
| `auto_publish` | Every 10 min | Auto-publish eligible pending articles |
| `scheduled_publish` | Every minute | Publish articles at their scheduled time |
| `deep_specs_backfill` | Every 6h | Auto-generate VehicleSpecs cards |
| `ab_lifecycle` | Daily 4 AM | A/B test cleanup + winner auto-pick |
| `stale_error_cleanup` | Every 6h | Auto-resolve old errors (24h+ no recurrence) |

**Docker services**: `celery_worker` (concurrency=2), `celery_beat` (scheduler).

---

## 🔍 PostgreSQL Full-Text Search

Article search uses PostgreSQL native FTS with weighted GIN index:
- **Weights**: Title (A), Summary (B), Content (C)
- **Query**: `SearchVector` + `SearchRank` + `websearch` query type
- **Fallback**: Short queries (< 3 chars) use `icontains`

---

## 📡 IndexNow — Instant Search Indexing

- On article publish, Django signal fires `indexnow.py` → notifies Bing/Yandex/etc. in background thread
- Key: `INDEXNOW_KEY` env var (currently: `freshmotors2026abc123`)
- Verification file served at `/static/{INDEXNOW_KEY}.txt`

---

## 💰 AI Cost Dashboard

- **Endpoint**: `GET /api/v1/admin/ai-costs/`
- Aggregates AI provider usage from Redis (Gemini/Groq)
- Shows daily breakdowns, per-provider costs, monthly projections

---

## 📋 Content Moderation Queue

- **Endpoint**: `GET/POST /api/v1/admin/moderation/`
- Model fields: `moderation_status` (pending/approved/rejected), `moderation_notes`, `moderation_reviewed_at/by`
- Supports bulk approve/reject actions

---

## 💾 Backup Strategy

- **Command**: `python manage.py backup_database`
- Uses `pg_dump` + gzip compression
- Optional upload to Cloudflare R2 (S3-compatible)
- Retention: 7 daily + 4 weekly backups

---

## 📋 Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Primary AI provider (complex tasks) |
| `GROQ_API_KEY` | Lightweight AI tasks via `get_light_provider()`, fallback to Gemini |
| `REDIS_URL` | Cache + view tracking + sessions |
| `DATABASE_URL` | PostgreSQL connection (production) |
| `CLOUDINARY_URL` | Media CDN (production) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth login |
| `GSC_KEY_JSON` | Search Console credentials |
| `YOUTUBE_COOKIES_CONTENT` | yt-dlp YouTube bypass |
| `PEXELS_API_KEY` | Stock photo search |
| `SENTRY_DSN` | Error monitoring |
| `TELEGRAM_BOT_TOKEN` | Telegram bot for auto-posting articles |
| `TELEGRAM_CHANNEL_ID` | Telegram channel for published articles |
| `TELEGRAM_ADMIN_ID` | Admin alerts and daily reports |
| `INDEXNOW_KEY` | IndexNow instant search indexing key (`freshmotors2026abc123`) |
| `SITE_URL` | Site URL for article links (default: `https://www.freshmotors.net`) |
| `CELERY_BROKER_URL` | Celery broker (falls back to `REDIS_URL` automatically) |
| `WEBAUTHN_RP_ID` | Passkey relying party ID (production: `freshmotors.net`) |
| `WEBAUTHN_ORIGIN` | Passkey allowed origin (production: `https://www.freshmotors.net`) |
| `RUNNING_IN_DOCKER` | Set to `1` in `docker-compose.yml` — prevents `.env.local` from overriding Docker service hostnames in `settings.py` |
