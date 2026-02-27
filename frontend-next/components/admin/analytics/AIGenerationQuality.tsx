'use client';

import useSWR from 'swr';
import { Wrench, Timer, Pencil } from 'lucide-react';
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
import { AIGenerationStats } from '@/types/analytics';

const fetcher = (url: string) => api.get(url).then(res => res.data);

export default function AIGenerationQuality() {
    const { data: aiGenStats, isLoading } = useSWR<AIGenerationStats>('/analytics/ai-generation/', fetcher, { keepPreviousData: true });

    if (isLoading) {
        return (
            <div className="space-y-6 mt-12 animate-pulse">
                <div className="h-8 w-64 bg-gray-200 rounded mb-6"></div>
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 lg:col-span-2 h-[400px]"></div>
                    <div className="space-y-6">
                        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-[188px]"></div>
                        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-[188px]"></div>
                    </div>
                </div>
            </div>
        );
    }

    if (!aiGenStats) return null;

    return (
        <div className="space-y-6">
            <h2 className="text-xl font-bold text-gray-900 border-l-4 border-amber-600 pl-4">⚙️ AI Generation Quality</h2>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Spec Field Coverage */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 lg:col-span-2">
                    <h3 className="text-lg font-bold text-gray-900 mb-2 flex items-center gap-2">
                        <Wrench className="text-amber-600" size={20} />
                        Spec Field Coverage
                    </h3>
                    <p className="text-xs text-gray-400 mb-4">
                        {aiGenStats.spec_coverage.total_with_specs} / {aiGenStats.spec_coverage.total_articles} articles have specs · Overall: <span className="font-bold text-gray-700">{aiGenStats.spec_coverage.overall_pct}%</span>
                    </p>
                    {Object.keys(aiGenStats.spec_coverage.per_field).length > 0 ? (
                        <div className="h-[280px]">
                            <Bar
                                data={{
                                    labels: Object.keys(aiGenStats.spec_coverage.per_field).map(f =>
                                        f.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())
                                    ),
                                    datasets: [{
                                        label: 'Fill Rate %',
                                        data: Object.values(aiGenStats.spec_coverage.per_field),
                                        backgroundColor: Object.values(aiGenStats.spec_coverage.per_field).map(v =>
                                            v >= 80 ? 'rgba(16, 185, 129, 0.75)' :
                                                v >= 50 ? 'rgba(245, 158, 11, 0.75)' :
                                                    'rgba(239, 68, 68, 0.75)'
                                        ),
                                        borderRadius: 6,
                                        borderWidth: 1,
                                        borderColor: Object.values(aiGenStats.spec_coverage.per_field).map(v =>
                                            v >= 80 ? 'rgb(16, 185, 129)' :
                                                v >= 50 ? 'rgb(245, 158, 11)' :
                                                    'rgb(239, 68, 68)'
                                        ),
                                    }],
                                }}
                                options={{
                                    indexAxis: 'y',
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: { legend: { display: false } },
                                    scales: {
                                        x: { beginAtZero: true, max: 100, title: { display: true, text: '%' } },
                                        y: { ticks: { font: { weight: 'bold' } } },
                                    },
                                }}
                            />
                        </div>
                    ) : (
                        <p className="text-gray-400 text-sm">No spec data available</p>
                    )}
                </div>

                {/* Time & Edit Stats */}
                <div className="space-y-6">
                    {/* Generation Time */}
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                        <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <Timer className="text-blue-600" size={20} />
                            Generation → Publish
                        </h3>
                        {aiGenStats.generation_time.sample_size ? (
                            <div className="space-y-3">
                                <div className="flex justify-between">
                                    <span className="text-sm text-gray-500">Average</span>
                                    <span className="font-bold text-gray-900">{Math.round(aiGenStats.generation_time.avg_seconds! / 60)}m</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-sm text-gray-500">Median</span>
                                    <span className="font-bold text-gray-900">{Math.round(aiGenStats.generation_time.median_seconds! / 60)}m</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-sm text-gray-500">Max</span>
                                    <span className="font-bold text-gray-900">{Math.round(aiGenStats.generation_time.max_seconds! / 3600)}h</span>
                                </div>
                                <p className="text-xs text-gray-400 pt-2 border-t">ℹ️ {aiGenStats.generation_time.sample_size} articles</p>
                            </div>
                        ) : (
                            <p className="text-gray-400 text-sm">No generation metadata available yet</p>
                        )}
                    </div>

                    {/* Edit Rates */}
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                        <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <Pencil className="text-rose-600" size={20} />
                            Content Editing
                        </h3>
                        {aiGenStats.edit_rates.sample_size ? (
                            <div className="space-y-3">
                                <div className="flex justify-between">
                                    <span className="text-sm text-gray-500">Avg Edit %</span>
                                    <span className="font-bold text-gray-900">{aiGenStats.edit_rates.avg_edit_pct}%</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-sm text-gray-500">Median</span>
                                    <span className="font-bold text-gray-900">{aiGenStats.edit_rates.median_edit_pct}%</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-sm text-gray-500">Untouched</span>
                                    <span className="font-bold text-emerald-600">{aiGenStats.edit_rates.unedited_count} articles</span>
                                </div>
                                <p className="text-xs text-gray-400 pt-2 border-t">ℹ️ {aiGenStats.edit_rates.sample_size} articles with AI originals</p>
                            </div>
                        ) : (
                            <p className="text-gray-400 text-sm">No content_original data yet</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
