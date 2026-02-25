import { getApiUrl } from './api';

/**
 * Authenticated fetch wrapper with 401 handling.
 * 
 * Handles expired tokens by:
 * 1. Attempting to refresh the access token using the refresh token
 * 2. If refresh succeeds, retrying the original request with the new token
 * 3. If refresh fails, clearing all auth tokens and redirecting to /login
 * 
 * Use this instead of raw fetch() for any authenticated API call.
 */

// Prevent multiple simultaneous refresh attempts
let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
    if (typeof window === 'undefined') return null;

    const refreshToken = document.cookie
        .split('; ')
        .find(row => row.startsWith('refresh_token='))
        ?.split('=')[1] || localStorage.getItem('refresh_token');

    if (!refreshToken) return null;

    try {
        const response = await fetch(`${getApiUrl()}/token/refresh/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh: refreshToken }),
        });

        if (!response.ok) return null;

        const { access, refresh: newRefresh } = await response.json();

        // Update cookies
        const isSecure = window.location.protocol === 'https:';
        const secureFlag = isSecure ? '; Secure' : '';
        document.cookie = `access_token=${access}; path=/; max-age=${7 * 24 * 60 * 60}; SameSite=Lax${secureFlag}`;
        if (newRefresh) {
            document.cookie = `refresh_token=${newRefresh}; path=/; max-age=${30 * 24 * 60 * 60}; SameSite=Lax${secureFlag}`;
        }

        // Update localStorage
        localStorage.setItem('access_token', access);
        if (newRefresh) {
            localStorage.setItem('refresh_token', newRefresh);
        }

        return access;
    } catch {
        return null;
    }
}

function clearAuthAndRedirect() {
    if (typeof window === 'undefined') return;

    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    document.cookie = 'access_token=; path=/; max-age=0';
    document.cookie = 'refresh_token=; path=/; max-age=0';
    window.dispatchEvent(new Event('authChange'));
    window.location.href = '/login';
}

function getTokenFromStorage(): string | null {
    if (typeof window === 'undefined') return null;

    // Check cookies first
    const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('access_token='))
        ?.split('=')[1];

    if (token && token !== 'null' && token !== 'undefined') return token;

    // Fallback to localStorage
    const localToken = localStorage.getItem('access_token');
    if (localToken && localToken !== 'null' && localToken !== 'undefined') return localToken;
    return null;
}

function safeRefreshAccessToken(): Promise<string | null> {
    if (!isRefreshing) {
        isRefreshing = true;
        refreshPromise = refreshAccessToken().finally(() => {
            isRefreshing = false;
            refreshPromise = null;
        });
    }
    return refreshPromise || refreshAccessToken();
}

/**
 * Make an authenticated API request with automatic 401 handling.
 * 
 * @param url - Full URL or path (relative to API base)
 * @param options - Standard fetch options (method, body, headers, etc.)
 * @returns Response object
 * @throws Error if request fails for non-auth reasons
 * 
 * @example
 * // GET request
 * const res = await authenticatedFetch('/comments/my_comments/');
 * 
 * // POST request
 * const res = await authenticatedFetch('/auth/password/change/', {
 *   method: 'POST',
 *   body: JSON.stringify({ old_password: '...', new_password1: '...' }),
 * });
 */
export async function authenticatedFetch(
    url: string,
    options: RequestInit = {}
): Promise<Response> {
    const token = getTokenFromStorage();
    if (!token) {
        clearAuthAndRedirect();
        throw new Error('Not authenticated');
    }

    // Build full URL if relative
    const fullUrl = url.startsWith('http') ? url : `${getApiUrl()}${url}`;

    // Merge auth header with any existing headers
    const headers: Record<string, string> = {
        ...(options.headers as Record<string, string> || {}),
        'Authorization': `Bearer ${token}`,
    };

    // Add Content-Type for non-GET requests with body (skip for FormData — browser sets boundary)
    if (options.body && !headers['Content-Type'] && !(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(fullUrl, { ...options, headers });

    // If not 401, return as-is
    if (response.status !== 401) {
        return response;
    }

    // 401 — try to refresh the token (prevent race conditions)
    const newToken = await safeRefreshAccessToken();

    if (!newToken) {
        // Refresh failed — clear everything and redirect
        clearAuthAndRedirect();
        throw new Error('Session expired');
    }

    // Retry with new token
    headers['Authorization'] = `Bearer ${newToken}`;
    return fetch(fullUrl, { ...options, headers });
}

/**
 * Make an authenticated API request that returns graceful defaults on auth failure.
 * Use for non-critical data fetching where you don't want to redirect on 401.
 * 
 * @example
 * const count = await silentAuthFetch('/favorites/', []);
 */
export async function silentAuthFetch<T>(
    url: string,
    fallback: T,
    options: RequestInit = {}
): Promise<T> {
    const token = getTokenFromStorage();
    if (!token) return fallback;

    const fullUrl = url.startsWith('http') ? url : `${getApiUrl()}${url}`;

    const headers: Record<string, string> = {
        ...(options.headers as Record<string, string> || {}),
        'Authorization': `Bearer ${token}`,
    };

    try {
        const response = await fetch(fullUrl, { ...options, headers });

        if (response.status === 401) {
            // Try to refresh the token before giving up
            const newToken = await safeRefreshAccessToken();
            if (newToken) {
                // Retry with new token
                headers['Authorization'] = `Bearer ${newToken}`;
                const retryResponse = await fetch(fullUrl, { ...options, headers });
                if (retryResponse.ok) {
                    return await retryResponse.json();
                }
            }

            // Refresh failed — clear stale tokens (without redirect)
            if (typeof window !== 'undefined') {
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                localStorage.removeItem('user');
                document.cookie = 'access_token=; path=/; max-age=0';
                document.cookie = 'refresh_token=; path=/; max-age=0';
                window.dispatchEvent(new Event('authChange'));
            }
            return fallback;
        }

        if (!response.ok) return fallback;
        return await response.json();
    } catch {
        return fallback;
    }
}
