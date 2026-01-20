import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value;
  const isAdminRoute = request.nextUrl.pathname.startsWith('/admin');
  const isLoginRoute = request.nextUrl.pathname === '/login';

  console.log('[Middleware]', {
    path: request.nextUrl.pathname,
    hasToken: !!token,
    isAdminRoute,
    isLoginRoute
  });

  // Если админский роут и нет токена - редирект на login
  if (isAdminRoute && !token) {
    console.log('[Middleware] No token for admin route, redirecting to /login');
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // Если админский роут и есть токен - проверить is_staff
  if (isAdminRoute && token) {
    try {
      // В Docker используем внутренний URL backend
      const apiUrl = 'http://backend:8001/api/v1';
      console.log('[Middleware] Checking user auth at:', apiUrl);
      
      const response = await fetch(`${apiUrl}/users/me/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        // Добавляем timeout
        signal: AbortSignal.timeout(5000),
      });

      console.log('[Middleware] Auth check response:', response.status);

      if (response.ok) {
        const user = await response.json();
        console.log('[Middleware] User:', { 
          username: user.username, 
          is_staff: user.is_staff, 
          is_superuser: user.is_superuser 
        });
        
        // Если НЕ админ - редирект на главную
        if (!user.is_staff && !user.is_superuser) {
          console.log('[Middleware] User is not admin, redirecting to /');
          return NextResponse.redirect(new URL('/', request.url));
        }
        
        console.log('[Middleware] User is admin, allowing access');
      } else {
        // Токен невалидный - редирект на login
        console.log('[Middleware] Invalid token, redirecting to /login');
        return NextResponse.redirect(new URL('/login', request.url));
      }
    } catch (error) {
      console.error('[Middleware] Auth check failed:', error);
      // При ошибке НЕ редиректим, пускаем дальше - проверку сделает страница
      // return NextResponse.redirect(new URL('/login', request.url));
    }
  }

  // Если есть токен и пытается зайти на login - проверить роль и редирект
  if (isLoginRoute && token) {
    try {
      const apiUrl = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1';
      
      const response = await fetch(`${apiUrl}/users/me/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const user = await response.json();
        
        // Админы идут в админку, обычные пользователи на главную
        if (user.is_staff || user.is_superuser) {
          return NextResponse.redirect(new URL('/admin', request.url));
        } else {
          return NextResponse.redirect(new URL('/', request.url));
        }
      }
    } catch (error) {
      // Ошибка - пускаем на login
      console.error('Middleware auth check failed:', error);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/admin/:path*', '/login', '/profile/:path*'],
};
