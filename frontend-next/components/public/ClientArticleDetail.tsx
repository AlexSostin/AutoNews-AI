'use client';

/**
 * ClientArticleDetail — thin wrapper.
 * Fetches the initial article by slug, then hands off rendering
 * to InfiniteArticleScroll which handles subsequent articles.
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import InfiniteArticleScroll from '@/components/public/InfiniteArticleScroll';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export default function ClientArticleDetail({ slug }: { slug: string }) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [article, setArticle] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        fetch(`${API_URL}/articles/${slug}/`)
            .then(res => {
                if (!res.ok) throw new Error(`${res.status}`);
                return res.json();
            })
            .then(data => setArticle(data))
            .catch(() => setError(true))
            .finally(() => setLoading(false));
    }, [slug]);

    if (loading) return <ArticleDetailSkeleton />;
    if (error || !article) {
        return (
            <main className="flex-1 bg-gray-50 flex items-center justify-center min-h-screen">
                <div className="text-center py-20">
                    <h1 className="text-4xl font-bold text-gray-900 mb-4">Article Not Found</h1>
                    <p className="text-gray-600 mb-8">The article you&apos;re looking for doesn&apos;t exist or has been removed.</p>
                    <Link href="/articles" className="bg-indigo-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-indigo-700 transition">
                        Browse Articles
                    </Link>
                </div>
            </main>
        );
    }

    return <InfiniteArticleScroll initialArticle={article} />;
}

function ArticleDetailSkeleton() {
    return (
        <main className="flex-1 bg-gray-50">
            <div className="relative h-[250px] sm:h-[350px] md:h-[500px] w-full bg-gray-300 animate-pulse rounded-2xl" />
            <div className="container mx-auto px-4 py-8">
                <div className="max-w-4xl mx-auto space-y-6">
                    <div className="h-4 bg-gray-200 rounded w-1/3 animate-pulse" />
                    <div className="flex gap-4">
                        <div className="h-4 bg-gray-200 rounded w-32 animate-pulse" />
                        <div className="h-4 bg-gray-200 rounded w-24 animate-pulse" />
                    </div>
                    <div className="h-10 bg-gray-200 rounded w-3/4 animate-pulse" />
                    <div className="h-6 bg-gray-200 rounded w-full animate-pulse" />
                    <div className="h-6 bg-gray-200 rounded w-2/3 animate-pulse" />
                    <div className="bg-white rounded-xl shadow-md p-8 space-y-4">
                        {[1, 2, 3, 4, 5, 6].map(i => (
                            <div key={i} className="h-4 bg-gray-200 rounded animate-pulse" style={{ width: `${90 - i * 5}%` }} />
                        ))}
                    </div>
                </div>
            </div>
        </main>
    );
}
