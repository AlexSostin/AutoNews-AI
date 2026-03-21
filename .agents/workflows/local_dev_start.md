---
description: How to start the full local development stack (Django + Celery + Next.js)
---

# Local Dev Stack

## 1. Activate Python environment and start Django backend

```bash
cd /home/kille_wsl/Projects/FreshMotors_GoogleAntigravity/AutoNews-AI/backend
source ../.env
python manage.py runserver 8000
```

## 2. Start Celery worker (required for article generation and regeneration)

Without this, any task that uses Celery (generate_from_youtube, regenerate) will hang in PENDING state forever.

// turbo
```bash
cd /home/kille_wsl/Projects/FreshMotors_GoogleAntigravity/AutoNews-AI/backend && source ../.venv/bin/activate 2>/dev/null || source ../venv/bin/activate 2>/dev/null; celery -A auto_news_site worker --loglevel=info -c 2
```

## 3. Start Next.js frontend

```bash
cd /home/kille_wsl/Projects/FreshMotors_GoogleAntigravity/AutoNews-AI/frontend-next
npm run dev
```

## Notes

- Celery requires Redis to be running (used as broker and result backend)
- Check Redis: `redis-cli ping` → should return `PONG`
- Tasks that use Celery: `generate_from_youtube`, `regenerate`, scheduled jobs (RSS scan, auto-publish, etc.)
- In production (Railway), Celery worker runs as a separate process automatically
