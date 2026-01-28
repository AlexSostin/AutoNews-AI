"""
Management command to create a superuser from environment variables.
Usage: python manage.py create_superuser_env

Required environment variables:
- DJANGO_SUPERUSER_USERNAME
- DJANGO_SUPERUSER_EMAIL
- DJANGO_SUPERUSER_PASSWORD
"""

import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create a superuser from environment variables'

    def handle(self, *args, **options):
        User = get_user_model()
        
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        
        if not all([username, email, password]):
            self.stderr.write(
                self.style.ERROR(
                    'Missing required environment variables:\n'
                    '  DJANGO_SUPERUSER_USERNAME\n'
                    '  DJANGO_SUPERUSER_EMAIL\n'
                    '  DJANGO_SUPERUSER_PASSWORD'
                )
            )
            return
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            if not user.is_superuser:
                user.is_superuser = True
                user.is_staff = True
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'User "{username}" upgraded to superuser')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Superuser "{username}" already exists')
                )
            return
        
        # Create new superuser
        try:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS(f'Superuser "{username}" created successfully!')
            )
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f'Failed to create superuser: {e}')
            )
