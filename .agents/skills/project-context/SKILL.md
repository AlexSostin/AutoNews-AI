---
name: FreshMotors Project Context
description: Essential project setup, architecture, and conventions for AutoNews-AI
---

# FreshMotors / AutoNews-AI — Project Context

## 👤 About the User (IMPORTANT — read first)

- **Саша** — founder/product owner, NOT a software engineer
- He is LEARNING development as the project grows — explain everything as a **friendly teacher**, not as a code reviewer
- When explaining technical concepts (ML, caching, signals, etc.) — use **simple analogies**, avoid jargon
- The project moves very fast ("at the speed of light") — Саша relies on the assistant to remember context
- Language: Саша writes in **Russian**, respond in **Russian** for explanations, code remains in English
- Be **patient and encouraging** — celebrate progress, don't criticize gaps in knowledge
- When something is complex, break it into: **What is it? → Why do we need it? → How does it work here?**

## Architecture

- **Backend**: Django 6.0 + DRF 3.15, Python 3.13, Docker container `autonews_backend`
- **Frontend**: Next.js 16.1 (App Router, TypeScript, Tailwind CSS)
- **Database**: PostgreSQL 17 (Railway prod / Docker local dev on port 5433)
- **Cache/Queue**: Redis 7 (Railway prod / Docker local dev on port 6379)
- **Local Config**: `.env` (Docker hostnames) + `.env.local` (localhost overrides) → `settings.py` loads both
- **Task Queue**: Celery (background enrichment, auto-spec extraction, auto-publishing)
- **AI Primary**: Google Gemini 2.0 Flash
- **AI Fallback**: Groq Llama 3.3 70b (NOT OpenAI)
- **ML Engine**: TF-IDF Content Recommender (sklearn, zero-cost, self-learning)
- **Media CDN**: Cloudinary (Railway has ephemeral filesystem)
- **Monitoring**: Sentry + custom FrontendEventLog + BackendErrorLog

## Hosting & Deployment

- **Backend**: Railway (Django + PostgreSQL + Redis) → `api.freshmotors.net`
- **Frontend**: Vercel (Next.js, global CDN, Edge Network) → `freshmotors.net`
- **DNS**: Cloudflare (manages both domains)
- **CI/CD**: `git push origin main` → Railway auto-deploys backend + Vercel auto-deploys frontend
- **Deploy pipeline**: `start.sh` → migrations → verify → superuser → tags → collectstatic → train ML model → Daphne

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
  ai_engine/modules/   # AI generation, RSS discovery, scoring, ML engine
    content_recommender.py  # TF-IDF ML engine (recommendations, dedup, brand, health)
  news/management/commands/
    analyze_car_data.py     # ML car analytics (--health, --duplicates, --validate, --prices, --enrich)
    backfill_vehicle_specs.py # Backfill VehicleSpecs from articles
  scripts/
    analyze_tests.py    # Test analytics (dupes, coverage, prioritization)
  tests/               # pytest tests (1875+)

frontend-next/
  app/admin/           # Admin panel pages
  app/(public)/        # Public-facing pages
  components/          # Shared components
  lib/                 # API client, auth, error-logger
```

## Git Workflow

- Single branch: `main`
- `git push origin main` → Railway (backend) + Vercel (frontend) auto-deploy simultaneously
- Always run tests + build before pushing
- ⚠️ **GitKraken MCP push не работает** — всегда пушить через `run_command` с `git push origin main`
- ⚠️ **turbo.json удалён** — Vercel не поддерживал Turborepo, билдим через обычный `next build`

## Error Reporting

- Frontend errors → `logCaughtError()` from `lib/error-logger.ts`
- Errors logged to `/admin/health` dashboard
- Backend: `FrontendEventLog` model in `news/models/system.py`

## Important Conventions

- Backend API base: `/api/v1/`
- Frontend uses `lib/api.ts` (Axios with auth interceptor)
- All admin pages in `app/admin/` use Tailwind CSS
- User language: Russian (communicate in Russian)
- User name: **Алекс / Санёк / Сашка** — используй в зависимости от ситуации:
  - **Алекс** — нейтрально, по делу, формально
  - **Санёк** — дружески, когда что-то получилось / хорошее настроение
  - **Сашка** — неформально, по-простому, в лёгкой обстановке

## Known Gotchas (from past bugs)

- **Gemini 429 rate limits**: AI functions (spec extraction, article generation) hit rate limits. Always add retry logic (3 retries, 30/60/90s delays) and regex fallback
- **ISR cache**: Next.js caches pages. After content changes, set `revalidate: 30` not 300. Use `api/revalidate` endpoint for on-demand revalidation
- **Entity warning banners**: `entity_validator.py` can inject HTML warnings into article content stored in DB. Always strip `<div class="entity-mismatch-warning">` before rendering on public site
- **A/B title overwrite**: `ABTitle` component is currently disabled — it was overwriting manually edited titles with old A/B variants. If re-enabling, check `ArticleTitleVariant` cleanup logic
- **Cloudinary URLs**: `_get_image_url()` in `cars_views.py` can double-prefix URLs. Check for absolute URLs before prepending media host
- **DuckDuckGo search**: `duckduckgo_search` library can fail silently. Always wrap in try/except
- **Tailwind CSS warnings**: `@theme` and `@apply` in `globals.css` are Tailwind v4 directives, not errors
- **Infinite scroll `next-article`**: Must use `ArticleDetailSerializer` (not `ArticleListSerializer`) — list serializer has no `content` field, causes empty article body in scroll
- **Infinite scroll scroll anchor**: When adding article to DOM above footer, use `getBoundingClientRect().top` before + `requestAnimationFrame` after to restore footer viewport position
- **BackToTop smart click**: Custom event `article-active-slug` dispatched by `InfiniteArticleScroll` on each article switch; `BackToTop` listens and stores `activeSlugRef` for single-click jump to current article. Double-click = page top

## Color Theme System (3 themes)

The site has 3 color themes. **NO Tailwind dark mode** — do NOT use `dark:` classes on public pages.

| Theme | `data-theme` | Preview Color |
|---|---|---|
| Indigo (default) | _(none)_ | `#6366f1` |
| Emerald | `midnight-green` | `#10b981` |
| Ocean Blue | `deep-ocean` | `#3b82f6` |

