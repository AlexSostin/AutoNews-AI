# Откаченные улучшения (Local Dev CORS) — 2026-03-03

Эти изменения были застэшены и удалены. Документация сохранена для будущей реализации.

---

## 1. `settings.py` — CORS headers fix ✅ (безопасно для production)

**Проблема:** `CORS_ALLOWED_HEADERS` — неправильное имя настройки django-cors-headers. Sentry шлёт `sentry-trace` и `baggage` которые блокировались.

```diff
-CORS_ALLOWED_HEADERS = [
+CORS_ALLOW_HEADERS = [
     'accept', 'accept-encoding', 'authorization',
     'content-type', 'dnt', 'origin',
     'user-agent', 'x-csrftoken', 'x-requested-with',
+    'sentry-trace',
+    'baggage',
 ]
```

> **ВАЖНО:** Это изменение **нужно** для production — без него Sentry CORS preflight падает.

---

## 2. `bot_protection.py` — Allow all localhost requests

**Проблема:** Next.js rewrite proxy шлёт запросы с `127.0.0.1` но с non-browser UA (`undici`), бот-защита блокировала.

```diff
-# Allow empty UA from internal/localhost
-if not user_agent:
-    client_ip = self._get_ip(request)
-    if client_ip in ('127.0.0.1', '::1', 'localhost'):
-        return self.get_response(request)
+client_ip = self._get_ip(request)
+# Allow ALL requests from localhost/internal IPs
+if client_ip in ('127.0.0.1', '::1', 'localhost') or client_ip.startswith('172.') or client_ip.startswith('10.'):
+    return self.get_response(request)
```

---

## 3. `api.ts` — Proxy через Next.js rewrite

**Проблема:** Client-side fetch шёл напрямую на `http://localhost:8000`, вызывая CORS.

```diff
 if (isLocalNetwork) {
-    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
-      return `http://${hostname}:8000/api/v1`;
-    }
-    return LOCAL_API_URL;
+    // Use Next.js rewrite proxy — avoids CORS entirely
+    return '/api/v1';
 }
```

---

## 4. `config.ts` — То же для error-logger

```diff
+if (typeof window !== 'undefined') {
+    return '/api/v1';  // Client-side local dev: use Next.js proxy
+}
 return LOCAL_API_URL;  // Server-side local dev: direct
```

---

## 5. `next.config.ts` — CSP prod-only + trailing slash fix

```diff
+skipTrailingSlashRedirect: true,  // Django APPEND_SLASH compatibility

 // CSP made production-only to avoid dev conflicts
+const isProd = process.env.NODE_ENV === 'production';
+if (isProd) { securityHeaders.push({ key: 'Content-Security-Policy', ... }); }

 // Added worker-src for Sentry replay
+worker-src 'self' blob:
```

---

## Статус

Все эти изменения были `git stash drop` — код вернулся к HEAD `1745f70`.

Для будущей реализации: **пункт 1 (settings.py)** нужно применить отдельно, он фиксит реальный production-баг с Sentry headers.
