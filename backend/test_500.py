import os
import django
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from django.test import Client
c = Client(
    SERVER_NAME='localhost',
    HTTP_USER_AGENT='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)

print("Testing ADS")
try:
    response = c.get('/api/v1/ads/active/?position=header')
    print("ADS RESPONSE:", response.status_code)
    if response.status_code >= 400:
        print("ADS BODY:", response.content)
except Exception as e:
    print("ADS EXCEPTION")
    traceback.print_exc()

print("Testing FAVS")
try:
    response = c.get('/api/v1/favorites/check/?article=118')
    print("FAVS RESPONSE:", response.status_code)
    if response.status_code >= 400:
        print("FAVS BODY:", response.content)
except Exception as e:
    print("FAVS EXCEPTION")
    traceback.print_exc()
