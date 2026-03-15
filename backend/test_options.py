import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from django.test import Client
c = Client()
resp = c.options('/api/v1/articles/deleted-slug/regenerate/')
print(f"Status OPTIONS: {resp.status_code}")
print(f"Access-Control-Allow-Origin: {resp.headers.get('Access-Control-Allow-Origin')}")
