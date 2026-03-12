'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import toast from 'react-hot-toast';
import {
  Timer, Clock, Calendar, Trash2, ExternalLink, Loader2,
  ArrowUp, ArrowDown, Play, Send, GripVertical, CheckCircle2,
} from 'lucide-react';

interface QueueArticle {
  id: number;
  title: string;
  slug: string;
  image: string;
  summary: string;
  categories: { id: number; name: string; slug: string }[];
  scheduled_publish_at: string | null;
  created_at: string;
  is_published: boolean;
}

interface QueueStats {
  total_drafts: number;
  scheduled: number;
  unscheduled: number;
  publishing_today: number;
}

function formatCountdown(targetDate: string): string {
  const diff = new Date(targetDate).getTime() - Date.now();
  if (diff <= 0) return '⏱ Publishing...';
  const hours = Math.floor(diff / 3600000);
  const mins = Math.floor((diff % 3600000) / 60000);
  if (hours > 24) {
    const days = Math.floor(hours / 24);
    return `${days}d ${hours % 24}h`;
  }
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

function formatScheduledTime(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  const timeStr = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });

  if (d.toDateString() === today.toDateString()) return `Today ${timeStr}`;
  if (d.toDateString() === tomorrow.toDateString()) return `Tomorrow ${timeStr}`;
  return `${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} ${timeStr}`;
}

