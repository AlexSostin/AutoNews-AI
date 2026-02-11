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

// Handle 401 responses - clear stale tokens
const handleAuthError = (response: Response) => {
  if (response.status === 401) {
    console.warn('Session expired, clearing auth tokens');
    // Clear tokens without redirect - let the UI handle it gracefully
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      document.cookie = 'access_token=; path=/; max-age=0';
      document.cookie = 'refresh_token=; path=/; max-age=0';
      window.dispatchEvent(new Event('authChange'));
    }
    return true;
  }
  return false;
};

export const favoriteAPI = {
  // Get all user favorites
  async getFavorites(token: string): Promise<Favorite[]> {
    if (!token) return []; // No token = no favorites, skip request

    const response = await fetch(`${getApiUrl()}/favorites/`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    if (handleAuthError(response)) return []; // Return empty on 401
    if (!response.ok) {
      throw new Error('Failed to fetch favorites');
    }
    const data = await response.json();
    // API returns paginated response {results: [...]} or array
    return Array.isArray(data) ? data : (data.results || []);
  },

  // Toggle favorite status
  async toggleFavorite(articleId: number, token: string): Promise<{
    detail: string;
    is_favorited: boolean;
    favorite?: Favorite;
  }> {
    if (!token) throw new Error('Please log in to add favorites');

    const response = await fetch(`${getApiUrl()}/favorites/toggle/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ article: articleId }),
    });
    if (handleAuthError(response)) throw new Error('Session expired. Please log in again.');
    if (!response.ok) {
      throw new Error('Failed to toggle favorite');
    }
    return response.json();
  },

  // Check if article is favorited
  async checkFavorite(articleId: number, token: string): Promise<{ is_favorited: boolean }> {
    if (!token) return { is_favorited: false }; // Not logged in = not favorited

    const response = await fetch(`${getApiUrl()}/favorites/check/?article=${articleId}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    if (handleAuthError(response)) return { is_favorited: false };
    if (!response.ok) {
      throw new Error('Failed to check favorite status');
    }
    return response.json();
  },

  // Add to favorites
  async addFavorite(articleId: number, token: string): Promise<Favorite> {
    if (!token) throw new Error('Please log in to add favorites');

    const response = await fetch(`${getApiUrl()}/favorites/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ article: articleId }),
    });
    if (handleAuthError(response)) throw new Error('Session expired. Please log in again.');
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to add favorite');
    }
    return response.json();
  },

  // Remove from favorites
  async removeFavorite(favoriteId: number, token: string): Promise<void> {
    if (!token) throw new Error('Please log in to manage favorites');

    const response = await fetch(`${getApiUrl()}/favorites/${favoriteId}/`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    if (handleAuthError(response)) throw new Error('Session expired. Please log in again.');
    if (!response.ok) {
      throw new Error('Failed to remove favorite');
    }
  },
};
