'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import ArticleCard from './ArticleCard';
import AdBanner from './AdBanner';
import { ArticleCardSkeleton } from './Skeletons';
import type { Article } from '@/types';

interface InfiniteArticleListProps {
    initialArticles: Article[];
    initialPage?: number;
    pageSize?: number;
}

export default function InfiniteArticleList({
    initialArticles,
    initialPage = 1,
    pageSize = 18,
}: InfiniteArticleListProps) {
    const [articles, setArticles] = useState<Article[]>(initialArticles);
    const [page, setPage] = useState(initialPage);
    const [loading, setLoading] = useState(false);
    const [hasMore, setHasMore] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const observerTarget = useRef<HTMLDivElement>(null);
    const loadingRef = useRef(false);

    // Get API URL
    const getApiUrl = () => {
        if (typeof window !== 'undefined') {
            return process.env.NEXT_PUBLIC_API_URL || 'https://heroic-healing-production-2365.up.railway.app/api/v1';
        }
        return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
    };

    // Load more articles
    const loadMore = useCallback(async () => {
        if (loadingRef.current || !hasMore) return;

        loadingRef.current = true;
        setLoading(true);
        setError(null);

        try {
            const nextPage = page + 1;
            const apiUrl = getApiUrl();
            const response = await fetch(
                `${apiUrl}/articles/?is_published=true&page=${nextPage}&page_size=${pageSize}`
            );

            if (!response.ok) {
                throw new Error('Failed to load articles');
            }

            const data = await response.json();

            if (data.results && data.results.length > 0) {
                setArticles(prev => [...prev, ...data.results]);
                setPage(nextPage);
                setHasMore(!!data.next);
            } else {
                setHasMore(false);
            }
        } catch (err) {
            console.error('Error loading articles:', err);
            setError('Failed to load more articles. Please try again.');
        } finally {
            setLoading(false);
            loadingRef.current = false;
        }
    }, [page, hasMore, pageSize]);

    // Intersection Observer for infinite scroll
    useEffect(() => {
        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting && hasMore && !loading) {
                    loadMore();
                }
            },
            { threshold: 0.5, rootMargin: '100px' }
        );

        const currentTarget = observerTarget.current;
        if (currentTarget) {
            observer.observe(currentTarget);
        }

        return () => {
            if (currentTarget) {
                observer.unobserve(currentTarget);
            }
        };
    }, [hasMore, loading, loadMore]);

    // Insert ads every 6 articles
    const renderArticlesWithAds = () => {
        const items: React.JSX.Element[] = [];

        articles.forEach((article, index) => {
            // Add article
            items.push(
                <ArticleCard
                    key={`article-${article.id}`}
                    article={article}
                    priority={index < 3}
                />
            );

            // Add ad after every 6 articles (but not after the last one)
            if ((index + 1) % 6 === 0 && index !== articles.length - 1) {
                items.push(
                    <div key={`ad-${index}`} className="col-span-1 md:col-span-2 xl:col-span-3 flex justify-center my-8">
                        <AdBanner position="between_articles" />
                    </div>
                );
            }
        });

        return items;
    };

    return (
        <div className="space-y-8">
            {/* Articles Grid with Ads */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
                {renderArticlesWithAds()}
            </div>

            {/* Loading State */}
            {loading && (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
                    {[...Array(6)].map((_, i) => (
                        <ArticleCardSkeleton key={`skeleton-${i}`} />
                    ))}
                </div>
            )}

            {/* Error State */}
            {error && (
                <div className="text-center py-8">
                    <p className="text-red-600 mb-4">{error}</p>
                    <button
                        onClick={loadMore}
                        className="px-6 py-3 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
                    >
                        Try Again
                    </button>
                </div>
            )}

            {/* End of Feed */}
            {!hasMore && !loading && articles.length > 0 && (
                <div className="text-center py-12">
                    <div className="inline-block px-8 py-4 bg-gradient-to-r from-brand-50 to-blue-50 rounded-2xl border border-brand-100">
                        <p className="text-gray-600 font-medium mb-2">🎉 You've reached the end!</p>
                        <p className="text-sm text-gray-500">
                            You've seen all {articles.length} articles
                        </p>
                    </div>
                </div>
            )}

            {/* Intersection Observer Target */}
            <div ref={observerTarget} className="h-4" />
        </div>
    );
}
