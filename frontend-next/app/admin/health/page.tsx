'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { getApiUrl } from '@/lib/config';
import {
    Loader2, CheckCircle, AlertTriangle, XCircle, Server, Monitor,
    Clock, RefreshCw, Trash2, Activity, Zap, Globe, X, ExternalLink, Copy, Square, CheckSquare
} from 'lucide-react';
import toast from 'react-hot-toast';

// ── Types ───────────────────────────────────────────────────────────
interface HealthSummary {
    backend_errors: { total: number; unresolved: number; last_24h: number };
    api_errors: { unresolved: number; last_24h: number };
    scheduler_errors: { unresolved: number; last_24h: number };
    frontend_errors: { total: number; unresolved: number; last_24h: number };
    overall_status: 'healthy' | 'degraded' | 'critical';
    total_unresolved: number;
    trend?: TrendDay[];
}

interface TrendDay {
    date: string;
    api: number;
    scheduler: number;
    frontend: number;
}

interface BackendError {
    id: number;
    source: string;
    source_display: string;
    severity: string;
    severity_display: string;
    error_class: string;
    message: string;
    traceback: string;
    request_method: string;
    request_path: string;
    request_user: string;
    request_ip: string | null;
    task_name: string;
    occurrence_count: number;
    first_seen: string;
    last_seen: string;
    resolved: boolean;
    resolved_at: string | null;
    resolution_notes: string;
}

interface FrontendError {
    id: number;
    error_type: string;
    message: string;
    stack_trace: string | null;
    url: string;
    user_agent: string;
    occurrence_count: number;
    first_seen: string;
    last_seen: string;
    resolved: boolean;
}

type UnifiedError = {
    _source: 'backend' | 'frontend';
    _id: string;
    id: number;
    source_label: string;
    severity: string;
    error_class: string;
    message: string;
    detail: string;
    occurrence_count: number;
    last_seen: string;
    first_seen: string;
    resolved: boolean;
    // Extra fields for detail modal
    url?: string;
    user_agent?: string;
    request_method?: string;
    request_path?: string;
    request_user?: string;
    request_ip?: string | null;
    task_name?: string;
};

