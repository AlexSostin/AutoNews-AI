'use client';

import { useState, useEffect } from 'react';
import { Star } from 'lucide-react';
import api from '@/lib/api';

interface RatingStarsProps {
  articleSlug: string;
  initialRating: number;
  ratingCount: number;
}

export default function RatingStars({ articleSlug, initialRating, ratingCount }: RatingStarsProps) {
  const [rating, setRating] = useState(initialRating || 0);
  const [count, setCount] = useState(ratingCount || 0);
  const [hoveredStar, setHoveredStar] = useState(0);
  const [userRating, setUserRating] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [message, setMessage] = useState('');

  // Load user's rating on mount
  useEffect(() => {
    const loadUserRating = async () => {
      try {
        const response = await api.get(`/articles/${articleSlug}/my-rating/`);
        if (response.data.has_rated) {
          setUserRating(response.data.user_rating);
        }
      } catch (error) {
        console.error('Failed to load user rating:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadUserRating();
  }, [articleSlug]);

  const handleRate = async (stars: number) => {
    setIsSubmitting(true);
    try {
      const response = await api.post(`/articles/${articleSlug}/rate/`, {
        rating: stars
      });
      
      console.log('Rating response:', response.data);
      setRating(response.data.average_rating);
      setCount(response.data.rating_count);
      setUserRating(stars);
      
      // Update the article rating display at the top of the page
      if (typeof window !== 'undefined' && (window as any).updateArticleRating) {
        (window as any).updateArticleRating(response.data.average_rating, response.data.rating_count);
      }
      
      setMessage('✓ Rating updated!');
      setTimeout(() => setMessage(''), 3000);
    } catch (error: any) {
      console.error('Rating error:', error);
      setMessage(error.response?.data?.error || 'Failed to submit rating');
      setTimeout(() => setMessage(''), 3000);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-md p-6 mb-8">
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-md p-6 mb-8">
      <h3 className="text-xl font-bold text-gray-900 mb-4 text-center">
        ⭐ Rate this Article
      </h3>
      
      {userRating > 0 && (
        <div className="text-center mb-2">
          <p className="text-sm text-indigo-600 font-medium">
            Your rating: {userRating} ★
          </p>
        </div>
      )}
      
      <div className="flex justify-center items-center gap-4 mb-4">
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((star) => (
            <button
              key={star}
              onClick={() => handleRate(star)}
              onMouseEnter={() => setHoveredStar(star)}
              onMouseLeave={() => setHoveredStar(0)}
              disabled={isSubmitting}
              className="transition-all transform hover:scale-110 disabled:cursor-not-allowed"
            >
              <Star
                size={40}
                className={`${
                  star <= (hoveredStar || userRating)
                    ? 'fill-amber-400 text-amber-400'
                    : 'text-gray-300'
                } transition-colors`}
              />
            </button>
          ))}
        </div>
        
        <div className="text-center">
          <div className="text-3xl font-bold text-gray-900">
            {(rating || 0).toFixed(1)}
          </div>
          <div className="text-sm text-gray-500">
            ({count || 0} {count === 1 ? 'vote' : 'votes'})
          </div>
        </div>
      </div>

      {message && (
        <p className={`text-center text-sm font-medium ${
          message.includes('✓') ? 'text-green-600' : 'text-red-600'
        }`}>
          {message}
        </p>
      )}

      {userRating === 0 && !message && (
        <p className="text-center text-sm text-gray-500">
          Click a star to rate
        </p>
      )}
    </div>
  );
}
