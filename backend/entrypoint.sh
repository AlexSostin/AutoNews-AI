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

# One-time migration fix: replace old migration records with new ones
# Production DB has records for deleted migrations (0038_vehiclespecs, 0039_merge).
# We need to replace them with the new 0038_vehiclespecs_and_more.
echo "🔧 Checking migration state..."
set +e  # Disable exit-on-error for migration fix
python manage.py shell << 'MIGRATION_FIX_EOF'
from django.db import connection
cursor = connection.cursor()
try:
    cursor.execute("SELECT name FROM django_migrations WHERE app='news' AND name IN ('0038_vehiclespecs', '0039_merge_0038_vehiclespecs_0038_vehiclespecs_and_more')")
    old_records = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app='news' AND name='0038_vehiclespecs_and_more'")
    new_exists = cursor.fetchone()[0] > 0

    if old_records and not new_exists:
        print(f"Found {len(old_records)} old migration record(s) to fix...")
        cursor.execute("DELETE FROM django_migrations WHERE app='news' AND name IN ('0038_vehiclespecs', '0039_merge_0038_vehiclespecs_0038_vehiclespecs_and_more')")
        cursor.execute("INSERT INTO django_migrations (app, name, applied) VALUES ('news', '0038_vehiclespecs_and_more', NOW())")
        connection.connection.commit()
        print("Migration records fixed!")
    elif old_records and new_exists:
        print("Cleaning up old records...")
        cursor.execute("DELETE FROM django_migrations WHERE app='news' AND name IN ('0038_vehiclespecs', '0039_merge_0038_vehiclespecs_0038_vehiclespecs_and_more')")
        connection.connection.commit()
        print("Old records cleaned!")
    else:
        print("Migration records already clean")
except Exception as e:
    print(f"Migration fix error (non-fatal): {e}")
MIGRATION_FIX_EOF
set -e  # Re-enable exit-on-error

python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Populating tags..."
python manage.py populate_tags || echo "Tags population skipped"

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
