import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from news.models import Article

c = Client()
user = User.objects.filter(is_staff=True).first()
if not user:
    user = User.objects.create_superuser('testadmin', 'test@test.com', 'testpwd')
c.force_login(user)

# Take any article
article = Article.objects.filter(is_deleted=False).first()
if article:
    print(f"Testing regenerate on {article.slug}...")
    resp = c.post(f'/api/v1/articles/{article.slug}/regenerate/', {'provider': 'gemini'})
    print(f"Status: {resp.status_code}")
    print(resp.content.decode())
else:
    print("No active articles found.")
