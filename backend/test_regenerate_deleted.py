import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from news.models import Article

c = Client()
user = User.objects.filter(is_staff=True).first()
c.force_login(user)

article = Article.objects.filter(is_deleted=False).first()
slug = article.slug
print(f"Deleting {slug}...")
article.is_deleted = True
article.save()

print(f"Testing regenerate on deleted {slug}...")
resp = c.post(f'/api/v1/articles/{slug}/regenerate/', {'provider': 'gemini'})
print(f"Status: {resp.status_code}")
print(resp.content.decode())

# Restore
article.is_deleted = False
article.save()
