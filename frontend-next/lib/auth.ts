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

// Special error class to signal that 2FA is required
export class TwoFARequiredError extends Error {
  constructor() {
    super('2FA required');
    this.name = 'TwoFARequiredError';
  }
}

// Special error class to signal that Passkey verification is required
export class PasskeyRequiredError extends Error {
  pendingToken: string;
  constructor(pendingToken: string) {
    super('Passkey required');
    this.name = 'PasskeyRequiredError';
    this.pendingToken = pendingToken;
  }
}

export const login = async (credentials: LoginCredentials): Promise<AuthTokens> => {
  const response = await api.post('/token/', credentials);
  const data = response.data;

  // If backend requires 2FA — throw special error for the login page to handle
  if (data.requires_2fa) {
    throw new TwoFARequiredError();
  }

  // If backend requires Passkey — throw special error with the one-time token
  if (data.requires_passkey) {
    throw new PasskeyRequiredError(data.pending_token ?? '');
  }

  const { access, refresh } = data;

  // Store tokens in cookies (needed for middleware)
  setCookie('access_token', access);
  setCookie('refresh_token', refresh, 30 * 24 * 60 * 60);

  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);

  const userData = await getCurrentUser(access);
  if (userData) {
    localStorage.setItem('user', JSON.stringify(userData));
    setUserContext({
      id: userData.id.toString(),
      email: userData.email,
      username: userData.username,
      is_staff: userData.is_staff
    });
  }

  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('authChange'));
  }

  return { access, refresh };
};

// Complete 2FA login — backend expects {username, password, totp_code}
export const login2FA = async (username: string, password: string, totpCode: string): Promise<AuthTokens> => {
  const response = await api.post('/auth/2fa/verify/', {
    username,
    password,
    totp_code: totpCode,
  });
  const { access, refresh } = response.data;

  setCookie('access_token', access);
  setCookie('refresh_token', refresh, 30 * 24 * 60 * 60);
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);

  const userData = await getCurrentUser(access);
  if (userData) {
    localStorage.setItem('user', JSON.stringify(userData));
    setUserContext({
      id: userData.id.toString(),
      email: userData.email,
      username: userData.username,
      is_staff: userData.is_staff
    });
  }

  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('authChange'));
  }

  return { access, refresh };
};

// Complete 2FA login after Google OAuth — backend expects {google_user_id, totp_code}
export const loginGoogle2FA = async (googleUserId: string, totpCode: string): Promise<AuthTokens> => {
  const response = await api.post('/auth/2fa/google-verify/', {
    google_user_id: googleUserId,
    totp_code: totpCode,
  });
  const { access, refresh } = response.data;

  setCookie('access_token', access);
  setCookie('refresh_token', refresh, 30 * 24 * 60 * 60);
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);

  const userData = await getCurrentUser(access);
  if (userData) {
    localStorage.setItem('user', JSON.stringify(userData));
    setUserContext({
      id: userData.id.toString(),
      email: userData.email,
      username: userData.username,
      is_staff: userData.is_staff
    });
  }

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
    if (access && access !== 'null' && access !== 'undefined') {
      // If we have an access token, check if it's valid.
      // Even if it's expired, if we have a refresh token, return it so the api interceptor can catch the 401 and refresh it.
      if (!_isTokenExpired(access) || document.cookie.includes('refresh_token=') || localStorage.getItem('refresh_token')) {
        return access;
      }
    }
  }

  // Fallback to localStorage - if found, restore the cookie!
  const tokenFromStorage = localStorage.getItem('access_token');
  if (tokenFromStorage && tokenFromStorage !== 'null' && tokenFromStorage !== 'undefined') {
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
