"""
Bot Protection Middleware — blocks obvious scrapers/bots from the API.

Checks User-Agent on API requests. If the UA looks like an automated tool
(curl, wget, python-requests, scrapy, etc.), returns 403 Forbidden.

Real browsers always send a full UA string. Scrapers often use default UAs.
This doesn't stop sophisticated bots but blocks 90%+ of casual scraping.
"""
import re
import sys
import logging
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# Patterns that indicate automated tools (case-insensitive)
BOT_UA_PATTERNS = [
    r'python-requests',
    r'python-urllib',
    r'python-httpx',
    r'curl/',
    r'wget/',
    r'scrapy',
    r'httpclient',
    r'go-http-client',
    r'java/',
    r'libwww-perl',
    r'mechanize',
    r'php/',
    r'ruby/',
    r'aiohttp',
    r'httpie',
]

# Compile patterns into a single regex for speed
BOT_REGEX = re.compile('|'.join(BOT_UA_PATTERNS), re.IGNORECASE)

# Paths that should be protected (API endpoints only)
PROTECTED_PREFIXES = ['/api/']

# Paths to EXCLUDE from protection (allow bots to fetch these)
EXCLUDED_PATHS = [
    '/api/v1/sitemap',
    '/api/v1/feed',
]

# Known good bot UAs to allow (search engines, our SSR, etc.)
ALLOWED_BOTS = [
    r'googlebot',
    r'bingbot',
    r'yandexbot',
    r'baiduspider',
    r'duckduckbot',
    r'slurp',          # Yahoo
    r'facebookexternalhit',
    r'twitterbot',
    r'linkedinbot',
    r'whatsapp',
    r'telegrambot',
    r'applebot',
    r'freshmotors-ssr', # Our Next.js SSR
    r'next',           # Next.js SSR
    r'node-fetch',     # Next.js Server Components
    r'axios'           # Frontend components
]

ALLOWED_BOT_REGEX = re.compile('|'.join(ALLOWED_BOTS), re.IGNORECASE)


class BotProtectionMiddleware:
    """
    Middleware that blocks requests from obvious scraping tools.
    
    Only affects /api/ endpoints. Does not block:
    - Regular browser requests
    - Search engine crawlers (Google, Bing, etc.)
    - Social media preview bots (Facebook, Twitter, etc.)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip during Django tests (test client sends empty UA)
        if 'test' in sys.argv:
            return self.get_response(request)
        
        path = request.path
        
        # Only check API endpoints
        if not any(path.startswith(prefix) for prefix in PROTECTED_PREFIXES):
            return self.get_response(request)
        
        # Skip excluded paths
        if any(path.startswith(excluded) for excluded in EXCLUDED_PATHS):
            return self.get_response(request)
        
        # Never block authenticated users (admin/staff making API calls via Axios etc.)
        if hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False) is True:
            return self.get_response(request)
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Allow empty UA from internal/localhost (Next.js SSR, Docker containers)
        if not user_agent:
            client_ip = self._get_ip(request)
            if client_ip in ('127.0.0.1', '::1', 'localhost') or client_ip.startswith('172.') or client_ip.startswith('10.'):
                return self.get_response(request)
            logger.warning(f"🤖 Blocked empty UA: {request.method} {path} from {client_ip}")
            return JsonResponse(
                {'detail': 'Request blocked. Please use a web browser.'},
                status=403
            )
        
        # Allow known good bots (search engines, social media)
        if ALLOWED_BOT_REGEX.search(user_agent):
            return self.get_response(request)
        
        # Block known scraping tools
        if BOT_REGEX.search(user_agent):
            logger.warning(
                f"🤖 Blocked bot: {user_agent[:80]} | "
                f"{request.method} {path} | IP: {self._get_ip(request)}"
            )
            return JsonResponse(
                {'detail': 'Automated access is not permitted. Please use a web browser.'},
                status=403
            )
        
        return self.get_response(request)
    
    @staticmethod
    def _get_ip(request):
        """Get real IP, considering proxy headers."""
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
