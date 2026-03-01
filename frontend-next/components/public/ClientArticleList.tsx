'use client';

import { useState, useEffect } from 'react';
import EmptyState from '@/components/public/EmptyState';
import InfiniteArticleList from '@/components/public/InfiniteArticleList';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export default function ClientArticleList() {
    const [articles, setArticles] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`${API_URL}/articles/?is_published=true`)
            .then(res => {
                if (!res.ok) throw new Error(`API returned ${res.status}`);
                return res.json();
            })
            .then(data => {
                setArticles(data.results || []);
            })
            .catch(err => {
                console.warn('Failed to load articles:', err.message);
            })
            .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="space-y-6">
                {[1, 2, 3].map(i => (
                    <div key={i} className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 animate-pulse">
                        <div className="flex gap-4">
                            <div className="w-48 h-32 bg-gray-200 rounded-xl flex-shrink-0" />
                            <div className="flex-1 space-y-3">
                                <div className="h-5 bg-gray-200 rounded w-3/4" />
                                <div className="h-4 bg-gray-200 rounded w-full" />
                                <div className="h-4 bg-gray-200 rounded w-2/3" />
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        );
    }

    if (articles.length === 0) {
        return <EmptyState />;
    }

    return (
        <InfiniteArticleList initialArticles={articles} />
    );
}
