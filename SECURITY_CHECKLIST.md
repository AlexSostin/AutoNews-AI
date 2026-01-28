# ====================================================
# 🔒 SECURITY CHECKLIST - Railway Deployment
# ====================================================

## ✅ PRE-DEPLOYMENT CHECKLIST

### 1. SECRET_KEY Generation
```bash
# Generate new SECRET_KEY for production:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
⚠️ **NEVER use the default SECRET_KEY in production!**

### 2. Environment Variables to Set in Railway:

#### Backend Service:
```env
SECRET_KEY=<generated-secret-key-from-step-1>
DEBUG=False
ALLOWED_HOSTS=.railway.app,yourdomain.com
ENVIRONMENT=production
GROQ_API_KEY=<your-groq-api-key>
SENTRY_DSN=https://87d896ae25bc56da5e80115c2c1364da@o4510742370648064.ingest.de.sentry.io/4510742712746064
CORS_ALLOWED_ORIGINS=https://your-frontend.railway.app,https://yourdomain.com
```

#### Frontend Service:
```env
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://your-backend.railway.app/api/v1
NEXT_PUBLIC_MEDIA_URL=https://your-backend.railway.app
NEXT_PUBLIC_SITE_URL=https://your-frontend.railway.app
NEXT_PUBLIC_SENTRY_DSN=https://87d896ae25bc56da5e80115c2c1364da@o4510742370648064.ingest.de.sentry.io/4510742712746064
```

#### PostgreSQL (Railway автоматически создаст):
Railway предоставит DATABASE_URL, который содержит все параметры подключения.

---

## 🔐 SECURITY MEASURES IN PLACE

### ✅ Already Configured:
- [x] SECRET_KEY from environment
- [x] DEBUG=False by default
- [x] ALLOWED_HOSTS from environment
- [x] CORS configured (only specific origins in production)
- [x] HTTPS redirect enabled (when DEBUG=False)
- [x] Secure cookies (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE)
- [x] HSTS enabled with 1-year duration
- [x] Sentry error tracking
- [x] JWT authentication with proper timeouts
- [x] Rate limiting (100/hour for anonymous, 1000/hour for users)
- [x] File upload size limits (5MB)
- [x] .env files in .gitignore

---

## 📋 POST-DEPLOYMENT CHECKLIST

### 1. Verify Security Headers
```bash
curl -I https://your-backend.railway.app
# Check for:
# - Strict-Transport-Security
# - X-Content-Type-Options: nosniff
# - X-Frame-Options: DENY
```

### 2. Test HTTPS Redirect
```bash
curl -I http://your-backend.railway.app
# Should redirect to https://
```

### 3. Check Sentry
- Go to: https://o4510742370648064.sentry.io/issues/
- Trigger test error
- Verify error appears in dashboard

### 4. Test CORS
```bash
curl -H "Origin: https://random-site.com" https://your-backend.railway.app/api/v1/articles/
# Should return CORS error (blocked)

curl -H "Origin: https://your-frontend.railway.app" https://your-backend.railway.app/api/v1/articles/
# Should work (allowed)
```

### 5. Verify Database Migrations
```bash
# Check Railway logs that migrations ran successfully
```

### 6. Test Authentication
- Try to login
- Check that JWT tokens work
- Verify admin panel access

---

## 🚨 NEVER COMMIT TO GIT:

- ❌ .env files (except .env.example)
- ❌ SECRET_KEY
- ❌ Database passwords
- ❌ API keys (GROQ_API_KEY)
- ❌ db.sqlite3
- ❌ /media/ folder with user uploads
- ❌ /logs/ folder

---

## 🔄 UPDATING PRODUCTION:

### Method 1: Git Push (Auto-deploy)
```bash
git push origin main
# Railway automatically rebuilds and deploys
```

### Method 2: Manual Deploy
- Go to Railway dashboard
- Click "Deploy" on your service

---

## 🆘 EMERGENCY PROCEDURES:

### Rollback to Previous Version:
1. Go to Railway dashboard
2. Go to "Deployments"
3. Click on previous working deployment
4. Click "Redeploy"

### Database Backup:
```bash
# From Railway dashboard or CLI
railway run pg_dump > backup.sql
```

### View Logs:
```bash
railway logs
```

---

## 📊 MONITORING:

### Check These Regularly:
1. **Sentry Dashboard** - For errors
2. **Railway Metrics** - CPU, Memory, Network usage
3. **Database Size** - Don't exceed plan limits
4. **Media Storage** - Monitor /media folder size

---

## 🎯 RECOMMENDED ADDITIONS (Optional):

### 1. Add Django Admin IP Restriction
```python
# settings.py
if not DEBUG:
    ALLOWED_ADMIN_IPS = os.getenv('ALLOWED_ADMIN_IPS', '').split(',')
    # Add middleware to check IP
```

### 2. Setup Automatic Backups
- Use Railway's backup feature
- Or setup cron job for pg_dump

### 3. Add Rate Limiting per IP
```python
# Use django-ratelimit for additional protection
```

### 4. Setup Uptime Monitoring
- Use UptimeRobot (free)
- Or Pingdom

---

## ✅ FINAL CHECK BEFORE GO-LIVE:

- [ ] New SECRET_KEY generated and set in Railway
- [ ] DEBUG=False confirmed
- [ ] ALLOWED_HOSTS includes your Railway domain
- [ ] All environment variables set in Railway dashboard
- [ ] Database migrations successful
- [ ] Static files collected
- [ ] Sentry receiving errors
- [ ] HTTPS working
- [ ] CORS configured correctly
- [ ] Admin panel accessible
- [ ] Authentication working
- [ ] Test created an article
- [ ] Test user registration/login
- [ ] All links working (frontend ↔ backend)

---

## 📞 SUPPORT:

If something breaks:
1. Check Railway logs
2. Check Sentry for errors
3. Verify environment variables
4. Check this security guide
5. Rollback to previous version if needed

**Good luck with deployment! 🚀**
