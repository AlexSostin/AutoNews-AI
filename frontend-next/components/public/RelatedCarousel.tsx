'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react';
import { Article } from '@/types';
import { fixImageUrl } from '@/lib/config';
import { formatDate } from '@/lib/utils';

interface RelatedCarouselProps {
    categorySlug: string;
    currentArticleSlug: string;
}

const getApiUrl = () => {
    if (typeof window === 'undefined') return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://localhost:8001/api/v1';
    }
    return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
};

export default function RelatedCarousel({ categorySlug, currentArticleSlug }: RelatedCarouselProps) {
    const [articles, setArticles] = useState<Article[]>([]);
    const [loading, setLoading] = useState(true);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        async function fetchRelated() {
            try {
                const res = await fetch(`${getApiUrl()}/articles/?category=${categorySlug}&page_size=10`);
                if (res.ok) {
                    const data = await res.json();
                    // Filter out the current article
                    const filtered = (data.results || []).filter((a: Article) => a.slug !== currentArticleSlug);
                    setArticles(filtered);
                }
            } catch (error) {
                console.error('Error fetching related articles:', error);
            } finally {
                setLoading(false);
            }
        }

        if (categorySlug) {
            fetchRelated();
        }
    }, [categorySlug, currentArticleSlug]);

    const scroll = (direction: 'left' | 'right') => {
        if (scrollRef.current) {
            const { scrollLeft, clientWidth } = scrollRef.current;
            const scrollTo = direction === 'left' ? scrollLeft - clientWidth : scrollLeft + clientWidth;
            scrollRef.current.scrollTo({ left: scrollTo, behavior: 'smooth' });
        }
    };

    if (loading || articles.length === 0) return null;

    return (
        <div className="bg-white rounded-xl shadow-md p-6 mb-8 overflow-hidden">
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-2xl font-bold text-gray-900">Recommended for You</h3>
                <div className="flex gap-2">
                    <button
                        onClick={() => scroll('left')}
                        className="p-2 rounded-full border border-gray-200 hover:bg-gray-50 transition-colors text-gray-600"
                        aria-label="Previous articles"
                    >
                        <ChevronLeft size={20} />
                    </button>
                    <button
                        onClick={() => scroll('right')}
                        className="p-2 rounded-full border border-gray-200 hover:bg-gray-50 transition-colors text-gray-600"
                        aria-label="Next articles"
                    >
                        <ChevronRight size={20} />
                    </button>
                </div>
            </div>

            <div
                ref={scrollRef}
                className="flex flex-row flex-nowrap gap-6 overflow-x-auto snap-x snap-mandatory scrollbar-hide pb-2"
                style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
            >
                {articles.map((article) => (
                    <Link
                        key={article.id}
                        href={`/articles/${article.slug}`}
                        className="flex-shrink-0 w-[280px] sm:w-[320px] snap-start group"
                    >
                        <div className="relative h-44 mb-3 rounded-lg overflow-hidden border border-gray-100 shadow-sm">
                            <Image
                                src={fixImageUrl(article.thumbnail_url || article.image || '')}
                                alt={article.title}
                                fill
                                className="object-cover group-hover:scale-110 transition-transform duration-500"
                                sizes="(max-width: 768px) 280px, 320px"
                            />
                            {article.category_name && (
                                <span className="absolute top-2 left-2 bg-indigo-600/90 backdrop-blur-sm text-white px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider">
                                    {article.category_name}
                                </span>
                            )}
                        </div>
                        <h4 className="font-bold text-gray-900 group-hover:text-indigo-600 transition-colors line-clamp-2 mb-2 leading-tight">
                            {article.title}
                        </h4>
                        <div className="flex items-center gap-2 text-xs text-gray-500 font-medium">
                            <Calendar size={14} className="text-indigo-400" />
                            <span>{formatDate(article.created_at)}</span>
                        </div>
                    </Link>
                ))}
            </div>

            {/* Visual cue for scrolling on mobile */}
            <div className="mt-4 flex justify-center md:hidden">
                <div className="flex gap-1">
                    {articles.slice(0, 5).map((_, i) => (
                        <div key={i} className="w-1.5 h-1.5 rounded-full bg-gray-200" />
                    ))}
                </div>
            </div>
        </div>
    );
}
