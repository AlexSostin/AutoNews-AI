# Backend Security Guide 🔒

Security recommendations and best practices for AutoNews backend.

---

## ✅ Already Implemented

### Infrastructure

- ✅ SECRET_KEY in environment variables
- ✅ DEBUG = False in production
- ✅ ALLOWED_HOSTS configured
- ✅ PostgreSQL database with SSL
- ✅ HTTPS with HSTS enabled
- ✅ Secure cookies configured
- ✅ CORS properly configured
- ✅ CSRF protection enabled
- ✅ X-Frame-Options protection
- ✅ SQL injection protection (ORM)
- ✅ File upload size limits (5MB)
- ✅ Sentry error monitoring

### Authentication & Authorization (Phases 2, 3, 5)

- ✅ JWT authentication with token rotation
- ✅ JWT instant logout (token blacklist)
- ✅ Rate limiting on critical endpoints (5/15min login, 5/min generation)
- ✅ Brute-force protection (`django-axes`, 5 attempts → 30min lockout)
- ✅ `IsAdminUser` on 16 admin-only endpoints (generation, enrichment, AI images, moderation)
- ✅ TOTP 2FA for admin accounts (Google Authenticator + 8 backup codes)
- ✅ Login activity logging (success/fail with IP)

### XSS & Input Protection (Phases 1, Prompt Injection Audit)

- ✅ DOMPurify on 11 `dangerouslySetInnerHTML` instances (8 frontend files)
- ✅ Prompt injection defense: 3-layer system (`prompt_sanitizer.py` → XML delimiters → system instruction isolation)
- ✅ CI dependency scanning (`pip-audit` + `npm audit`)

### Monitoring & Audit (Phase 4)

- ✅ Sensitive data scrubbing in error logs (passwords, tokens, API keys → `***REDACTED***`)
- ✅ `AdminActionLog` for all destructive operations (delete, publish, unpublish, edit_save, reformat, regenerate, re_enrich)
- ✅ `ErrorCaptureMiddleware` auto-logs 500 errors with deduplication
- ✅ Security logging configured

---

## 🔐 Security Configuration

### Environment Variables

```env
# Django
SECRET_KEY=<64+ character random string>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,.railway.app

# Database
DATABASE_URL=postgresql://user:password@host:5432/db

# CORS
CORS_ORIGINS=https://yourdomain.com

# API Keys
GROQ_API_KEY=<your_key>
GEMINI_API_KEY=<your_key>

# Monitoring
SENTRY_DSN=<your_sentry_dsn>
ENVIRONMENT=production
```

### Security Headers

```python
# settings.py
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```

### Rate Limiting

```python
# Applied to critical endpoints
@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
def generate_from_youtube(self, request):
    ...

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),  # 15 minutes
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
```

---

## 📋 Production Checklist

- [x] SECRET_KEY in environment variables
- [x] DEBUG = False
- [x] ALLOWED_HOSTS configured
- [x] PostgreSQL instead of SQLite
- [x] HTTPS configured
- [x] Secure cookies enabled
- [x] Rate limiting configured
- [x] Logging configured
- [x] Error monitoring (Sentry)
- [x] All dependencies updated
- [x] .env in .gitignore
- [x] XSS protection (DOMPurify)
- [x] Brute-force protection (django-axes)
- [x] JWT blacklist (instant logout)
- [x] IsAdminUser on admin endpoints
- [x] Prompt injection defense
- [x] Error log data scrubbing
- [x] Admin action audit trail
- [x] TOTP 2FA for admin accounts
- [x] CI dependency vulnerability scanning

---

## 🔄 Regular Maintenance

### Monthly

- Review Sentry error logs
- Check for failed login attempts
- Update dependencies

### Quarterly

- Rotate SECRET_KEY
- Security audit
- Dependency vulnerability scan

---

For complete security documentation, see [SECURITY.md](../SECURITY.md) in the project root.
