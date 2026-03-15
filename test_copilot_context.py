import os
import sys
import json

sys.path.append('/home/kille_wsl/Projects/FreshMotors_GoogleAntigravity/AutoNews-AI/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from news.models import Article

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()

client = APIClient()
client.force_authenticate(user=admin_user)

article = Article.objects.first()
slug = article.slug

payload = {
    "text": "This car is very fast.",
    "instruction": "Rewrite to sound more exciting.",
    "context": {
        "title": "2025 Porsche 911 Review",
        "summary": "We test the new 911.",
        "tags": ["Porsche", "Sports Car"],
        "content": "<p>This car is very fast.</p>"
    }
}

response = client.post(f'/api/v1/articles/{slug}/ai_edit_chunk/', payload, format='json')
print(f"Status: {response.status_code}")
print(json.dumps(response.data, indent=2))
