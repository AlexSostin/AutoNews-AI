---
name: Troubleshooting Guide
description: Solved bugs, CORS issues, CI failures, and debugging patterns for AutoNews-AI
---

# Troubleshooting Guide — Solved Issues & Patterns

Quick reference for bugs we've already solved. Check here BEFORE debugging from scratch.

---

## CORS Errors (sentry-trace / baggage)

**Symptom**: Browser console shows:

```
Access to fetch at 'http://localhost:8000/api/v1/...' from origin 'http://localhost:3000'
has been blocked by CORS policy:
Request header field sentry-trace is not allowed by Access-Control-Allow-Headers
```

**Root Cause**: TWO bugs combined:

1. `CORS_ALLOWED_HEADERS` (wrong name!) — `django-cors-headers` expects `CORS_ALLOW_HEADERS` (without "ED"). The wrong name is **silently ignored**, so Django uses default headers list
2. Missing `sentry-trace` and `baggage` in allowed headers — Sentry SDK adds these to every fetch request automatically

**Fix** (`backend/auto_news_site/settings.py`):

```python
# WRONG (silently ignored!):
CORS_ALLOWED_HEADERS = [...]

# CORRECT:
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'sentry-trace',   # ← Sentry distributed tracing
    'baggage',        # ← Sentry baggage header
]
```

**Safe for production**: ✅ Yes — these are standard Sentry headers, no security risk. Actually **improves** production Sentry tracing.

**Lesson learned**: `django-cors-headers` has confusing setting names. Always verify: `CORS_ALLOW_HEADERS` (not ALLOWED), `CORS_ALLOW_METHODS` (not ALLOWED), etc. The library **silently ignores** misspelled settings.

---

## CSP Worker-src Error (Sentry Replay)

**Symptom**: Browser console shows:

```
Creating a worker from 'blob:http://localhost:3000/...' violates Content Security Policy
directive: "script-src ...". Note that 'worker-src' was not explicitly set, so 'script-src'
is used as a fallback.
```

**Root Cause**: Sentry Session Replay creates Web Workers from blob URLs. The CSP in `next.config.ts` didn't include `worker-src`, so the browser fell back to `script-src` which didn't allow `blob:`.

**Fix** (`frontend-next/next.config.ts`): Add `worker-src 'self' blob:;` to the CSP header.

**Safe for production**: ✅ Yes — only allows workers from same origin and blob URLs (needed for Sentry).

---

## API Proxy Approach — DON'T DO THIS

**What we tried**: Routing client-side API requests through Next.js rewrites proxy (`/api/v1` → `http://localhost:8000/api/v1`) to avoid CORS entirely.

**Files modified**:

- `lib/api.ts` — `getApiUrl()` → `/api/v1`
- `lib/config.ts` — `getRuntimeApiUrl()` → `/api/v1`
- `next.config.ts` — `skipTrailingSlashRedirect: true`
- `backend/news/bot_protection.py` — allow all localhost

**Why it's DANGEROUS**: ❌ **Breaks production!** Railway/Vercel deployment doesn't have this proxy setup. Requests to `/api/v1` on Vercel would hit Next.js routes, not the Django backend.

**Lesson**: Fix the actual CORS problem (correct setting names + add headers) instead of adding a proxy layer that only works locally. The proxy creates more problems than it solves.

---

## CI Pipeline Failures

### Missing `sendgrid` dependency

**Symptom**: CI fails with `ModuleNotFoundError: No module named 'sendgrid'`

**Root Cause**: `sendgrid` package is imported in email-related code but not in `requirements.txt`.

**Fix**: Add `sendgrid` to `requirements.txt` and `pip install sendgrid`.

### DDGS (DuckDuckGo Search) test failures

**Symptom**: 2 tests fail related to `duckduckgo_search` (DDGS) library.

**Root Cause**: The `duckduckgo-search` library updates frequently and changes its API. Mocks may become outdated.

**Fix**: Update `duckduckgo-search` package and verify/update test mocks accordingly.

---

## Stale Docker-Proxy → Ghost PostgreSQL (CRITICAL, 2026-03-03)

**Time lost**: ~3 hours debugging perfectly correct code.

**Symptom**: Admin panel (`/admin/brands`) showed 18 brands (8 visible), but public `/cars` page showed 13 brands (all visible). Visibility toggle (`is_visible`) appeared not to work. Code was correct — `Brand.objects.filter(is_visible=True)` was there.

