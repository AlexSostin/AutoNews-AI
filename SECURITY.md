# 🔐 Security Guide - AutoNews

Comprehensive security documentation for the AutoNews platform.

**Last Updated**: February 2026  
**Environment**: Railway.app (Production)  
**Status**: ✅ Production Ready

---

## 📊 Security Overview

| Category | Rating | Status |
|----------|--------|--------|
| Authentication | 9/10 | ✅ Excellent |
| Authorization | 8/10 | ✅ Good |
| CORS & HTTPS | 9/10 | ✅ Excellent |
| Secrets Management | 9/10 | ✅ Excellent |
| Rate Limiting | 8/10 | ✅ Good |
| Input Validation | 8/10 | ✅ Good |
| Logging | 8/10 | ✅ Good |
| Infrastructure | 9/10 | ✅ Excellent |

**Overall Rating: 8.5/10** ✅

---

## ✅ Security Features Implemented

### 1. HTTPS & Secure Headers
```python
# settings.py - Production Configuration
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```

### 2. JWT Authentication
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ]
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

### 3. CORS Configuration
```python
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only in development
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',')
CORS_ALLOW_CREDENTIALS = True
```

### 4. Rate Limiting
```python
# Applied to critical endpoints
@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
def generate_from_youtube(self, request):
    ...

@method_decorator(ratelimit(key='user', rate='5/h', method='POST'))
class ChangePasswordView(APIView):
    ...
```

### 5. Environment Variables
- ✅ SECRET_KEY not hardcoded
- ✅ DEBUG = False in production
- ✅ Database passwords in environment variables
- ✅ .env in .gitignore
- ✅ API keys secured

### 6. Database Security
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'sslmode': 'require',  # SSL for database connections
        }
    }
}
```

### 7. Error Tracking
```python
# Sentry integration for production error monitoring
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=os.getenv('ENVIRONMENT', 'production'),
        traces_sample_rate=0.1,
    )
```

---

## 🔒 Security Checklist

### Before Production Deployment

- [x] SECRET_KEY is unique and complex (64+ characters)
- [x] DEBUG = False
- [x] ALLOWED_HOSTS configured
- [x] HTTPS enabled with HSTS
- [x] CSRF protection enabled
- [x] Rate limiting on auth endpoints
- [x] JWT tokens with short expiration
- [x] Security logging configured
- [x] CORS properly configured
- [x] Database SSL enabled
- [x] Sentry error tracking
- [x] .env files in .gitignore
- [x] File upload size limits (5MB)
- [x] Input validation on all forms
- [x] Bot protection (User-Agent middleware)
- [x] CI pipeline with 75 automated tests

**Completed: 16/16 (100%)**

---

## 🛡️ Best Practices

### 1. Password Security
```python
# Strong password requirements
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
```

### 2. File Upload Security
```python
# Limit file sizes and types
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# Validate file types
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
```

### 3. API Security
```python
# Throttling for anonymous and authenticated users
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
```

### 4. Logging Security Events
```python
LOGGING = {
    'handlers': {
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 30,
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
        },
    },
}
```

---

## 🔐 Secrets Management

### Required Environment Variables

**Django:**
```env
SECRET_KEY=<64+ character random string>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,.railway.app
```

**Database:**
```env
DATABASE_URL=postgresql://user:password@host:5432/db
```

**CORS:**
```env
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

**API Keys:**
```env
GROQ_API_KEY=<your_groq_key>
GEMINI_API_KEY=<your_gemini_key>
```

**Monitoring:**
```env
SENTRY_DSN=<your_sentry_dsn>
ENVIRONMENT=production
```

### Generating Secure Keys

```bash
# Generate SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate random password (16+ characters)
python -c "import secrets; import string; chars = string.ascii_letters + string.digits + string.punctuation; print(''.join(secrets.choice(chars) for _ in range(24)))"
```

---

## 🚨 Security Incident Response

### If You Discover a Vulnerability

1. **Do NOT** disclose publicly
2. Email: security@freshmotors.net
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

**Response Time**: 24-48 hours

### If Credentials Are Compromised

1. **Immediately** rotate affected secrets:
   ```bash
   # Update in Railway dashboard
   - SECRET_KEY
   - DATABASE_URL password
   - API keys
   ```

2. **Invalidate** all JWT tokens:
   ```bash
   python manage.py flush_expired_tokens
   ```

3. **Review** access logs in Sentry

4. **Notify** users if user data was accessed

---

## 🔄 Regular Maintenance

### Monthly Tasks
- [ ] Review Sentry error logs
- [ ] Check for failed login attempts
- [ ] Update dependencies (`pip list --outdated`)
- [ ] Review rate limiting effectiveness

### Quarterly Tasks
- [ ] Rotate SECRET_KEY
- [ ] Rotate admin passwords
- [ ] Security audit of new features
- [ ] Dependency vulnerability scan

### Annually
- [ ] Full security penetration test
- [ ] Review and update security policies
- [ ] Audit user permissions
- [ ] Review backup and recovery procedures

---

## 📋 Dependency Security

### Automated Scanning
```bash
# Install safety
pip install safety

# Check for vulnerabilities
safety check --json

# Or use pip-audit
pip install pip-audit
pip-audit
```

### GitHub Dependabot
- ✅ Enabled for automatic dependency updates
- ✅ Security alerts configured
- ✅ Auto-merge for patch updates

---

## 🛡️ Additional Security Measures

### 1. Database Backups
```bash
# Automated daily backups in Railway
# Retention: 7 days minimum
# Manual backup:
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### 2. Monitoring & Alerts
- ✅ Sentry for error tracking
- ✅ Railway metrics (CPU, Memory, Bandwidth)
- ✅ Failed login attempt logging
- ✅ Rate limit violation alerts

### 3. Content Security Policy (CSP)
```python
# Recommended CSP headers
SECURE_CONTENT_SECURITY_POLICY = {
    'default-src': ["'self'"],
    'script-src': ["'self'", "'unsafe-inline'", 'https://cdn.jsdelivr.net'],
    'style-src': ["'self'", "'unsafe-inline'", 'https://fonts.googleapis.com'],
    'img-src': ["'self'", 'data:', 'https:'],
    'font-src': ["'self'", 'https://fonts.gstatic.com'],
    'connect-src': ["'self'", 'https://your-api.railway.app'],
    'frame-ancestors': ["'none'"],
}
```

---

## 📞 Security Contacts

**Security Team**: security@freshmotors.net  
**Response Time**: 24-48 hours  
**PGP Key**: Available on request

---

## 📝 Version History

- **v3.0** - February 2026 - Added A/B testing, automation system, CI pipeline (75 tests), bot protection
- **v2.0** - January 2026 - Updated for Railway deployment
- **v1.0** - December 2025 - Initial security implementation

**Next Security Audit**: April 2026
