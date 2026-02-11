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
        return 'http://localhost:8000/api/v1';
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
                // 1️⃣ Try AI-powered similar articles first (best option)
                const similarRes = await fetch(`${getApiUrl()}/articles/${currentArticleSlug}/similar_articles/`);

                if (similarRes.ok) {
                    const data = await similarRes.json();
                    const similarArticles = data.similar_articles || [];

                    if (similarArticles.length > 0) {
                        console.log('✨ AI-powered similar articles:', similarArticles.length);
                        setArticles(similarArticles.slice(0, 15));
                        setLoading(false);
                        return;
                    }
                }

                // 2️⃣ Fallback: Articles from same category (good relevance)
                if (categorySlug) {
                    console.log('📂 Trying category-based articles...');
                    const categoryRes = await fetch(`${getApiUrl()}/articles/?category=${categorySlug}&page_size=15`);

                    if (categoryRes.ok) {
                        const data = await categoryRes.json();
                        const filtered = (data.results || []).filter((a: Article) => a.slug !== currentArticleSlug);

                        if (filtered.length > 0) {
                            console.log('✅ Using category-based articles:', filtered.length);
                            setArticles(filtered);
                            setLoading(false);
                            return;
                        }
                    }
                }

                // 3️⃣ Fallback: Popular articles (most viewed)
                console.log('🔥 Trying popular articles...');
                const popularRes = await fetch(`${getApiUrl()}/articles/?ordering=-views&page_size=15`);

                if (popularRes.ok) {
                    const data = await popularRes.json();
                    const filtered = (data.results || []).filter((a: Article) => a.slug !== currentArticleSlug);

                    if (filtered.length > 0) {
                        console.log('✅ Using popular articles:', filtered.length);
                        setArticles(filtered);
                        setLoading(false);
                        return;
                    }
                }

                // 4️⃣ Final fallback: Newest articles (always has content)
                console.log('🆕 Using newest articles as final fallback...');
                const newestRes = await fetch(`${getApiUrl()}/articles/?ordering=-created_at&page_size=15`);

                if (newestRes.ok) {
                    const data = await newestRes.json();
                    const filtered = (data.results || []).filter((a: Article) => a.slug !== currentArticleSlug);
                    console.log('✅ Using newest articles:', filtered.length);
                    setArticles(filtered);
                }

            } catch (error) {
                console.error('❌ Error fetching related articles:', error);
            } finally {
                setLoading(false);
            }
        }

        if (currentArticleSlug) {
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
                <div className="flex items-center gap-3">
                    <h3 className="text-2xl font-bold text-gray-900">Similar Articles</h3>
                    <span className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white px-2 py-0.5 rounded-full text-[10px] font-bold shadow-sm">
                        AI-POWERED
                    </span>
                </div>
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
                            {article.categories && article.categories.length > 0 && (
                                <span className="absolute top-2 left-2 bg-indigo-600 text-white px-2 py-0.5 rounded text-[10px] font-bold shadow">
                                    {article.categories[0].name}
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
