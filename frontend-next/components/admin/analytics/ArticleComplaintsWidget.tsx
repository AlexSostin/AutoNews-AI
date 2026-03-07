'use client';

/**
 * ArticleComplaintsWidget — shows articles with the most editor reports.
 * Data from: GET /api/v1/analytics/article-complaints/
 */

import useSWR from 'swr';
import { AlertTriangle, CheckCircle } from 'lucide-react';
import api from '@/lib/api';
import Link from 'next/link';

interface ArticleComplaints {
    total: number;
    unresolved_total: number;
    resolved_total: number;
    most_complained: Array<{
        article_id: number; title: string; slug: string;
        total_reports: number; unresolved_reports: number;
    }>;
    by_category: Array<{ category: string; count: number }>;
}

const CATEGORY_LABELS: Record<string, string> = {
    factual_error: '❌ Factual Error',
    hallucination: '🤖 AI Hallucination',
    typo: '✏️ Typo / Grammar',
    outdated: '📅 Outdated Info',
    other: '💬 Other',
};

const fetcher = () => api.get('/analytics/article-complaints/').then(r => r.data);

export default function ArticleComplaintsWidget() {
    const { data, isLoading, error } = useSWR<ArticleComplaints>('article-complaints', fetcher, { refreshInterval: 120000 });

    if (error || !data) {
        return (
            <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-100 text-center">
                <p className="text-3xl mb-2">✅</p>
                <p className="text-sm font-semibold text-gray-500">No complaints yet</p>
                <p className="text-xs text-gray-400 mt-1">Reader feedback reports will appear here</p>
            </div>
        );
    }

    const hasIssues = data.unresolved_total > 0;

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-5">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className={`p-2 rounded-lg ${hasIssues ? 'bg-amber-100' : 'bg-emerald-100'}`}>
                        {hasIssues
                            ? <AlertTriangle className="text-amber-600" size={18} />
                            : <CheckCircle className="text-emerald-600" size={18} />}
                    </div>
                    <div>
                        <h3 className="text-sm font-bold text-gray-900">Article Complaints</h3>
                        <p className="text-xs text-gray-400">{data.total} reports from readers</p>
                    </div>
                </div>
                <div className="flex gap-3">
                    <div className="text-center">
                        <p className={`text-xl font-black ${data.unresolved_total > 0 ? 'text-amber-500' : 'text-emerald-500'}`}>{data.unresolved_total}</p>
                        <p className="text-[10px] text-gray-400">Open</p>
                    </div>
                    <div className="text-center">
                        <p className="text-xl font-black text-gray-400">{data.resolved_total}</p>
                        <p className="text-[10px] text-gray-400">Resolved</p>
                    </div>
                </div>
            </div>

            {/* By category */}
            {data.by_category.length > 0 && (
                <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">By Type</p>
                    <div className="flex flex-wrap gap-2">
                        {data.by_category.map(cat => (
                            <span key={cat.category} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-gray-100 text-xs text-gray-700">
                                {CATEGORY_LABELS[cat.category] || cat.category}
                                <span className="font-bold text-gray-900 ml-0.5">{cat.count}</span>
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Most complained articles */}
            {data.most_complained.length === 0 ? (
                <p className="text-sm text-emerald-600 font-medium text-center py-4">✅ No complaints yet!</p>
            ) : (
                <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Most Reported</p>
                    <div className="space-y-1.5">
                        {data.most_complained.map((a, i) => (
                            <div key={a.article_id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors">
                                <span className="text-xs font-black text-gray-300 w-5 shrink-0">#{i + 1}</span>
                                <div className="flex-1 min-w-0">
                                    <Link href={`/admin/feedback?article=${a.slug}`}
                                        className="text-xs text-gray-800 font-semibold line-clamp-1 hover:text-indigo-600 transition-colors">
                                        {a.title}
                                    </Link>
                                </div>
                                <div className="flex items-center gap-1.5 shrink-0">
                                    {a.unresolved_reports > 0 && (
                                        <span className="text-[10px] text-amber-600 font-semibold bg-amber-50 px-1.5 py-0.5 rounded">
                                            {a.unresolved_reports} open
                                        </span>
                                    )}
                                    <span className="text-xs font-mono text-gray-500">{a.total_reports} total</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
