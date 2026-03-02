'use client';

import useSWR from 'swr';
import {
    Users, Rss, AlertTriangle, TrendingUp,
    Radio, Bug, ArrowUpRight
} from 'lucide-react';
import api from '@/lib/api';
import Link from 'next/link';

interface TopFeed {
    name: string;
    entries_processed: number;
    source_type: string;
}

interface TopError {
    error_type: string;
    message: string;
    occurrence_count: number;
    last_seen: string;
}

interface ExtraStats {
    subscribers: {
        total: number;
        labels: string[];
        data: number[];
        cumulative: number[];
    };
    rss: {
        total_feeds: number;
        active_feeds: number;
        total_entries: number;
        recently_active: number;
        by_type: Record<string, number>;
        top_feeds: TopFeed[];
    };
    errors: {
        frontend_total: number;
        frontend_unresolved: number;
        frontend_last_24h: number;
        top_errors: TopError[];
        backend_total: number;
        backend_last_24h: number;
    };
}

const fetcher = (url: string) => api.get(url).then(res => res.data);

function MiniBar({ value, max, color }: { value: number; max: number; color: string }) {
    const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
    return (
        <div className="w-full bg-gray-100 rounded-full h-1.5">
            <div className={`${color} h-1.5 rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
        </div>
    );
}

// ─── Subscriber Growth Widget ──────────────────────────────
function SubscriberGrowth({ data }: { data: ExtraStats['subscribers'] }) {
    const maxVal = Math.max(...data.data, 1);

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <div className="bg-blue-100 p-2 rounded-lg">
                        <Users className="text-blue-600" size={18} />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold text-gray-900">Subscribers</h3>
                        <p className="text-xs text-gray-400">Newsletter growth</p>
                    </div>
                </div>
                <div className="text-right">
                    <p className="text-2xl font-black text-gray-900">{data.total}</p>
                    <p className="text-xs text-gray-400">Active</p>
                </div>
            </div>

            {/* Mini bar chart */}
            {data.labels.length > 0 ? (
                <div className="space-y-2">
                    <div className="flex items-end gap-1 h-16">
                        {data.data.map((val, i) => (
                            <div key={i} className="flex-1 flex flex-col items-center">
                                <div
                                    className="w-full bg-gradient-to-t from-blue-500 to-blue-400 rounded-t transition-all duration-500 min-h-[2px]"
                                    style={{ height: `${Math.max((val / maxVal) * 100, 5)}%` }}
                                    title={`${data.labels[i]}: ${val} new`}
                                />
                            </div>
                        ))}
                    </div>
                    <div className="flex justify-between text-[10px] text-gray-300">
                        <span>{data.labels[0]}</span>
                        <span>{data.labels[data.labels.length - 1]}</span>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-blue-600">
                        <TrendingUp size={12} />
                        <span>
                            {data.data[data.data.length - 1] || 0} new this month
                        </span>
                    </div>
                </div>
            ) : (
                <p className="text-sm text-gray-400 text-center py-4">No subscriber data yet</p>
            )}
        </div>
    );
}

// ─── RSS Feed Stats Widget ──────────────────────────────
function RSSFeedStats({ data }: { data: ExtraStats['rss'] }) {
    const maxEntries = Math.max(...data.top_feeds.map(f => f.entries_processed), 1);

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <div className="bg-orange-100 p-2 rounded-lg">
                        <Rss className="text-orange-600" size={18} />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold text-gray-900">RSS Feeds</h3>
                        <p className="text-xs text-gray-400">Content pipeline</p>
                    </div>
                </div>
                <Link href="/admin/rss" className="text-xs text-orange-500 hover:text-orange-700 flex items-center gap-0.5">
                    Manage <ArrowUpRight size={10} />
                </Link>
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-3 gap-2 mb-4">
                <div className="text-center p-2 bg-orange-50 rounded-lg">
                    <p className="text-lg font-black text-gray-900">{data.active_feeds}</p>
                    <p className="text-[10px] text-gray-400 uppercase">Active</p>
                </div>
                <div className="text-center p-2 bg-orange-50 rounded-lg">
                    <p className="text-lg font-black text-gray-900">{data.total_entries.toLocaleString()}</p>
                    <p className="text-[10px] text-gray-400 uppercase">Entries</p>
                </div>
                <div className="text-center p-2 bg-orange-50 rounded-lg">
                    <p className="text-lg font-black text-gray-900">{data.recently_active}</p>
                    <p className="text-[10px] text-gray-400 uppercase">24h Active</p>
                </div>
            </div>

            {/* Source type breakdown */}
            <div className="flex gap-2 mb-3">
                {Object.entries(data.by_type).map(([type, count]) => (
                    <span key={type} className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 capitalize">
                        {type}: {count}
                    </span>
                ))}
            </div>

            {/* Top feeds */}
            <div className="space-y-2">
                {data.top_feeds.slice(0, 3).map((feed, i) => (
                    <div key={i}>
                        <div className="flex justify-between text-xs mb-0.5">
                            <span className="text-gray-600 truncate max-w-[180px]">{feed.name}</span>
                            <span className="text-gray-400 font-mono">{feed.entries_processed}</span>
                        </div>
                        <MiniBar value={feed.entries_processed} max={maxEntries} color="bg-orange-400" />
                    </div>
                ))}
            </div>
        </div>
    );
}

// ─── Error Summary Widget ──────────────────────────────
function ErrorSummary({ data }: { data: ExtraStats['errors'] }) {
    const hasIssues = data.frontend_unresolved > 0 || data.backend_last_24h > 0;

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <div className={`p-2 rounded-lg ${hasIssues ? 'bg-red-100' : 'bg-green-100'}`}>
                        {hasIssues
                            ? <AlertTriangle className="text-red-600" size={18} />
                            : <Bug className="text-green-600" size={18} />
                        }
                    </div>
                    <div>
                        <h3 className="text-sm font-bold text-gray-900">System Health</h3>
                        <p className="text-xs text-gray-400">
                            {hasIssues ? 'Issues require attention' : 'All clear'}
                        </p>
                    </div>
                </div>
                <Link href="/admin/health" className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-0.5">
                    Details <ArrowUpRight size={10} />
                </Link>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-3 mb-4">
                <div className={`p-3 rounded-lg ${data.frontend_unresolved > 0 ? 'bg-red-50' : 'bg-green-50'}`}>
                    <p className="text-lg font-black text-gray-900">{data.frontend_unresolved}</p>
                    <p className="text-[10px] text-gray-400 uppercase">Frontend Active</p>
                </div>
                <div className={`p-3 rounded-lg ${data.backend_last_24h > 0 ? 'bg-amber-50' : 'bg-green-50'}`}>
                    <p className="text-lg font-black text-gray-900">{data.backend_last_24h}</p>
                    <p className="text-[10px] text-gray-400 uppercase">Backend 24h</p>
                </div>
            </div>

            {/* Top errors */}
            {data.top_errors.length > 0 && (
                <div className="space-y-2">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Active Issues</p>
                    {data.top_errors.slice(0, 3).map((err, i) => (
                        <div key={i} className="flex items-start gap-2 p-2 bg-red-50/50 rounded-lg">
                            <span className="text-xs font-mono text-red-400 mt-0.5 shrink-0">×{err.occurrence_count}</span>
                            <div className="min-w-0">
                                <p className="text-xs text-gray-700 truncate">{err.message}</p>
                                <p className="text-[10px] text-gray-400">{err.error_type}</p>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// ─── Main Export: Combined Widget ──────────────────────────────
export default function ExtraStatsWidgets() {
    const { data, isLoading, error } = useSWR<ExtraStats>('/analytics/extra-stats/', fetcher, {
        refreshInterval: 120000,
    });

    if (isLoading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-pulse">
                {[...Array(3)].map((_, i) => (
                    <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 h-[280px]" />
                ))}
            </div>
        );
    }

    if (error || !data) return null;

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <SubscriberGrowth data={data.subscribers} />
            <RSSFeedStats data={data.rss} />
            <ErrorSummary data={data.errors} />
        </div>
    );
}
