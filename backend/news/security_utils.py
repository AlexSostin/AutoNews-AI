"""
Security utilities for logging and monitoring security events
"""
from .models import SecurityLog


def log_security_event(user=None, action=None, ip_address=None, user_agent=None, old_value='', new_value='', details=''):
    """
    Log a security event to the database.
    
    Args:
        user: User object (can be None for failed logins)
        action: str - one of SecurityLog.ACTION_CHOICES
        ip_address: str - IP address of the request
        user_agent: str - Browser user agent string
        old_value: str - Previous value (e.g., old email)
        new_value: str - New value (e.g., new email)
        details: str - Additional details (JSON string)
    
    Returns:
        SecurityLog instance
    """
    return SecurityLog.objects.create(
        user=user,
        action=action,
        ip_address=ip_address,
        user_agent=user_agent,
        old_value=old_value,
        new_value=new_value,
        details=details,
    )


def get_client_ip(request):
    """
    Get client IP address from request.
    Handles proxies and load balancers.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Get user agent string from request"""
    return request.META.get('HTTP_USER_AGENT', '')
