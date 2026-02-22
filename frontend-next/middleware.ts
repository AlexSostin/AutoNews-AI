import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Cache settings to avoid hitting API on every request
let cachedSettings: { maintenance_mode: boolean; maintenance_message: string } | null = null;
let settingsCacheTime = 0;
const CACHE_TTL = 60_000; // 60 seconds (was 30s — too aggressive for middleware)

// Fire-and-forget: update cache in background, never block navigation
function refreshMaintenanceCache() {
  const now = Date.now();
  if (now - settingsCacheTime < CACHE_TTL) return;

  // Mark as refreshed immediately to prevent concurrent fetches
  settingsCacheTime = now;

  const apiBase = process.env.API_INTERNAL_URL
    || process.env.CUSTOM_DOMAIN_API
    || (process.env.RAILWAY_ENVIRONMENT === 'production'
      ? 'https://heroic-healing-production-2365.up.railway.app/api/v1'
      : 'http://backend:8000/api/v1');

  fetch(`${apiBase}/settings/`, {
    signal: AbortSignal.timeout(2000),
  })
    .then(res => res.ok ? res.json() : null)
    .then(data => {
      if (data) {
        cachedSettings = {
          maintenance_mode: data.maintenance_mode || false,
          maintenance_message: data.maintenance_message || '',
        };
      }
    })
    .catch(() => {
      // API unavailable — keep stale cache or null
    });
}

export async function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value;
  const pathname = request.nextUrl.pathname;
  const isAdminRoute = pathname.startsWith('/admin');
  const isLoginRoute = pathname === '/login';

  // Kick off non-blocking cache refresh
  refreshMaintenanceCache();

  // Admin routes - check if token exists (no API call needed)
  if (isAdminRoute) {
    if (!token) {
      return NextResponse.redirect(new URL('/login', request.url));
    }
    return NextResponse.next();
  }

  // Login page - redirect if has token
  if (isLoginRoute && token) {
    return NextResponse.redirect(new URL('/', request.url));
  }

  // Maintenance mode — use CACHED value only, never block on fetch
  if (!isLoginRoute && pathname !== '/register') {
    if (cachedSettings?.maintenance_mode) {
      // Only block non-admin users; skip admin check to avoid more fetches
      // Admins can bypass by going to /admin first which sets the cookie
      if (!token) {
        const url = request.nextUrl.clone();
        url.pathname = '/';
        return NextResponse.rewrite(url);
      }
    }
  }

  return NextResponse.next();
}

export const config = {
  // Only match actual page routes, NOT _next/*, static assets, API routes, etc.
  matcher: [
    '/',
    '/login',
    '/register',
    '/admin/:path*',
    '/articles/:path*',
    '/about',
    '/contact',
    '/cars/:path*',
    '/compare',
    '/categories/:path*',
    '/search',
    '/trending',
    '/profile/:path*',
    '/privacy-policy',
    '/terms',
    '/for-authors',
  ],
};
