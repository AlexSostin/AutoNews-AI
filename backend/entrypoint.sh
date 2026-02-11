#!/bin/bash

# Exit on error
set -e

echo "========================================="
echo "🚗 Fresh Motors Backend Starting..."
echo "========================================="

# Check Cloudinary configuration
if [ -n "$CLOUDINARY_URL" ]; then
    echo "✓ CLOUDINARY_URL is set - media files will persist!"
else
    echo "⚠️ WARNING: CLOUDINARY_URL not set!"
    echo "   Media files will be LOST on every redeploy!"
    echo "   Set CLOUDINARY_URL in Railway variables."
fi

# Run branding update only once (on first deploy after this change)
BRANDING_FLAG="/tmp/.branding_updated"
if [ ! -f "$BRANDING_FLAG" ]; then
    echo "🎨 Updating branding to Fresh Motors..."
    python manage.py update_branding || echo "⚠️ Branding update failed (might not exist yet)"
    touch "$BRANDING_FLAG"
    echo "✅ Branding update complete"
fi

echo "Running migrations..."

# Fix: unfake previously faked migrations so they actually apply
echo "🔧 Checking migration state..."
python manage.py migrate news 0037 --fake 2>&1 || true
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Populating tags..."
python manage.py populate_tags || echo "Tags population skipped"

echo "📊 Indexing articles for vector search (background)..."
(python manage.py index_articles &) || echo "Article indexing skipped"

# One-time reset of views (remove after first deploy)
if [ "$RESET_VIEWS_ONCE" = "true" ]; then
    echo "Resetting view counts for real analytics..."
    python manage.py reset_views || echo "Views reset skipped"
fi

echo "Creating superuser if not exists..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
import os

User = get_user_model()
username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created successfully!")
else:
    print(f"Superuser '{username}' already exists.")
EOF

echo "========================================="
echo "✓ Starting Daphne server on port 8001..."
echo "========================================="
exec daphne -b 0.0.0.0 -p 8001 auto_news_site.asgi:application