**How it works**: `globals.css` overrides `--color-indigo-*` and `--color-purple-*` CSS variables via `[data-theme]` selectors. Components using `indigo-*` or `purple-*` Tailwind classes **automatically adapt** to all 3 themes.

**Key files**:

- `frontend-next/components/public/ThemeProvider.tsx` — context + `useTheme()` hook
- `frontend-next/components/public/ThemeSwitcher.tsx` — UI dropdown
- `frontend-next/app/globals.css` — CSS variable overrides per theme
- Theme stored in `localStorage('user-theme-choice')`, admin default in API `/site/theme/`

**Critical rules**:

- ✅ Use `indigo-*` / `purple-*` / `brand-*` classes → auto-adapts to theme
- ❌ Do NOT use `dark:` prefix on public pages — picks up OS dark mode, NOT site theme
- ❌ Do NOT hardcode specific colors (e.g. `#6366f1`) — use CSS variables

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

## ML System (Content Recommender)

All ML functions live in `ai_engine/modules/content_recommender.py`. Zero-cost (no API calls), uses sklearn TF-IDF.

### Core Functions

| Function | Purpose |
|---|---|
| `build()` | Train/rebuild TF-IDF model from published articles |
| `predict_tags()` | Predict tags via k-nearest in TF-IDF space |
| `predict_categories()` | Same approach for categories |
| `find_similar()` | Pre-computed similarity matrix |
| `semantic_search()` | Search by meaning, not keywords |
| `select_newsletter_articles()` | Diverse high-view picks |
| `extract_specs_from_text()` | Regex extraction of 15+ vehicle spec fields |

### Car Data Analytics (added 2026-03-02)

| Function | Purpose |
|---|---|
| `find_duplicate_specs()` | TF-IDF char n-gram similarity on make+model+trim |
| `validate_specs_consistency()` | Cross-check CarSpec vs VehicleSpecs (±10% tolerance) |
| `enrich_specs_from_similar()` | Fill empty fields from TF-IDF similar articles |
| `detect_price_anomalies()` | IQR-based statistical outlier detection by brand |
| `detect_brand()` | 6-step pipeline: sub-brand → exact → alias → partial → TF-IDF |
| `get_ml_health_report()` | Maturity level (1-5), per-feature scores, recommendations |

### ML Maturity Levels

| Level | Name | Articles | |
|---|---|---|---|
| 🥉 1 | Rookie | <50 | Basic regex |
| 🥈 2 | Learning | 50-200 | Recommendations + dedup |
| 🥇 3 | Competent | 200-500 | Good predictions |
| 💎 4 | Expert | 500-1000 | Precise search |
| 🏆 5 | Master | 1000+ | Maximum accuracy |

### Key Commands

```bash
# Health dashboard
python manage.py analyze_car_data --health

# Full analysis (dedup + validation + prices + enrichment)
python manage.py analyze_car_data

# Train/rebuild ML model
python manage.py train_content_model

# Backfill VehicleSpecs for articles without them
python manage.py backfill_vehicle_specs

# Test analytics (standalone, no Django needed)
python scripts/analyze_tests.py
```

