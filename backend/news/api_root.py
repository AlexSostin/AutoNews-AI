"""
Simple API-only root view for Django backend
"""
from django.http import JsonResponse


def api_root(request):
    """
    Root endpoint - just returns API info
    No HTML templates, no ads - backend is API only!
    """
    return JsonResponse({
        'message': '🚗 Fresh Motors API',
        'version': '1.0',
        'docs': '/admin/ (Django admin - use Next.js admin instead)',
        'api_endpoints': {
            'articles': '/api/v1/articles/',
            'search': '/api/v1/search/',
            'analytics': '/api/v1/analytics/',
            'categories': '/api/v1/categories/',
            'comments': '/api/v1/comments/',
        },
        'frontend': 'http://localhost:3000',
        'admin_panel': 'http://localhost:3000/admin',
    })
