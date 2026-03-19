import { getApiUrl } from './api';
import { refreshAccessToken, logout } from './auth';

/**
 * Authenticated fetch wrapper with automatic 401 handling.
 *
 * Uses refreshAccessToken() from auth.ts (single source of truth).
 * On failed refresh → calls logout() which clears all auth state and redirects.
 *
 * Use instead of raw fetch() for any authenticated API call.
 */

// Prevent multiple simultaneous refresh attempts
let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

function getTokenFromStorage(): string | null {
    if (typeof window === 'undefined') return null;

    const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('access_token='))
        ?.split('=')[1];

    if (token && token !== 'null' && token !== 'undefined') return token;

    const localToken = localStorage.getItem('access_token');
    if (localToken && localToken !== 'null' && localToken !== 'undefined') return localToken;
    return null;
}

function safeRefresh(): Promise<string | null> {
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
 * @param url - Full URL or path relative to API base (e.g. '/comments/my_comments/')
 * @param options - Standard fetch options
 * @returns Response object
 *
 * @example
 * const res = await authenticatedFetch('/comments/my_comments/');
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
        logout();
        throw new Error('Not authenticated');
    }

    const fullUrl = url.startsWith('http') ? url : `${getApiUrl()}${url}`;

    const headers: Record<string, string> = {
        ...(options.headers as Record<string, string> || {}),
        'Authorization': `Bearer ${token}`,
    };

    if (options.body && !headers['Content-Type'] && !(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(fullUrl, { ...options, headers });

    if (response.status !== 401) return response;

    // 401 — try to refresh (race-condition safe)
    const newToken = await safeRefresh();

    if (!newToken) {
        logout();
        throw new Error('Session expired');
    }

    headers['Authorization'] = `Bearer ${newToken}`;
    return fetch(fullUrl, { ...options, headers });
}

/**
 * Authenticated fetch that returns a graceful fallback on auth failure.
 * Use for non-critical data where you don't want a redirect on 401.
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
            const newToken = await safeRefresh();
            if (newToken) {
                headers['Authorization'] = `Bearer ${newToken}`;
                const retryResponse = await fetch(fullUrl, { ...options, headers });
                if (retryResponse.ok) return await retryResponse.json();
            }
            // Refresh failed — clear stale tokens silently (no redirect)
            if (typeof window !== 'undefined') {
                document.cookie = 'access_token=; path=/; max-age=0';
                document.cookie = 'refresh_token=; path=/; max-age=0';
                localStorage.removeItem('access_token');
                localStorage.removeItem('user');
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
