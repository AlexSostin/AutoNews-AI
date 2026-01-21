import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value;
  const isAdminRoute = request.nextUrl.pathname.startsWith('/admin');
  const isLoginRoute = request.nextUrl.pathname === '/login';

  // Debug logging
  console.log('[Middleware] Path:', request.nextUrl.pathname, '| Has token:', !!token);

  // Admin routes - just check if token exists
  // Actual validation happens on API calls
  if (isAdminRoute) {
    if (!token) {
      console.log('[Middleware] No token for admin, redirecting to login');
      return NextResponse.redirect(new URL('/login', request.url));
    }
    // Token exists - let it through, API will validate
    return NextResponse.next();
  }

  // Login page - redirect if has token
  if (isLoginRoute && token) {
    console.log('[Middleware] Has token on login page, redirecting to admin');
    return NextResponse.redirect(new URL('/admin', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/admin/:path*', '/login'],
};
