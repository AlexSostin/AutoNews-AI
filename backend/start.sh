#!/bin/bash
# Railway start script for Django backend

echo "=== Running migrations ==="
python manage.py migrate --noinput

echo "=== Creating superuser from env (if set) ==="
python manage.py create_superuser_env || true

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

echo "=== Starting Daphne server ==="
daphne -b 0.0.0.0 -p ${PORT:-8000} auto_news_site.asgi:application
