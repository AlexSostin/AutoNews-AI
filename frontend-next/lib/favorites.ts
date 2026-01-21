import { getApiUrl } from './api';

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

export const favoriteAPI = {
  // Get all user favorites
  async getFavorites(token: string): Promise<Favorite[]> {
    const response = await fetch(`${getApiUrl()}/favorites/`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
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
    const response = await fetch(`${getApiUrl()}/favorites/toggle/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ article: articleId }),
    });
    if (!response.ok) {
      throw new Error('Failed to toggle favorite');
    }
    return response.json();
  },

  // Check if article is favorited
  async checkFavorite(articleId: number, token: string): Promise<{ is_favorited: boolean }> {
    const response = await fetch(`${getApiUrl()}/favorites/check/?article=${articleId}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      throw new Error('Failed to check favorite status');
    }
    return response.json();
  },

  // Add to favorites
  async addFavorite(articleId: number, token: string): Promise<Favorite> {
    const response = await fetch(`${getApiUrl()}/favorites/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ article: articleId }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to add favorite');
    }
    return response.json();
  },

  // Remove from favorites
  async removeFavorite(favoriteId: number, token: string): Promise<void> {
    const response = await fetch(`${getApiUrl()}/favorites/${favoriteId}/`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      throw new Error('Failed to remove favorite');
    }
  },
};