export default function PublishQueuePage() {
  const router = useRouter();
  const [articles, setArticles] = useState<QueueArticle[]>([]);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [scheduling, setScheduling] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // Batch schedule form
  const [intervalHours, setIntervalHours] = useState(3);
  const [startTimeOffset, setStartTimeOffset] = useState(1); // hours from now

  // Live countdown ticker
  const [, setTick] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setTick(t => t + 1), 30_000); // refresh every 30s
    return () => clearInterval(timer);
  }, []);

  const fetchQueue = useCallback(async () => {
    try {
      const { data } = await api.get('/articles/publish_queue/');
      setArticles(data.articles || []);
      setStats(data.stats || null);
    } catch (err) {
      toast.error('Failed to load publish queue');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchQueue(); }, [fetchQueue]);

  const toggleSelect = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const selectAllUnscheduled = () => {
    const unsched = articles.filter(a => !a.scheduled_publish_at).map(a => a.id);
    setSelectedIds(new Set(unsched));
  };

  const handleBatchSchedule = async () => {
    if (selectedIds.size === 0) {
      toast.error('Select articles to schedule');
      return;
    }
    setScheduling(true);

    const startTime = new Date(Date.now() + startTimeOffset * 3600000).toISOString();
    const articleIds = articles
      .filter(a => selectedIds.has(a.id))
      .map(a => a.id);

    try {
      const { data } = await api.post('/articles/batch_schedule/', {
        article_ids: articleIds,
        start_time: startTime,
        interval_hours: intervalHours,
      });
      toast.success(`✅ Scheduled ${data.scheduled_count} articles`);
      setSelectedIds(new Set());
      fetchQueue();
    } catch {
      toast.error('Batch schedule failed');
    } finally {
      setScheduling(false);
    }
  };

  const handleClearSchedule = async (articleId: number) => {
    try {
      await api.patch(`/articles/${articleId}/`, { scheduled_publish_at: null });
      toast.success('Schedule cleared');
      fetchQueue();
    } catch {
      toast.error('Failed to clear schedule');
    }
  };

  const handlePublishNow = async (articleId: number) => {
    try {
      await api.patch(`/articles/${articleId}/`, { is_published: true, scheduled_publish_at: null });
      toast.success('Published!');
      fetchQueue();
    } catch {
      toast.error('Publish failed');
    }
  };

  const handleMoveSchedule = async (articleId: number, direction: 'earlier' | 'later') => {
    const article = articles.find(a => a.id === articleId);
    if (!article?.scheduled_publish_at) return;
    const current = new Date(article.scheduled_publish_at);
    const delta = direction === 'earlier' ? -intervalHours * 3600000 : intervalHours * 3600000;
    const newTime = new Date(current.getTime() + delta);
    if (newTime.getTime() < Date.now()) {
      toast.error('Cannot schedule in the past');
      return;
    }
    try {
      await api.patch(`/articles/${articleId}/`, { scheduled_publish_at: newTime.toISOString() });
      fetchQueue();
    } catch {
      toast.error('Failed to update schedule');
    }
  };

  const scheduledArticles = articles.filter(a => a.scheduled_publish_at);
  const unscheduledArticles = articles.filter(a => !a.scheduled_publish_at);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-indigo-600" size={32} />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl shadow-lg">
            <Timer size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-black text-gray-900">Publish Queue</h1>
            <p className="text-sm text-gray-500">Schedule and manage article publishing</p>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl font-black text-gray-900">{stats.total_drafts}</div>
            <div className="text-xs text-gray-500 font-medium">Total Drafts</div>
          </div>
          <div className="bg-white rounded-xl border border-emerald-200 p-4">
            <div className="text-2xl font-black text-emerald-600">{stats.scheduled}</div>
            <div className="text-xs text-gray-500 font-medium">Scheduled</div>
          </div>
          <div className="bg-white rounded-xl border border-amber-200 p-4">
            <div className="text-2xl font-black text-amber-600">{stats.unscheduled}</div>
            <div className="text-xs text-gray-500 font-medium">Unscheduled</div>
          </div>
          <div className="bg-white rounded-xl border border-blue-200 p-4">
            <div className="text-2xl font-black text-blue-600">{stats.publishing_today}</div>
            <div className="text-xs text-gray-500 font-medium">Publishing Today</div>
          </div>
        </div>
      )}

      {/* Batch Scheduler */}
      <div className="bg-gradient-to-r from-indigo-50 to-violet-50 rounded-2xl border border-indigo-100 p-5">
        <h2 className="text-sm font-bold text-indigo-900 mb-3 flex items-center gap-2">
          <Calendar size={16} /> Batch Scheduler
        </h2>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Start In</label>
            <select
              value={startTimeOffset}
              onChange={e => setStartTimeOffset(Number(e.target.value))}
              className="px-3 py-2 rounded-lg border border-indigo-200 bg-white text-sm font-semibold text-gray-900 focus:ring-2 focus:ring-indigo-400 focus:outline-none"
            >
              <option value={0.5}>30 min</option>
              <option value={1}>1 hour</option>
              <option value={2}>2 hours</option>
              <option value={3}>3 hours</option>
              <option value={6}>6 hours</option>
              <option value={12}>12 hours</option>
              <option value={24}>Tomorrow</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Interval</label>
            <select
              value={intervalHours}
              onChange={e => setIntervalHours(Number(e.target.value))}
              className="px-3 py-2 rounded-lg border border-indigo-200 bg-white text-sm font-semibold text-gray-900 focus:ring-2 focus:ring-indigo-400 focus:outline-none"
            >
              <option value={1}>Every 1h</option>
              <option value={2}>Every 2h</option>
              <option value={3}>Every 3h</option>
              <option value={4}>Every 4h</option>
              <option value={6}>Every 6h</option>
              <option value={8}>Every 8h</option>
              <option value={12}>Every 12h</option>
              <option value={24}>Every 24h</option>
            </select>
          </div>
          <div className="flex gap-2">
            <button
              onClick={selectAllUnscheduled}
              className="px-3 py-2 text-xs font-bold text-indigo-600 bg-white border border-indigo-200 rounded-lg hover:bg-indigo-50 transition-colors"
            >
              Select All ({unscheduledArticles.length})
            </button>
            <button
              onClick={handleBatchSchedule}
              disabled={scheduling || selectedIds.size === 0}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-lg text-sm font-bold hover:from-indigo-700 hover:to-violet-700 disabled:opacity-50 transition-all shadow-md"
            >
              {scheduling ? (
                <><Loader2 className="animate-spin" size={14} /> Scheduling...</>
              ) : (
                <><Send size={14} /> Schedule {selectedIds.size > 0 ? `(${selectedIds.size})` : 'Selected'}</>
              )}
            </button>
          </div>
        </div>
        {selectedIds.size > 0 && (
          <p className="mt-2 text-xs text-indigo-600">
            📅 {selectedIds.size} articles will be published starting in {startTimeOffset}h, every {intervalHours}h
            (last one at ~{new Date(Date.now() + (startTimeOffset + intervalHours * (selectedIds.size - 1)) * 3600000).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })})
          </p>
        )}
      </div>

      {/* Scheduled Timeline */}
      {scheduledArticles.length > 0 && (
        <div>
          <h2 className="text-sm font-bold text-gray-700 mb-3 flex items-center gap-2">
            <Clock size={16} className="text-emerald-500" /> Scheduled ({scheduledArticles.length})
          </h2>
          <div className="space-y-2">
            {scheduledArticles
              .sort((a, b) => new Date(a.scheduled_publish_at!).getTime() - new Date(b.scheduled_publish_at!).getTime())
              .map((article, idx) => (
              <div
                key={article.id}
                className="bg-white rounded-xl border border-emerald-100 p-4 flex items-center gap-4 hover:shadow-md transition-shadow group"
              >
                {/* Timeline dot */}
                <div className="flex flex-col items-center gap-1">
                  <div className="w-3 h-3 rounded-full bg-emerald-500 ring-4 ring-emerald-100" />
                  {idx < scheduledArticles.length - 1 && <div className="w-0.5 h-6 bg-emerald-200" />}
                </div>

                {/* Image */}
                {article.image ? (
                  <img src={article.image} alt="" className="w-12 h-12 rounded-lg object-cover flex-shrink-0" />
                ) : (
                  <div className="w-12 h-12 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
                    <Timer size={16} className="text-gray-400" />
                  </div>
                )}

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-bold text-gray-900 truncate">{article.title}</h3>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs font-semibold text-emerald-600">
                      {formatScheduledTime(article.scheduled_publish_at!)}
                    </span>
                    <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                      ⏱ {formatCountdown(article.scheduled_publish_at!)}
                    </span>
                    {article.categories.length > 0 && (
                      <span className="text-xs text-gray-400">{article.categories[0].name}</span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleMoveSchedule(article.id, 'earlier')}
                    className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                    title={`Move ${intervalHours}h earlier`}
                  >
                    <ArrowUp size={14} />
                  </button>
                  <button
                    onClick={() => handleMoveSchedule(article.id, 'later')}
                    className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                    title={`Move ${intervalHours}h later`}
                  >
                    <ArrowDown size={14} />
                  </button>
                  <button
                    onClick={() => handlePublishNow(article.id)}
                    className="p-1.5 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                    title="Publish now"
                  >
                    <Play size={14} />
                  </button>
                  <button
                    onClick={() => handleClearSchedule(article.id)}
                    className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    title="Remove from schedule"
                  >
                    <Trash2 size={14} />
                  </button>
                  <button
                    onClick={() => router.push(`/admin/articles/${article.id}/edit`)}
                    className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    title="Edit article"
                  >
                    <ExternalLink size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Unscheduled Drafts */}
      {unscheduledArticles.length > 0 && (
        <div>
          <h2 className="text-sm font-bold text-gray-700 mb-3 flex items-center gap-2">
            <GripVertical size={16} className="text-amber-500" /> Unscheduled Drafts ({unscheduledArticles.length})
          </h2>
          <div className="space-y-2">
            {unscheduledArticles.map(article => (
              <div
                key={article.id}
                className={`bg-white rounded-xl border p-4 flex items-center gap-4 hover:shadow-md transition-all cursor-pointer ${
                  selectedIds.has(article.id) ? 'border-indigo-400 ring-2 ring-indigo-100' : 'border-gray-200'
                }`}
                onClick={() => toggleSelect(article.id)}
              >
                {/* Checkbox */}
                <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                  selectedIds.has(article.id) ? 'bg-indigo-600 border-indigo-600' : 'border-gray-300'
                }`}>
                  {selectedIds.has(article.id) && <CheckCircle2 size={14} className="text-white" />}
                </div>

                {/* Image */}
                {article.image ? (
                  <img src={article.image} alt="" className="w-12 h-12 rounded-lg object-cover flex-shrink-0" />
                ) : (
                  <div className="w-12 h-12 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
                    <Timer size={16} className="text-gray-400" />
                  </div>
                )}

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-bold text-gray-900 truncate">{article.title}</h3>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-gray-400">
                      Created {new Date(article.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    </span>
                    {article.categories.length > 0 && (
                      <span className="text-xs text-gray-400">{article.categories[0].name}</span>
                    )}
                  </div>
                </div>

                {/* Quick actions */}
                <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                  <button
                    onClick={() => handlePublishNow(article.id)}
                    className="p-1.5 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                    title="Publish now"
                  >
                    <Play size={14} />
                  </button>
                  <button
                    onClick={() => router.push(`/admin/articles/${article.id}/edit`)}
                    className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    title="Edit article"
                  >
                    <ExternalLink size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {articles.length === 0 && (
        <div className="text-center py-16">
          <Timer size={48} className="mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-bold text-gray-500">No drafts in queue</h3>
          <p className="text-sm text-gray-400 mt-1">Generate articles from RSS or approve pending articles to fill the queue</p>
        </div>
      )}
    </div>
  );
}
