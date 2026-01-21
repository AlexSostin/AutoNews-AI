'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { TrendingUp, Eye } from 'lucide-react';

interface TrendingArticle {
  id: number;
  title: string;
  slug: string;
  image: string | null;
  views: number;
  category_name: string;
}

export default function TrendingSection() {
  const [articles, setArticles] = useState<TrendingArticle[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const getApiUrl = () => {
      if (typeof window !== 'undefined') {
        const host = window.location.hostname;
        if (host !== 'localhost' && host !== '127.0.0.1') {
          return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
        }
      }
      return 'http://localhost:8001/api/v1';
    };
    const apiUrl = getApiUrl();
    
    fetch(`${apiUrl}/articles/?is_published=true&ordering=-views&page_size=5`)
      .then(res => res.json())
      .then(data => {
        setArticles(data.results || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load trending articles:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="bg-gradient-to-br from-orange-500 to-pink-500 rounded-xl p-6 shadow-xl">
        <div className="flex items-center gap-2 mb-6">
          <TrendingUp className="text-white animate-bounce" size={24} />
          <h2 className="text-2xl font-bold text-white">Trending Now</h2>
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
      <div className="bg-gradient-to-br from-orange-500 to-pink-500 rounded-xl p-6 shadow-xl sticky top-24">
        <div className="flex items-center gap-2 mb-6">
          <TrendingUp className="text-white" size={24} />
          <h2 className="text-2xl font-bold text-white">🔥 Trending Now</h2>
        </div>
        <div className="text-center py-8">
          <p className="text-white/80 text-lg">Пока нет статей</p>
          <p className="text-white/60 text-sm mt-2">Скоро здесь появятся популярные материалы</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-orange-500 to-pink-500 rounded-xl p-6 shadow-xl sticky top-24">
      <div className="flex items-center gap-2 mb-6">
        <TrendingUp className="text-white animate-bounce" size={24} />
        <h2 className="text-2xl font-bold text-white">🔥 Trending Now</h2>
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
              <div className="flex-shrink-0 w-8 h-8 bg-white rounded-full flex items-center justify-center font-bold text-orange-500 text-sm">
                {index + 1}
              </div>
              
              {/* Image */}
              {article.image && (
                <div className="relative w-16 h-16 flex-shrink-0 rounded-lg overflow-hidden">
                  <Image
                    src={(() => {
                      const mediaUrl = typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
                        ? 'https://heroic-healing-production-2365.up.railway.app'
                        : 'http://localhost:8001';
                      if (article.image.startsWith('http')) {
                        return article.image.replace('http://backend:8001', mediaUrl).replace('http://localhost:8001', mediaUrl);
                      }
                      return `${mediaUrl}${article.image}`;
                    })()}
                    alt={article.title}
                    fill
                    className="object-cover group-hover:scale-110 transition-transform"
                    unoptimized
                  />
                </div>
              )}
              
              {/* Content */}
              <div className="flex-1 min-w-0">
                <h3 className="text-white font-semibold text-sm line-clamp-2 group-hover:text-yellow-200 transition-colors mb-1">
                  {article.title}
                </h3>
                <div className="flex items-center gap-2 text-xs text-white/80">
                  <span className="px-2 py-0.5 bg-white/20 rounded-full">
                    {article.category_name}
                  </span>
                  {article.views > 0 && (
                    <div className="flex items-center gap-1">
                      <Eye size={12} />
                      <span>{article.views}</span>
                    </div>
                  )}
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
        View All Trending →
      </Link>
    </div>
  );
}
