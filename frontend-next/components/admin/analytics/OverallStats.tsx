'use client';

import useSWR from 'swr';
import { Eye, FileText, MessageSquare, Mail, ArrowUp, ArrowDown, Loader2 } from 'lucide-react';
import api from '@/lib/api';
import { Stats } from '@/types/analytics';

const fetcher = (url: string) => api.get(url).then(res => res.data);

export default function OverallStats() {
    const { data: stats, isLoading } = useSWR<Stats>('/analytics/overview/', fetcher, { keepPreviousData: true });

    if (isLoading) {
        return (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {[...Array(4)].map((_, i) => (
                    <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-[142px] animate-pulse">
                        <div className="flex items-center justify-between mb-4">
                            <div className="w-12 h-12 bg-gray-200 rounded-lg"></div>
                            <div className="w-16 h-4 bg-gray-200 rounded"></div>
                        </div>
                        <div className="w-24 h-8 bg-gray-200 rounded mb-2"></div>
                        <div className="w-20 h-4 bg-gray-200 rounded"></div>
                    </div>
                ))}
            </div>
        );
    }

    const statCards = [
        {
            title: 'Total Views',
            value: stats?.total_views?.toLocaleString() || '0',
            icon: Eye,
            color: 'bg-blue-500',
            trend: `${(stats?.views_growth ?? 0) > 0 ? '+' : ''}${stats?.views_growth ?? 0}%`,
            trendUp: (stats?.views_growth ?? 0) >= 0
        },
        {
            title: 'Articles',
            value: stats?.total_articles?.toString() || '0',
            icon: FileText,
            color: 'bg-green-500',
            trend: `${(stats?.articles_growth ?? 0) > 0 ? '+' : ''}${stats?.articles_growth ?? 0}%`,
            trendUp: (stats?.articles_growth ?? 0) >= 0
        },
        {
            title: 'Comments',
            value: stats?.total_comments?.toString() || '0',
            icon: MessageSquare,
            color: 'bg-orange-500',
            trend: `${(stats?.comments_growth ?? 0) > 0 ? '+' : ''}${stats?.comments_growth ?? 0}%`,
            trendUp: (stats?.comments_growth ?? 0) >= 0
        },
        {
            title: 'Subscribers',
            value: stats?.total_subscribers?.toString() || '0',
            icon: Mail,
            color: 'bg-purple-500',
            trend: `${(stats?.subscribers_growth ?? 0) > 0 ? '+' : ''}${stats?.subscribers_growth ?? 0}%`,
            trendUp: (stats?.subscribers_growth ?? 0) >= 0
        },
    ];

    return (
        <>
            <h2 className="text-xl font-bold text-gray-900 border-l-4 border-purple-600 pl-4">Site Usage</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {statCards.map((stat) => {
                    const Icon = stat.icon;
                    return (
                        <div key={stat.title} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
                            <div className="flex items-center justify-between mb-4">
                                <div className={`${stat.color} p-3 rounded-lg text-white shadow-sm`}>
                                    <Icon size={24} />
                                </div>
                                <div className={`flex items-center gap-1 text-sm font-semibold ${stat.trendUp ? 'text-green-600' : 'text-red-600'}`}>
                                    {stat.trendUp ? <ArrowUp size={16} /> : <ArrowDown size={16} />}
                                    {stat.trend}
                                </div>
                            </div>
                            <p className="text-3xl font-black text-gray-900">{stat.value}</p>
                            <p className="text-gray-500 text-sm font-medium mt-1 uppercase tracking-wider">{stat.title}</p>
                        </div>
                    );
                })}
            </div>
        </>
    );
}
