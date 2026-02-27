'use client';

import useSWR from 'swr';
import { TrendingUp, Eye, BarChart3, Clock, ArrowUp, ArrowDown } from 'lucide-react';
import { Line } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    ArcElement,
    Title,
    Tooltip,
    Legend,
    Filler,
} from 'chart.js';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    ArcElement,
    Title,
    Tooltip,
    Legend,
    Filler
);
import api from '@/lib/api';
import { GSCStats } from '@/types/analytics';

const fetcher = (url: string) => api.get(url).then(res => res.data);

export default function GSCDashboard() {
    const { data: gscStats, isLoading } = useSWR<GSCStats>('/analytics/gsc/?days=30', fetcher, { keepPreviousData: true });

    if (isLoading) {
        return (
            <div className="space-y-6 mt-12 animate-pulse">
                <div className="h-8 w-64 bg-gray-200 rounded mb-6"></div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-[142px]"></div>
                    ))}
                </div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-[400px]"></div>
            </div>
        );
    }

    if (!gscStats) return null;

    const getTrend = (current: number, previous: number) => {
        if (previous === 0) return { percent: '0%', up: true };
        const diff = ((current - previous) / previous) * 100;
        return {
            percent: `${Math.abs(Math.round(diff))}%`,
            up: diff >= 0
        };
    };

    const gscSummaries = [
        {
            title: 'Search Clicks',
            value: gscStats.summary.clicks.toLocaleString(),
            icon: TrendingUp,
            color: 'bg-indigo-600',
            ...getTrend(gscStats.summary.clicks, gscStats.previous_summary.clicks)
        },
        {
            title: 'Search Impressions',
            value: gscStats.summary.impressions.toLocaleString(),
            icon: Eye,
            color: 'bg-cyan-600',
            ...getTrend(gscStats.summary.impressions, gscStats.previous_summary.impressions)
        },
        {
            title: 'Avg. CTR',
            value: `${gscStats.summary.ctr}%`,
            icon: BarChart3,
            color: 'bg-pink-600',
            ...getTrend(gscStats.summary.ctr, gscStats.previous_summary.ctr)
        },
        {
            title: 'Avg. Position',
            value: gscStats.summary.position.toString(),
            icon: Clock,
            color: 'bg-amber-600',
            percent: (gscStats.summary.position < gscStats.previous_summary.position) ? 'Better' : 'Worse',
            up: gscStats.summary.position <= gscStats.previous_summary.position
        }
    ];

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900 border-l-4 border-indigo-600 pl-4">Google Search Console Performance</h2>
                <div className="bg-green-50 px-4 py-2 rounded-lg border border-green-100 hidden sm:block">
                    <p className="text-xs text-green-700 font-medium">Last GSC Sync:</p>
                    <p className="text-sm text-green-800 font-bold">
                        {gscStats.last_sync
                            ? new Date(gscStats.last_sync).toLocaleString()
                            : 'Never synced yet'}
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {gscSummaries.map((stat) => {
                    const Icon = stat.icon;
                    return (
                        <div key={stat.title} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow">
                            <div className="flex items-center justify-between mb-4">
                                <div className={`${stat.color} p-3 rounded-lg text-white shadow-sm`}>
                                    <Icon size={24} />
                                </div>
                                {stat.percent && (
                                    <div className={`flex items-center gap-1 text-sm font-semibold ${stat.up ? 'text-green-600' : 'text-red-600'}`}>
                                        {stat.up ? <ArrowUp size={16} /> : <ArrowDown size={16} />}
                                        {stat.percent}
                                    </div>
                                )}
                            </div>
                            <p className="text-3xl font-black text-gray-900">{stat.value}</p>
                            <p className="text-gray-500 text-sm font-medium mt-1 uppercase tracking-wider">{stat.title}</p>
                        </div>
                    );
                })}
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
                    <TrendingUp className="text-indigo-600" />
                    Daily Search Clicks & Impressions
                </h3>
                <div className="h-[300px]">
                    <Line
                        data={{
                            labels: gscStats.timeline.labels,
                            datasets: [
                                {
                                    label: 'Clicks',
                                    data: gscStats.timeline.clicks,
                                    borderColor: 'rgb(79, 70, 229)',
                                    backgroundColor: 'rgba(79, 70, 229, 0.1)',
                                    yAxisID: 'y',
                                    tension: 0.3,
                                    fill: true,
                                },
                                {
                                    label: 'Impressions',
                                    data: gscStats.timeline.impressions,
                                    borderColor: 'rgb(8, 145, 178)',
                                    backgroundColor: 'transparent',
                                    yAxisID: 'y1',
                                    tension: 0.3,
                                    borderDash: [5, 5],
                                },
                            ],
                        }}
                        options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            interaction: {
                                mode: 'index',
                                intersect: false,
                            },
                            plugins: {
                                legend: { position: 'top' as const },
                            },
                            scales: {
                                y: {
                                    type: 'linear' as const,
                                    display: true,
                                    position: 'left' as const,
                                    title: { display: true, text: 'Clicks' },
                                    beginAtZero: true
                                },
                                y1: {
                                    type: 'linear' as const,
                                    display: true,
                                    position: 'right' as const,
                                    title: { display: true, text: 'Impressions' },
                                    grid: { drawOnChartArea: false },
                                    beginAtZero: true
                                },
                            }
                        }}
                    />
                </div>
            </div>
        </div>
    );
}
