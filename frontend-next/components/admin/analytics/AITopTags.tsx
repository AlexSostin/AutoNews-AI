'use client';

import useSWR from 'swr';
import { Tag } from 'lucide-react';
import { Bar } from 'react-chartjs-2';
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
import { AIStats } from '@/types/analytics';

const fetcher = (url: string) => api.get(url).then(res => res.data);

export default function AITopTags() {
    const { data: aiStats, isLoading } = useSWR<AIStats>('/analytics/ai-stats/', fetcher, { keepPreviousData: true });

    if (isLoading) {
        return (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-[400px] animate-pulse"></div>
        );
    }

    if (!aiStats || aiStats.top_tags.length === 0) return null;

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-full">
            <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
                <Tag className="text-emerald-600" size={20} />
                🏷️ Top Tags by Views
            </h3>
            <div className="h-[300px]">
                <Bar
                    data={{
                        labels: aiStats.top_tags.map(t => t.name),
                        datasets: [
                            {
                                label: 'Total Views',
                                data: aiStats.top_tags.map(t => t.total_views),
                                backgroundColor: 'rgba(16, 185, 129, 0.7)',
                                borderColor: 'rgba(16, 185, 129, 1)',
                                borderWidth: 1,
                                borderRadius: 6,
                            },
                            {
                                label: 'Articles',
                                data: aiStats.top_tags.map(t => t.article_count),
                                backgroundColor: 'rgba(139, 92, 246, 0.7)',
                                borderColor: 'rgba(139, 92, 246, 1)',
                                borderWidth: 1,
                                borderRadius: 6,
                                yAxisID: 'y1',
                            },
                        ],
                    }}
                    options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {
                            mode: 'index' as const,
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
                                title: { display: true, text: 'Views' },
                                beginAtZero: true,
                            },
                            y1: {
                                type: 'linear' as const,
                                display: true,
                                position: 'right' as const,
                                title: { display: true, text: 'Articles' },
                                grid: { drawOnChartArea: false },
                                beginAtZero: true,
                                ticks: { precision: 0 },
                            },
                            x: {
                                ticks: {
                                    maxRotation: 45,
                                    minRotation: 45,
                                    font: { size: 11 },
                                },
                            },
                        },
                    }}
                />
            </div>
        </div>
    );
}
