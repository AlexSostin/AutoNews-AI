'use client';

import { useState, useEffect } from 'react';
import { Heart } from 'lucide-react';
import { favoriteAPI } from '@/lib/favorites';
import { getToken } from '@/lib/auth';
import { useRouter } from 'next/navigation';

interface FavoriteButtonProps {
  articleId: number;
  initialIsFavorited?: boolean;
  showText?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export default function FavoriteButton({ 
  articleId, 
  initialIsFavorited = false,
  showText = false,
  size = 'md',
  className = ''
}: FavoriteButtonProps) {
  const [isFavorited, setIsFavorited] = useState(initialIsFavorited);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setIsFavorited(initialIsFavorited);
  }, [initialIsFavorited]);

  const handleToggle = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const token = getToken();
    if (!token) {
      router.push('/login');
      return;
    }

    setIsLoading(true);
    try {
      const result = await favoriteAPI.toggleFavorite(articleId, token);
      setIsFavorited(result.is_favorited);
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
  };

  const iconSizes = {
    sm: 16,
    md: 20,
    lg: 24,
  };

  return (
    <button
      onClick={handleToggle}
      disabled={isLoading}
      className={`
        ${sizeClasses[size]}
        flex items-center justify-center
        rounded-full
        transition-all duration-200
        ${isFavorited 
          ? 'bg-red-50 text-red-600 hover:bg-red-100' 
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
        }
        ${isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:scale-110'}
        ${className}
      `}
      aria-label={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
    >
      <Heart
        size={iconSizes[size]}
        className={`transition-all ${isFavorited ? 'fill-current' : ''}`}
      />
      {showText && (
        <span className="ml-2 text-sm font-medium">
          {isFavorited ? 'Saved' : 'Save'}
        </span>
      )}
    </button>
  );
}
