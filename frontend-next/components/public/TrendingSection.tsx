'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { TrendingUp, Eye } from 'lucide-react';
import { fixImageUrl } from '@/lib/config';
import { getApiUrl } from '@/lib/config';

interface TrendingArticle {
  id: number;
  title: string;
  display_title?: string;
  slug: string;
  image: string | null;
  display_image?: string | null;
  views: number;
  categories: { id: number; name: string; slug: string }[];
}

export default function TrendingSection() {
  const [articles, setArticles] = useState<TrendingArticle[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const apiUrl = getApiUrl();

    const processResults = (data: { results?: TrendingArticle[] }) => {
      const results = data.results || [];
      const seen = new Set<number>();
      const unique = results.filter((a: TrendingArticle) => {
        if (seen.has(a.id)) return false;
        seen.add(a.id);
        return true;
      });
      setArticles(unique.slice(0, 5));
      setLoading(false);
    };

    fetch(`${apiUrl}/articles/recommended/?page_size=10`)
      .then(res => {
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        return res.json();
      })
      .then(processResults)
      .catch(() => {
        // Fallback to trending if recommended fails (e.g. during backend restart)
        fetch(`${apiUrl}/articles/trending/`)
          .then(res => {
            if (!res.ok) throw new Error(`Trending API returned ${res.status}`);
            return res.json();
          })
          .then(data => processResults({ results: Array.isArray(data) ? data : data.results || [] }))
          .catch(err => {
            console.error('Failed to load articles:', err);
            setLoading(false);
          });
      });
  }, []);

  if (loading) {
    return (
      <div className="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-xl p-6 shadow-xl">
        <div className="flex items-center gap-2 mb-6">
          <Eye className="text-white animate-pulse" size={24} />
          <h2 className="text-2xl font-bold text-white">Recommended for You</h2>
        </div>
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="animate-pulse bg-white/20 rounded-lg p-3 h-20" />
          ))}
        </div>
      </div>
    );
  }

  if (articles.length === 0) {
    return (
      <div className="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-xl p-6 shadow-xl sticky top-24">
        <div className="flex items-center gap-2 mb-6">
          <Eye className="text-white" size={24} />
          <h2 className="text-2xl font-bold text-white">🎯 Recommended</h2>
        </div>
        <div className="text-center py-8">
          <p className="text-white/80 text-lg">No articles yet</p>
          <p className="text-white/60 text-sm mt-2">Popular articles will appear here soon</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-xl p-6 shadow-xl sticky top-24">
      <div className="flex items-center gap-2 mb-6">
        <Eye className="text-white animate-pulse" size={24} />
        <h2 className="text-2xl font-bold text-white">🎯 Recommended for You</h2>
      </div>

      <div className="space-y-4">
        {articles.map((article, index) => (
          <Link
            key={article.id}
            href={`/articles/${article.slug}`}
            className="group block bg-white/10 hover:bg-white/20 backdrop-blur-sm rounded-lg p-3 transition-all duration-300 hover:scale-105 border border-white/20"
          >
            <div className="flex items-start gap-3">
              {/* Ranking Badge */}
              <div className="flex-shrink-0 w-8 h-8 bg-white rounded-full flex items-center justify-center font-bold text-indigo-600 text-sm">
                {index + 1}
              </div>

              {/* Image */}
              {(article.display_image || article.image) && (
                <div className="relative w-16 h-16 flex-shrink-0 rounded-lg overflow-hidden">
                  <Image
                    src={fixImageUrl(article.display_image || article.image)}
                    alt={article.display_title || article.title}
                    fill
                    className="object-cover group-hover:scale-110 transition-transform"
                    unoptimized
                  />
                </div>
              )}

              {/* Content */}
              <div className="flex-1 min-w-0">
                <h3 className="text-white font-semibold text-sm line-clamp-2 group-hover:text-yellow-200 transition-colors mb-1">
                  {article.display_title || article.title}
                </h3>
                <div className="flex items-center gap-2 text-xs text-white/80 flex-wrap">
                  <span className="px-2 py-0.5 bg-white/20 rounded-full truncate max-w-[80px]">
                    {article.categories?.[0]?.name || 'News'}
                  </span>
                  <div className="flex items-center gap-1">
                    <Eye size={12} />
                    <span>{article.views}</span>
                  </div>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>

      <Link
        href="/trending"
        className="mt-4 block text-center bg-white/20 hover:bg-white/30 text-white font-semibold py-2 rounded-lg transition-colors"
      >
        View All Popular →
      </Link>
    </div>
  );
}
