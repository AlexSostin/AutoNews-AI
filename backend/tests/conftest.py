"""
Pytest configuration and fixtures
"""
import pytest
import os
import sys
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_news_site.settings')

import django
django.setup()


@pytest.fixture
def sample_analysis():
    """Sample article analysis for testing"""
    return {
        'make': 'Tesla',
        'model': 'Model 3',
        'year': 2024,
        'category': 'Electric Vehicle',
        'content': 'Detailed analysis of Tesla Model 3 performance and features...'
    }


@pytest.fixture
def sample_article_data():
    """Sample article data for DB tests"""
    return {
        'title': 'Test Article: 2024 Tesla Model 3',
        'content': '<p>Test content</p>',
        'summary': 'Test summary',
        'category_name': 'Electric Vehicles',
        'is_published': True,
    }


@pytest.fixture
def api_client():
    """Django REST framework test client"""
    from rest_framework.test import APIClient
    client = APIClient()
    client.defaults['HTTP_USER_AGENT'] = 'TestClient/1.0'
    return client


@pytest.fixture
def authenticated_client(api_client, django_user_model):
    """Authenticated API client using JWT"""
    from rest_framework_simplejwt.tokens import RefreshToken
    
    user = django_user_model.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        is_staff=True,
        is_superuser=True,  # For admin-only endpoints
    )
    
    # Create JWT token
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    return api_client
