'use client';

import { useState } from 'react';
import { Star } from 'lucide-react';

interface ArticleRatingProps {
  initialRating: number;
  initialCount: number;
}

export default function ArticleRating({ initialRating, initialCount }: ArticleRatingProps) {
  const [rating, setRating] = useState(initialRating);
  const [count, setCount] = useState(initialCount);

  // This function will be called by RatingStars to update the display
  if (typeof window !== 'undefined') {
    (window as any).updateArticleRating = (newRating: number, newCount: number) => {
      setRating(newRating);
      setCount(newCount);
    };
  }

  if (rating === 0 || count === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-2">
      <Star size={18} className="fill-amber-400 text-amber-400" />
      <span className="font-semibold text-amber-600">
        {rating.toFixed(1)} ({count} {count === 1 ? 'rating' : 'ratings'})
      </span>
    </div>
  );
}
