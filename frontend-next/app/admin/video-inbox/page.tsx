'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Search, RefreshCw, Loader2, X, Eye, Check, FileText,
  LayoutGrid, List, ExternalLink,
  Youtube, Trash2, Wand2, Edit,
} from 'lucide-react';
import api from '@/lib/api';
import { logCaughtError } from '@/lib/error-logger';
import Link from 'next/link';

/* ---------- types ---------- */
interface VideoCandidate {
  id: number;
  channel: number;
  channel_name: string;
  video_id: string;
  title: string;
  description: string;
  thumbnail_url: string;
  duration_seconds: number | null;
  duration_display: string;
  view_count: number | null;
  published_at: string | null;
  status: 'new' | 'approved' | 'generating' | 'dismissed';
  video_url: string;
  created_at: string;
  // Article existence info
  has_article: boolean;
  article_status: 'published' | 'pending' | 'draft' | null;
  article_slug: string | null;
  similar_articles_count: number;
  // Generation tracking (persisted on model)
  generation_task_id: string;
  generation_error: string;
}

interface InboxStats {
  new_count: number;
  approved_count: number;
  dismissed_count: number;
  channels: { id: number; name: string }[];
}

/* ---------- capsule config ---------- */
const CAPSULES = [
  { key: 'ev', label: '🔋 EV', color: 'bg-green-50 text-green-700 border-green-200 hover:bg-green-100' },
  { key: 'hybrid', label: '⚡ Hybrid', color: 'bg-yellow-50 text-yellow-700 border-yellow-200 hover:bg-yellow-100' },
  { key: 'suv', label: '🏎️ SUV', color: 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100' },
  { key: 'sedan', label: '🚗 Sedan', color: 'bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100' },
  { key: 'review', label: '📏 Review', color: 'bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100' },
  { key: 'walkaround', label: '👀 Walk-around', color: 'bg-pink-50 text-pink-700 border-pink-200 hover:bg-pink-100' },
  { key: 'price', label: '💰 Price', color: 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100' },
];

const SORT_OPTIONS = [
  { value: '-published_at', label: 'Newest' },
  { value: '-view_count', label: 'Most Viewed' },
  { value: '-duration_seconds', label: 'Longest' },
  { value: 'published_at', label: 'Oldest' },
];

/* ---------- helpers ---------- */
function formatViews(n: number | null): string {
  if (!n) return '—';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const h = diff / 3600000;
  if (h < 1) return 'Just now';
  if (h < 24) return `${Math.floor(h)}h ago`;
  const d = h / 24;
  if (d < 7) return `${Math.floor(d)}d ago`;
  if (d < 30) return `${Math.floor(d / 7)}w ago`;
  return `${Math.floor(d / 30)}mo ago`;
}

/* Article status badge component */
function ArticleBadge({ v }: { v: VideoCandidate }) {
  if (v.has_article) {
    const cfg = {
      published: { bg: 'bg-green-50 border-green-200 text-green-700', icon: <Check size={12} />, label: 'Published' },
      pending:   { bg: 'bg-amber-50 border-amber-200 text-amber-700', icon: <FileText size={12} />, label: 'Pending' },
      draft:     { bg: 'bg-blue-50 border-blue-200 text-blue-700', icon: <FileText size={12} />, label: 'Draft' },
    }[v.article_status || 'pending'];

    const inner = (
      <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${cfg.bg}`}>
        {cfg.icon} {cfg.label}
      </div>
    );

    if (v.article_slug) {
      return <Link href={`/admin/articles/${v.article_slug}/edit`}>{inner}</Link>;
    }
    return inner;
  }
  if (v.similar_articles_count > 0) {
    return (
      <div className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border bg-orange-50 border-orange-200 text-orange-600" title={`${v.similar_articles_count} similar article(s) found`}>
        ⚠️ {v.similar_articles_count} similar
      </div>
    );
  }
  return null;
}

/* ---------- component ---------- */
export default function VideoInboxPage() {
  const [videos, setVideos] = useState<VideoCandidate[]>([]);
  const [stats, setStats] = useState<InboxStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState('');

  // Filters
  const [search, setSearch] = useState('');
  const [activeCapsule, setActiveCapsule] = useState('');
  const [channelFilter, setChannelFilter] = useState('');
  const [ordering, setOrdering] = useState('-published_at');
  const [statusFilter, setStatusFilter] = useState('new');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Selection
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [approvingIds, setApprovingIds] = useState<Set<number>>(new Set());

  // Generation tracking: id -> { taskId, status, message, pendingId }
  const [genStatus, setGenStatus] = useState<Record<number, { taskId: string; status: 'running' | 'done' | 'error'; message?: string; pendingId?: number }>>({});
  const pollingRef = useRef<Record<string, NodeJS.Timeout>>({});

  // Pagination
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = 24;

  // Cleanup polling intervals on unmount
  useEffect(() => {
    const intervals = pollingRef.current;
    return () => {
      Object.values(intervals).forEach(clearInterval);
    };
  }, []);

  /* ---------- fetch ---------- */
  const fetchVideos = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {
        status: statusFilter,
        ordering,
        page: page.toString(),
        page_size: pageSize.toString(),
      };
      if (search) params.search = search;
      if (activeCapsule) params.capsule = activeCapsule;
      if (channelFilter) params.channel_id = channelFilter;

      const res = await api.get('/video-inbox/', { params });
      setVideos(res.data.results || []);
      setTotalCount(res.data.count || 0);
    } catch (err) {
      logCaughtError('video_inbox_fetch', err);
    } finally {
      setLoading(false);
    }
  }, [search, activeCapsule, channelFilter, ordering, statusFilter, page]);

  const fetchStats = useCallback(async () => {
    try {
      const res = await api.get('/video-inbox/stats/');
      setStats(res.data);
    } catch (err) {
      logCaughtError('video_inbox_stats', err);
    }
  }, []);

  useEffect(() => { fetchStats(); }, [fetchStats]);
  useEffect(() => { fetchVideos(); }, [fetchVideos]);

  // Auto-resume polling for videos that are currently generating (persisted state)
  useEffect(() => {
    videos.forEach(v => {
      if (v.status === 'generating' && v.generation_task_id && !genStatus[v.id]) {
        // Resume polling for this video
        setGenStatus(prev => ({ ...prev, [v.id]: { taskId: v.generation_task_id, status: 'running' } }));
        const taskId = v.generation_task_id;
        const interval = setInterval(async () => {
          try {
            const poll = await api.get(`/video-inbox/generate_status/?task_id=${taskId}`);
            const s = poll.data.status;
            if (s === 'done') {
              clearInterval(interval);
              delete pollingRef.current[taskId];
              const pId = poll.data.result?.pending_id;
              setGenStatus(prev => ({ ...prev, [v.id]: { taskId, status: 'done', message: 'Article created!', pendingId: pId } }));
              fetchStats();
              fetchVideos();
            } else if (s === 'error') {
              clearInterval(interval);
              delete pollingRef.current[taskId];
              setGenStatus(prev => ({ ...prev, [v.id]: { taskId, status: 'error', message: poll.data.error || 'Generation failed' } }));
            } else if (s === 'not_found') {
              // Task expired from cache — check if model has error
              clearInterval(interval);
              delete pollingRef.current[taskId];
              // Will be picked up by next fetchVideos() which returns updated model state
              fetchVideos();
            }
          } catch {
            // poll failed, keep trying
          }
        }, 3000);
        pollingRef.current[taskId] = interval;
      }
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videos.length]); // Only re-run when video list changes
  // Reset page when filters change
  useEffect(() => { setPage(1); }, [search, activeCapsule, channelFilter, ordering, statusFilter]);

  /* ---------- actions ---------- */
  const handleScanAll = async () => {
    setScanning(true);
    setScanMessage('');
    try {
      const res = await api.post('/video-inbox/scan_channels/');
      setScanMessage(res.data.message || 'Scan complete');
      fetchVideos();
      fetchStats();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Scan failed';
      setScanMessage(`❌ ${msg}`);
    } finally {
      setScanning(false);
    }
  };

  const handleApprove = async (id: number) => {
    setApprovingIds(prev => new Set(prev).add(id));
    try {
      await api.post(`/video-inbox/${id}/approve/`);
      // Remove from local state immediately for responsiveness
      setVideos(prev => prev.filter(v => v.id !== id));
      setTotalCount(prev => prev - 1);
      // Re-fetch stats AND videos to stay in sync with the server
      await Promise.all([fetchStats(), fetchVideos()]);
    } catch (err) {
      logCaughtError('video_inbox_approve', err);
    } finally {
      setApprovingIds(prev => { const s = new Set(prev); s.delete(id); return s; });
    }
  };

  const handleDismiss = async (id: number) => {
    try {
      await api.post(`/video-inbox/${id}/dismiss/`);
      setVideos(prev => prev.filter(v => v.id !== id));
      setTotalCount(prev => prev - 1);
      fetchStats();
    } catch (err) {
      logCaughtError('video_inbox_dismiss', err);
    }
  };

  const handleGenerate = async (id: number) => {
    try {
      const res = await api.post(`/video-inbox/${id}/generate/`);
      const taskId = res.data.task_id;
      setGenStatus(prev => ({ ...prev, [id]: { taskId, status: 'running' } }));

      // Poll for status every 3 seconds
      const interval = setInterval(async () => {
        try {
          const poll = await api.get(`/video-inbox/generate_status/?task_id=${taskId}`);
          const s = poll.data.status;
          if (s === 'done') {
            clearInterval(interval);
            delete pollingRef.current[taskId];
            const pId = poll.data.result?.pending_id;
            setGenStatus(prev => ({ ...prev, [id]: { taskId, status: 'done', message: 'Article created!', pendingId: pId } }));
            fetchStats();
            fetchVideos();
          } else if (s === 'error') {
            clearInterval(interval);
            delete pollingRef.current[taskId];
            setGenStatus(prev => ({ ...prev, [id]: { taskId, status: 'error', message: poll.data.error || 'Generation failed' } }));
          }
          // status 'running' -> keep polling
        } catch {
          // poll failed, keep trying
        }
      }, 3000);
      pollingRef.current[taskId] = interval;
    } catch (err) {
      logCaughtError('video_inbox_generate', err);
      setGenStatus(prev => ({ ...prev, [id]: { taskId: '', status: 'error', message: 'Failed to start generation' } }));
    }
  };

  const handleBulkApprove = async () => {
    if (selected.size === 0) return;
    if (!confirm(`Approve ${selected.size} videos?`)) return;
    const ids = Array.from(selected);
    setApprovingIds(new Set(ids));
    try {
      await api.post('/video-inbox/bulk_approve/', { ids });
      setVideos(prev => prev.filter(v => !selected.has(v.id)));
      setTotalCount(prev => prev - ids.length);
      setSelected(new Set());
      fetchStats();
    } catch (err) {
      logCaughtError('video_inbox_bulk_approve', err);
    } finally {
      setApprovingIds(new Set());
    }
  };

  const handleBulkDismiss = async () => {
    if (selected.size === 0) return;
    if (!confirm(`Dismiss ${selected.size} videos?`)) return;
    const ids = Array.from(selected);
    try {
      await api.post('/video-inbox/bulk_dismiss/', { ids });
      setVideos(prev => prev.filter(v => !selected.has(v.id)));
      setTotalCount(prev => prev - ids.length);
      setSelected(new Set());
      fetchStats();
    } catch (err) {
      logCaughtError('video_inbox_bulk_dismiss', err);
    }
  };

  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const s = new Set(prev);
      if (s.has(id)) s.delete(id);
      else s.add(id);
      return s;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === videos.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(videos.map(v => v.id)));
    }
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  /* ---------- render ---------- */
  return (
    <div className="p-4 sm:p-6 lg:p-10 max-w-[1400px] mx-auto min-h-screen bg-gray-50 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-gray-950 flex items-center gap-3">
            📥 Video Inbox
            {stats && stats.new_count > 0 && (
              <span className="px-3 py-1 text-sm font-bold bg-red-500 text-white rounded-full">
                {stats.new_count}
              </span>
            )}
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Review discovered videos and cherry-pick which ones become articles
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/admin/youtube-channels"
            className="px-4 py-2.5 border border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 font-medium text-sm"
          >
            ← Channels
          </Link>
          <button
            onClick={handleScanAll}
            disabled={scanning}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl hover:from-purple-700 hover:to-indigo-700 transition-all font-bold text-sm shadow-lg disabled:opacity-50"
          >
            {scanning ? <Loader2 size={18} className="animate-spin" /> : <RefreshCw size={18} />}
            Scan All Channels
          </button>
        </div>
      </div>

      {/* Scan message */}
      {scanMessage && (
        <div className={`p-3 rounded-xl text-sm font-medium ${scanMessage.startsWith('❌') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
          {scanMessage}
        </div>
      )}

      {/* Status tabs */}
      <div className="flex gap-2 bg-white p-1.5 rounded-xl shadow-sm border border-gray-100">
        {[
          { key: 'new', label: 'New', count: stats?.new_count },
          { key: 'approved', label: 'Approved', count: stats?.approved_count },
          { key: 'dismissed', label: 'Dismissed', count: stats?.dismissed_count },
          { key: 'all', label: 'All' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setStatusFilter(tab.key)}
            className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-bold transition-all ${
              statusFilter === tab.key
                ? 'bg-purple-600 text-white shadow-md'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            {tab.label}
            {tab.count != null && tab.count > 0 && (
              <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
                statusFilter === tab.key ? 'bg-white/20' : 'bg-gray-100'
              }`}>{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Filter bar */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 space-y-3">
        <div className="flex flex-wrap gap-3">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search by title..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900"
            />
          </div>

          {/* Channel filter */}
          <select
            value={channelFilter}
            onChange={e => setChannelFilter(e.target.value)}
            className="px-4 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-700 bg-white focus:ring-2 focus:ring-purple-500 min-w-[160px]"
          >
            <option value="">All Channels</option>
            {stats?.channels.map(ch => (
              <option key={ch.id} value={ch.id}>{ch.name}</option>
            ))}
          </select>

          {/* Sort */}
          <select
            value={ordering}
            onChange={e => setOrdering(e.target.value)}
            className="px-4 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-700 bg-white focus:ring-2 focus:ring-purple-500 min-w-[140px]"
          >
            {SORT_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          {/* View toggle */}
          <div className="flex border border-gray-200 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2.5 ${viewMode === 'grid' ? 'bg-purple-100 text-purple-700' : 'text-gray-400 hover:bg-gray-50'}`}
            >
              <LayoutGrid size={18} />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2.5 ${viewMode === 'list' ? 'bg-purple-100 text-purple-700' : 'text-gray-400 hover:bg-gray-50'}`}
            >
              <List size={18} />
            </button>
          </div>
        </div>

        {/* Capsule filters */}
        <div className="flex flex-wrap gap-2">
          {CAPSULES.map(c => (
            <button
              key={c.key}
              onClick={() => setActiveCapsule(activeCapsule === c.key ? '' : c.key)}
              className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all ${
                activeCapsule === c.key
                  ? 'ring-2 ring-purple-400 ring-offset-1 ' + c.color
                  : c.color
              }`}
            >
              {c.label}
            </button>
          ))}
          {activeCapsule && (
            <button
              onClick={() => setActiveCapsule('')}
              className="px-3 py-1.5 rounded-full text-xs font-medium text-gray-500 hover:text-gray-700 border border-gray-200"
            >
              ✕ Clear filter
            </button>
          )}
        </div>
      </div>

      {/* Bulk action bar */}
      {selected.size > 0 && (
        <div className="sticky top-0 z-20 bg-purple-600 text-white rounded-xl p-4 flex items-center justify-between shadow-lg">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={selected.size === videos.length}
              onChange={toggleSelectAll}
              className="w-5 h-5 rounded"
            />
            <span className="font-bold">{selected.size} selected</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleBulkApprove}
              className="flex items-center gap-2 px-4 py-2 bg-white text-purple-700 rounded-lg font-bold text-sm hover:bg-gray-100"
            >
              <Check size={16} />
              Approve {selected.size}
            </button>
            <button
              onClick={handleBulkDismiss}
              className="flex items-center gap-2 px-4 py-2 bg-white/20 text-white rounded-lg font-bold text-sm hover:bg-white/30"
            >
              <Trash2 size={16} />
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="animate-spin text-purple-600" size={48} />
        </div>
      ) : videos.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-2xl shadow-sm border border-gray-100">
          <div className="text-6xl mb-4">📭</div>
          <h2 className="text-xl font-bold text-gray-800 mb-2">No videos found</h2>
          <p className="text-gray-500 mb-6">
            {statusFilter === 'new'
              ? 'Click "Scan All Channels" to discover new videos'
              : 'No videos match your current filters'}
          </p>
          {statusFilter === 'new' && (
            <button
              onClick={handleScanAll}
              disabled={scanning}
              className="px-6 py-3 bg-purple-600 text-white rounded-xl font-bold hover:bg-purple-700"
            >
              Scan Now
            </button>
          )}
        </div>
      ) : viewMode === 'grid' ? (
        /* ============ GRID VIEW ============ */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
          {videos.map(v => (
            <div
              key={v.id}
              className={`bg-white rounded-xl shadow-sm border overflow-hidden transition-all hover:shadow-md group ${
                selected.has(v.id) ? 'ring-2 ring-purple-500 border-purple-300' : 'border-gray-100'
              }`}
            >
              {/* Thumbnail */}
              <div className="relative">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={v.thumbnail_url || `https://i.ytimg.com/vi/${v.video_id}/hqdefault.jpg`}
                  alt={v.title}
                  className="w-full aspect-video object-cover"
                />
                {/* Duration badge */}
                {v.duration_display && (
                  <span className="absolute bottom-2 right-2 bg-black/80 text-white text-xs font-bold px-2 py-0.5 rounded">
                    {v.duration_display}
                  </span>
                )}
                {/* Article status badge in top-right */}
                <div className="absolute top-2 right-2">
                  <ArticleBadge v={v} />
                </div>
                {/* Checkbox */}
                <div className="absolute top-2 left-2">
                  <input
                    type="checkbox"
                    checked={selected.has(v.id)}
                    onChange={() => toggleSelect(v.id)}
                    className="w-5 h-5 rounded border-2 border-white shadow-lg cursor-pointer"
                  />
                </div>
              </div>

              {/* Info */}
              <div className="p-3">
                <h3 className="font-bold text-gray-900 text-sm line-clamp-2 leading-snug mb-2">
                  {v.title}
                </h3>
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span className="font-medium text-purple-600 truncate max-w-[60%]">{v.channel_name}</span>
                  <span>{timeAgo(v.published_at)}</span>
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                  {v.view_count != null && (
                    <span className="flex items-center gap-1">
                      <Eye size={12} /> {formatViews(v.view_count)}
                    </span>
                  )}
                  {v.similar_articles_count > 0 && !v.has_article && (
                    <span className="text-orange-500 font-medium">
                      {v.similar_articles_count} similar
                    </span>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-2 mt-3">
                  {v.has_article ? (
                    <div className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-gray-100 text-gray-500 rounded-lg text-xs font-bold">
                      <Check size={14} />
                      Already processed
                    </div>
                  ) : v.status === 'generating' || genStatus[v.id]?.status === 'running' ? (
                    <div className="flex-1 flex items-center justify-center gap-2 py-2 bg-amber-50 text-amber-700 border border-amber-200 rounded-lg text-xs font-bold animate-pulse">
                      <Loader2 size={14} className="animate-spin" />
                      Generating...
                    </div>
                  ) : genStatus[v.id]?.status === 'done' ? (
                    <Link
                      href={genStatus[v.id]?.pendingId ? `/admin/youtube-channels/pending?highlight=${genStatus[v.id]?.pendingId}` : '/admin/youtube-channels/pending'}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-green-50 text-green-600 border border-green-200 rounded-lg text-xs font-bold hover:bg-green-100 transition-colors"
                    >
                      <Edit size={14} />
                      Review & Edit
                      <ExternalLink size={12} />
                    </Link>
                  ) : (v.status === 'approved' && v.generation_error) || genStatus[v.id]?.status === 'error' ? (
                    <button
                      onClick={() => handleGenerate(v.id)}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-red-50 text-red-600 border border-red-200 rounded-lg text-xs font-bold hover:bg-red-100"
                      title={v.generation_error || genStatus[v.id]?.message}
                    >
                      <X size={14} />
                      Failed — Retry
                    </button>
                  ) : v.status === 'approved' ? (
                    <button
                      onClick={() => handleGenerate(v.id)}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-lg text-xs font-bold hover:from-amber-600 hover:to-orange-600 shadow-sm"
                    >
                      <Wand2 size={14} />
                      Generate Article
                    </button>
                  ) : (
                    <button
                      onClick={() => handleApprove(v.id)}
                      disabled={approvingIds.has(v.id)}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg text-xs font-bold hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 shadow-sm"
                    >
                      {approvingIds.has(v.id) ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                      Approve
                    </button>
                  )}
                  <button
                    onClick={() => handleDismiss(v.id)}
                    className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    title="Dismiss"
                  >
                    <X size={16} />
                  </button>
                  <a
                    href={v.video_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    title="Watch on YouTube"
                  >
                    <Youtube size={16} />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* ============ LIST VIEW ============ */
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="w-10 py-3 px-4">
                  <input
                    type="checkbox"
                    checked={selected.size === videos.length && videos.length > 0}
                    onChange={toggleSelectAll}
                    className="w-4 h-4 rounded"
                  />
                </th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase">Video</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase">Channel</th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase">Duration</th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase">Views</th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase">Published</th>
                <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {videos.map(v => (
                <tr key={v.id} className={`hover:bg-gray-50 transition-colors ${selected.has(v.id) ? 'bg-purple-50' : ''}`}>
                  <td className="py-3 px-4">
                    <input
                      type="checkbox"
                      checked={selected.has(v.id)}
                      onChange={() => toggleSelect(v.id)}
                      className="w-4 h-4 rounded"
                    />
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-3">
                      <div className="w-[120px] flex-shrink-0 relative">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={v.thumbnail_url || `https://i.ytimg.com/vi/${v.video_id}/hqdefault.jpg`}
                          alt=""
                          className="w-full h-[68px] object-cover rounded-lg"
                        />
                        {v.duration_display && (
                          <span className="absolute bottom-1 right-1 bg-black/80 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">
                            {v.duration_display}
                          </span>
                        )}
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-bold text-gray-900 text-sm line-clamp-2">{v.title}</h3>
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-sm text-purple-600 font-medium whitespace-nowrap">{v.channel_name}</td>
                  <td className="py-3 px-4 text-center text-sm text-gray-600">{v.duration_display || '—'}</td>
                  <td className="py-3 px-4 text-center text-sm text-gray-600">{formatViews(v.view_count)}</td>
                  <td className="py-3 px-4 text-center">
                    <ArticleBadge v={v} />
                    {v.similar_articles_count > 0 && !v.has_article && (
                      <div className="text-[10px] text-orange-500 font-bold mt-1">
                        {v.similar_articles_count} similar
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4 text-center text-sm text-gray-500">{timeAgo(v.published_at)}</td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {v.has_article ? (
                        <span className="px-3 py-1.5 bg-gray-100 text-gray-500 rounded-lg text-xs font-bold">Done</span>
                      ) : v.status === 'generating' || genStatus[v.id]?.status === 'running' ? (
                        <span className="px-3 py-1.5 bg-amber-50 text-amber-700 border border-amber-200 rounded-lg text-xs font-bold animate-pulse flex items-center gap-1">
                          <Loader2 size={12} className="animate-spin" /> Generating...
                        </span>
                      ) : genStatus[v.id]?.status === 'done' ? (
                        <Link
                          href={genStatus[v.id]?.pendingId ? `/admin/youtube-channels/pending?highlight=${genStatus[v.id]?.pendingId}` : '/admin/youtube-channels/pending'}
                          className="px-3 py-1.5 bg-green-50 text-green-600 border border-green-200 rounded-lg text-xs font-bold flex items-center gap-1 hover:bg-green-100 transition-colors"
                        >
                          <Edit size={12} /> Review & Edit <ExternalLink size={10} />
                        </Link>
                      ) : (v.status === 'approved' && v.generation_error) ? (
                        <button
                          onClick={() => handleGenerate(v.id)}
                          className="px-3 py-1.5 bg-red-50 text-red-600 border border-red-200 rounded-lg text-xs font-bold hover:bg-red-100 flex items-center gap-1"
                          title={v.generation_error}
                        >
                          <X size={12} /> Retry
                        </button>
                      ) : v.status === 'approved' ? (
                        <button
                          onClick={() => handleGenerate(v.id)}
                          className="px-3 py-1.5 bg-amber-500 text-white rounded-lg text-xs font-bold hover:bg-amber-600 flex items-center gap-1"
                        >
                          <Wand2 size={12} /> Generate
                        </button>
                      ) : (
                        <button
                          onClick={() => handleApprove(v.id)}
                          disabled={approvingIds.has(v.id)}
                          className="px-3 py-1.5 bg-purple-600 text-white rounded-lg text-xs font-bold hover:bg-purple-700 disabled:opacity-50"
                        >
                          {approvingIds.has(v.id) ? <Loader2 size={12} className="animate-spin" /> : 'Approve'}
                        </button>
                      )}
                      <button
                        onClick={() => handleDismiss(v.id)}
                        className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg"
                        title="Dismiss"
                      >
                        <X size={16} />
                      </button>
                      <a
                        href={v.video_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1.5 text-gray-400 hover:text-red-600 rounded-lg"
                      >
                        <Youtube size={16} />
                      </a>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium disabled:opacity-30 hover:bg-gray-50"
          >
            ← Prev
          </button>
          <span className="text-sm text-gray-600">
            Page {page} of {totalPages} ({totalCount} videos)
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium disabled:opacity-30 hover:bg-gray-50"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
