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

## Debugging Checklist (Before Going Down Rabbit Holes)

1. **Check the exact error message** — copy it fully, don't paraphrase
2. **Verify setting names** — Django packages often have confusing names that are silently ignored if wrong
3. **Check if it's a dev-only issue** — CSP, CORS, and proxy issues often don't affect production
4. **Don't over-engineer** — fix the root cause, don't add proxy layers or middleware
5. **Stash changes and test clean** — `git stash` → run tests → confirms if the issue is from your changes or pre-existing
6. **Check CI independently** — CI failures may be unrelated to your current work (missing deps, API changes)
