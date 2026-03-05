'use client';

import { useState } from 'react';
import useSWR from 'swr';
import { Cpu } from 'lucide-react';
import api from '@/lib/api';
import { GSCStats } from '@/types/analytics';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const PERIOD_OPTIONS = [
    { label: '1d', days: 1 },
    { label: '7d', days: 7 },
    { label: '30d', days: 30 },
    { label: '3mo', days: 90 },
];

function getTrend(current: number, previous: number): { percent: string; up: boolean } {
    if (!previous) return { percent: '—', up: true };
    const diff = Math.round(((current - previous) / previous) * 100);
    return { percent: `${Math.abs(diff)}%`, up: diff >= 0 };
}

export default function GSCDashboard() {
    const [days, setDays] = useState(30);
    const { data: gscStats, isLoading } = useSWR<GSCStats>(
        `/analytics/gsc/?days=${days}`,
        fetcher,
        { keepPreviousData: true }
    );

    const periodLabel = PERIOD_OPTIONS.find(p => p.days === days)?.label ?? `${days}d`;

    if (isLoading && !gscStats) {
        return (
            <div className="space-y-6 mt-12 animate-pulse">
                <div className="h-8 w-64 bg-gray-200 rounded mb-6"></div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 h-[170px]"></div>
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 h-[170px]"></div>
                </div>
            </div>
        );
    }

    if (!gscStats) return null;

    const gscSummaries = [
        {
            label: 'Search Clicks',
            icon: '📈',
            iconBg: 'bg-emerald-500',
            value: gscStats.summary.clicks.toLocaleString(),
            ...getTrend(gscStats.summary.clicks, gscStats.previous_summary.clicks)
        },
        {
            label: 'Search Impressions',
            icon: '👁️',
            iconBg: 'bg-cyan-500',
            value: gscStats.summary.impressions.toLocaleString(),
            ...getTrend(gscStats.summary.impressions, gscStats.previous_summary.impressions)
        },
        {
            label: 'Avg. CTR',
            icon: '📊',
            iconBg: 'bg-pink-500',
            value: `${gscStats.summary.ctr}%`,
            ...getTrend(gscStats.summary.ctr, gscStats.previous_summary.ctr)
        },
        {
            label: 'Avg. Position',
            icon: '⏱',
            iconBg: 'bg-orange-500',
            value: gscStats.summary.position.toString(),
            percent: (gscStats.summary.position < gscStats.previous_summary.position) ? 'Better' : 'Worse',
            up: gscStats.summary.position <= gscStats.previous_summary.position
        },
    ];

    return (
        <div className="space-y-4">

            {/* Header row */}
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                    <h2 className="text-xl font-bold text-gray-900 border-l-4 border-green-500 pl-4">
                        🔍 Google Search Console Performance
                    </h2>
                    <p className="text-xs text-gray-400 mt-0.5 pl-5">Showing last {days} day{days !== 1 ? 's' : ''}</p>
                </div>

                {/* Period selector */}
                <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
                    {PERIOD_OPTIONS.map(opt => (
                        <button
                            key={opt.days}
                            onClick={() => setDays(opt.days)}
                            className={`px-3 py-1 rounded-md text-sm font-medium transition-all ${days === opt.days
                                    ? 'bg-white text-gray-900 shadow-sm'
                                    : 'text-gray-500 hover:text-gray-700'
                                }`}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Sync badge */}
            <div className="flex justify-end">
                <span className="text-xs bg-green-50 border border-green-200 text-green-700 px-2 py-0.5 rounded">
                    Last GSC Sync: {gscStats.last_sync ? new Date(gscStats.last_sync).toLocaleString() : 'N/A'}
                </span>
            </div>

            {/* Metric cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {gscSummaries.map((stat) => {
                    const trendColor = stat.up ? 'text-green-600' : 'text-red-500';
                    const trendIcon = stat.up ? '↑' : '↓';
                    return (
                        <div key={stat.label} className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow">
                            <div className={`w-9 h-9 rounded-lg ${stat.iconBg} flex items-center justify-center text-white text-base mb-3`}>
                                {stat.icon}
                            </div>
                            <div className={`text-xs font-medium mb-1 ${trendColor}`}>
                                {trendIcon} {stat.percent}
                            </div>
                            <div className="text-2xl font-bold text-gray-900">{stat.value}</div>
                            <div className="text-xs text-gray-500 mt-1 uppercase tracking-wide">{stat.label}</div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
