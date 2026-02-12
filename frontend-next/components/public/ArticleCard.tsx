'use client';

import Link from 'next/link';
import Image from 'next/image';
import { Article } from '@/types';
import { formatDate } from '@/lib/utils';
import { Calendar, Star } from 'lucide-react';
import FavoriteButton from './FavoriteButton';
import { fixImageUrl } from '@/lib/config';

interface ArticleCardProps {
  article: Article;
  priority?: boolean;
}

export default function ArticleCard({ article, priority = false }: ArticleCardProps) {
  // Use first screenshot from video as background
  const defaultImage = 'https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=800&h=400&fit=crop';

  // Priority: image (screenshot 1) > thumbnail_url
  const thumbnailUrl = article.thumbnail_url || article.image;
  const imageUrl = thumbnailUrl ? fixImageUrl(thumbnailUrl) : defaultImage;

  return (
    <Link href={`/articles/${article.slug}`} className="group">
      <div className="bg-white rounded-xl shadow-md overflow-hidden transition-all hover:shadow-2xl hover:-translate-y-1 border border-gray-100 h-full flex flex-col">
        <div className="relative h-48 w-full overflow-hidden">
          <Image
            src={imageUrl}
            alt={article.title}
            fill
            className="object-cover group-hover:scale-110 transition-transform duration-300"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
            priority={priority}
            loading={priority ? "eager" : "lazy"}
          />
          {article.categories && article.categories.length > 0 && (
            <span className="absolute top-3 left-3 bg-indigo-600 text-white px-4 py-1.5 rounded-full text-xs font-bold shadow-lg">
              {article.categories[0].name}
            </span>
          )}
          <div className="absolute top-3 right-3" onClick={(e) => e.preventDefault()}>
            <FavoriteButton
              articleId={article.id}
              initialIsFavorited={article.is_favorited}
              size="sm"
            />
          </div>
        </div>

        <div className="p-5 flex-1 flex flex-col">
          <h3 className="text-xl font-black mb-3 text-gray-950 group-hover:text-indigo-600 transition-all duration-300 line-clamp-2 leading-tight group-hover:translate-x-1">
            {article.title}
          </h3>

          <p className="text-gray-700 mb-4 line-clamp-2 text-sm leading-relaxed font-medium">
            {article.summary}
          </p>

          <div className="flex items-center justify-between text-sm text-gray-600 mb-3 font-medium">
            <div className="flex items-center gap-1.5">
              <Calendar size={16} className="text-indigo-500" />
              <span>{formatDate(article.created_at)}</span>
            </div>

            {article.average_rating > 0 && (
              <div className="flex items-center gap-1.5">
                <Star size={16} className="fill-amber-400 text-amber-400" />
                <span className="font-semibold text-amber-600">{article.average_rating.toFixed(1)}</span>
              </div>
            )}
          </div>

          {article.tag_names && article.tag_names.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-auto">
              {article.tag_names.slice(0, 3).map((tag) => (
                <span key={tag} className="text-xs bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full border border-indigo-100">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
