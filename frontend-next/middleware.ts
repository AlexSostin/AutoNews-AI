import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value;
  const isAdminRoute = request.nextUrl.pathname.startsWith('/admin');
  const isLoginRoute = request.nextUrl.pathname === '/login';
  const isProfileRoute = request.nextUrl.pathname.startsWith('/profile');

  // Debug logging
  console.log('[Middleware] Path:', request.nextUrl.pathname);
  console.log('[Middleware] Has token:', !!token);
  console.log('[Middleware] All cookies:', request.cookies.getAll().map(c => c.name));

  // Helper to get API URL
  const getApiUrl = (request: NextRequest) => {
    const host = request.headers.get('host') || '';
    return host.includes('localhost') || host.includes('127.0.0.1')
      ? 'http://localhost:8001/api/v1'
      : 'https://heroic-healing-production-2365.up.railway.app/api/v1';
  };

  // Helper to verify token and get user
  const verifyToken = async (token: string): Promise<{ valid: boolean; user?: any; status?: number }> => {
    try {
      const apiUrl = getApiUrl(request);
      const response = await fetch(`${apiUrl}/users/me/`, {
        headers: { 'Authorization': `Bearer ${token}` },
        signal: AbortSignal.timeout(5000),
      });
      
      if (response.ok) {
        const user = await response.json();
        return { valid: true, user };
      }
      
      return { valid: false, status: response.status };
    } catch (error) {
      console.error('[Middleware] Token verification error:', error);
      // Network error - don't invalidate, let page handle it
      return { valid: true, user: null };
    }
  };

  // Admin routes - require staff/superuser
  if (isAdminRoute) {
    if (!token) {
      console.log('[Middleware] No token for admin route');
      return NextResponse.redirect(new URL('/login', request.url));
    }

    const { valid, user, status } = await verifyToken(token);
    
    if (!valid) {
      console.log('[Middleware] Admin token invalid, status:', status);
      // Only clear cookies on explicit 401/403
      if (status === 401 || status === 403) {
        const response = NextResponse.redirect(new URL('/login', request.url));
        response.cookies.delete('access_token');
        response.cookies.delete('refresh_token');
        return response;
      }
      // Other errors - redirect but don't clear (might be temporary)
      return NextResponse.redirect(new URL('/login', request.url));
    }
    
    // User exists but not admin
    if (user && !user.is_staff && !user.is_superuser) {
      console.log('[Middleware] User is not admin');
      return NextResponse.redirect(new URL('/', request.url));
    }
    
    // Valid admin or network error (let page handle)
    return NextResponse.next();
  }

  // Login page - redirect if already logged in
  if (isLoginRoute && token) {
    const { valid, user } = await verifyToken(token);
    
    if (valid && user) {
      // Redirect based on role
      if (user.is_staff || user.is_superuser) {
        return NextResponse.redirect(new URL('/admin', request.url));
      }
      return NextResponse.redirect(new URL('/', request.url));
    }
    // Invalid token or error - let them login
  }

  // Profile routes - require authentication
  if (isProfileRoute) {
    if (!token) {
      console.log('[Middleware] No token for profile route');
      const redirectUrl = new URL('/login', request.url);
      redirectUrl.searchParams.set('redirect', request.nextUrl.pathname);
      return NextResponse.redirect(redirectUrl);
    }

    const { valid, status } = await verifyToken(token);
    
    if (!valid && (status === 401 || status === 403)) {
      console.log('[Middleware] Profile token invalid');
      const response = NextResponse.redirect(new URL('/login?redirect=/profile', request.url));
      response.cookies.delete('access_token');
      response.cookies.delete('refresh_token');
      return response;
    }
    // Valid or network error - let page handle
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/admin/:path*', '/login', '/profile', '/profile/:path*'],
};
