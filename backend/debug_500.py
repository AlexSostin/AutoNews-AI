"""Debug script to capture 500 error from real Django WSGI handler."""
import os, sys, io
os.environ['DJANGO_SETTINGS_MODULE'] = 'auto_news_site.settings'

import django
django.setup()

from django.core.handlers.wsgi import WSGIHandler
from django.test.utils import setup_test_environment

application = WSGIHandler()

# Simulate WSGI environ for the problematic request
environ = {
    'REQUEST_METHOD': 'GET',
    'PATH_INFO': '/api/v1/articles/recommended/',
    'QUERY_STRING': 'page_size=5',
    'SERVER_NAME': 'localhost',
    'SERVER_PORT': '8000',
    'HTTP_HOST': 'localhost:8000',
    'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'HTTP_ACCEPT': '*/*',
    'HTTP_ORIGIN': 'http://localhost:3000',
    'HTTP_REFERER': 'http://localhost:3000/',
    'wsgi.input': io.BytesIO(b''),
    'wsgi.errors': sys.stderr,
    'wsgi.url_scheme': 'http',
    'wsgi.multithread': True,
    'wsgi.multiprocess': False,
    'wsgi.run_once': False,
}

status_line = None
headers = None

def start_response(status, response_headers, exc_info=None):
    global status_line, headers
    status_line = status
    headers = response_headers
    return lambda s: None

try:
    response_body = b''.join(application(environ, start_response))
    print(f"Status: {status_line}")
    
    if '500' in str(status_line):
        # Parse error from HTML
        import re
        html = response_body.decode('utf-8', errors='replace')
        m = re.search(r'<pre class="exception_value">(.*?)</pre>', html, re.DOTALL)
        if m:
            print(f"Exception: {m.group(1).strip()[:500]}")
        m = re.search(r'<textarea[^>]*id="traceback_area"[^>]*>(.*?)</textarea>', html, re.DOTALL)
        if m:
            print(m.group(1).strip()[:3000])
        else:
            print(html[:1000])
    else:
        print(f"Body length: {len(response_body)}")
        print(f"First 200 chars: {response_body[:200].decode()}")
except Exception as e:
    import traceback
    traceback.print_exc()
