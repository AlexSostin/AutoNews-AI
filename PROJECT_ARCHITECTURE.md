# FreshMotors — Project Architecture

This document provides a comprehensive overview of the FreshMotors platform architecture, technology stack, and core workflows.

**Last Updated**: February 2026

---

## 🚀 Technology Stack

### Backend
- **Framework**: Django 6.0.1 / Django REST Framework 3.15
- **Language**: Python 3.13
- **Database**: PostgreSQL (Production via Railway), SQLite (Local dev)
- **Cache / Queue**: Redis (view tracking, caching, Celery broker, sessions)
- **Task Queue**: Celery (background enrichment, auto-spec extraction, auto-publishing)
- **AI Providers**: Google Gemini 2.0 Flash (primary), Groq Llama 3.3 70b (fallback)
- **Media**: Cloudinary (production CDN), local storage (dev)
- **APIs**: YouTube Data API v3, Google Search Console API, Google OAuth 2.0, Pexels API
- **Monitoring**: Sentry (error tracking)
- **Testing**: pytest (75 tests), GitHub Actions CI

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
| `news/models.py` | DB schema: Article, Category, Tag, Brand, CarSpecification, VehicleSpecs, ArticleTitleVariant, AdPlacement, RSSFeed, PendingArticle, AutomationSettings, AutoPublishLog, Feedback, etc. |
| `news/api_views.py` | 30+ DRF ViewSets for all API endpoints |
| `news/api_urls.py` | Router registrations and URL patterns |
| `news/serializers.py` | Data serialization layer (with A/B variant injection for public users) |
| `news/signals.py` | Auto-notifications, car spec extraction triggers |
| `news/admin.py` | Django Admin registrations |
| `news/ab_testing_views.py` | A/B test tracking (impressions, clicks) & admin management |
| `news/cars_views.py` | Brand catalog API (brands, models, specs) |
| `news/search_analytics_views.py` | Search + Analytics endpoints (overview, top articles, timeline, categories, GSC, AI stats) |
| `news/health.py` | Health check endpoints for load balancers |
| `ai_engine/main.py` | AI pipeline orchestrator (transcript → analysis → generation → screenshots → AI editor) |
| `ai_engine/modules/transcriber.py` | YouTube transcript retrieval (yt-dlp + oEmbed fallback) |
| `ai_engine/modules/analyzer.py` | LLM content analysis and car specs extraction |
| `ai_engine/modules/publisher.py` | Article persistence to database |
| `ai_engine/modules/article_reviewer.py` | AI Editor — reviews and improves generated articles |
| `ai_engine/modules/auto_publisher.py` | Automated publishing engine with quality scoring & safety gating |
| `ai_engine/modules/screenshot_extractor.py` | Video frame capture (ffmpeg) |
| `ai_engine/modules/content_formatter.py` | Content formatting and image distribution |
| `tests/` | pytest test suite (75 tests across 7 test files) |

### Frontend Structure (`/frontend-next`)

| Directory / File | Purpose |
|-----------------|---------|
| `app/(public)/` | Public pages: articles, categories, brands, profile, login |
| `app/admin/` | Admin pages: 25+ management screens |
| `app/admin/automation/` | Automation control panel |
| `app/admin/ab-testing/` | A/B testing management |
| `app/admin/ads/` | Ad placement management |
| `app/admin/users/` | User management |
| `components/admin/` | Sidebar, AdminHeader, modals |
| `components/public/` | ViewTracker, FeedbackButton, ShareButtons, RatingStars, ReadingProgressBar |
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
1. **RSS Scan**: Celery task periodically scans monitored RSS feeds
2. **Deduplication**: Title similarity + content hash prevents duplicates
3. **Safety Gating**: Each RSS source has a safety score (`human_reviewed`, `has_copyright_notice`, etc.)
4. **Quality Scoring**: Pending articles scored by content quality, image presence, completeness
5. **Auto-Publish**: Articles above quality threshold automatically published up to daily limit
6. **Decision Logging**: Every accept/reject decision logged in `AutoPublishLog` for audit

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
- **Image Optimization**: Auto WebP conversion and resizing on upload

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
- **Feed Monitoring**: Periodic scan of brand RSS feeds
- **Safety Scoring**: Each feed rated for trustworthiness (human reviewed, copyright, contact info)
- **Deduplication**: Title similarity + content hash to prevent duplicates
- **Workflow**: New → Read → Generating → Generated (or Dismissed)

---

## 🧪 Testing & CI

### Test Suite (75 tests)
| File | Tests | Coverage |
|------|-------|----------|
| `test_analytics_api.py` | 8 | Analytics overview, top articles, timeline, growth |
| `test_search_api.py` | 11 | Search, filters, sorting, pagination |
| `test_article_generation.py` | 6 | Publishing, image distribution |
| `test_seo_helpers.py` | 8 | SEO keyword generation, extraction |
| `test_auto_publisher.py` | 8 | Safety gating, quality thresholds, rate limits |
| `test_automation_api.py` | 8 | Settings CRUD, stats, auth |
| `test_models.py` | 12 | Singleton, counters, RSS safety, status flow |
| `test_ab_testing.py` | 10 | Variant serving, tracking, winner selection |

### CI Pipeline (`.github/workflows/ci.yml`)
- **Backend**: PostgreSQL + Redis services → `pytest tests/ -v`
- **Frontend**: `npm run lint` + `npx tsc --noEmit` + `npm run build`
- **Trigger**: Push to main, pull requests

---

## 🔒 Security & Authentication

- **JWT Tokens**: Access (1h) + Refresh (7d) via SimpleJWT with rotation
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
