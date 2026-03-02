'use client';

import { useState } from 'react';
import useSWR from 'swr';
import { Brain, TrendingUp, Shield, Tag, Search, Cpu, Target, ChevronRight } from 'lucide-react';
import api from '@/lib/api';

interface FeatureScore {
    score: number;
    status: string;
    details: string;
}

interface MLHealthReport {
    overall_level: {
        level: number;
        name: string;
        emoji: string;
        description: string;
    };
    overall_score: number;
    next_level: {
        level: number;
        name: string;
        emoji: string;
        articles_needed: number;
    } | null;
    data_stats: {
        total_articles: number;
        total_vehicle_specs: number;
        total_car_specs: number;
        total_brands: number;
        total_aliases: number;
        total_tags: number;
        spec_coverage_pct: number;
        spec_completeness_pct: number;
        model_trained: boolean;
        model_articles: number;
    };
    feature_scores: Record<string, FeatureScore>;
    recommendations: string[];
}

const fetcher = (url: string) => api.get(url).then(res => res.data);

const FEATURE_ICONS: Record<string, typeof Brain> = {
    recommendations: TrendingUp,
    tag_prediction: Tag,
    spec_extraction: Cpu,
    duplicate_detection: Shield,
    brand_detection: Target,
    data_validation: Shield,
    semantic_search: Search,
};

const FEATURE_COLORS: Record<string, string> = {
    recommendations: 'from-blue-500 to-cyan-500',
    tag_prediction: 'from-emerald-500 to-green-500',
    spec_extraction: 'from-amber-500 to-orange-500',
    duplicate_detection: 'from-rose-500 to-pink-500',
    brand_detection: 'from-violet-500 to-purple-500',
    data_validation: 'from-indigo-500 to-blue-500',
    semantic_search: 'from-cyan-500 to-teal-500',
};

function ScoreBar({ score, size = 'md' }: { score: number; size?: 'sm' | 'md' }) {
    const color = score >= 70 ? 'bg-emerald-500' : score >= 40 ? 'bg-amber-500' : 'bg-red-500';
    const h = size === 'sm' ? 'h-1.5' : 'h-2.5';
    return (
        <div className={`w-full bg-gray-100 rounded-full ${h}`}>
            <div
                className={`${color} ${h} rounded-full transition-all duration-700 ease-out`}
                style={{ width: `${Math.min(score, 100)}%` }}
            />
        </div>
    );
}

export default function MLHealthWidget() {
    const { data: report, isLoading, error } = useSWR<MLHealthReport>('/articles/ml-health/', fetcher, {
        refreshInterval: 60000,
    });

    if (isLoading) {
        return (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 animate-pulse">
                <div className="h-6 w-48 bg-gray-200 rounded mb-4" />
                <div className="h-3 w-full bg-gray-100 rounded mb-6" />
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="h-20 bg-gray-50 rounded-lg" />
                    ))}
                </div>
            </div>
        );
    }

    if (error || !report) return null;

    const { overall_level, overall_score, next_level, data_stats, feature_scores, recommendations } = report;

    const levelEmojis = ['', '🥉', '🥈', '🥇', '💎', '🏆'];
    const levelGradients = [
        '',
        'from-stone-400 to-stone-500',
        'from-slate-400 to-slate-500',
        'from-amber-400 to-yellow-500',
        'from-cyan-400 to-blue-500',
        'from-amber-300 to-yellow-400',
    ];

    return (
        <div className="space-y-6">
            {/* Main health card */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                {/* Header with level */}
                <div className={`bg-gradient-to-r ${levelGradients[overall_level.level] || 'from-gray-400 to-gray-500'} px-6 py-4`}>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <span className="text-3xl">{levelEmojis[overall_level.level]}</span>
                            <div>
                                <h3 className="text-lg font-bold text-white">
                                    Level {overall_level.level}: {overall_level.name}
                                </h3>
                                <p className="text-white/80 text-sm">{overall_level.description}</p>
                            </div>
                        </div>
                        <div className="text-right">
                            <p className="text-3xl font-black text-white">{overall_score}%</p>
                            <p className="text-white/70 text-xs uppercase tracking-wider">Overall Score</p>
                        </div>
                    </div>
                    <div className="mt-3">
                        <div className="w-full bg-white/20 rounded-full h-2">
                            <div
                                className="bg-white h-2 rounded-full transition-all duration-1000 ease-out"
                                style={{ width: `${overall_score}%` }}
                            />
                        </div>
                        {next_level && (
                            <p className="text-white/70 text-xs mt-1.5 flex items-center gap-1">
                                <ChevronRight size={12} />
                                {next_level.articles_needed} more articles to reach {next_level.emoji} {next_level.name}
                            </p>
                        )}
                    </div>
                </div>

                {/* Data stats row */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-gray-100">
                    <div className="bg-white p-4 text-center">
                        <p className="text-2xl font-black text-gray-900">{data_stats.total_articles}</p>
                        <p className="text-xs text-gray-400 uppercase tracking-wider">Articles</p>
                    </div>
                    <div className="bg-white p-4 text-center">
                        <p className="text-2xl font-black text-gray-900">{data_stats.total_vehicle_specs}</p>
                        <p className="text-xs text-gray-400 uppercase tracking-wider">VehicleSpecs</p>
                    </div>
                    <div className="bg-white p-4 text-center">
                        <p className="text-2xl font-black text-gray-900">{data_stats.spec_coverage_pct}%</p>
                        <p className="text-xs text-gray-400 uppercase tracking-wider">Spec Coverage</p>
                    </div>
                    <div className="bg-white p-4 text-center">
                        <p className="text-2xl font-black text-gray-900">{data_stats.spec_completeness_pct}%</p>
                        <p className="text-xs text-gray-400 uppercase tracking-wider">Completeness</p>
                    </div>
                </div>
            </div>

            {/* Feature scores grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {Object.entries(feature_scores).map(([key, feat]) => {
                    const Icon = FEATURE_ICONS[key] || Brain;
                    const gradient = FEATURE_COLORS[key] || 'from-gray-500 to-gray-600';
                    return (
                        <div key={key} className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow">
                            <div className="flex items-center gap-2 mb-3">
                                <div className={`bg-gradient-to-br ${gradient} p-1.5 rounded-lg text-white`}>
                                    <Icon size={14} />
                                </div>
                                <span className="text-sm font-semibold text-gray-700 capitalize">
                                    {key.replace(/_/g, ' ')}
                                </span>
                            </div>
                            <div className="flex items-center justify-between mb-1.5">
                                <span className="text-xs text-gray-400">{feat.status}</span>
                                <span className="text-sm font-black text-gray-900">{feat.score}%</span>
                            </div>
                            <ScoreBar score={feat.score} size="sm" />
                            <p className="text-xs text-gray-400 mt-2 line-clamp-1">{feat.details}</p>
                        </div>
                    );
                })}
            </div>

            {/* Recommendations */}
            {recommendations.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                    <h4 className="text-sm font-bold text-amber-800 mb-2 flex items-center gap-2">
                        💡 Recommendations
                    </h4>
                    <ul className="space-y-1">
                        {recommendations.map((r, i) => (
                            <li key={i} className="text-sm text-amber-700">{r}</li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
