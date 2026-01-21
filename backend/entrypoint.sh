#!/bin/bash

# Exit on error
set -e

echo "Running migrations..."
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

echo "Starting Daphne server..."
exec daphne -b 0.0.0.0 -p 8001 auto_news_site.asgi:application
