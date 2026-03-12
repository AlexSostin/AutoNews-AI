# FreshMotors — Roadmap & Ideas

## ✅ Completed

- AI article generation pipeline (YouTube/RSS → Gemini → article)
- SEO optimization (meta tags, JSON-LD, sitemap, canonical URLs)
- A/B title testing with auto-winner selection
- ML quality scorer (GradientBoosting on engagement data)
- Engagement tracking (scroll depth, dwell time, micro-feedback)
- Brand Intelligence system (make/model normalization)
- Security audit (2FA, brute-force protection, prompt injection defense)
- AI summary regeneration (clean_summaries Gemini pipeline)
- www domain redirect (308 freshmotors.net → <www.freshmotors.net>)
- Telegram auto-publishing (bot API, channel posting)
- Smart RSS Curator (cluster + merge into roundup articles)
- **Production error fixes (March 2026)**:
  - React #419 SSR fallback → `fetchWithRetry` (2 retries, 3s timeout)
  - `pushState` read-only crash → `replaceState({...state, slug})`
  - `ChunkLoadError` stale JS → `ErrorBoundary` auto-reload
  - PostgreSQL "too many clients" → `close_old_connections()` in scheduler finally
  - RSS scan progress bar survives page navigation (on-mount resume check)

## 🔄 In Progress

- AI Quality Gate — detect AI-sounding content before publish
- RSS feed auto-ingestion improvements

## 📋 Backlog — Next Steps

### 🤖 Full Autopilot Pipeline

1. **AI Quality Gate** — score articles for "AI-ness", auto-draft if score < threshold
2. **Telegram Channel** — auto-publish to Telegram channel on article publish
3. **Twitter/X Auto-post** — Free tier (500 posts/mo), needs developer account at developer.x.com
4. **Reddit Semi-auto** — bot prepares post, manual approve (PRAW, avoid bans)
5. **ML Feedback Loop** — admin 👍/👎 trains quality scorer on editor preferences

### 📡 Social Media Distribution

- **Telegram**: Bot API (free, unlimited), create @freshmotors_news channel
- **X/Twitter**: developer.x.com → free tier → OAuth posting via API
- **Reddit**: r/freshmotors + relevant car subreddits, semi-auto with PRAW
- **LinkedIn**: API posting for industry authority

### 💰 Product Ideas

- **SocialHub SaaS** — own social media auto-publishing service (compete with Ayrshare @ $29/mo)
  - Unified API for Telegram, Twitter, Reddit, LinkedIn
  - AI-generated posts from article content (Claude/Gemini)
  - Scheduling, analytics, A/B testing of posts
  - Target: automotive publishers, tech bloggers

### 📊 Analytics & ML

- CTR prediction from headlines (train on A/B test results)
- AI-detection classifier (is this text AI-generated?)
- Content recommender improvements (already have vector search)
- Google Search Console integration improvements

### 🔧 Technical Debt

- Migrate to Railway CLI for management commands
- Add E2E tests for article generation pipeline
- Performance monitoring (APM) for Gemini API latency

## 🏗️ Tech Stack (March 2026)

### Backend

- **Django 5.x** + Django REST Framework
- **PostgreSQL** (Railway) + **Redis** (caching, sessions, scheduler)
- **Gemini 2.5-flash-lite** (primary AI) + **Groq Llama 3.3** (fallback)
- **scikit-learn** — GradientBoosting for engagement prediction
- **Celery/APScheduler** — background tasks, RSS polling, auto-publish

### Frontend

- **Next.js 14** (App Router, React Server Components)
- **TypeScript** + vanilla CSS
- **Vercel** — hosting + edge functions

### AI Pipeline

- YouTube transcript → Gemini analysis → article generation → post-processing
- RSS feed polling → dedup → AI expansion → pending article
- Web search enrichment (DuckDuckGo, direct site scraping)
- Competitor lookup from internal DB
- Few-shot examples for consistent quality

### Infrastructure

- **Railway** — Django backend + PostgreSQL + Redis
- **Vercel** — Next.js frontend
- **Cloudinary** — image storage/CDN
- **GitHub Actions** — CI/CD (1875+ tests)
