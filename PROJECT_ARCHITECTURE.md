# FreshMotors — Project Architecture

This document provides a comprehensive overview of the FreshMotors platform architecture, technology stack, and core workflows.

**Last Updated**: 12 March 2026

---

## 🚀 Technology Stack

### Backend

- **Framework**: Django 6.0.1 / Django REST Framework 3.15
- **Language**: Python 3.13
- **Database**: PostgreSQL (Production via Railway, Local via Docker)
- **Cache / Queue**: Redis (view tracking, caching, Celery broker, sessions)
- **Task Queue**: Celery (background enrichment, auto-spec extraction, auto-publishing)
- **AI Providers**: Google Gemini 2.0 Flash (primary), Groq Llama 3.3 70b (fallback)
- **Media**: Cloudinary (production CDN), local storage (dev)
- **APIs**: YouTube Data API v3, Google Search Console API, Google OAuth 2.0, Pexels API
- **Monitoring**: Sentry (error tracking)
- **Testing**: pytest (1880+ tests, 73+ files), Playwright E2E (29 tests), GitHub Actions CI

### Frontend

- **Framework**: Next.js 16.1 (App Router, Server Components, SSR/SSG)
- **Language**: TypeScript 5.0
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Analytics**: Google Analytics 4 (article views, scroll depth, read time)
- **State**: React hooks, Local Storage, Context API

### Infrastructure

- **Containerization**: Docker Compose (backend + Redis)
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
| `auto_news_site/` | Django settings, URL routing, WSGI/ASGI config |
| `news/models/` | DB schema package: `__init__.py` re-exports all models. Split into: `articles.py`, `categories_tags.py`, `vehicles.py`, `pending_articles.py`, `user_accounts.py`, `system.py` (BackendErrorLog, FrontendEventLog, AdminActionLog, Notification) |
| `news/api_views/` | 22+ DRF ViewSets split by domain: `articles.py`, `auth.py`, `system.py`, `rss_feeds.py`, `youtube.py`, `vehicles.py`, `images.py`, etc. |
| `news/api_views/mixins/` | Mixin classes for ArticleViewSet: `ArticleGenerationMixin` (YouTube, RSS, reformat, regenerate), `ArticleEnrichmentMixin` (re-enrich specs), `ArticleEngagementMixin` (comments, ratings, favorites) |
| `news/api_urls.py` | Router registrations and URL patterns (89+ endpoints) |
| `news/serializers.py` | Data serialization layer (with A/B variant injection for public users) |
| `news/signals.py` | Auto-notifications, car spec extraction triggers, tag learning signal, human review ML logging |
| `news/error_capture.py` | ErrorCaptureMiddleware — auto-logs 500 errors to BackendErrorLog |
| `news/management/commands/` | Custom commands: `verify_migrations` (startup DB schema check), `reformat_rss_articles`, `sync_views` |
| `news/admin.py` | Django Admin registrations |
| `ai_engine/main.py` | AI pipeline orchestrator (transcript → analysis → generation → screenshots → AI editor) |
| `ai_engine/modules/transcriber.py` | YouTube transcript retrieval (yt-dlp + oEmbed fallback) |
| `ai_engine/modules/analyzer.py` | LLM content analysis and car specs extraction |
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
| `ai_engine/modules/license_checker.py` | RSS feed license/copyright validation |
| `ai_engine/modules/provider_tracker.py` | AI provider usage tracking and fallback |
| `ai_engine/modules/quality_scorer.py` | Content quality scoring for auto-publishing |
| `ai_engine/modules/seo_helpers.py` | SEO keyword extraction and meta generation |
| `ai_engine/modules/youtube_client.py` | YouTube channel monitoring and batch scanning |
| `news/cache_signals.py` | Auto-invalidation of Redis + @cache_page on model changes |
| `tests/` | pytest test suite (1880+ tests across 73+ test files) |

### Frontend Structure (`/frontend-next`)

| Directory / File | Purpose |
|-----------------|---------|
| `app/(public)/` | Public pages: articles, categories, brands, profile, login |
| `app/admin/` | Admin pages: 31+ management screens (incl. health dashboard) |
| `app/admin/automation/` | Automation control panel |
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
3. **Analysis**: Gemini/Groq analyzes transcript → extracts car specs, pros/cons, key points
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

