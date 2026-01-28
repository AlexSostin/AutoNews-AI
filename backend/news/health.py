"""
Health Check Endpoints for monitoring and load balancers
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
import os


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Basic health check endpoint for load balancers and monitoring.
    Returns 200 if the service is running.
    """
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'autonews-backend',
        'version': '1.0.0',
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check_detailed(request):
    """
    Detailed health check with database and cache status.
    Use for internal monitoring only.
    """
    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'autonews-backend',
        'version': '1.0.0',
        'checks': {}
    }
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health_status['checks']['database'] = {
            'status': 'healthy',
            'type': connection.vendor
        }
    except Exception as e:
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'degraded'
    
    # Check cache connection
    try:
        cache.set('health_check', 'ok', 10)
        cache_result = cache.get('health_check')
        if cache_result == 'ok':
            health_status['checks']['cache'] = {
                'status': 'healthy',
                'backend': cache.__class__.__name__
            }
        else:
            health_status['checks']['cache'] = {
                'status': 'degraded',
                'message': 'Cache write/read mismatch'
            }
    except Exception as e:
        health_status['checks']['cache'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # Environment info (safe to expose)
    health_status['environment'] = os.getenv('ENVIRONMENT', 'production')
    
    return Response(health_status)


@api_view(['GET'])
@permission_classes([AllowAny])
def readiness_check(request):
    """
    Readiness probe for Kubernetes/Railway.
    Returns 200 only if the service can handle requests.
    """
    try:
        # Check database is accessible
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        
        return Response({
            'ready': True,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return Response({
            'ready': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=503)