### API Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/articles/ml-health/` | Full health report JSON |
| `GET /api/v1/articles/ml-info/` | Basic model info |
| `GET /api/v1/analytics/extra-stats/` | Subscriber growth, RSS stats, error summary |

### Brand Detection Pipeline (detect_brand())

1. Sub-brand check (Geely ZEEKR → ZEEKR) — runs FIRST before exact match
2. Exact regex match against Brand table
3. BrandAlias resolution (Huawei → Avatr)
4. 2-word alias combo (DongFeng VOYAH → VOYAH)
5. Case-insensitive partial match
6. TF-IDF fallback (find similar article's brand)

### Pricing Architecture

- `VehicleSpecs.get_price_display()` returns **original currency only** (no stale USD estimate)
- Frontend `PriceConverter` component handles **live** USD conversion via `/api/v1/currency-rates/`
- This prevents conflicting USD amounts (DB rate vs live rate)

## Prompt Injection Defense (added 2026-03-05)

All AI prompts are protected by a 3-layer defense system:

**Layer 1 — Gemini System Instruction Isolation**

- `ai_provider.py` → Gemini uses `system_instruction` API parameter (not string concat)
- Groq already had proper `role: system` / `role: user` separation

**Layer 2 — Centralized Sanitizer** (`ai_engine/modules/prompt_sanitizer.py`)

- `sanitize_for_prompt(text, max_length)` — strips 25+ injection patterns (instruction override, role hijack, model tokens, prompt leaking)
- `wrap_untrusted(text, label)` — wraps in `<LABEL role="data" trust="untrusted">` XML delimiters
- `ANTI_INJECTION_NOTICE` — constant appended after every external data block

**Layer 3 — Structural Delimiters in all prompts**
Protected modules: `analyzer.py`, `article_generator.py` (3 functions), `fact_checker.py` (2 functions), `translator.py`, `image_generator.py`, `article_generation.py` mixin, `vehicles.py`

**Key rule**: When adding NEW `generate_completion()` calls, ALWAYS:

1. Import `from ai_engine.modules.prompt_sanitizer import wrap_untrusted, ANTI_INJECTION_NOTICE`
2. Wrap external data: `wrap_untrusted(external_text, 'LABEL_NAME')`
3. Add `{ANTI_INJECTION_NOTICE}` after the wrapped block

## Known Technical Debt

- `CarSpecification` ↔ `VehicleSpecs` — duplicate models, need consolidation
- `notifications` admin page — dead (0 triggers)
- 5 dead AI modules identified in audit (1,078 lines to remove)
- Feed keyword search filter too strict — needs word-by-word matching instead of full phrase

## TODOs (Temporary Code to Remove)

- **`start.sh` line 19-22**: `train_content_model` runs on every deploy. Remove once ML model is stable and retrained via scheduled Celery task instead. Added: 2026-03-02

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

---

## ML Feedback Loop Architecture (RLHF in progress)

We collect human preference signals in two ways:

### 1. A/B Title Winner Logging (course-grained)

`ArticleTitleVariant` model — Саша manually picks winner from admin A/B panel.

**Fields for ML training:**

```python
selected_at         # timestamp of selection
selection_source    # 'admin' (manual) / 'auto' (CTR-based)
title_pattern       # JSON: pre-extracted features
```

**`title_pattern` features** (computed by `extract_title_pattern()` in `ab_testing_views.py`):

```json
{ "word_count": 9, "char_count": 67, "has_numbers": true,
  "has_question": false, "has_colon": true,
  "has_superlative": false, "has_spec": true, "uppercase_ratio": 0.09 }
```

Saved for **all variants** (winners AND losers) — contrast is what trains the model.

Migration: `0096_ab_title_variant_winner_tracking`

### 2. ArticleMicroFeedback (fine-grained)

`news/models/interactions.py` → `ArticleMicroFeedback`

Users give 👍/👎 on **specific article components** (not the whole article).
`component_type` examples: `vehicle_specs`, `fact_block`, `pros_cons`

This is our **fine-grained reward signal** — the most powerful form of feedback.
In 2025-2026 research this approach ("Fine-Grained RLHF") outperforms single reward signals.

### Roadmap to Full RLHF

```
NOW:  Logging human choices (selection_source, title_pattern, micro_feedback)
↓
NEXT: Pattern analysis — "titles with has_numbers=True win 70% of the time"
↓
FUTURE: Feed patterns back into Gemini prompt as style guidelines
↓
VISION: Fine-tuned reward model → auto-score generated titles without human review
```

### Key Principle (from 2025-2026 research)

- **Contrast beats volume**: 50 winner/loser pairs > 500 unlabelled examples
- **Domain specificity**: our car-spec titles (has_spec=True) are far more learnable than generic news
- **Admin as expert annotator**: for niche automotive content, Саша IS the expert signal
