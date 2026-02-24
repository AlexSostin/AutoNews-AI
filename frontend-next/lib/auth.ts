import api, { getApiUrl } from './api';
import { authenticatedFetch } from './authenticatedFetch';
import { AuthTokens, LoginCredentials, User } from '@/types';
import { setUserContext, clearUserContext } from './errorTracking';

// Helper to set cookies with proper security flags
const setCookie = (name: string, value: string, maxAgeSeconds: number = 7 * 24 * 60 * 60) => {
  const isSecure = typeof window !== 'undefined' && window.location.protocol === 'https:';
  const secureFlag = isSecure ? '; Secure' : '';
  document.cookie = `${name}=${value}; path=/; max-age=${maxAgeSeconds}; SameSite=Lax${secureFlag}`;
};

export const login = async (credentials: LoginCredentials): Promise<AuthTokens> => {
  const response = await api.post('/token/', credentials);
  const { access, refresh } = response.data;

  // Store tokens in cookies (needed for middleware)
  // Access token cookie lives 7 days (cookie presence allows middleware to pass)
  // The actual token validation happens on the backend
  setCookie('access_token', access); // 7 days (default)
  setCookie('refresh_token', refresh, 30 * 24 * 60 * 60); // 30 days

  // Also store in localStorage for client-side access
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);

  // Store user data
  const userData = await getCurrentUser(access);
  if (userData) {
    localStorage.setItem('user', JSON.stringify(userData));

    // Установить пользователя в Sentry для отслеживания ошибок
    setUserContext({
      id: userData.id.toString(),
      email: userData.email,
      username: userData.username,
      is_staff: userData.is_staff
    });
  }

  // Trigger auth change event for Header update
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('authChange'));
  }

  return { access, refresh };
};

export const logout = () => {
  // Clear localStorage
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');

  // Clear cookies
  document.cookie = 'access_token=; path=/; max-age=0';
  document.cookie = 'refresh_token=; path=/; max-age=0';

  // Очистить пользователя из Sentry
  clearUserContext();

  // Trigger auth change event
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('authChange'));
  }

  window.location.href = '/login';
};

const _isTokenExpired = (token: string): boolean => {
  try {
    const payload = token.split('.')[1];
    if (!payload) return true;

    // JWT uses Base64Url, which atob doesn't directly support (needs + and / instead of - and _)
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const decoded = JSON.parse(atob(base64));

    if (!decoded.exp) return false; // No expiry = treat as valid
    // exp is in seconds, Date.now() is in ms. Add 30s buffer.
    return decoded.exp * 1000 < Date.now() + 30000;
  } catch {
    return true; // Can't decode = treat as expired
  }
};

export const isAuthenticated = (): boolean => {
  if (typeof window === 'undefined') return false;

  // Check cookies first (middleware uses cookies)
  const cookieToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('access_token='));

  if (cookieToken) {
    const token = cookieToken.split('=')[1];
    if (token && !_isTokenExpired(token)) return true;

    // Token is expired. Check if we have a refresh token before clearing!
    const hasRefreshToken = document.cookie.includes('refresh_token=') || localStorage.getItem('refresh_token');
    if (hasRefreshToken) return true; // Let api.ts interceptor handle the refresh

    // Only clean up if BOTH are missing/expired
    _clearAuthData();
    return false;
  }

  // Fallback to localStorage - if found, restore the cookie!
  const tokenFromStorage = localStorage.getItem('access_token');
  if (tokenFromStorage) {
    if (_isTokenExpired(tokenFromStorage)) {
      // Check if we have a refresh token before clearing
      const hasRefreshToken = document.cookie.includes('refresh_token=') || localStorage.getItem('refresh_token');
      if (hasRefreshToken) return true; // Let api.ts interceptor handle the refresh

      // Token expired and no refresh token — clean up stale data
      _clearAuthData();
      return false;
    }
    // Restore the cookie for middleware
    setCookie('access_token', tokenFromStorage);
    const refreshFromStorage = localStorage.getItem('refresh_token');
    if (refreshFromStorage) {
      setCookie('refresh_token', refreshFromStorage);
    }
    return true;
  }

  return false;
};

// Clean up expired/stale auth data without redirect
const _clearAuthData = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  document.cookie = 'access_token=; path=/; max-age=0';
  document.cookie = 'refresh_token=; path=/; max-age=0';
};

export const getAccessToken = (): string | null => {
  if (typeof window === 'undefined') return null;

  // Check cookies first (middleware uses cookies)
  const token = document.cookie
    .split('; ')
    .find(row => row.startsWith('access_token='));

  if (token) {
    const access = token.split('=')[1];
    // If we have an access token, check if it's valid.
    // Even if it's expired, if we have a refresh token, return it so the api interceptor can catch the 401 and refresh it.
    if (!_isTokenExpired(access) || document.cookie.includes('refresh_token=') || localStorage.getItem('refresh_token')) {
      return access;
    }
  }

  // Fallback to localStorage - if found, restore the cookie!
  const tokenFromStorage = localStorage.getItem('access_token');
  if (tokenFromStorage) {
    if (!_isTokenExpired(tokenFromStorage) || document.cookie.includes('refresh_token=') || localStorage.getItem('refresh_token')) {
      // Restore the cookie for middleware
      setCookie('access_token', tokenFromStorage);
      const refreshFromStorage = localStorage.getItem('refresh_token');
      if (refreshFromStorage) {
        setCookie('refresh_token', refreshFromStorage);
      }
      return tokenFromStorage;
    }
  }
  return null;
};

// Alias for convenience
export const getToken = getAccessToken;

export const getCurrentUser = async (token?: string): Promise<User | null> => {
  try {
    const accessToken = token || getAccessToken();
    if (!accessToken) return null;

    // Use authenticatedFetch instead of raw fetch to ensure token refresh works
    // if this is ever called outside of the immediate login flow
    const response = await authenticatedFetch('/users/me/', {
      headers: token ? { 'Authorization': `Bearer ${token}` } : undefined
    });

    if (!response.ok) return null;

    return await response.json();
  } catch (error) {
    console.error('Error fetching user:', error);
    return null;
  }
};

export const getUserFromStorage = (): User | null => {
  if (typeof window === 'undefined') return null;

  const userData = localStorage.getItem('user');
  return userData ? JSON.parse(userData) : null;
};

export const isAdmin = (): boolean => {
  const user = getUserFromStorage();
  return user?.is_staff || user?.is_superuser || false;
};

export const isSuperuser = (): boolean => {
  const user = getUserFromStorage();
  return user?.is_superuser || false;
};
