'use client';

/**
 * CapsuleFeedbackWidget — shows capsule sentiment across all articles.
 * Data from: GET /api/v1/analytics/capsule-feedback-summary/
 */

import useSWR from 'swr';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import api from '@/lib/api';
import Link from 'next/link';

interface CapsuleFeedbackSummary {
    total: number;
    positive_total: number;
    negative_total: number;
    by_type: Array<{ type: string; is_positive: boolean; count: number }>;
    top_positive_articles: Array<{ article_id: number; title: string; slug: string; votes: number }>;
    top_negative_articles: Array<{ article_id: number; title: string; slug: string; votes: number }>;
}

const LABEL_MAP: Record<string, string> = {
    accurate_specs: '📊 Accurate Specs', well_written: '✍️ Well Written',
    great_photos: '📸 Great Photos', fair_review: '⚖️ Fair Review', useful_info: '💡 Useful Info',
    wrong_specs: '📊 Wrong Specs', too_long: '✍️ Too Long', need_photos: '📸 Need Photos',
    missing_price: '💰 Missing Price', inaccurate: '❌ Inaccurate',
};

const fetcher = () => api.get('/analytics/capsule-feedback-summary/').then(r => r.data);

export default function CapsuleFeedbackWidget() {
    const { data, isLoading, error } = useSWR<CapsuleFeedbackSummary>('capsule-feedback-summary', fetcher, { refreshInterval: 120000 });

    if (isLoading) return <div className="bg-white rounded-xl shadow-sm border border-gray-100 h-72 animate-pulse" />;
    if (error || !data) {
        return (
            <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-100 text-center">
                <p className="text-3xl mb-2">👍</p>
                <p className="text-sm font-semibold text-gray-500">No capsule votes yet</p>
                <p className="text-xs text-gray-400 mt-1">Votes will appear once readers interact with article capsules</p>
            </div>
        );
    }

    const pct = data.total > 0 ? Math.round(data.positive_total / data.total * 100) : 0;

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-5">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className="bg-violet-100 p-2 rounded-lg"><ThumbsUp className="text-violet-600" size={18} /></div>
                    <div>
                        <h3 className="text-sm font-bold text-gray-900">Reader Capsule Votes</h3>
                        <p className="text-xs text-gray-400">{data.total.toLocaleString()} total votes</p>
                    </div>
                </div>
                <div className="text-right">
                    <p className="text-2xl font-black text-gray-900">{pct}%</p>
                    <p className="text-xs text-gray-400">positive</p>
                </div>
            </div>

            {/* Sentiment bar */}
            <div>
                <div className="flex justify-between text-xs mb-1">
                    <span className="text-emerald-600 font-semibold flex items-center gap-1"><ThumbsUp size={11} />{data.positive_total}</span>
                    <span className="text-rose-600 font-semibold flex items-center gap-1">{data.negative_total}<ThumbsDown size={11} /></span>
                </div>
                <div className="w-full bg-rose-100 rounded-full h-3">
                    <div className="bg-emerald-400 h-3 rounded-full transition-all duration-700" style={{ width: `${pct}%` }} />
                </div>
            </div>

            {/* Top capsule types */}
            <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Most Voted</p>
                <div className="space-y-1.5">
                    {data.by_type.slice(0, 6).map(item => {
                        const maxCount = data.by_type[0]?.count || 1;
                        return (
                            <div key={item.type} className="flex items-center gap-2">
                                <span className="text-xs text-gray-600 w-36 shrink-0">{LABEL_MAP[item.type] || item.type}</span>
                                <div className="flex-1 bg-gray-100 rounded-full h-2">
                                    <div
                                        className={`h-2 rounded-full transition-all ${item.is_positive ? 'bg-emerald-400' : 'bg-rose-400'}`}
                                        style={{ width: `${Math.round(item.count / maxCount * 100)}%` }}
                                    />
                                </div>
                                <span className="text-xs font-mono text-gray-500 w-8 text-right">{item.count}</span>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Top praised + criticized */}
            {data.top_positive_articles.length > 0 && (
                <div className="grid grid-cols-2 gap-3">
                    <div>
                        <p className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wider mb-1">👍 Most Praised</p>
                        {data.top_positive_articles.slice(0, 3).map(a => (
                            <Link key={a.article_id} href={`/admin/articles?slug=${a.slug}`}
                                className="block text-[11px] text-gray-700 line-clamp-1 hover:text-indigo-600 transition-colors py-0.5">
                                {a.title}
                            </Link>
                        ))}
                    </div>
                    <div>
                        <p className="text-[10px] font-semibold text-rose-500 uppercase tracking-wider mb-1">👎 Most Criticized</p>
                        {data.top_negative_articles.slice(0, 3).map(a => (
                            <Link key={a.article_id} href={`/admin/articles?slug=${a.slug}`}
                                className="block text-[11px] text-gray-700 line-clamp-1 hover:text-indigo-600 transition-colors py-0.5">
                                {a.title}
                            </Link>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