- **Feed Monitoring**: Periodic background scan (Python `threading.Timer`) — works independently of user's browser session
- **Safety Scoring**: Each feed rated for trustworthiness (human reviewed, copyright, contact info)
- **Deduplication**: Title similarity + content hash to prevent duplicates
- **Workflow**: New → Read → Generating → Generated (or Dismissed)
- **Progress Persistence**: `/rss-feeds/scan_progress/` endpoint in Redis. Admin page re-attaches polling on mount if scan is mid-flight (survive page navigation)
- **Connection Safety**: Scheduler explicitly calls `close_old_connections()` in `finally` block after each scan cycle to prevent PostgreSQL "too many clients" exhaustion

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

### Test Suite (1880+ tests, 73+ files)

| File | Tests | What it covers |
|------|-------|----------------|
| `test_analytics_api.py` | 8 | Analytics overview, top articles, timeline, growth |
| `test_search_api.py` | 11 | Search, filters, sorting, pagination |
| `test_article_generation.py` | 6 | Publishing, image distribution |
| `test_seo_helpers.py` | 8 | SEO keyword generation, extraction |
| `test_auto_publisher.py` | 8 | Safety gating, quality thresholds, rate limits |
| `test_automation_api.py` | 8 | Settings CRUD, stats, auth |
| `test_models.py` | 12 | Singleton, counters, RSS safety, status flow |
| `test_ab_testing.py` | 10 | Variant serving, tracking, winner selection |
| `test_publisher.py` | 24 | Article persistence, specs, tags, categories |
| `test_scheduler.py` | 15 | RSS scan, YouTube scan, auto-publish scheduling |
| `test_articles_crud.py` | 30+ | CRUD operations, permissions, filtering |
| `test_auth.py` | 15+ | JWT, login, registration, password reset |
| `test_brands_rss.py` | 15+ | Brand catalog API, RSS feed management |
| `test_cars_api.py` | 10+ | Car specs API, vehicle specs |
| `test_comments_ratings.py` | 15+ | Comments CRUD, ratings, moderation |
| `test_content_formatter.py` | 8 | HTML formatting, image placement |
| `test_publisher_helpers.py` | 10+ | Slug generation, metadata extraction |
| `test_quality_scorer.py` | 8 | Quality scoring logic |
| `test_rss_aggregator.py` | 12 | RSS parsing, deduplication |
| `test_signals.py` | 10+ | Post-save signals, cache invalidation |
| `test_spec_extractor.py` | 10+ | Spec extraction from content |
| `test_spec_refill.py` | 5 | Auto-refill missing specs |
| `test_specs_enricher.py` | 16 | Enrichment pipeline |
| `test_validators.py` | 9 | Title validation, content validators |
| `test_views.py` | 10+ | Django views, robots.txt, health check |
| + 3 more files | — | Provider tracker, AI main, user management |

### CI Pipeline (`.github/workflows/ci.yml`)

- **Backend**: PostgreSQL + Redis services → `pytest tests/ -v` (1880+ tests)
- **Frontend**: `npm run lint` + `npx tsc --noEmit` + `npm run build`
- **E2E**: Playwright → 29 tests against live site (continue-on-error)
- **Security**: `safety check` for Python dependency vulnerabilities
- **Trigger**: Push to main, pull requests

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
- **Email Verification**: 6-digit code for email changes
- **Password Reset**: Token-based with email delivery
- **Rate Limiting**: Per-IP and per-user throttles on all sensitive endpoints
- **Bot Protection**: User-Agent middleware blocking automated requests
- **CORS**: Whitelisted origins only (freshmotors.net, localhost)
- **Security Headers**: HSTS, X-Content-Type-Options, X-Frame-Options, CSP

---

## 📋 Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Primary AI provider |
| `GROQ_API_KEY` | Fallback AI provider |
| `REDIS_URL` | Cache + view tracking + sessions |
| `DATABASE_URL` | PostgreSQL connection (production) |
| `CLOUDINARY_URL` | Media CDN (production) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth login |
| `GSC_KEY_JSON` | Search Console credentials |
| `YOUTUBE_COOKIES_CONTENT` | yt-dlp YouTube bypass |
| `PEXELS_API_KEY` | Stock photo search |
| `SENTRY_DSN` | Error monitoring |
| `RUNNING_IN_DOCKER` | Set to `1` in `docker-compose.yml` — prevents `.env.local` from overriding Docker service hostnames in `settings.py` |
