from django.http import HttpResponse
from django.urls import reverse
from .models import SiteSettings

class MaintenanceModeMiddleware:
    """
    Middleware to handle maintenance mode.
    Shows maintenance message to non-admin users when maintenance mode is enabled.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get site settings
        try:
            settings = SiteSettings.load()
            if settings.maintenance_mode:
                # Allow access to admin and API for authenticated staff users
                if (request.user.is_staff or
                    request.path.startswith('/admin/') or
                    request.path.startswith('/api/') or
                    request.path.startswith('/static/') or
                    request.path.startswith('/media/')):
                    return self.get_response(request)

                # Show maintenance page for everyone else
                return HttpResponse(
                    f"""
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>Maintenance - {settings.site_name}</title>
                        <style>
                            body {{
                                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                color: white;
                                margin: 0;
                                padding: 0;
                                min-height: 100vh;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                            }}
                            .maintenance-container {{
                                text-align: center;
                                max-width: 600px;
                                padding: 2rem;
                                background: rgba(255, 255, 255, 0.1);
                                border-radius: 20px;
                                backdrop-filter: blur(10px);
                                border: 1px solid rgba(255, 255, 255, 0.2);
                            }}
                            h1 {{
                                font-size: 3rem;
                                margin-bottom: 1rem;
                                font-weight: 700;
                            }}
                            p {{
                                font-size: 1.2rem;
                                line-height: 1.6;
                                margin-bottom: 2rem;
                            }}
                            .logo {{
                                font-size: 4rem;
                                margin-bottom: 1rem;
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="maintenance-container">
                            <div class="logo">🔧</div>
                            <h1>Under Maintenance</h1>
                            <p>{settings.maintenance_message}</p>
                        </div>
                    </body>
                    </html>
                    """,
                    content_type='text/html',
                    status=503
                )
        except Exception as e:
            # If there's an error loading settings, continue normally
            pass

        return self.get_response(request)