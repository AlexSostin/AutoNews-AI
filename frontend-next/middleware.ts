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
      // Always use production URL on non-localhost hosts
      const host = request.headers.get('host') || '';
      const apiUrl = host.includes('localhost') || host.includes('127.0.0.1')
        ? 'http://localhost:8001/api/v1'
        : 'https://heroic-healing-production-2365.up.railway.app/api/v1';
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
      // При ошибке проверки токена - безопасный редирект на login
      const response = NextResponse.redirect(new URL('/login', request.url));
      response.cookies.delete('access_token');
      response.cookies.delete('refresh_token');
      return response;
    }
  }

  // Если есть токен и пытается зайти на login - проверить роль и редирект
  if (isLoginRoute && token) {
    try {
      // Always use production URL on non-localhost hosts
      const host = request.headers.get('host') || '';
      const apiUrl = host.includes('localhost') || host.includes('127.0.0.1')
        ? 'http://localhost:8001/api/v1'
        : 'https://heroic-healing-production-2365.up.railway.app/api/v1';
      
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

  // Защита profile роутов - требуется авторизация
  const isProfileRoute = request.nextUrl.pathname.startsWith('/profile');
  if (isProfileRoute && !token) {
    console.log('[Middleware] No token for profile route, redirecting to /login');
    const redirectUrl = new URL('/login', request.url);
    redirectUrl.searchParams.set('redirect', request.nextUrl.pathname);
    return NextResponse.redirect(redirectUrl);
  }

  // Если есть токен на профиле - проверим что он ещё валиден
  if (isProfileRoute && token) {
    try {
      const host = request.headers.get('host') || '';
      const apiUrl = host.includes('localhost') || host.includes('127.0.0.1')
        ? 'http://localhost:8001/api/v1'
        : 'https://heroic-healing-production-2365.up.railway.app/api/v1';
      
      const response = await fetch(`${apiUrl}/users/me/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        signal: AbortSignal.timeout(5000),
      });

      if (!response.ok) {
        // Токен истёк или невалиден - очистить и редирект
        console.log('[Middleware] Profile token invalid, clearing and redirecting');
        const redirectResponse = NextResponse.redirect(new URL('/login?redirect=/profile', request.url));
        redirectResponse.cookies.delete('access_token');
        redirectResponse.cookies.delete('refresh_token');
        return redirectResponse;
      }
    } catch (error) {
      console.error('[Middleware] Profile auth check failed:', error);
      // При ошибке сети - пропускаем (пусть клиент решит)
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/admin/:path*', '/login', '/profile', '/profile/:path*'],
};
