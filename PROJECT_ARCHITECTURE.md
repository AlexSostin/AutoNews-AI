# FreshMotors — Project Architecture

This document provides a comprehensive overview of the FreshMotors platform architecture, technology stack, and core workflows.

---

## 🚀 Technology Stack

### Backend
- **Framework**: Django 6.0.1 / Django REST Framework 3.15
- **Language**: Python 3.13
- **Database**: PostgreSQL (Production via Railway), SQLite (Local dev)
- **Cache / Queue**: Redis (view tracking, caching, Celery broker)
- **Task Queue**: Celery (background enrichment, auto-spec extraction)
- **AI Providers**: Google Gemini 2.0 Flash (primary), Groq Llama 3.3 70b (fallback)
- **Media**: Cloudinary (production CDN), local storage (dev)
- **APIs**: YouTube Data API v3, Google Search Console API, Google OAuth 2.0
- **Monitoring**: Sentry (error tracking)

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
- **CI/CD**: GitHub → Railway auto-deploy, GitHub → Vercel auto-deploy
- **Domain**: freshmotors.net (Vercel) + api.freshmotors.net (Railway)

---

## 📂 Project Structure

### Root Directory
```text
AutoNews-AI/
├── backend/              # Django Application
├── frontend-next/        # Next.js Application
├── docker-compose.yml    # Backend + Redis containers
├── DEPLOYMENT.md         # Deployment guide
├── PROJECT_ARCHITECTURE.md
├── SECURITY.md
└── README.md
```

### Backend Structure (`/backend`)

| Directory / File | Purpose |
|-----------------|---------|
| `auto_news_site/` | Django settings, URL routing, WSGI/ASGI config |
| `news/models.py` | DB schema: Article, Category, Tag, Brand, CarSpecification, VehicleSpecs, ArticleFeedback, RSS models, etc. |
| `news/api_views.py` | 30+ DRF ViewSets for all API endpoints |
| `news/api_urls.py` | Router registrations and URL patterns |
| `news/serializers.py` | Data serialization layer |
| `news/signals.py` | Auto-notifications, car spec extraction triggers |
| `news/admin.py` | Django Admin registrations |
| `news/cars_views.py` | Brand catalog API (brands, models, specs) |
| `news/search_analytics_views.py` | Search + Analytics endpoints |
| `news/health.py` | Health check endpoints for load balancers |
| `ai_engine/main.py` | AI pipeline orchestrator (transcript → analysis → generation → screenshots → AI editor) |
| `ai_engine/modules/transcriber.py` | YouTube transcript retrieval (yt-dlp + oEmbed fallback) |
| `ai_engine/modules/analyzer.py` | LLM content analysis and car specs extraction |
| `ai_engine/modules/publisher.py` | Article persistence to database |
| `ai_engine/modules/article_reviewer.py` | AI Editor — reviews and improves generated articles |
| `ai_engine/modules/screenshot_extractor.py` | Video frame capture (ffmpeg) |

### Frontend Structure (`/frontend-next`)

| Directory / File | Purpose |
|-----------------|---------|
| `app/(public)/` | Public pages: articles, categories, brands, profile, login |
| `app/admin/` | Admin pages: 20+ management screens |
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

### 2. Auto-Enrichment
- **Car Specs**: Auto-extracted from article content on save (signal-triggered)
- **Brand Catalog**: Brands auto-created from car specs with logo, country, aliases
- **Drivetrain Tags**: Auto-tagged (EV, PHEV, Hybrid, ICE) based on spec analysis
- **Price Segments**: Auto-tagged (Budget, Mid-Range, Premium, Luxury, Supercar)
- **Image Optimization**: Auto WebP conversion and resizing on upload

### 3. Analytics & Tracking
- **GA4 Events**: `article_view`, `article_read` (scroll milestones), `read_time` (on unload)
- **Redis View Counter**: Incremented per page view, batch-synced to PostgreSQL via management command
- **GSC Integration**: Pulls clicks, impressions, CTR, position for all pages
- **Generation Metadata**: Per-article timing breakdown and AI Editor diff stats

### 4. User Feedback Loop
- **Feedback Button**: Public users can report errors (factual, hallucination, typo, outdated)
- **Rate Limited**: 1 report per IP per article per day
- **Admin Panel**: Feedback management with resolve/reopen/delete actions

### 5. RSS Aggregation
- **Feed Monitoring**: Periodic scan of brand RSS feeds
- **Deduplication**: Title similarity + content hash to prevent duplicates
- **Workflow**: New → Read → Generating → Generated (or Dismissed)

---

## 🔒 Security & Authentication

- **JWT Tokens**: Access (5h) + Refresh (1d) via SimpleJWT
- **Google OAuth 2.0**: Social login with automatic account linking
- **Email Verification**: 6-digit code for email changes
- **Password Reset**: Token-based with email delivery
- **Rate Limiting**: Per-IP and per-user throttles on all sensitive endpoints
- **CORS**: Whitelisted origins only (freshmotors.net, localhost)
- **Security Headers**: HSTS, X-Content-Type-Options, X-Frame-Options, CSP

---

## 📋 Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Primary AI provider |
| `GROQ_API_KEY` | Fallback AI provider |
| `REDIS_URL` | Cache + view tracking |
| `DATABASE_URL` | PostgreSQL connection (production) |
| `CLOUDINARY_URL` | Media CDN (production) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth login |
| `GSC_KEY_JSON` | Search Console credentials |
| `YOUTUBE_COOKIES_CONTENT` | yt-dlp YouTube bypass |
| `SENTRY_DSN` | Error monitoring |
