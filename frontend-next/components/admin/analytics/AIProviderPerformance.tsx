'use client';

import useSWR from 'swr';
import { Cpu } from 'lucide-react';
import api from '@/lib/api';
import { ProviderStatsData } from '@/types/analytics';

const fetcher = (url: string) => api.get(url).then(res => res.data);

/** Map provider family → card gradient */
function providerGradient(provider: string): string {
    if (provider === 'gemini') return 'bg-gradient-to-br from-blue-500 to-cyan-500';
    if (provider === 'groq') return 'bg-gradient-to-br from-orange-500 to-red-500';
    return 'bg-gradient-to-br from-gray-500 to-gray-700';
}

/** Friendly display name for a model key */
function modelLabel(key: string): string {
    const map: Record<string, string> = {
        'gemini-2.5-flash-lite': 'Gemini 2.5 Flash Lite',
        'gemini-2.5-flash': 'Gemini 2.5 Flash',
        'gemini-2.0-flash': 'Gemini 2.0 Flash',
        'gemini': 'Gemini',
        'groq': 'Groq',
        'llama-3.3-70b-versatile': 'Groq Llama 3.3 70b',
    };
    return map[key] ?? key;
}

export default function AIProviderPerformance() {
    const { data: providerStats, isLoading } = useSWR<ProviderStatsData>('/analytics/provider-stats/', fetcher, { keepPreviousData: true });

    if (isLoading) {
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

    if (!providerStats || providerStats.total_records === 0) return null;

    return (
        <div className="space-y-6">
            <h2 className="text-xl font-bold text-gray-900 border-l-4 border-amber-500 pl-4">🤖 AI Provider Performance</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(providerStats.providers).map(([key, data]) => {
                    // `data.provider` = family ('gemini'/'groq'), `key` = model name
                    const family = (data as any).provider ?? key;
                    return (
                        <div key={key} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-shadow">
                            <div className="flex items-center gap-3 mb-4">
                                <div className={`p-2.5 rounded-lg text-white shadow-sm ${providerGradient(family)}`}>
                                    <Cpu size={20} />
                                </div>
                                <div>
                                    <h3 className="text-base font-bold text-gray-900">{modelLabel(key)}</h3>
                                    <p className="text-xs text-gray-400">{data.count} generations</p>
                                </div>
                            </div>
                            <div className="space-y-2">
                                <div className="flex justify-between text-sm">
                                    <span className="text-gray-500">Avg Quality</span>
                                    <span className="font-semibold text-gray-900">{data.avg_quality}/10</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-gray-500">Spec Coverage</span>
                                    <span className="font-semibold text-gray-900">{data.avg_coverage}%</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-gray-500">Avg Time</span>
                                    <span className="font-semibold text-gray-900">{data.avg_time}s</span>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
