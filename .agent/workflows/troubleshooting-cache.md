---
description: Troubleshooting cache and ISR issues — Vercel + Django + Redis
---

# Cache & ISR Troubleshooting Guide

## Problem: Articles don't appear/disappear on homepage after toggle publish

### Root Cause (March 2026)
Vercel ISR `revalidatePath` / `revalidateTag` via Route Handlers is **unreliable**. 
The API returns `revalidated: true` but the Vercel edge cache retains stale HTML.

### Solution
Use `force-dynamic` + `cache: 'no-store'` for pages that must always show fresh article data:

```tsx
// page.tsx
export const dynamic = 'force-dynamic';

// In fetch calls for articles:
fetch(url, { cache: 'no-store' })  // NOT next: { revalidate: 60, tags: [...] }
```

Keep ISR caching (`next: { revalidate: N }`) only for rarely-changing data (categories, brands, settings).

### Files involved
- `frontend-next/app/(public)/page.tsx` — homepage
- `frontend-next/app/(public)/articles/page.tsx` — article listing
- `frontend-next/app/api/revalidate/route.ts` — on-demand revalidation endpoint

---

## Problem: Backend API returns stale cached article list (Redis)

### Root Cause
Django `@cache_page(60, key_prefix='articles_list')` caches API responses in Redis.
Redis persists across deployments (unlike Vercel ISR which resets on deploy).

### Solution
1. `cache_signals.py` → `_delete_cache_page_prefix('articles_list')` clears on Article save/delete
2. `scheduler.py` → `start_scheduler()` flushes `cache_page` keys on every deploy/restart
3. Session keys (`django.contrib.sessions*`) are NOT touched during flush

### Verifying Redis cache is cleared
```bash
# Check what cache_page keys exist in Redis
redis-cli --scan --pattern "*cache_page*" | head -20
```

---

## Problem: Toggle button sends multiple requests (race condition)

### Root Cause
Frontend toggle button fires multiple rapid POST requests if user clicks fast.
Backend `toggle_publish` does `article.is_published = not article.is_published` — each request flips state.

### Solution (if needed)
1. **Frontend**: Add loading state / disable button during API call
2. **Backend**: Accept explicit `publish: true/false` instead of blind toggle (idempotent)

---

## Debugging Checklist

1. **Is article published in DB?**
   ```bash
   curl -s "https://BACKEND_URL/api/v1/articles/SLUG/" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('is_published'))"
   ```

2. **Is article in the list API?**
   ```bash
   curl -s "https://BACKEND_URL/api/v1/articles/?is_published=true" | python3 -c "import sys,json; d=json.load(sys.stdin); print([a['title'] for a in d['results'] if 'KEYWORD' in a['title']])"
   ```

3. **Check backend logs for revalidation**
   Look for: `[TOGGLE-PUBLISH]`, `🔄 Triggering Next.js revalidation`, `✅ Next.js revalidation OK`

4. **Check for multiple rapid requests**
   If you see `→ draft` and `→ published` alternating in the same second = race condition

5. **Vercel function logs**
   Check for `[REVALIDATE] Tags invalidated` and `[REVALIDATE] Paths invalidated` in Vercel logs

---

## Architecture: Cache Layers (top → bottom)

```
Browser → Vercel CDN Edge → Next.js ISR (force-dynamic bypasses) → Backend API → Redis cache_page (60s) → PostgreSQL
```

- **Vercel CDN**: Controlled by `Cache-Control` header and `revalidate` export
- **Next.js ISR**: Controlled by `cache: 'no-store'` vs `next: { revalidate: N }`
- **Redis cache_page**: Controlled by `@cache_page` decorator + `invalidate_article_caches()`
- **PostgreSQL**: Always fresh, source of truth
