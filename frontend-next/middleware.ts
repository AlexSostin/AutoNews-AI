import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Cache settings to avoid hitting API on every request
let cachedSettings: { maintenance_mode: boolean; maintenance_message: string } | null = null;
let settingsCacheTime = 0;
const CACHE_TTL = 30_000; // 30 seconds

async function getMaintenanceSettings(request: NextRequest) {
  const now = Date.now();
  if (cachedSettings && now - settingsCacheTime < CACHE_TTL) {
    return cachedSettings;
  }

  try {
    // Use internal API URL if available, otherwise construct from request
    const apiBase = process.env.API_INTERNAL_URL
      || process.env.CUSTOM_DOMAIN_API
      || (process.env.RAILWAY_ENVIRONMENT === 'production'
        ? 'https://heroic-healing-production-2365.up.railway.app/api/v1'
        : 'http://localhost:8000/api/v1');

    const res = await fetch(`${apiBase}/settings/`, {
      signal: AbortSignal.timeout(3000),
    });
    if (res.ok) {
      const data = await res.json();
      cachedSettings = {
        maintenance_mode: data.maintenance_mode || false,
        maintenance_message: data.maintenance_message || '',
      };
      settingsCacheTime = now;
      return cachedSettings;
    }
  } catch {
    // API unavailable — don't block users
  }
  return null;
}

async function isAdminUser(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value;
  if (!token) return false;

  try {
    const apiBase = process.env.API_INTERNAL_URL
      || process.env.CUSTOM_DOMAIN_API
      || (process.env.RAILWAY_ENVIRONMENT === 'production'
        ? 'https://heroic-healing-production-2365.up.railway.app/api/v1'
        : 'http://localhost:8000/api/v1');

    const res = await fetch(`${apiBase}/users/me/`, {
      headers: { 'Authorization': `Bearer ${token}` },
      signal: AbortSignal.timeout(3000),
    });
    if (res.ok) {
      const user = await res.json();
      return user.is_staff || user.is_superuser;
    }
  } catch {
    // Can't verify — treat as non-admin
  }
  return false;
}

export async function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value;
  const pathname = request.nextUrl.pathname;
  const isAdminRoute = pathname.startsWith('/admin');
  const isLoginRoute = pathname === '/login';
  const isRegisterRoute = pathname === '/register';
  const isApiRoute = pathname.startsWith('/api');
  const isStaticRoute = pathname.startsWith('/_next') || pathname.startsWith('/static');

  // Skip static assets and API routes
  if (isApiRoute || isStaticRoute) {
    return NextResponse.next();
  }

  // Admin routes - check if token exists
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

  // Maintenance mode check — for ALL public routes
  // Skip login/register so admins can still log in
  if (!isLoginRoute && !isRegisterRoute) {
    const settings = await getMaintenanceSettings(request);
    if (settings?.maintenance_mode) {
      // Check if user is admin — let admins through
      const admin = await isAdminUser(request);
      if (!admin) {
        // Rewrite to home page which will show MaintenancePage
        // This ensures maintenance page is shown on ALL routes
        const url = request.nextUrl.clone();
        url.pathname = '/';
        return NextResponse.rewrite(url);
      }
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon.ico, robots.txt, sitemap.xml
     */
    '/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)',
  ],
};
