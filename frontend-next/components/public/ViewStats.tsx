'use client';

import { Eye, TrendingUp, Clock } from 'lucide-react';

interface ViewStatsProps {
  views: number;
  createdAt: string;
  isTrending?: boolean;
}

export default function ViewStats({ views, createdAt, isTrending = false }: ViewStatsProps) {
  // Calculate how many days ago
  const daysAgo = Math.floor((Date.now() - new Date(createdAt).getTime()) / (1000 * 60 * 60 * 24));
  const isRecent = daysAgo <= 7;
  
  // Determine if trending (simplified: > 100 views in last 7 days)
  const isTrendingArticle = isTrending || (isRecent && views > 100);

  return (
    <div className="flex items-center gap-4 flex-wrap">
      {/* Views Count */}
      <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-full text-sm font-medium">
        <Eye size={16} className="text-gray-600" />
        <span className="font-semibold">{views.toLocaleString()}</span>
        <span>views</span>
      </div>

      {/* Trending Badge */}
      {isTrendingArticle && (
        <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-full text-sm font-bold shadow-md animate-pulse">
          <TrendingUp size={16} />
          <span>TRENDING</span>
        </div>
      )}

      {/* Recent Badge */}
      {isRecent && !isTrendingArticle && (
        <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-green-100 text-green-700 rounded-full text-sm font-medium border border-green-200">
          <Clock size={16} className="text-green-600" />
          <span>New</span>
        </div>
      )}
    </div>
  );
}
