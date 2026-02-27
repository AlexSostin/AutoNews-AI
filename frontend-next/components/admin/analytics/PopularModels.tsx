'use client';

import useSWR from 'swr';
import { Car } from 'lucide-react';
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
import { PopularModel } from '@/types/analytics';

const fetcher = (url: string) => api.get(url).then(res => res.data?.models || []);

export default function PopularModels() {
    const { data: popularModels, isLoading } = useSWR<PopularModel[]>('/analytics/popular-models/', fetcher, { keepPreviousData: true });

    if (isLoading) {
        return (
            <div className="space-y-6 mt-12 animate-pulse">
                <div className="h-8 w-64 bg-gray-200 rounded mb-6"></div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-[450px]"></div>
            </div>
        );
    }

    if (!popularModels || popularModels.length === 0) return null;

    return (
        <div className="space-y-6">
            <h2 className="text-xl font-bold text-gray-900 border-l-4 border-cyan-600 pl-4">🏎️ Popular Car Models</h2>
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-2 flex items-center gap-2">
                    <Car className="text-cyan-600" size={20} />
                    Top Models by Views
                </h3>
                <p className="text-xs text-gray-400 mb-4">
                    Aggregated from CarSpecification make + model fields
                </p>
                <div className="h-[350px]">
                    <Bar
                        data={{
                            labels: popularModels.map(m => m.label),
                            datasets: [
                                {
                                    label: 'Total Views',
                                    data: popularModels.map(m => m.total_views),
                                    backgroundColor: 'rgba(8, 145, 178, 0.75)',
                                    borderColor: 'rgb(8, 145, 178)',
                                    borderWidth: 1,
                                    borderRadius: 6,
                                },
                                {
                                    label: 'Articles',
                                    data: popularModels.map(m => m.article_count),
                                    backgroundColor: 'rgba(139, 92, 246, 0.75)',
                                    borderColor: 'rgb(139, 92, 246)',
                                    borderWidth: 1,
                                    borderRadius: 6,
                                    yAxisID: 'y1',
                                },
                            ],
                        }}
                        options={{
                            indexAxis: 'y',
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
                                x: {
                                    type: 'linear' as const,
                                    display: true,
                                    position: 'bottom' as const,
                                    title: { display: true, text: 'Views' },
                                    beginAtZero: true,
                                },
                                y: {
                                    ticks: { font: { weight: 'bold' as const, size: 11 } },
                                },
                                y1: {
                                    type: 'linear' as const,
                                    display: true,
                                    position: 'top' as const,
                                    title: { display: true, text: 'Articles' },
                                    grid: { drawOnChartArea: false },
                                    beginAtZero: true,
                                    ticks: { precision: 0 },
                                },
                            },
                        }}
                    />
                </div>
            </div>
        </div>
    );
}
