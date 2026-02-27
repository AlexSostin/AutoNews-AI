'use client';

import useSWR from 'swr';
import { FileText, BarChart3 } from 'lucide-react';
import { Line, Pie } from 'react-chartjs-2';
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
import { TimelineData, CategoriesData } from '@/types/analytics';

const fetchTimeline = () => api.get('/analytics/views/timeline/?days=30').then(res => res.data);
const fetchCategories = () => api.get('/analytics/categories/').then(res => res.data);

export default function EngagementDistribution() {
    const { data: timeline, isLoading: tlLoading } = useSWR<TimelineData>('timeline', fetchTimeline, { keepPreviousData: true });
    const { data: categories, isLoading: catLoading } = useSWR<CategoriesData>('categories', fetchCategories, { keepPreviousData: true });

    if (tlLoading || catLoading) {
        return (
            <div className="space-y-6 mt-12 animate-pulse">
                <div className="h-8 w-64 bg-gray-200 rounded mb-6"></div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-[400px]"></div>
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-[400px]"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Timeline Chart */}
            {timeline && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <FileText className="text-blue-600" />
                        Articles Published (Last 30 Days)
                    </h3>
                    <Line
                        data={{
                            labels: timeline.labels,
                            datasets: [
                                {
                                    label: 'Articles',
                                    data: timeline.data,
                                    borderColor: 'rgb(59, 130, 246)',
                                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                    tension: 0.4,
                                    fill: true,
                                },
                            ],
                        }}
                        options={{
                            responsive: true,
                            plugins: {
                                legend: { display: false },
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: { precision: 0 }
                                }
                            }
                        }}
                    />
                </div>
            )}

            {/* Categories Pie Chart */}
            {categories && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <BarChart3 className="text-green-600" />
                        Articles by Category
                    </h3>
                    <div className="flex justify-center">
                        <div className="w-full max-w-[300px]">
                            <Pie
                                data={{
                                    labels: categories.labels,
                                    datasets: [
                                        {
                                            data: categories.data,
                                            backgroundColor: [
                                                'rgba(59, 130, 246, 0.8)',
                                                'rgba(16, 185, 129, 0.8)',
                                                'rgba(139, 92, 246, 0.8)',
                                                'rgba(249, 115, 22, 0.8)',
                                                'rgba(236, 72, 153, 0.8)',
                                                'rgba(234, 179, 8, 0.8)',
                                            ],
                                            borderWidth: 2,
                                        },
                                    ],
                                }}
                                options={{
                                    responsive: true,
                                    plugins: {
                                        legend: { position: 'bottom' },
                                    },
                                }}
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
