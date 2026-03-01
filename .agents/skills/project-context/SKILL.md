---
name: FreshMotors Project Context
description: Essential project setup, architecture, and conventions for AutoNews-AI
---

# FreshMotors / AutoNews-AI — Project Context

## Architecture

- **Backend**: Django 6.0 + DRF 3.15, Python 3.13, Docker container `autonews_backend`
- **Frontend**: Next.js 16.1 (App Router, TypeScript, Tailwind CSS)
- **Database**: PostgreSQL (Railway prod / SQLite local dev)
- **Cache/Queue**: Redis (view tracking, caching, Celery broker, sessions)
- **Task Queue**: Celery (background enrichment, auto-spec extraction, auto-publishing)
- **AI Primary**: Google Gemini 2.0 Flash
- **AI Fallback**: Groq Llama 3.3 70b (NOT OpenAI)
- **Media CDN**: Cloudinary (Railway has ephemeral filesystem)
- **Monitoring**: Sentry + custom FrontendEventLog + BackendErrorLog

## Hosting & Deployment

- **Backend**: Railway (Django + PostgreSQL + Redis) → `api.freshmotors.net`
- **Frontend**: Railway (Next.js) → `freshmotors.net` (⚠️ Vercel ещё не подключен)
- **CI/CD**: GitHub Actions (pytest 391+ tests + lint + build) → auto-deploy on push to `main`

## External Services

| Service | Env Var | Purpose |
|---|---|---|
| Google Gemini | `GEMINI_API_KEY` | Primary AI for article generation |
| Groq | `GROQ_API_KEY` | Fallback AI provider |
| Google OAuth | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | User login |
| Google Search Console | `GSC_KEY_JSON` | SEO analytics |
| Cloudinary | `CLOUDINARY_URL` | Media storage (production) |
| YouTube | `YOUTUBE_COOKIES_CONTENT` | Video transcript source (yt-dlp) |
| Pexels | `PEXELS_API_KEY` | Stock photo search |
| Sentry | `SENTRY_DSN` | Error monitoring |
| DuckDuckGo | (no key) | Web search for RSS feeds |

## Docker Commands

```bash
# Run backend tests
docker exec autonews_backend python -m pytest tests/ -x --tb=short -q

# Restart backend (after model/serializer/view changes)
docker restart autonews_backend

# Django management commands
docker exec autonews_backend python manage.py <command>

# Check backend logs
docker logs autonews_backend --tail 50
```

## Frontend Commands

```bash
# Dev server
cd frontend-next && npm run dev

# Build check (verify no errors)
cd frontend-next && npx next build

# Run tests
cd frontend-next && npx vitest run
```

## Key Directories

```
backend/
  news/models/         # Django models (articles.py, sources.py, system.py, etc.)
  news/api_views/      # DRF ViewSets
  news/serializers.py  # All serializers
  ai_engine/modules/   # AI generation, RSS discovery, scoring, etc.
  tests/               # pytest tests

frontend-next/
  app/admin/           # Admin panel pages
  app/(public)/        # Public-facing pages
  components/          # Shared components
  lib/                 # API client, auth, error-logger
```

## Git Workflow

- Single branch: `main`
- Push triggers Railway auto-deploy
- Always run tests + build before pushing
- Push command: `git push origin main`
- ⚠️ **GitKraken MCP push не работает** — всегда пушить через `run_command` с `git push origin main`

## Error Reporting

- Frontend errors → `logCaughtError()` from `lib/error-logger.ts`
- Errors logged to `/admin/health` dashboard
- Backend: `FrontendEventLog` model in `news/models/system.py`

## Important Conventions

- Backend API base: `/api/v1/`
- Frontend uses `lib/api.ts` (Axios with auth interceptor)
- All admin pages in `app/admin/` use Tailwind CSS
- User language: Russian (communicate in Russian)
- User name: Саша (Alex)

## Known Gotchas (from past bugs)

- **Gemini 429 rate limits**: AI functions (spec extraction, article generation) hit rate limits. Always add retry logic (3 retries, 30/60/90s delays) and regex fallback
- **ISR cache**: Next.js caches pages. After content changes, set `revalidate: 30` not 300. Use `api/revalidate` endpoint for on-demand revalidation
- **Entity warning banners**: `entity_validator.py` can inject HTML warnings into article content stored in DB. Always strip `<div class="entity-mismatch-warning">` before rendering on public site
- **A/B title overwrite**: `ABTitle` component is currently disabled — it was overwriting manually edited titles with old A/B variants. If re-enabling, check `ArticleTitleVariant` cleanup logic
- **Cloudinary URLs**: `_get_image_url()` in `cars_views.py` can double-prefix URLs. Check for absolute URLs before prepending media host
- **DuckDuckGo search**: `duckduckgo_search` library can fail silently. Always wrap in try/except
- **Tailwind CSS warnings**: `@theme` and `@apply` in `globals.css` are Tailwind v4 directives, not errors

