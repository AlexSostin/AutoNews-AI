# Backend Security Guide 🔒

Security recommendations and best practices for AutoNews backend.

---

## ✅ Already Implemented

- ✅ SECRET_KEY in environment variables
- ✅ DEBUG = False in production
- ✅ ALLOWED_HOSTS configured
- ✅ PostgreSQL database with SSL
- ✅ HTTPS with HSTS enabled
- ✅ Secure cookies configured
- ✅ Rate limiting on critical endpoints
- ✅ Security logging configured
- ✅ CORS properly configured
- ✅ JWT authentication with token rotation
- ✅ CSRF protection enabled
- ✅ X-Frame-Options protection
- ✅ SQL injection protection (ORM)
- ✅ File upload size limits (5MB)
- ✅ Sentry error monitoring

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
