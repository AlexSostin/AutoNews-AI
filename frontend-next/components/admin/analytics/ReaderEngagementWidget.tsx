'use client';

/**
 * ReaderEngagementWidget — shows dwell time, scroll depth funnel, bounce rate.
 * Data from: GET /api/v1/analytics/reader-engagement/
 */

import useSWR from 'swr';
import { Clock, ArrowDown, TrendingDown, Users } from 'lucide-react';
import api from '@/lib/api';
import Link from 'next/link';

interface ReaderEngagement {
    top_articles: Array<{
        article_id: number;
        title: string;
        slug: string;
        avg_dwell_seconds: number;
        avg_scroll_depth: number;
        session_count: number;
    }>;
    scroll_funnel: Record<string, number>;
    overall: {
        avg_dwell_seconds: number;
        avg_scroll_depth: number;
        bounce_rate_pct: number;
        total_sessions: number;
    };
}

const fetcher = () => api.get('/analytics/reader-engagement/').then(r => r.data);

function fmtTime(secs: number) {
    if (secs < 60) return `${Math.round(secs)}s`;
    return `${Math.floor(secs / 60)}m ${Math.round(secs % 60)}s`;
}

export default function ReaderEngagementWidget() {
    const { data, isLoading, error } = useSWR<ReaderEngagement>('reader-engagement', fetcher, { refreshInterval: 120000 });

    if (isLoading) {
        return (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 animate-pulse">
                {[0, 1].map(i => <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-100 h-80" />)}
            </div>
        );
    }

    if (error || !data) {
        return <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 text-sm text-gray-400">Unable to load reader engagement</div>;
    }

    const { overall, top_articles, scroll_funnel } = data;
    const funnelKeys = ['25', '50', '75', '100'];
    const funnelColors = ['bg-emerald-400', 'bg-blue-400', 'bg-violet-400', 'bg-rose-400'];
    const funnelLabels = ['25% scroll', '50% scroll', '75% scroll', 'Full read'];

    return (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {/* Overall KPIs + Scroll Funnel */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-5">
                <div className="flex items-center gap-2">
                    <div className="bg-emerald-100 p-2 rounded-lg"><Clock className="text-emerald-600" size={18} /></div>
                    <div>
                        <h3 className="text-sm font-bold text-gray-900">Reader Quality</h3>
                        <p className="text-xs text-gray-400">{overall.total_sessions.toLocaleString()} sessions tracked</p>
                    </div>
                </div>

                {/* KPI row */}
                <div className="grid grid-cols-3 gap-3">
                    <div className="text-center p-3 bg-emerald-50 rounded-xl">
                        <p className="text-xl font-black text-gray-900">{fmtTime(overall.avg_dwell_seconds)}</p>
                        <p className="text-[10px] text-gray-400 uppercase mt-0.5">Avg. Read Time</p>
                    </div>
                    <div className="text-center p-3 bg-blue-50 rounded-xl">
                        <p className="text-xl font-black text-gray-900">{overall.avg_scroll_depth}%</p>
                        <p className="text-[10px] text-gray-400 uppercase mt-0.5">Avg. Scroll</p>
                    </div>
                    <div className={`text-center p-3 rounded-xl ${overall.bounce_rate_pct > 50 ? 'bg-rose-50' : 'bg-gray-50'}`}>
                        <p className="text-xl font-black text-gray-900">{overall.bounce_rate_pct}%</p>
                        <p className="text-[10px] text-gray-400 uppercase mt-0.5">Bounce Rate</p>
                    </div>
                </div>

                {/* Scroll funnel */}
                <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-1">
                        <ArrowDown size={12} /> Scroll Depth Funnel
                    </p>
                    <div className="space-y-2">
                        {funnelKeys.map((k, i) => (
                            <div key={k}>
                                <div className="flex justify-between text-xs mb-1">
                                    <span className="text-gray-600">{funnelLabels[i]}</span>
                                    <span className="font-mono text-gray-700 font-semibold">{scroll_funnel[k]}%</span>
                                </div>
                                <div className="w-full bg-gray-100 rounded-full h-2.5">
                                    <div
                                        className={`${funnelColors[i]} h-2.5 rounded-full transition-all duration-700`}
                                        style={{ width: `${scroll_funnel[k]}%` }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Top articles by dwell time */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                <div className="flex items-center gap-2 mb-4">
                    <div className="bg-blue-100 p-2 rounded-lg"><Users className="text-blue-600" size={18} /></div>
                    <div>
                        <h3 className="text-sm font-bold text-gray-900">Most-Read Articles</h3>
                        <p className="text-xs text-gray-400">By average reading time</p>
                    </div>
                </div>

                {top_articles.length === 0 ? (
                    <p className="text-sm text-gray-400 text-center py-8">No reading sessions yet</p>
                ) : (
                    <div className="space-y-2">
                        {top_articles.map((a, i) => (
                            <div key={a.article_id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors">
                                <span className="text-xs font-black text-gray-300 w-5 shrink-0">#{i + 1}</span>
                                <div className="flex-1 min-w-0">
                                    <Link href={`/admin/articles?slug=${a.slug}`} className="text-xs text-gray-800 font-semibold line-clamp-1 hover:text-indigo-600 transition-colors">
                                        {a.title}
                                    </Link>
                                    <p className="text-[10px] text-gray-400">{a.session_count} sessions · {a.avg_scroll_depth}% avg scroll</p>
                                </div>
                                <span className="text-xs font-mono font-bold text-emerald-600 shrink-0">{fmtTime(a.avg_dwell_seconds)}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
