# 🚀 Deployment Guide - AutoNews on Railway

Complete guide for deploying AutoNews to Railway platform.

---

## ✅ Pre-Deployment Checklist

### Security (100% Ready):
- ✅ `SECRET_KEY` from environment variables
- ✅ `DEBUG=False` by default
- ✅ `ALLOWED_HOSTS` configured
- ✅ HTTPS redirect (SECURE_SSL_REDIRECT=True)
- ✅ Secure cookies (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE)
- ✅ HSTS with 1-year duration
- ✅ CORS restricted (only allowed domains)
- ✅ SecurityMiddleware activated
- ✅ XFrameOptionsMiddleware against clickjacking
- ✅ CsrfViewMiddleware protection
- ✅ .gitignore configured (no secrets in git)
- ✅ Sentry for error tracking
- ✅ Rate limiting (100 req/hour for anonymous, 1000 for authenticated)
- ✅ File upload limit (5MB)

---

## 🎯 Step-by-Step Deployment

### STEP 1: Create Railway Projects

1. Go to [Railway.app](https://railway.app)
2. Create **New Project** → **Empty Project**
3. Add 3 services:
   - **PostgreSQL** (Database)
   - **Backend** (Django)
   - **Frontend** (Next.js)

---

### STEP 2: Configure PostgreSQL

1. Click **+ New** → **Database** → **PostgreSQL**
2. Railway will automatically create the database
3. Copy the `DATABASE_URL` variable (appears automatically)
4. **IMPORTANT**: Remember this variable for Backend

---

### STEP 3: Configure Backend (Django)

#### 3.1 Connect Repository:
1. Click **+ New** → **GitHub Repo**
2. Select your `AutoNews-AI` repository
3. In **Root Directory** specify: `backend`

#### 3.2 Set Environment Variables:

Go to **Variables** and add:

```env
# 🔐 CRITICAL - Your new SECRET_KEY:
SECRET_KEY=your_generated_secret_key_here

# 🚨 MUST be False in production:
DEBUG=False

# 🌐 Domains (update after getting Railway URLs):
ALLOWED_HOSTS=.railway.app

# 🗄️ Database (copy from PostgreSQL service):
DATABASE_URL=postgresql://postgres:...@postgres.railway.internal:5432/railway

# 🔗 CORS (replace with actual frontend URL):
CORS_ALLOWED_ORIGINS=https://your-frontend.up.railway.app

# 🤖 API keys:
GROQ_API_KEY=your_groq_api_key

# 📊 Sentry:
SENTRY_DSN=your_sentry_dsn
ENVIRONMENT=production
```

#### 3.3 Configure Port:
In **Settings** → **Networking**:
- **Port**: `8001`

#### 3.4 Deploy Commands:
Railway will detect from Dockerfile automatically. If needed, override in **Settings** → **Deploy**:
```bash
# Build Command:
pip install -r requirements.txt

# Start Command:
python manage.py collectstatic --noinput && python manage.py migrate --noinput && daphne -b 0.0.0.0 -p 8001 auto_news_site.asgi:application
```

---

### STEP 4: Configure Frontend (Next.js)

#### 4.1 Connect Repository:
1. Click **+ New** → **GitHub Repo**
2. Select the same `AutoNews-AI` repository
3. In **Root Directory** specify: `frontend-next`

#### 4.2 Set Environment Variables:

Go to **Variables** and add:

```env
# 🌐 Node environment:
NODE_ENV=production

# 🔗 API URL (replace with actual backend URL):
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app/api/v1

# 🔗 For server-side rendering (internal Railway address):
NEXT_PUBLIC_API_URL_SERVER=http://backend:8001/api/v1
API_INTERNAL_URL=http://backend:8001/api/v1

# 📁 Media URL (images):
NEXT_PUBLIC_MEDIA_URL=https://your-backend.up.railway.app

# 🌍 Site URL:
NEXT_PUBLIC_SITE_URL=https://your-frontend.up.railway.app

# 📊 Sentry:
NEXT_PUBLIC_SENTRY_DSN=your_sentry_dsn
```

#### 4.3 Configure Port:
In **Settings** → **Networking**:
- **Port**: `3000`

---

### STEP 5: Update URLs

After deployment, Railway will provide URLs:
- Backend: `https://auto-news-backend-production.up.railway.app`
- Frontend: `https://auto-news-frontend-production.up.railway.app`

**IMPORTANT**: Update environment variables with real URLs:

#### Backend:
```env
ALLOWED_HOSTS=auto-news-backend-production.up.railway.app,.railway.app
CORS_ALLOWED_ORIGINS=https://auto-news-frontend-production.up.railway.app
```

#### Frontend:
```env
NEXT_PUBLIC_API_URL=https://auto-news-backend-production.up.railway.app/api/v1
NEXT_PUBLIC_MEDIA_URL=https://auto-news-backend-production.up.railway.app
NEXT_PUBLIC_SITE_URL=https://auto-news-frontend-production.up.railway.app
```

---

### STEP 6: Create Superuser

1. Go to **Backend service**
2. Open **Console** (Terminal)
3. Execute:
```bash
python manage.py createsuperuser
```

Enter:
- Username: `admin`
- Email: `your@email.com`
- Password: `strong_password_123!`

---

### STEP 7: Verify Deployment

#### Test 1: Backend API
```bash
curl https://your-backend.up.railway.app/api/v1/articles/
```
Should return JSON with articles.

#### Test 2: Django Admin
Open: `https://your-backend.up.railway.app/admin/`
Login with created superuser.

#### Test 3: Frontend
Open: `https://your-frontend.up.railway.app`
Site should load.

#### Test 4: Sentry
1. Open [Sentry Dashboard](https://sentry.io)
2. Trigger an error on the site
3. Verify error appears in Sentry

---

## 🆘 Common Issues

### ❌ "DisallowedHost at /"
**Cause**: Incorrect ALLOWED_HOSTS  
**Solution**: Add Railway URL to ALLOWED_HOSTS:
```env
ALLOWED_HOSTS=.railway.app,your-domain.railway.app
```

### ❌ "CORS error"
**Cause**: Frontend URL not in CORS_ALLOWED_ORIGINS  
**Solution**: Add exact frontend URL:
```env
CORS_ALLOWED_ORIGINS=https://your-frontend.up.railway.app
```

### ❌ "Database connection error"
**Cause**: Incorrect DATABASE_URL  
**Solution**: Copy DATABASE_URL from PostgreSQL service to Backend variables.

### ❌ "Static files not found"
**Cause**: collectstatic didn't run  
**Solution**: Check deployment logs, ensure command executed:
```bash
python manage.py collectstatic --noinput
```

---

## 💰 Pricing

Railway Hobby Plan:
- **$5/month** - includes $5 credits
- **Usage-based billing** after credits exhausted
- **Approximately $10-15/month** for this project:
  - PostgreSQL: ~$3-5
  - Backend: ~$3-5
  - Frontend: ~$3-5

**First month**: $5 (trial credits)

---

## 📊 Monitoring

### 1. Railway Dashboard:
- CPU Usage
- Memory Usage
- Bandwidth
- Deployment logs

### 2. Sentry Dashboard:
- Issues
- Performance
- Session Replay

---

## 🔄 Code Updates

After code changes:

1. **Commit and Push to GitHub**:
```bash
git add .
git commit -m "Update: description of changes"
git push origin main
```

2. **Railway automatically**:
- Detects changes in GitHub
- Rebuilds project
- Deploys new version

**Deployment time**: 2-5 minutes

---

## 🌐 Custom Domain (Optional)

When you buy a domain:

1. In Railway service → **Settings** → **Networking** → **Custom Domain**
2. Add domain: `example.com`
3. Railway will show CNAME record
4. At domain registrar (Namecheap, Porkbun) add CNAME:
   ```
   Type: CNAME
   Name: @
   Value: <railway-provided-value>
   ```

5. Update environment variables:
```env
# Backend:
ALLOWED_HOSTS=.railway.app,example.com

# Frontend:
NEXT_PUBLIC_SITE_URL=https://example.com
```

---

## ✅ Final Checklist

Before considering deployment complete:

- [ ] PostgreSQL service running
- [ ] Backend deploys without errors
- [ ] Frontend deploys without errors
- [ ] All environment variables set
- [ ] ALLOWED_HOSTS updated with Railway URLs
- [ ] CORS_ALLOWED_ORIGINS updated with Railway URLs
- [ ] Superuser created
- [ ] Django Admin opens
- [ ] Authentication works
- [ ] API returns data
- [ ] Frontend loads and shows articles
- [ ] Sentry receives errors
- [ ] Static files (CSS/JS) load
- [ ] Images display

---

## 📞 Support

If something goes wrong:

1. **Railway Logs**: Each service has a "Logs" tab
2. **Sentry Errors**: [Dashboard](https://sentry.io)
3. **Railway Discord**: [Community](https://discord.gg/railway)
4. **Documentation**: [Railway Docs](https://docs.railway.app)

---

**🎉 Good luck with deployment! Everything is ready for production!**
