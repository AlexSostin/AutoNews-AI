import { getApiUrl } from './api';
import { authenticatedFetch, silentAuthFetch } from './authenticatedFetch';

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
    if (!token) return [];

    try {
      const data = await silentAuthFetch('/favorites/', []);
      return Array.isArray(data) ? data : ((data as any).results || []);
    } catch {
      return [];
    }
  },

  // Toggle favorite status
  async toggleFavorite(articleId: number, token: string): Promise<{
    detail: string;
    is_favorited: boolean;
    favorite?: Favorite;
  }> {
    if (!token) throw new Error('Please log in to add favorites');

    try {
      const response = await authenticatedFetch('/favorites/toggle/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ article: articleId }),
      });

      if (!response.ok) {
        throw new Error('Failed to toggle favorite');
      }
      return await response.json();
    } catch (error: any) {
      if (error.message === 'Session expired' || error.message === 'Not authenticated') {
        throw new Error('Session expired. Please log in again.');
      }
      throw error;
    }
  },

  // Check if article is favorited
  async checkFavorite(articleId: number, token: string): Promise<{ is_favorited: boolean }> {
    if (!token) return { is_favorited: false };

    try {
      return await silentAuthFetch(
        `/favorites/check/?article=${articleId}`,
        { is_favorited: false }
      );
    } catch {
      return { is_favorited: false };
    }
  },

  // Add to favorites
  async addFavorite(articleId: number, token: string): Promise<Favorite> {
    if (!token) throw new Error('Please log in to add favorites');

    try {
      const response = await authenticatedFetch('/favorites/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ article: articleId }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to add favorite');
      }
      return await response.json();
    } catch (error: any) {
      if (error.message === 'Session expired' || error.message === 'Not authenticated') {
        throw new Error('Session expired. Please log in again.');
      }
      throw error;
    }
  },

  // Remove from favorites
  async removeFavorite(favoriteId: number, token: string): Promise<void> {
    if (!token) throw new Error('Please log in to manage favorites');

    try {
      const response = await authenticatedFetch(`/favorites/${favoriteId}/`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to remove favorite');
      }
    } catch (error: any) {
      if (error.message === 'Session expired' || error.message === 'Not authenticated') {
        throw new Error('Session expired. Please log in again.');
      }
      throw error;
    }
  },
};

