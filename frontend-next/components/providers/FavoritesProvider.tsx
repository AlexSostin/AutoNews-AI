'use client';

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { getToken } from '@/lib/auth';
import { favoriteAPI } from '@/lib/favorites';

interface FavoritesContextType {
  favoriteIds: Set<number>;
  isFavorited: (articleId: number) => boolean;
  toggleFavorite: (articleId: number) => Promise<boolean>;
  isLoaded: boolean;
}

const FavoritesContext = createContext<FavoritesContextType>({
  favoriteIds: new Set(),
  isFavorited: () => false,
  toggleFavorite: async () => false,
  isLoaded: false,
});

export function useFavorites() {
  return useContext(FavoritesContext);
}

export default function FavoritesProvider({ children }: { children: ReactNode }) {
  const [favoriteIds, setFavoriteIds] = useState<Set<number>>(new Set());
  const [isLoaded, setIsLoaded] = useState(false);

  // Load all favorites once on mount (1 API call instead of N)
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setIsLoaded(true);
      return;
    }

    favoriteAPI.getAllFavoriteIds(token)
      .then(ids => {
        setFavoriteIds(new Set(ids));
        setIsLoaded(true);
      })
      .catch(() => {
        setIsLoaded(true);
      });

    // Re-check when user logs in/out
    const handleAuthChange = () => {
      const newToken = getToken();
      if (!newToken) {
        setFavoriteIds(new Set());
        return;
      }
      favoriteAPI.getAllFavoriteIds(newToken)
        .then(ids => setFavoriteIds(new Set(ids)))
        .catch(() => {});
    };

    window.addEventListener('authChange', handleAuthChange);
    return () => window.removeEventListener('authChange', handleAuthChange);
  }, []);

  const isFavorited = useCallback(
    (articleId: number) => favoriteIds.has(articleId),
    [favoriteIds]
  );

  const toggleFavorite = useCallback(async (articleId: number): Promise<boolean> => {
    const token = getToken();
    if (!token) return false;

    try {
      const result = await favoriteAPI.toggleFavorite(articleId, token);
      
      setFavoriteIds(prev => {
        const next = new Set(prev);
        if (result.is_favorited) {
          next.add(articleId);
        } else {
          next.delete(articleId);
        }
        return next;
      });
      
      return result.is_favorited;
    } catch {
      return favoriteIds.has(articleId);
    }
  }, [favoriteIds]);

  return (
    <FavoritesContext.Provider value={{ favoriteIds, isFavorited, toggleFavorite, isLoaded }}>
      {children}
    </FavoritesContext.Provider>
  );
}
