import api, { getApiUrl } from './api';
import { authenticatedFetch } from './authenticatedFetch';
import { AuthTokens, LoginCredentials, User } from '@/types';
import { setUserContext, clearUserContext } from './errorTracking';

// ─── Cookie helpers ───────────────────────────────────────────────────────────

const setCookie = (name: string, value: string, maxAgeSeconds: number = 7 * 24 * 60 * 60) => {
  const isSecure = typeof window !== 'undefined' && window.location.protocol === 'https:';
  const secureFlag = isSecure ? '; Secure' : '';
  document.cookie = `${name}=${value}; path=/; max-age=${maxAgeSeconds}; SameSite=Lax${secureFlag}`;
};

const deleteCookie = (name: string) => {
  document.cookie = `${name}=; path=/; max-age=0; SameSite=Lax`;
  document.cookie = `${name}=; path=/; max-age=0`;
};

const getCookieValue = (name: string): string | null => {
  if (typeof window === 'undefined') return null;
  const found = document.cookie.split('; ').find(row => row.startsWith(`${name}=`));
  const value = found?.split('=')[1];
  return value && value !== 'null' && value !== 'undefined' ? value : null;
};

// ─── Custom error classes ─────────────────────────────────────────────────────

export class TwoFARequiredError extends Error {
  hasPasskeys: boolean;
  pendingToken: string;
  constructor(hasPasskeys = false, pendingToken = '') {
    super('2FA required');
    this.name = 'TwoFARequiredError';
    this.hasPasskeys = hasPasskeys;
    this.pendingToken = pendingToken;
  }
}

export class PasskeyRequiredError extends Error {
  pendingToken: string;
  has2FA: boolean;
  googleUserId?: string;

  constructor(pendingToken: string, has2FA = false, googleUserId?: string) {
    super('Passkey required');
    this.name = 'PasskeyRequiredError';
    this.pendingToken = pendingToken;
    this.has2FA = has2FA;
    this.googleUserId = googleUserId;
  }
}

// ─── Token management ─────────────────────────────────────────────────────────

/**
 * Single source of truth for refreshing access tokens.
 * Reads refresh_token from cookie, calls /token/refresh/, updates cookies.
 * Used by: authenticatedFetch.ts, useProactiveTokenRefresh.ts, verifyAndRefreshSession()
 */
export const refreshAccessToken = async (): Promise<string | null> => {
  if (typeof window === 'undefined') return null;

  const refreshToken = getCookieValue('refresh_token');
  if (!refreshToken) return null;

  try {
    const response = await fetch(`${getApiUrl()}/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    if (!response.ok) return null;

    const { access, refresh: newRefresh } = await response.json();

    setCookie('access_token', access, 7 * 24 * 60 * 60);
    if (newRefresh) {
      setCookie('refresh_token', newRefresh, 30 * 24 * 60 * 60);
    }

    // Keep user in localStorage (non-sensitive, used for quick display)
    localStorage.setItem('access_token', access);

    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event('authChange'));
    }

    return access;
  } catch {
    return null;
  }
};

/**
 * Verifies current session is alive; tries to refresh if expired.
 * Use in admin layout on mount instead of raw fetch() inline code.
 * Returns true = session ok, false = both tokens invalid (should redirect to login).
 */
export const verifyAndRefreshSession = async (): Promise<boolean> => {
  if (typeof window === 'undefined') return false;

  const accessToken = getCookieValue('access_token');
  if (!accessToken) {
    // No access token — try refresh directly
    const newToken = await refreshAccessToken();
    return newToken !== null;
  }

  try {
    const res = await fetch(`${getApiUrl()}/token/verify/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: accessToken }),
    });

    if (res.ok) return true;

    // Access token expired — try refresh
    const newToken = await refreshAccessToken();
    return newToken !== null;
  } catch {
    // Network error (e.g. 502 during Railway redeploy) — don't log out!
    // If we have any token at all, assume session is still valid.
    const refreshToken = getCookieValue('refresh_token');
    if (accessToken || refreshToken) {
      console.warn('⚠️ Token verify failed (network?), assuming session valid');
      return true;
    }
    return false;
  }
};