## Common Patterns

- **Adding a new admin page**: Create `app/admin/{name}/page.tsx`, uses `api` from `@/lib/api`, wrap errors with `logCaughtError`
- **Adding a backend action**: Add `@action(detail=True/False, methods=['post'])` to ViewSet, import in URL router
- **Parallel HTTP requests**: Use `ThreadPoolExecutor(max_workers=10)` for I/O-bound tasks (RSS discovery, license checks)
- **Error logging frontend**: Import `logCaughtError` from `@/lib/error-logger` in every admin page catch block
- **New serializer field** (computed): Add `SerializerMethodField()` + `def get_field_name(self, obj)` — no migration needed

## Refactoring Rules

- Monolithic pages > 800 lines → extract into components (`components/admin/`)
- Monolithic ViewSets > 1000 lines → extract into mixins (`api_views/mixins/`)
- Shared interfaces → extract into `types.ts` files
- Pattern: `ArticleViewSet` inherits from `ArticleGenerationMixin`, `ArticleEngagementMixin`, `ArticleEnrichmentMixin`

## Known Technical Debt

- `CarSpecification` ↔ `VehicleSpecs` — duplicate models, need consolidation
- `notifications` admin page — dead (0 triggers)
- 5 dead AI modules identified in audit (1,078 lines to remove)
- Feed keyword search filter too strict — needs word-by-word matching instead of full phrase

## Brand Management

- **Domain**: `freshmotors.net` (production), `api.freshmotors.net` (API)
- **Current traffic**: ~600 visits/month (growing). AdSense configured, waiting for scale
- **BrandAlias** (`news/models/vehicles.py`): maps name variations → canonical (e.g. `DongFeng VOYAH` → `VOYAH`). Has optional `model_prefix` field for sub-brand extraction rules
- **`is_make_locked`** on `CarSpecification`: when True, AI re-extraction and VehicleSpecs sync will NOT overwrite `make`/`model`/`model_name`. Set automatically by `move-article` admin action
- **Admin**: `/admin/brands` — merge, move-article, sync. `/admin/brand-aliases` — alias management
- **Key rule**: NIO ≠ ONVO, BYD ≠ DENZA — separate brands. Use `move-article` to reassign, lock holds permanently

## Docker + Turbopack SSR Fetch Bug (CRITICAL)

**Problem**: Next.js 16 Turbopack (`npm run dev`) in Docker **patches `fetch()`** with its own caching layer.
This patched fetch **cannot resolve Docker service hostnames** (like `backend`) because Turbopack's
internal DNS resolver ignores Docker DNS (`127.0.0.11`). Direct IP also fails. This breaks all SSR
data fetching in Docker dev mode.

**Symptom**: `getaddrinfo ENOTFOUND backend` for any SSR `fetch()` call in Docker.

**Solution**: Hybrid SSR + client-side fallback pattern:

```tsx
// In server component (page.tsx):
const data = await fetchData(); // try SSR
if (!data) {
  return <ClientFallbackComponent />; // client-side fetch via browser
}
// ... render SSR with SEO
```

**Key files using this pattern**:

- `app/(public)/page.tsx` → falls back to `ClientHomepage.tsx`
- `app/(public)/articles/[slug]/page.tsx` → falls back to `ClientArticleDetail.tsx`

**On Railway (production)**: SSR works normally — Turbopack not used (`next start`), full SEO.
**In Docker dev**: SSR fails → client components fetch via browser → `localhost:8000` → works.

**DO NOT**:

- Remove `ClientHomepage.tsx` or `ClientArticleDetail.tsx` — they are essential Docker dev fallbacks
- Use `notFound()` when SSR fetch fails — it's not a 404, just Docker DNS failure
- Try `NODE_OPTIONS=--dns-result-order=ipv4first` — doesn't fix Turbopack's patched fetch

## Redis Cache (API Responses)

Redis is configured as `django_redis.cache.RedisCache` with prefix `autonews:`.

| Endpoint | Cached By | TTL | Notes |
|---|---|---|---|
| `/articles/` list | `@cache_page(60)` | 1 min | Bypass for authenticated users |
| `/categories/` list | `@cache_page(300)` | 5 min | Bypass for authenticated users |
| `/tags/` list | `@cache_page(300)` | 5 min | Bypass for staff users |
| `/settings/` list | `@cache_page(300)` | 5 min | SiteSettings singleton |
| `/currency-rates/` | `@cache_page(3600)` | 1 hr | External API rates |

Cache invalidation is handled by `cache_signals.py` — post_save/post_delete signals on Article, Category, Tag, Rating, Comment automatically clear related cache keys + `@cache_page` patterns.
