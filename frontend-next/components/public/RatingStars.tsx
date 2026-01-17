'use client';

import { useState } from 'react';
import { Star } from 'lucide-react';
import api from '@/lib/api';

interface RatingStarsProps {
  articleId: number;
  initialRating: number;
  ratingCount: number;
}

export default function RatingStars({ articleId, initialRating, ratingCount }: RatingStarsProps) {
  const [rating, setRating] = useState(initialRating);
  const [count, setCount] = useState(ratingCount);
  const [hoveredStar, setHoveredStar] = useState(0);
  const [userRating, setUserRating] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState('');

  const handleRate = async (stars: number) => {
    if (userRating > 0) {
      setMessage('You have already rated this article!');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await api.post(`/articles/${articleId}/rate/`, {
        rating: stars
      });
      
      setRating(response.data.average_rating);
      setCount(response.data.rating_count);
      setUserRating(stars);
      setMessage('✓ Thank you for rating!');
      setTimeout(() => setMessage(''), 3000);
    } catch (error: any) {
      console.error('Rating error:', error);
      setMessage(error.response?.data?.error || 'Failed to submit rating');
      setTimeout(() => setMessage(''), 3000);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-6 mb-8">
      <h3 className="text-xl font-bold text-gray-900 mb-4 text-center">
        ⭐ Rate this Article
      </h3>
      
      <div className="flex justify-center items-center gap-4 mb-4">
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((star) => (
            <button
              key={star}
              onClick={() => handleRate(star)}
              onMouseEnter={() => setHoveredStar(star)}
              onMouseLeave={() => setHoveredStar(0)}
              disabled={isSubmitting || userRating > 0}
              className="transition-all transform hover:scale-110 disabled:cursor-not-allowed"
            >
              <Star
                size={40}
                className={`${
                  star <= (hoveredStar || userRating || Math.round(rating))
                    ? 'fill-amber-400 text-amber-400'
                    : 'text-gray-300'
                } transition-colors`}
              />
            </button>
          ))}
        </div>
        
        <div className="text-center">
          <div className="text-3xl font-bold text-gray-900">
            {rating.toFixed(1)}
          </div>
          <div className="text-sm text-gray-500">
            ({count} {count === 1 ? 'vote' : 'votes'})
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