const _storeTokensAndUser = async (access: string, refresh: string) => {
  setCookie('access_token', access, 7 * 24 * 60 * 60);
  setCookie('refresh_token', refresh, 30 * 24 * 60 * 60);
  // Keep access_token in localStorage as a convenience fallback for SSR edge cases
  localStorage.setItem('access_token', access);

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
};

// ─── Auth actions ─────────────────────────────────────────────────────────────

export const login = async (credentials: LoginCredentials): Promise<AuthTokens> => {
  const response = await api.post('/token/', credentials);
  const data = response.data;

  if (data.requires_2fa) {
    throw new TwoFARequiredError(data.has_passkeys === true, data.pending_token ?? '');
  }

  if (data.requires_passkey) {
    throw new PasskeyRequiredError(data.pending_token ?? '', data.has_2fa === true, data.google_user_id);
  }

  const { access, refresh } = data;
  await _storeTokensAndUser(access, refresh);
  return { access, refresh };
};

export const login2FA = async (username: string, password: string, totpCode: string): Promise<AuthTokens> => {
  const response = await api.post('/auth/2fa/verify/', { username, password, totp_code: totpCode });
  const { access, refresh } = response.data;
  await _storeTokensAndUser(access, refresh);
  return { access, refresh };
};

export const loginGoogle2FA = async (googleUserId: string, totpCode: string): Promise<AuthTokens> => {
  const response = await api.post('/auth/2fa/google-verify/', { google_user_id: googleUserId, totp_code: totpCode });
  const { access, refresh } = response.data;
  await _storeTokensAndUser(access, refresh);
  return { access, refresh };
};

export const logout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user');

  deleteCookie('access_token');
  deleteCookie('refresh_token');

  clearUserContext();

  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('authChange'));
  }

  window.location.href = '/login';
};

// ─── Token state helpers ──────────────────────────────────────────────────────

const _isTokenExpired = (token: string): boolean => {
  try {
    const payload = token.split('.')[1];
    if (!payload) return true;
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const decoded = JSON.parse(atob(base64));
    if (!decoded.exp) return false;
    return decoded.exp * 1000 < Date.now() + 30000; // 30s buffer
  } catch {
    return true;
  }
};

export const getTokenExpiresInMs = (token: string): number => {
  try {
    const payload = token.split('.')[1];
    if (!payload) return 0;
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const decoded = JSON.parse(atob(base64));
    if (!decoded.exp) return Infinity;
    return decoded.exp * 1000 - Date.now();
  } catch {
    return 0;
  }
};

export const isAuthenticated = (): boolean => {
  if (typeof window === 'undefined') return false;

  const token = getCookieValue('access_token');
  if (token) {
    if (!_isTokenExpired(token)) return true;
    // Expired access token — still authenticated if refresh token exists
    return getCookieValue('refresh_token') !== null;
  }

  // Fallback: localStorage access token (restores cookie for middleware)
  const tokenFromStorage = localStorage.getItem('access_token');
  if (tokenFromStorage && tokenFromStorage !== 'null' && tokenFromStorage !== 'undefined') {
    if (!_isTokenExpired(tokenFromStorage)) {
      setCookie('access_token', tokenFromStorage);
      return true;
    }
    // Expired — check if refresh token cookie exists
    return getCookieValue('refresh_token') !== null;
  }

  return false;
};

export const getAccessToken = (): string | null => {
  if (typeof window === 'undefined') return null;

  const token = getCookieValue('access_token');
  if (token) return token;

  // Fallback to localStorage (restores cookie)
  const tokenFromStorage = localStorage.getItem('access_token');
  if (tokenFromStorage && tokenFromStorage !== 'null' && tokenFromStorage !== 'undefined') {
    setCookie('access_token', tokenFromStorage);
    return tokenFromStorage;
  }

  return null;
};

// Alias for convenience
export const getToken = getAccessToken;

// ─── User helpers ─────────────────────────────────────────────────────────────

export const getCurrentUser = async (token?: string): Promise<User | null> => {
  try {
    const accessToken = token || getAccessToken();
    if (!accessToken) return null;

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
