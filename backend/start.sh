#!/bin/bash
# Railway start script for Django backend

echo "=== Running migrations ==="
python manage.py migrate --noinput

echo "=== Verifying database schema ==="
python manage.py verify_migrations

echo "=== Creating superuser from env (if set) ==="
python manage.py create_superuser_env || true

echo "=== Populating tags ==="
python manage.py populate_tags || true

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

# TODO: TEMPORARY — auto-train ML model on deploy until it stabilizes
# Remove this once model is stable and trained via scheduled task instead
# Added: 2026-03-02 | Remove after: model is confirmed stable on prod
echo "=== Training ML content model ==="
python manage.py train_content_model || true

echo "=== Starting Daphne server ==="
daphne -b 0.0.0.0 -p ${PORT:-8000} auto_news_site.asgi:application --access-log -
