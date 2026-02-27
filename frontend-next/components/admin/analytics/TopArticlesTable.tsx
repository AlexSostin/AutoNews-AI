'use client';

import useSWR from 'swr';
import { BarChart3 } from 'lucide-react';
import api from '@/lib/api';
import { Article } from '@/types/analytics';

const fetcher = (url: string) => api.get(url).then(res => res.data?.articles || []);

export default function TopArticlesTable() {
    const { data: popularArticles, isLoading } = useSWR<Article[]>('/analytics/articles/top/?limit=10', fetcher, { keepPreviousData: true });

    if (isLoading) {
        return (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mt-12 animate-pulse h-[500px]"></div>
        );
    }

    if (!popularArticles || popularArticles.length === 0) return null;

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <div className="flex items-center gap-2 mb-6">
                <BarChart3 className="text-purple-500" size={24} />
                <h2 className="text-xl font-bold text-gray-900">🔥 Top 10 Articles by Views</h2>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead>
                        <tr className="border-b border-gray-100 text-left">
                            <th className="pb-4 px-4 text-sm font-semibold text-gray-400 uppercase tracking-wider">Rank</th>
                            <th className="pb-4 px-4 text-sm font-semibold text-gray-400 uppercase tracking-wider">Article</th>
                            <th className="pb-4 px-4 text-sm font-semibold text-gray-400 uppercase tracking-wider text-right">Views</th>
                            <th className="pb-4 px-4 text-sm font-semibold text-gray-400 uppercase tracking-wider text-right">Published</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50 text-gray-700">
                        {popularArticles.map((article, index) => (
                            <tr key={article.id} className="hover:bg-gray-50/50 transition-colors">
                                <td className="py-4 px-4">
                                    <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-sm font-bold text-gray-600">
                                        {index + 1}
                                    </span>
                                </td>
                                <td className="py-4 px-4">
                                    <a href={`/article/${article.slug}`} target="_blank" className="font-bold text-gray-900 hover:text-purple-600 transition-colors line-clamp-1">
                                        {article.title}
                                    </a>
                                </td>
                                <td className="py-4 px-4 text-right">
                                    <span className="font-black text-gray-900">{article.views?.toLocaleString() || 0}</span>
                                </td>
                                <td className="py-4 px-4 text-right text-sm text-gray-500 font-medium">
                                    {new Date(article.created_at).toLocaleDateString()}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
