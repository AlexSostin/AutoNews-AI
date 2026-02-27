'use client';

import useSWR from 'swr';
import { CheckCircle2, Cpu, Eye, Tag, Sparkles, Youtube, Languages, Rss } from 'lucide-react';
import { Doughnut } from 'react-chartjs-2';
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

export default function AIEnrichmentStats() {
    const { data: aiStats, isLoading } = useSWR<AIStats>('/analytics/ai-stats/', fetcher, { keepPreviousData: true });

    if (isLoading) {
        return (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-pulse">
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-[400px]"></div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-[400px]"></div>
            </div>
        );
    }

    if (!aiStats) return null;

    const getEnrichmentPercent = (count: number) => {
        if (!aiStats.enrichment.total_articles) return 0;
        return Math.round((count / aiStats.enrichment.total_articles) * 100);
    };

    const enrichmentItems = [
        { label: 'Deep Specs (VehicleSpecs)', count: aiStats.enrichment.vehicle_specs, icon: Sparkles, color: 'bg-violet-500' },
        { label: 'A/B Title Variants', count: aiStats.enrichment.ab_titles, icon: FileTextIcon, color: 'bg-blue-500' },
        { label: 'Tags Assigned', count: aiStats.enrichment.tags, icon: Tag, color: 'bg-emerald-500' },
        { label: 'Car Specifications', count: aiStats.enrichment.car_specs, icon: Cpu, color: 'bg-orange-500' },
        { label: 'Featured Images', count: aiStats.enrichment.images, icon: Eye, color: 'bg-pink-500' },
    ];

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Enrichment Coverage */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-2 flex items-center gap-2">
                    <CheckCircle2 className="text-violet-600" size={20} />
                    Enrichment Coverage
                </h3>
                <p className="text-xs text-gray-400 mb-6">
                    Out of {aiStats.enrichment.total_articles} published articles
                </p>
                <div className="space-y-4">
                    {enrichmentItems.map((item) => {
                        const Icon = item.icon;
                        const percent = getEnrichmentPercent(item.count);
                        return (
                            <div key={item.label}>
                                <div className="flex items-center justify-between mb-1.5">
                                    <div className="flex items-center gap-2">
                                        <Icon size={16} className="text-gray-500" />
                                        <span className="text-sm font-semibold text-gray-700">{item.label}</span>
                                    </div>
                                    <span className="text-sm font-black text-gray-900">
                                        {item.count} <span className="text-gray-400 font-medium">({percent}%)</span>
                                    </span>
                                </div>
                                <div className="w-full bg-gray-100 rounded-full h-2.5">
                                    <div
                                        className={`${item.color} h-2.5 rounded-full transition-all duration-500`}
                                        style={{ width: `${Math.max(percent, 2)}%` }}
                                    />
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* AI Source Breakdown */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
                    <Cpu className="text-violet-600" size={20} />
                    Article Sources
                </h3>
                <div className="flex flex-col items-center gap-6">
                    <div className="w-full max-w-[250px]">
                        <Doughnut
                            data={{
                                labels: ['YouTube', 'RSS Feeds', 'Translated/Manual'],
                                datasets: [{
                                    data: [
                                        aiStats.sources.youtube,
                                        aiStats.sources.rss,
                                        aiStats.sources.translated,
                                    ],
                                    backgroundColor: [
                                        'rgba(239, 68, 68, 0.85)',
                                        'rgba(249, 115, 22, 0.85)',
                                        'rgba(139, 92, 246, 0.85)',
                                    ],
                                    borderWidth: 3,
                                    borderColor: '#fff',
                                }],
                            }}
                            options={{
                                responsive: true,
                                cutout: '60%',
                                plugins: {
                                    legend: { display: false },
                                },
                            }}
                        />
                    </div>
                    <div className="grid grid-cols-3 gap-3 w-full">
                        {[
                            { label: 'YouTube', count: aiStats.sources.youtube, icon: Youtube, color: 'text-red-500', bg: 'bg-red-50' },
                            { label: 'RSS', count: aiStats.sources.rss, icon: Rss, color: 'text-orange-500', bg: 'bg-orange-50' },
                            { label: 'Translated', count: aiStats.sources.translated, icon: Languages, color: 'text-violet-500', bg: 'bg-violet-50' },
                        ].map((src) => {
                            const SrcIcon = src.icon;
                            return (
                                <div key={src.label} className={`${src.bg} rounded-lg p-3 text-center`}>
                                    <SrcIcon size={18} className={`${src.color} mx-auto mb-1`} />
                                    <p className="text-xl font-black text-gray-900">{src.count}</p>
                                    <p className="text-xs font-semibold text-gray-500">{src.label}</p>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}

function FileTextIcon(props: any) {
    return (
        <svg
            {...props}
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" x2="8" y1="13" y2="13" />
            <line x1="16" x2="8" y1="17" y2="17" />
            <line x1="10" x2="8" y1="9" y2="9" />
        </svg>
    )
}