// ── Helpers ────────────────────────────────────────────────────────
function timeAgo(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

function getBrowser(ua: string): string {
    if (!ua) return 'Unknown';
    if (ua.includes('Chrome') && !ua.includes('Edge')) return 'Chrome';
    if (ua.includes('Firefox')) return 'Firefox';
    if (ua.includes('Safari') && !ua.includes('Chrome')) return 'Safari';
    if (ua.includes('Edge')) return 'Edge';
    return 'Other';
}

// ── Component ──────────────────────────────────────────────────────
// Active threshold: errors seen in last 5 minutes are "active"
const ACTIVE_THRESHOLD_MS = 5 * 60 * 1000;
function isActive(lastSeen: string): boolean {
    return Date.now() - new Date(lastSeen).getTime() < ACTIVE_THRESHOLD_MS;
}

export default function SystemHealthPage() {
    const [summary, setSummary] = useState<HealthSummary | null>(null);
    const [errors, setErrors] = useState<UnifiedError[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<'all' | 'backend' | 'frontend' | 'scheduler'>('all');
    const [showResolved, setShowResolved] = useState(false);
    const [selectedError, setSelectedError] = useState<UnifiedError | null>(null);
    const [autoRefresh, setAutoRefresh] = useState(true);
    const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
    const [groupByClass, setGroupByClass] = useState(false);
    const [backendPage, setBackendPage] = useState(1);
    const [frontendPage, setFrontendPage] = useState(1);
    const [hasMoreBackend, setHasMoreBackend] = useState(false);
    const [hasMoreFrontend, setHasMoreFrontend] = useState(false);
    const [loadingMore, setLoadingMore] = useState(false);
    const [selected, setSelected] = useState<Set<string>>(new Set());

    const toggleSelect = (id: string) => {
        setSelected(prev => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });
    };

    const selectAllFiltered = () => {
        const filtered = errors.filter(e => {
            if (!showResolved && e.resolved) return false;
            if (filter === 'backend') return e._source === 'backend' && !e.source_label.startsWith('Scheduler');
            if (filter === 'scheduler') return e._source === 'backend' && e.source_label.startsWith('Scheduler');
            if (filter === 'frontend') return e._source === 'frontend';
            return true;
        });
        if (selected.size === filtered.length && filtered.every(e => selected.has(e._id))) {
            setSelected(new Set());
        } else {
            setSelected(new Set(filtered.map(e => e._id)));
        }
    };

    const apiUrl = getApiUrl();

    const PAGE_SIZE = 20;

    // Parse paginated API response into unified errors
    const parseBackend = (bd: any): UnifiedError[] => {
        const results: BackendError[] = bd.results || bd;
        return results.map(e => ({
            _source: 'backend' as const, _id: `be-${e.id}`, id: e.id,
            source_label: e.source === 'scheduler' ? `Scheduler (${e.task_name})` : `API ${e.request_method} ${e.request_path}`,
            severity: e.severity, error_class: e.error_class, message: e.message,
            detail: e.traceback, occurrence_count: e.occurrence_count,
            last_seen: e.last_seen, first_seen: e.first_seen, resolved: e.resolved,
            request_method: e.request_method, request_path: e.request_path,
            request_user: e.request_user, request_ip: e.request_ip, task_name: e.task_name,
        }));
    };

    const parseFrontend = (fd: any): UnifiedError[] => {
        const results: FrontendError[] = fd.results || fd;
        return results.map(e => ({
            _source: 'frontend' as const, _id: `fe-${e.id}`, id: e.id,
            source_label: `Frontend (${e.error_type})`,
            severity: e.error_type === 'network' ? 'warning' : 'error',
            error_class: e.error_type, message: e.message,
            detail: e.stack_trace || '', occurrence_count: e.occurrence_count,
            last_seen: e.last_seen, first_seen: e.first_seen, resolved: e.resolved,
            url: e.url, user_agent: e.user_agent,
        }));
    };

    // ── Fetch all data (page 1) ──────────────────────────────────────
    const loadData = useCallback(async (silent = false) => {
        if (!silent) setLoading(true);
        try {
            const [summaryRes, backendRes, frontendRes] = await Promise.allSettled([
                api.get(`${apiUrl}/health/errors-summary/`),
                api.get(`${apiUrl}/backend-errors/?ordering=-last_seen&page_size=${PAGE_SIZE}`),
                api.get(`${apiUrl}/frontend-events/?page_size=${PAGE_SIZE}`),
            ]);

            if (summaryRes.status === 'fulfilled') setSummary(summaryRes.value.data);

            const unified: UnifiedError[] = [];

            if (backendRes.status === 'fulfilled') {
                const bd = backendRes.value.data;
                unified.push(...parseBackend(bd));
                setHasMoreBackend(!!bd.next);
            }

            if (frontendRes.status === 'fulfilled') {
                const fd = frontendRes.value.data;
                unified.push(...parseFrontend(fd));
                setHasMoreFrontend(!!fd.next);
            }

            unified.sort((a, b) => new Date(b.last_seen).getTime() - new Date(a.last_seen).getTime());
            setErrors(unified);
            setBackendPage(1);
            setFrontendPage(1);
            setLastUpdated(new Date());
        } catch (err) {
            if (!silent) {
                console.error('Failed to load health data:', err);
                toast.error('Failed to load health data');
            }
        } finally {
            setLoading(false);
        }
    }, [apiUrl]);

    // ── Load More ────────────────────────────────────────────────────
    const loadMore = async () => {
        setLoadingMore(true);
        try {
            const newErrors: UnifiedError[] = [];

            if (hasMoreBackend) {
                const nextPage = backendPage + 1;
                const { data: bd } = await api.get(`${apiUrl}/backend-errors/?ordering=-last_seen&page_size=${PAGE_SIZE}&page=${nextPage}`);
                newErrors.push(...parseBackend(bd));
                setHasMoreBackend(!!bd.next);
                setBackendPage(nextPage);
            }

            if (hasMoreFrontend) {
                const nextPage = frontendPage + 1;
                const { data: fd } = await api.get(`${apiUrl}/frontend-events/?page_size=${PAGE_SIZE}&page=${nextPage}`);
                newErrors.push(...parseFrontend(fd));
                setHasMoreFrontend(!!fd.next);
                setFrontendPage(nextPage);
            }

            if (newErrors.length > 0) {
                setErrors(prev => {
                    const all = [...prev, ...newErrors];
                    all.sort((a, b) => new Date(b.last_seen).getTime() - new Date(a.last_seen).getTime());
                    return all;
                });
            }
        } catch { toast.error('Failed to load more errors'); }
        finally { setLoadingMore(false); }
    };

    useEffect(() => { loadData(); }, [loadData]);

    // Auto-refresh every 30s
    useEffect(() => {
        if (!autoRefresh) return;
        const interval = setInterval(() => loadData(true), 30000);
        return () => clearInterval(interval);
    }, [autoRefresh, loadData]);

    // ── Actions ──────────────────────────────────────────────────────
    const markResolved = async (err: UnifiedError, resolved: boolean) => {
        const endpoint = err._source === 'backend' ? 'backend-errors' : 'frontend-events';
        try {
            await api.patch(`${apiUrl}/${endpoint}/${err.id}/`, { resolved });
            toast.success(resolved ? 'Marked resolved' : 'Reopened');
            if (selectedError?._id === err._id) setSelectedError({ ...selectedError, resolved });
            loadData(true);
        } catch { toast.error('Action failed'); }
    };

    const deleteError = async (err: UnifiedError) => {
        const endpoint = err._source === 'backend' ? 'backend-errors' : 'frontend-events';
        try {
            await api.delete(`${apiUrl}/${endpoint}/${err.id}/`);
            toast.success('Deleted');
            setSelectedError(null);
            loadData(true);
        } catch { toast.error('Delete failed'); }
    };

    const resolveAll = async () => {
        try {
            const [backendRes, frontendRes] = await Promise.allSettled([
                api.post(`${apiUrl}/backend-errors/resolve-all/`),
                api.post(`${apiUrl}/frontend-events/resolve-all/`),
            ]);
            const backendCount = backendRes.status === 'fulfilled' ? backendRes.value.data?.resolved ?? 0 : 0;
            const frontendCount = frontendRes.status === 'fulfilled' ? frontendRes.value.data?.resolved ?? 0 : 0;
            const total = backendCount + frontendCount;
            toast.success(total > 0 ? `Resolved ${total} error(s)` : 'No unresolved errors');
            loadData(true);
        } catch { toast.error('Failed'); }
    };

    const clearStale = async () => {
        try {
            const { data } = await api.post(`${apiUrl}/backend-errors/clear-stale/`);
            toast.success(`Cleared ${data.resolved} stale error(s)`);
            loadData(true);
        } catch { toast.error('Failed to clear stale'); }
    };

    // ── Filtering & Grouping ─────────────────────────────────────────
    const filtered = errors.filter(e => {
        if (!showResolved && e.resolved) return false;
        if (filter === 'backend') return e._source === 'backend' && !e.source_label.startsWith('Scheduler');
        if (filter === 'scheduler') return e._source === 'backend' && e.source_label.startsWith('Scheduler');
        if (filter === 'frontend') return e._source === 'frontend';
        return true;
    });

    // Group by error_class if toggled
    type GroupedError = { key: string; errors: UnifiedError[]; totalCount: number };
    const grouped: GroupedError[] = [];
    if (groupByClass) {
        const map = new Map<string, UnifiedError[]>();
        for (const e of filtered) {
            const key = `${e._source}:${e.error_class}`;
            if (!map.has(key)) map.set(key, []);
            map.get(key)!.push(e);
        }
        for (const [key, errs] of map) {
            grouped.push({ key, errors: errs, totalCount: errs.reduce((s, e) => s + e.occurrence_count, 0) });
        }
        grouped.sort((a, b) => b.totalCount - a.totalCount);
    }

    const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
    const toggleGroup = (key: string) => {
        setExpandedGroups(prev => {
            const next = new Set(prev);
            next.has(key) ? next.delete(key) : next.add(key);
            return next;
        });
    };

    // ── Badge helpers ────────────────────────────────────────────────
    const severityBadge = (s: string) => {
        const colors: Record<string, string> = {
            critical: 'bg-red-100 text-red-700 border-red-200',
            error: 'bg-orange-100 text-orange-700 border-orange-200',
            warning: 'bg-amber-100 text-amber-700 border-amber-200',
        };
        return colors[s] || colors.error;
    };

    const sourceBadge = (err: UnifiedError) => {
        if (err._source === 'frontend') return { icon: '🌐', label: 'Frontend', color: 'bg-cyan-50 text-cyan-700 border-cyan-200' };
        if (err.source_label.startsWith('Scheduler')) return { icon: '⚡', label: 'Scheduler', color: 'bg-purple-50 text-purple-700 border-purple-200' };
        return { icon: '🖥️', label: 'API', color: 'bg-blue-50 text-blue-700 border-blue-200' };
    };

    // ── Copy error info ────────────────────────────────────────────
    const copyError = (err: UnifiedError) => {
        const lines = [
            `## Error Type`,
            `${err.severity.toUpperCase()} ${err.error_class}`,
            ``,
            `## Error Message`,
            err.message,
            ``,
            `## Source`,
            err.source_label,
        ];
        if (err.request_method && err.request_path) {
            lines.push(``, `## Request`, `${err.request_method} ${err.request_path}`);
            if (err.request_user) lines.push(`User: ${err.request_user}`);
        }
        if (err.url) lines.push(``, `## URL`, err.url);
        if (err.task_name) lines.push(``, `## Task`, err.task_name);
        lines.push(
            ``,
            `## Timing`,
            `First seen: ${new Date(err.first_seen).toLocaleString()}`,
            `Last seen: ${new Date(err.last_seen).toLocaleString()}`,
            `Occurrences: ${err.occurrence_count}`,
            `Status: ${err.resolved ? 'Resolved' : isActive(err.last_seen) ? 'Active' : 'Stale'}`,
        );
        if (err.detail) {
            lines.push(``, `## Stack Trace`, '```', err.detail.trim(), '```');
        }
        navigator.clipboard.writeText(lines.join('\n'));
        toast.success('Error info copied!');
    };

    const copySelected = () => {
        const selErrors = errors.filter(e => selected.has(e._id));
        if (selErrors.length === 0) return;
        const blocks = selErrors.map((err, i) => {
            const lines = [
                `--- Error ${i + 1}/${selErrors.length} ---`,
                `${err.severity.toUpperCase()} ${err.error_class}: ${err.message}`,
                `Source: ${err.source_label}`,
            ];
            if (err.request_method && err.request_path) lines.push(`Request: ${err.request_method} ${err.request_path}`);
            if (err.url) lines.push(`URL: ${err.url}`);
            if (err.task_name) lines.push(`Task: ${err.task_name}`);
            lines.push(
                `Last seen: ${new Date(err.last_seen).toLocaleString()}`,
                `Occurrences: ${err.occurrence_count}`,
                `Status: ${err.resolved ? 'Resolved' : isActive(err.last_seen) ? 'Active' : 'Stale'}`,
            );
            if (err.detail) lines.push(`Stack: ${err.detail.trim().split('\n').slice(-3).join(' → ')}`);
            return lines.join('\n');
        });
        navigator.clipboard.writeText(blocks.join('\n\n'));
        toast.success(`${selErrors.length} error(s) copied!`);
    };

    const batchResolve = async () => {
        const promises = errors.filter(e => selected.has(e._id) && !e.resolved).map(err => {
            const endpoint = err._source === 'backend' ? 'backend-errors' : 'frontend-events';
            return api.patch(`${apiUrl}/${endpoint}/${err.id}/`, { resolved: true });
        });
        await Promise.all(promises);
        toast.success(`${promises.length} error(s) resolved`);
        setSelected(new Set());
        loadData(true);
    };

    const batchDelete = async () => {
        const promises = errors.filter(e => selected.has(e._id)).map(err => {
            const endpoint = err._source === 'backend' ? 'backend-errors' : 'frontend-events';
            return api.delete(`${apiUrl}/${endpoint}/${err.id}/`);
        });
        await Promise.all(promises);
        toast.success(`${promises.length} error(s) deleted`);
        setSelected(new Set());
        loadData(true);
    };

    // ── Trend Chart ──────────────────────────────────────────────────
    const TrendChart = ({ trend }: { trend: TrendDay[] }) => {
        if (!trend || trend.length === 0) return null;
        const maxVal = Math.max(...trend.map(d => d.api + d.scheduler + d.frontend), 1);

        return (
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Error Trend (7 days)</h3>
                <div className="flex items-end gap-2 h-24">
                    {trend.map((day, i) => {
                        const total = day.api + day.scheduler + day.frontend;
                        const height = total > 0 ? Math.max((total / maxVal) * 100, 8) : 4;
                        const apiH = total > 0 ? (day.api / total) * height : 0;
                        const schedH = total > 0 ? (day.scheduler / total) * height : 0;
                        const frontH = total > 0 ? (day.frontend / total) * height : 0;

                        return (
                            <div key={i} className="flex-1 flex flex-col items-center gap-1" title={`${day.date}: ${total} errors`}>
                                <div className="w-full flex flex-col justify-end rounded-t-sm overflow-hidden" style={{ height: `${height}%` }}>
                                    {frontH > 0 && <div className="bg-cyan-400 w-full" style={{ height: `${(frontH / height) * 100}%` }} />}
                                    {schedH > 0 && <div className="bg-purple-400 w-full" style={{ height: `${(schedH / height) * 100}%` }} />}
                                    {apiH > 0 && <div className="bg-blue-400 w-full" style={{ height: `${(apiH / height) * 100}%` }} />}
                                    {total === 0 && <div className="bg-gray-200 w-full h-full rounded-t-sm" />}
                                </div>
                                <span className="text-[9px] text-gray-400">{day.date.slice(5)}</span>
                            </div>
                        );
                    })}
                </div>
                <div className="flex gap-4 mt-2 text-[10px] text-gray-500">
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-400" /> API</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-400" /> Scheduler</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-400" /> Frontend</span>
                </div>
            </div>
        );
    };

    // ── Error Row ────────────────────────────────────────────────────
    const ErrorRow = ({ err }: { err: UnifiedError }) => {
        const sb = sourceBadge(err);
        return (
            <div
                onClick={() => setSelectedError(err)}
                className={`border rounded-xl p-4 transition shadow-sm cursor-pointer ${err.resolved ? 'bg-gray-50 border-gray-200 opacity-60' : selected.has(err._id) ? 'bg-indigo-50 border-indigo-300 shadow-md' : 'bg-white border-gray-200 hover:border-indigo-300 hover:shadow-md'
                    }`}
            >
                <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                        <div className="shrink-0 pt-0.5" onClick={e => { e.stopPropagation(); toggleSelect(err._id); }}>
                            {selected.has(err._id) ? (
                                <CheckSquare className="w-5 h-5 text-indigo-600 cursor-pointer" />
                            ) : (
                                <Square className="w-5 h-5 text-gray-300 hover:text-gray-500 cursor-pointer" />
                            )}
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap mb-1.5">
                                <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${severityBadge(err.severity)}`}>
                                    {err.severity}
                                </span>
                                <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${sb.color}`}>
                                    {sb.icon} {sb.label}
                                </span>
                                {err.occurrence_count > 1 && (
                                    <span className="text-xs px-2 py-0.5 rounded-full bg-red-50 text-red-600 border border-red-200 font-semibold">
                                        ×{err.occurrence_count}
                                    </span>
                                )}
                                {err.resolved ? (
                                    <span className="text-xs text-emerald-600 font-medium">✅ Resolved</span>
                                ) : isActive(err.last_seen) ? (
                                    <span className="text-xs px-2 py-0.5 rounded-full bg-red-500 text-white font-bold animate-pulse">🔴 Active</span>
                                ) : (
                                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 border border-gray-200 font-medium">⚪ Stale</span>
                                )}
                            </div>
                            <p className="text-sm text-gray-800 font-mono break-all">
                                <span className="text-gray-500 font-semibold">{err.error_class}:</span> {err.message.slice(0, 200)}
                            </p>
                            <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                                <span className="flex items-center gap-1"><Monitor className="w-3 h-3" /> {err.source_label}</span>
                                <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {timeAgo(err.last_seen)}</span>
                                {err.user_agent && <span className="flex items-center gap-1"><Globe className="w-3 h-3" /> {getBrowser(err.user_agent)}</span>}
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0" onClick={e => e.stopPropagation()}>
                        <button onClick={() => copyError(err)}
                            className="p-2 rounded-lg text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition"
                            title="Copy error info"><Copy className="w-4 h-4" /></button>
                        <button onClick={() => markResolved(err, !err.resolved)}
                            className="p-2 rounded-lg text-gray-400 hover:bg-emerald-50 hover:text-emerald-600 transition"
                            title={err.resolved ? 'Reopen' : 'Resolve'}><CheckCircle className="w-4 h-4" /></button>
                        <button onClick={() => deleteError(err)}
                            className="p-2 rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600 transition"
                            title="Delete"><Trash2 className="w-4 h-4" /></button>
                    </div>
                </div>
            </div>
        );
    };

    // ── Render ───────────────────────────────────────────────────────
    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[50vh]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    return (
        <div>
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-2xl sm:text-3xl font-black text-gray-950 flex items-center gap-2">
                        <Activity className="w-7 h-7 text-indigo-600" />
                        System Health Monitor
                    </h1>
                    <p className="text-sm text-gray-600 font-medium mt-1">
                        Unified error tracking · Last updated {timeAgo(lastUpdated.toISOString())}
                        {autoRefresh && <span className="text-emerald-600 ml-2">● Live</span>}
                    </p>
                </div>
                <div className="flex gap-2 flex-wrap">
                    <button onClick={() => { throw new Error('Test error from System Health — verifying pipeline'); }}
                        className="px-3 py-2 rounded-xl bg-red-50 text-red-700 hover:bg-red-100 text-sm font-semibold border border-red-200 transition">
                        🧪 Test Error
                    </button>
                    <button onClick={clearStale}
                        className="px-3 py-2 rounded-xl bg-amber-50 text-amber-700 hover:bg-amber-100 text-sm font-semibold border border-amber-200 transition flex items-center gap-1.5">
                        ⚪ Clear Stale
                    </button>
                    <button onClick={resolveAll}
                        className="px-3 py-2 rounded-xl bg-emerald-50 text-emerald-700 hover:bg-emerald-100 text-sm font-semibold border border-emerald-200 transition flex items-center gap-1.5">
                        <CheckCircle className="w-4 h-4" /> Resolve All
                    </button>
                    <button onClick={() => { setLoading(true); loadData(); }}
                        className="px-3 py-2 rounded-xl bg-gray-100 text-gray-700 hover:bg-gray-200 text-sm font-semibold border border-gray-200 transition flex items-center gap-1.5">
                        <RefreshCw className="w-4 h-4" /> Refresh
                    </button>
                </div>
            </div>

            {/* Status Cards */}
            {summary && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                        <div className="flex items-center gap-2 mb-2">
                            {summary.overall_status === 'healthy' && <CheckCircle className="w-5 h-5 text-emerald-500" />}
                            {summary.overall_status === 'degraded' && <AlertTriangle className="w-5 h-5 text-amber-500" />}
                            {summary.overall_status === 'critical' && <XCircle className="w-5 h-5 text-red-500" />}
                            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Overall</span>
                        </div>
                        <p className={`text-2xl font-black capitalize ${summary.overall_status === 'healthy' ? 'text-emerald-600' :
                            summary.overall_status === 'degraded' ? 'text-amber-600' : 'text-red-600'
                            }`}>{summary.overall_status}</p>
                        <p className="text-xs text-gray-500 mt-1">{summary.total_unresolved} unresolved total</p>
                    </div>
                    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                        <div className="flex items-center gap-2 mb-2">
                            <Server className="w-5 h-5 text-blue-500" />
                            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">API Errors</span>
                        </div>
                        <p className="text-2xl font-black text-gray-900">{summary.api_errors.unresolved}</p>
                        <p className="text-xs text-gray-500 mt-1">{summary.api_errors.last_24h} in last 24h</p>
                    </div>
                    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                        <div className="flex items-center gap-2 mb-2">
                            <Zap className="w-5 h-5 text-purple-500" />
                            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Scheduler</span>
                        </div>
                        <p className="text-2xl font-black text-gray-900">{summary.scheduler_errors.unresolved}</p>
                        <p className="text-xs text-gray-500 mt-1">{summary.scheduler_errors.last_24h} in last 24h</p>
                    </div>
                    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                        <div className="flex items-center gap-2 mb-2">
                            <Globe className="w-5 h-5 text-cyan-500" />
                            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Frontend</span>
                        </div>
                        <p className="text-2xl font-black text-gray-900">{summary.frontend_errors.unresolved}</p>
                        <p className="text-xs text-gray-500 mt-1">{summary.frontend_errors.last_24h} in last 24h</p>
                    </div>
                </div>
            )}

            {/* Trend Chart */}
            {summary?.trend && <TrendChart trend={summary.trend} />}

            {/* Filters */}
            <div className="flex items-center gap-3 flex-wrap mb-6">
                {(['all', 'backend', 'scheduler', 'frontend'] as const).map(f => (
                    <button key={f} onClick={() => setFilter(f)}
                        className={`px-4 py-2 rounded-xl text-sm font-semibold transition capitalize border ${filter === f ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50 hover:border-gray-300'
                            }`}>{f === 'all' ? 'All Sources' : f}</button>
                ))}
                <div className="flex items-center gap-4 ml-auto">
                    <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
                        <input type="checkbox" checked={groupByClass} onChange={e => setGroupByClass(e.target.checked)}
                            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
                        Group by class
                    </label>
                    <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
                        <input type="checkbox" checked={showResolved} onChange={e => setShowResolved(e.target.checked)}
                            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
                        Show resolved
                    </label>
                    <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
                        <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)}
                            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
                        Auto-refresh
                    </label>
                </div>
            </div>

            {/* Error Feed */}
            <div className="space-y-3">
                {/* Selection toolbar */}
                {filtered.length > 0 && (
                    <div className="flex items-center gap-3 mb-1">
                        <button onClick={selectAllFiltered}
                            className="flex items-center gap-2 text-sm text-gray-500 hover:text-indigo-600 transition">
                            {selected.size > 0 && selected.size === filtered.length ? (
                                <><CheckSquare className="w-4 h-4" /> Deselect all</>
                            ) : (
                                <><Square className="w-4 h-4" /> Select all ({filtered.length})</>
                            )}
                        </button>
                        {selected.size > 0 && (
                            <span className="text-xs text-indigo-600 font-semibold">{selected.size} selected</span>
                        )}
                    </div>
                )}
                {filtered.length === 0 ? (
                    <div className="text-center py-16 bg-white rounded-xl border border-gray-200 shadow-sm">
                        <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
                        <p className="text-gray-700 text-lg font-semibold">All clear! No errors to show.</p>
                        <p className="text-gray-500 text-sm mt-1">The system is running smoothly.</p>
                    </div>
                ) : groupByClass ? (
                    grouped.map(g => (
                        <div key={g.key} className="border rounded-xl shadow-sm bg-white border-gray-200">
                            <button onClick={() => toggleGroup(g.key)}
                                className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition rounded-xl">
                                <div className="flex items-center gap-3">
                                    <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${severityBadge(g.errors[0].severity)}`}>
                                        {g.errors[0].severity}
                                    </span>
                                    <span className="font-mono text-sm text-gray-800 font-semibold">{g.errors[0].error_class}</span>
                                    <span className="text-xs text-gray-500">{g.errors.length} unique · ×{g.totalCount} total</span>
                                </div>
                                <span className="text-gray-400 text-sm">{expandedGroups.has(g.key) ? '▼' : '▶'}</span>
                            </button>
                            {expandedGroups.has(g.key) && (
                                <div className="border-t border-gray-100 p-3 space-y-2">
                                    {g.errors.map(err => <ErrorRow key={err._id} err={err} />)}
                                </div>
                            )}
                        </div>
                    ))
                ) : (
                    filtered.map(err => <ErrorRow key={err._id} err={err} />)
                )}

                {/* Load More */}
                {(hasMoreBackend || hasMoreFrontend) && (
                    <div className="text-center pt-4">
                        <button
                            onClick={loadMore}
                            disabled={loadingMore}
                            className="px-6 py-3 rounded-xl bg-white text-indigo-600 hover:bg-indigo-50 text-sm font-semibold border border-indigo-200 transition inline-flex items-center gap-2 disabled:opacity-50"
                        >
                            {loadingMore ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                            {loadingMore ? 'Loading...' : `Load more errors`}
                        </button>
                    </div>
                )}
            </div>

            {/* Floating selection toolbar */}
            {selected.size > 0 && (
                <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-gray-900 text-white rounded-2xl shadow-2xl px-6 py-3 flex items-center gap-4 animate-in slide-in-from-bottom-4">
                    <span className="text-sm font-bold">{selected.size} selected</span>
                    <div className="w-px h-6 bg-gray-700" />
                    <button onClick={copySelected}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-sm font-semibold transition">
                        <Copy className="w-4 h-4" /> Copy
                    </button>
                    <button onClick={batchResolve}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-sm font-semibold transition">
                        <CheckCircle className="w-4 h-4" /> Resolve
                    </button>
                    <button onClick={batchDelete}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-sm font-semibold transition">
                        <Trash2 className="w-4 h-4" /> Delete
                    </button>
                    <button onClick={() => setSelected(new Set())}
                        className="p-1.5 rounded-lg hover:bg-gray-700 transition">
                        <X className="w-4 h-4" />
                    </button>
                </div>
            )}

            {/* Detail Modal */}
            {selectedError && (
                <div className="fixed inset-0 bg-gray-500/75 flex items-center justify-center p-4 z-50" onClick={() => setSelectedError(null)}>
                    <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col" onClick={e => e.stopPropagation()}>
                        {/* Modal Header */}
                        <div className="flex items-center justify-between p-6 border-b border-gray-200">
                            <div className="flex items-center gap-3">
                                <span className={`text-xs px-2.5 py-1 rounded-md border font-semibold ${severityBadge(selectedError.severity)}`}>
                                    {selectedError.severity}
                                </span>
                                <span className={`text-xs px-2.5 py-1 rounded-md border font-medium ${sourceBadge(selectedError).color}`}>
                                    {sourceBadge(selectedError).icon} {sourceBadge(selectedError).label}
                                </span>
                                <h3 className="text-lg font-bold text-gray-900">Error Details</h3>
                            </div>
                            <button onClick={() => setSelectedError(null)} className="text-gray-400 hover:text-gray-500">
                                <X className="h-6 w-6" />
                            </button>
                        </div>

                        {/* Modal Body */}
                        <div className="flex-1 overflow-y-auto p-6 space-y-5">
                            {/* Message */}
                            <div>
                                <h4 className="text-sm font-medium text-gray-500 mb-1">Message</h4>
                                <div className="bg-red-50 text-red-900 border border-red-100 rounded-lg p-3 font-mono text-sm break-all">
                                    <span className="text-red-600 font-semibold">{selectedError.error_class}:</span> {selectedError.message}
                                </div>
                            </div>

                            {/* Meta Cards */}
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                                    <span className="block text-xs text-gray-500 font-medium mb-1">Status</span>
                                    <span className={`inline-flex items-center gap-1.5 font-semibold text-sm ${selectedError.resolved ? 'text-emerald-600' : 'text-orange-600'}`}>
                                        {selectedError.resolved ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                                        {selectedError.resolved ? 'Resolved' : 'Unresolved'}
                                    </span>
                                </div>
                                <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                                    <span className="block text-xs text-gray-500 font-medium mb-1">Occurrences</span>
                                    <span className="font-semibold text-sm text-gray-900">×{selectedError.occurrence_count}</span>
                                </div>
                                <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                                    <span className="block text-xs text-gray-500 font-medium mb-1">First Seen</span>
                                    <span className="text-sm text-gray-900">{new Date(selectedError.first_seen).toLocaleString()}</span>
                                </div>
                                <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                                    <span className="block text-xs text-gray-500 font-medium mb-1">Last Seen</span>
                                    <span className="text-sm text-gray-900">{new Date(selectedError.last_seen).toLocaleString()}</span>
                                </div>
                            </div>

                            {/* Context: API errors */}
                            {selectedError._source === 'backend' && selectedError.request_path && (
                                <div>
                                    <h4 className="text-sm font-medium text-gray-500 mb-1">Request Context</h4>
                                    <div className="bg-gray-50 p-3 rounded-lg border border-gray-100 text-sm space-y-1">
                                        <p><span className="text-gray-500">Method:</span> <span className="font-mono text-gray-800">{selectedError.request_method}</span></p>
                                        <p><span className="text-gray-500">Path:</span> <span className="font-mono text-gray-800">{selectedError.request_path}</span></p>
                                        {selectedError.request_user && <p><span className="text-gray-500">User:</span> <span className="text-gray-800">{selectedError.request_user}</span></p>}
                                        {selectedError.request_ip && <p><span className="text-gray-500">IP:</span> <span className="font-mono text-gray-800">{selectedError.request_ip}</span></p>}
                                    </div>
                                </div>
                            )}

                            {/* Context: Scheduler */}
                            {selectedError.task_name && (
                                <div>
                                    <h4 className="text-sm font-medium text-gray-500 mb-1">Scheduler Task</h4>
                                    <p className="font-mono text-sm text-gray-800 bg-purple-50 p-2 rounded-lg border border-purple-100">{selectedError.task_name}</p>
                                </div>
                            )}

                            {/* Context: Frontend URL + browser */}
                            {selectedError.url && (
                                <div>
                                    <h4 className="text-sm font-medium text-gray-500 mb-1">URL / Source</h4>
                                    <a href={selectedError.url} target="_blank" rel="noopener noreferrer"
                                        className="text-indigo-600 hover:text-indigo-800 text-sm break-all underline decoration-indigo-200 underline-offset-2 inline-flex items-center gap-1">
                                        {selectedError.url} <ExternalLink className="w-3 h-3" />
                                    </a>
                                </div>
                            )}
                            {selectedError.user_agent && (
                                <div>
                                    <h4 className="text-sm font-medium text-gray-500 mb-1">Browser / User Agent</h4>
                                    <p className="text-sm text-gray-700 bg-gray-50 p-2 rounded border border-gray-100 font-mono text-xs break-all">
                                        {getBrowser(selectedError.user_agent)} — {selectedError.user_agent}
                                    </p>
                                </div>
                            )}

                            {/* Stack trace / Traceback */}
                            {selectedError.detail && (
                                <div>
                                    <h4 className="text-sm font-medium text-gray-500 mb-1">
                                        {selectedError._source === 'backend' ? 'Traceback' : 'Stack Trace'}
                                    </h4>
                                    <pre className="bg-gray-900 text-gray-300 p-4 rounded-lg overflow-x-auto text-xs whitespace-pre-wrap font-mono leading-relaxed max-h-64 overflow-y-auto">
                                        {selectedError.detail}
                                    </pre>
                                </div>
                            )}
                        </div>

                        {/* Modal Footer */}
                        <div className="p-5 border-t border-gray-200 bg-gray-50 flex items-center justify-between rounded-b-xl">
                            <div className="flex gap-2">
                                <button onClick={() => deleteError(selectedError)}
                                    className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-lg text-red-700 bg-red-100 hover:bg-red-200 transition">
                                    <Trash2 className="h-4 w-4 mr-2" /> Delete
                                </button>
                                <button onClick={() => copyError(selectedError)}
                                    className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-lg text-indigo-700 bg-indigo-100 hover:bg-indigo-200 transition">
                                    <Copy className="h-4 w-4 mr-2" /> Copy
                                </button>
                            </div>
                            <div className="flex gap-3">
                                <button onClick={() => setSelectedError(null)}
                                    className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 transition">
                                    Close
                                </button>
                                <button onClick={() => markResolved(selectedError, !selectedError.resolved)}
                                    className={`inline-flex items-center px-4 py-2 text-sm font-medium rounded-lg text-white shadow-sm transition ${selectedError.resolved ? 'bg-orange-600 hover:bg-orange-700' : 'bg-emerald-600 hover:bg-emerald-700'
                                        }`}>
                                    {selectedError.resolved ? (
                                        <><RefreshCw className="h-4 w-4 mr-2" /> Reopen</>
                                    ) : (
                                        <><CheckCircle className="h-4 w-4 mr-2" /> Resolve</>
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
