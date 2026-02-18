import { getApiUrl } from './api';
import { logout, getAccessToken } from './auth';

export interface Favorite {
  id: number;
  article: number;
  article_title: string;
  article_slug: string;
  article_image: string;
  article_summary: string;
  article_category: string;
  created_at: string;
}

// Try to refresh the access token, returns new token or null
async function tryRefreshToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null;

  const refreshToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('refresh_token='))
    ?.split('=')[1]
    || localStorage.getItem('refresh_token');

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

// Clear all auth tokens without redirect
function clearAuthTokens() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  document.cookie = 'access_token=; path=/; max-age=0';
  document.cookie = 'refresh_token=; path=/; max-age=0';
  window.dispatchEvent(new Event('authChange'));
}

// Helper: make a fetch request, and on 401 try refresh + retry once
async function fetchWithRefresh(
  url: string,
  options: RequestInit,
  token: string
): Promise<{ response: Response; authFailed: boolean }> {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
    },
  });

  if (response.status !== 401) {
    return { response, authFailed: false };
  }

  // 401 — try refresh
  const newToken = await tryRefreshToken();
  if (!newToken) {
    // Refresh failed — clear tokens
    clearAuthTokens();
    return { response, authFailed: true };
  }

  // Retry with new token
  const retryResponse = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${newToken}`,
    },
  });

  return { response: retryResponse, authFailed: retryResponse.status === 401 };
}

export const favoriteAPI = {
  // Get all user favorites
  async getFavorites(token: string): Promise<Favorite[]> {
    if (!token) return [];

    const { response, authFailed } = await fetchWithRefresh(
      `${getApiUrl()}/favorites/`,
      {},
      token
    );
    if (authFailed) return [];
    if (!response.ok) {
      throw new Error('Failed to fetch favorites');
    }
    const data = await response.json();
    return Array.isArray(data) ? data : (data.results || []);
  },

  // Toggle favorite status
  async toggleFavorite(articleId: number, token: string): Promise<{
    detail: string;
    is_favorited: boolean;
    favorite?: Favorite;
  }> {
    if (!token) throw new Error('Please log in to add favorites');

    const { response, authFailed } = await fetchWithRefresh(
      `${getApiUrl()}/favorites/toggle/`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ article: articleId }),
      },
      token
    );
    if (authFailed) throw new Error('Session expired. Please log in again.');
    if (!response.ok) {
      throw new Error('Failed to toggle favorite');
    }
    return response.json();
  },

  // Check if article is favorited
  async checkFavorite(articleId: number, token: string): Promise<{ is_favorited: boolean }> {
    if (!token) return { is_favorited: false };

    const { response, authFailed } = await fetchWithRefresh(
      `${getApiUrl()}/favorites/check/?article=${articleId}`,
      {},
      token
    );
    if (authFailed) return { is_favorited: false };
    if (!response.ok) {
      throw new Error('Failed to check favorite status');
    }
    return response.json();
  },

  // Add to favorites
  async addFavorite(articleId: number, token: string): Promise<Favorite> {
    if (!token) throw new Error('Please log in to add favorites');

    const { response, authFailed } = await fetchWithRefresh(
      `${getApiUrl()}/favorites/`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ article: articleId }),
      },
      token
    );
    if (authFailed) throw new Error('Session expired. Please log in again.');
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to add favorite');
    }
    return response.json();
  },

  // Remove from favorites
  async removeFavorite(favoriteId: number, token: string): Promise<void> {
    if (!token) throw new Error('Please log in to manage favorites');

    const { response, authFailed } = await fetchWithRefresh(
      `${getApiUrl()}/favorites/${favoriteId}/`,
      { method: 'DELETE' },
      token
    );
    if (authFailed) throw new Error('Session expired. Please log in again.');
    if (!response.ok) {
      throw new Error('Failed to remove favorite');
    }
  },
};