**Investigation path** (what DIDN'T help):

1. ❌ Checked Django code — filter was correct
2. ❌ Checked .env — settings looked fine
3. ❌ Checked Redis cache — no brands cache
4. ❌ Restarted Django — still 13 brands
5. ❌ Touched public_views.py — no change

**What DID help** — checking PostgreSQL version from inside vs outside Docker:

```bash
# Inside Docker (correct PG 17)
docker exec autonews_postgres psql -U autonews_user -d autonews -c "SELECT version();"
# → PostgreSQL 17.8 ✅ (18 brands, 8 visible)

# Outside Docker (wrong PG 15!)
PGPASSWORD=SecurePass123 psql -h localhost -p 5433 -U autonews_user -d autonews -c "SELECT version();"
# → PostgreSQL 15.16 ❌ (13 brands, all visible)
```

**Root cause**: A **stale `docker-proxy` process** (started Feb 28, PIDs 980/990) was still routing `localhost:5433` to an old container IP (`172.18.0.5`, PG 15). The new `autonews_postgres` container (PG 17) had IP `172.18.0.2`, but the old proxy was never cleaned up.

```bash
# How to detect stale docker-proxy:
ps aux | grep "docker-proxy.*5433"
# → root 980 ... /usr/bin/docker-proxy -container-ip 172.18.0.5 -container-port 5432
# If container IP doesn't match current container → STALE!
```

**Fix**:

```bash
sudo kill 980 990           # Kill stale proxies
docker compose restart postgres  # Creates fresh proxies
```

**Prevention**: Added `.env.local` system (see next section).

**Lesson**: When Docker data looks inconsistent, **ALWAYS compare `SELECT version()` from inside vs outside**. Different versions = different databases = stale docker-proxy.

---

## Local Dev Environment Setup (2026-03-03)

### Architecture

```
Docker:     PostgreSQL 17 (port 5433) + Redis (port 6379)
Local:      Django runserver (port 8000) + Next.js dev (port 3000)
```

### Config files

| File | Purpose | Used by |
|---|---|---|
| `.env` | Base config (Docker hostnames: `postgres`, `redis`) | Docker backend |
| `.env.local` | Overrides for local dev (`127.0.0.1:5433`) | Local `manage.py` |
| `settings.py` | Loads both: `.env` then `.env.local` (override=True) | Both |

**How it works**:

- **Inside Docker**: `.env.local` doesn't exist → `DB_HOST=postgres`, `DB_PORT=5432`
- **Outside Docker (local)**: `.env.local` overrides → `DB_HOST=127.0.0.1`, `DB_PORT=5433`
- **Production (Railway)**: `DATABASE_URL` env var → `dj_database_url.parse()` (bypasses both files)

### Env var naming

Settings.py expects these exact names:

```python
'NAME': os.getenv('POSTGRES_DB', 'autonews'),        # NOT DB_NAME
'USER': os.getenv('POSTGRES_USER', 'autonews_user'),  # NOT DB_USER
'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),        # NOT DB_PASSWORD
'HOST': os.getenv('DB_HOST', '127.0.0.1'),
'PORT': os.getenv('DB_PORT', '5433'),
```

⚠️ **If you rename env vars, make sure settings.py `os.getenv()` calls match!** Mismatched names are silently ignored (defaults used).

---

## Docker Debugging Playbook

When Docker data looks wrong, run these checks **in order**:

### 1. Version check (is it the same DB?)

```bash
docker exec autonews_postgres psql -U autonews_user -d autonews -c "SELECT version();"
PGPASSWORD=SecurePass123 psql -h localhost -p 5433 -U autonews_user -d autonews -c "SELECT version();"
# Different versions = DIFFERENT databases!
```

### 2. Stale docker-proxy check

```bash
ps aux | grep "docker-proxy.*5433"
docker inspect autonews_postgres --format='{{range .NetworkSettings.Networks}}IP: {{.IPAddress}}{{end}}'
# Proxy container-ip MUST match inspect IP
```

### 3. Port binding check

```bash
ss -tlnp | grep 5433
# Should show docker-proxy, NOT a bare postgres process
```

### 4. Data consistency check

```bash
# Run same query inside and outside — results MUST match
docker exec autonews_postgres psql -U autonews_user -d autonews -c "SELECT COUNT(*) FROM news_brand;"
PGPASSWORD=SecurePass123 psql -h localhost -p 5433 -U autonews_user -d autonews -c "SELECT COUNT(*) FROM news_brand;"
```

### 5. Nuclear fix (if proxies are stale)

```bash
docker compose down
docker volume prune -f
sudo kill $(pgrep -f "docker-proxy.*5433")  # Kill stale proxies
docker compose up -d postgres redis
```

---

## Debugging Checklist (Before Going Down Rabbit Holes)

1. **Check the exact error message** — copy it fully, don't paraphrase
2. **Verify setting names** — Django packages often have confusing names that are silently ignored if wrong
3. **Check if it's a dev-only issue** — CSP, CORS, and proxy issues often don't affect production
4. **Don't over-engineer** — fix the root cause, don't add proxy layers or middleware
5. **Stash changes and test clean** — `git stash` → run tests → confirms if the issue is from your changes or pre-existing
6. **Check CI independently** — CI failures may be unrelated to your current work (missing deps, API changes)
7. **Compare Docker inside vs outside** — different PostgreSQL versions = stale docker-proxy = ghost DB!
8. **Check env var names match** — `POSTGRES_DB` ≠ `DB_NAME`, silent fallback to defaults
9. **AI prompt injection** — when adding new `generate_completion()` calls, always use `wrap_untrusted()` from `prompt_sanitizer.py` for external data. Never f-string raw user/RSS/web content into prompts
10. **⚠️ After adding packages to requirements.txt** — ALWAYS rebuild Docker image: `docker compose build backend` (from `/backend` dir). Without rebuild the container runs the OLD image without the new packages → `ModuleNotFoundError`. This happened with `django-axes`, `pyotp`, `qrcode` (March 2026).

---

## WSL Zombie Port (port 3000 stuck after closing terminal)

**Symptom**: `npm run dev` says "Port 3000 is in use by an unknown process" even though no terminal is running the frontend. Happens almost every day in WSL after closing VS Code terminal without stopping the dev server.

**Fix** (two commands):

```bash
# 1. Kill whatever holds port 3000
sudo fuser -k 3000/tcp

# 2. Start frontend fresh
cd /home/kille_wsl/Projects/FreshMotors_GoogleAntigravity/AutoNews-AI/frontend-next && npm run dev
```

**Why it happens**: WSL doesn't always clean up child processes when a terminal is closed. The Node.js dev server stays alive as a zombie process without a parent terminal. `fuser -k` sends SIGKILL to all processes on that port.

**Alternative** if `fuser` is not installed:

```bash
sudo lsof -ti:3000 | xargs sudo kill -9
```

---

## 2FA Login Flow — Critical Gotchas (March 2026)

### Gotcha 1: Missing `permission_classes = [AllowAny]` on verify endpoints

**Symptom**: `/api/v1/auth/2fa/verify/` always returns `401` even with correct credentials and correct TOTP code.

**Root cause**: DRF global default is `IsAuthenticatedOrReadOnly`. POST requests from unauthenticated users are blocked **before your view code runs**.

**Fix**: Always add `permission_classes = [AllowAny]` to any endpoint called before login is complete:

```python
class TwoFactorVerifyView(APIView):
    permission_classes = [AllowAny]  # ← REQUIRED

class TwoFactorGoogleVerifyView(APIView):
    permission_classes = [AllowAny]  # ← REQUIRED
```

**Applies to**: any verify/refresh/reset-password endpoint that users hit without a JWT.

---

### Gotcha 2: `django-axes` blocks `authenticate()` in verify endpoints

**Symptom**: After a few failed login attempts, `TwoFactorVerifyView` starts returning 401 for correct credentials.

**Root cause**: `django-axes` intercepts all calls to Django's `authenticate()`. If the user's IP is locked out from `/token/` failures, `authenticate()` in your verify endpoint also returns `None`.

**Fix**: Replace `authenticate()` with direct user lookup + `check_password()`:

```python
# WRONG — axes can block this
user = authenticate(request, username=username, password=password)

# CORRECT — bypasses axes (safe because 2FA adds a second factor)
try:
    user = User.objects.get(username__iexact=username)
except User.DoesNotExist:
    return Response({'detail': 'Invalid credentials.'}, status=401)
if not user.check_password(password):
    return Response({'detail': 'Invalid credentials.'}, status=401)
```

---

### Gotcha 3: Google OAuth bypasses 2FA

**Symptom**: Staff user with 2FA enabled can log in via Google without entering TOTP.

**Root cause**: `google_oauth` view calls `RefreshToken.for_user(user)` directly without checking for 2FA.

**Fix** (`user_accounts.py`): Check `TOTPDevice` before issuing tokens:

```python
if user.is_staff and TOTPDevice.objects.filter(user=user, is_confirmed=True).exists():
    return Response({'requires_2fa': True, 'google_user_id': str(user.id)}, status=200)
# Only proceed to token generation if no 2FA required
```

New endpoint: `POST /api/v1/auth/2fa/google-verify/` with `{google_user_id, totp_code}`.

---

### Gotcha 4: 2FA must be staff-only in the token endpoint

**Fix** (`api_urls.py`): Add `user.is_staff` check before the 2FA gate:

```python
if user.is_staff:
    has_2fa = TOTPDevice.objects.filter(user=user, is_confirmed=True).exists()
    if has_2fa:
        return Response({'requires_2fa': True}, status=200)
```

Regular users should never see the 2FA screen.

---

## Tailwind `dark:` Classes in Admin Panel

**Symptom**: Admin UI tables/badges turn black/unreadable for users with dark OS mode.

**Root cause**: Tailwind uses `darkMode: 'media'` (OS preference) by default. Components with `dark:bg-gray-800` etc. render dark for all users with dark OS.

**Fix**: Remove all `dark:` variants from admin components that should always be light:

```tsx
// WRONG — goes black on dark OS
<div className="bg-white dark:bg-gray-800">

// CORRECT — always white
<div className="bg-white">
```

Affected files: `UserTable.tsx`, `UserRoleBadge.tsx`, and any admin component.
