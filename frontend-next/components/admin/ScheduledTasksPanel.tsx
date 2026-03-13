'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Clock, RefreshCw, Zap, Hand, CheckCircle2, XCircle, Loader2 } from 'lucide-react';

interface ScheduledTask {
  name: string;
  task_id: string;
  schedule: string;
  schedule_detail: string;
  next_run: string | null;
  last_run: string | null;
  last_status: string;
  type: 'automated' | 'manual';
  enabled?: boolean;
  icon: string;
}

function timeUntil(iso: string): string {
  const diff = new Date(iso).getTime() - Date.now();
  if (diff <= 0) return 'Running...';
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '< 1m';
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  const remainMins = mins % 60;
  if (hours < 24) return `${hours}h ${remainMins}m`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}

function formatLastRun(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function ScheduledTasksPanel() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchTasks = async () => {
    try {
      const { data } = await api.get('/admin/scheduled-tasks/');
      setTasks(data.tasks || []);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 60000); // refresh every 60s
    return () => clearInterval(interval);
  }, []);

  // Live countdown ticker
  const [, setTick] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setTick(t => t + 1), 30000);
    return () => clearInterval(timer);
  }, []);

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="animate-spin text-indigo-500" size={24} />
        </div>
      </div>
    );
  }

  if (error) return null;

  const automated = tasks.filter(t => t.type === 'automated');
  const manual = tasks.filter(t => t.type === 'manual');

  return (
    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 bg-gradient-to-r from-slate-50 to-gray-50 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-lg">
            <Clock size={16} className="text-white" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-gray-900">Background Tasks</h2>
            <p className="text-[11px] text-gray-500">
              {automated.length} automated · {manual.length} manual
            </p>
          </div>
        </div>
        <button
          onClick={() => { setLoading(true); fetchTasks(); }}
          className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
          title="Refresh"
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Automated Tasks */}
      <div className="divide-y divide-gray-50">
        {automated.map(task => (
          <div key={task.task_id} className="px-5 py-3 flex items-center gap-3 hover:bg-gray-50/50 transition-colors">
            {/* Icon */}
            <span className="text-lg flex-shrink-0 w-7 text-center">{task.icon}</span>

            {/* Name + schedule */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-gray-900">{task.name}</span>
                {task.enabled === false && (
                  <span className="text-[10px] font-bold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded-full">
                    DISABLED
                  </span>
                )}
              </div>
              <div className="text-[11px] text-gray-400 truncate">{task.last_status}</div>
            </div>

            {/* Schedule + next run */}
            <div className="text-right flex-shrink-0">
              <div className="text-xs font-medium text-gray-600">{task.schedule}</div>
              {task.next_run && (
                <div className="text-[11px] text-emerald-600 font-semibold">
                  ⏱ {timeUntil(task.next_run)}
                </div>
              )}
            </div>

            {/* Last run */}
            <div className="text-right flex-shrink-0 w-16">
              <div className="text-[11px] text-gray-400">{formatLastRun(task.last_run)}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Manual Tasks Separator */}
      {manual.length > 0 && (
        <>
          <div className="px-5 py-2 bg-amber-50/50 border-t border-b border-amber-100/50">
            <div className="flex items-center gap-1.5">
              <Hand size={12} className="text-amber-500" />
              <span className="text-[11px] font-bold text-amber-700 uppercase tracking-wider">
                Manual Only
              </span>
            </div>
          </div>
          <div className="divide-y divide-gray-50">
            {manual.map(task => (
              <div key={task.task_id} className="px-5 py-3 flex items-center gap-3 hover:bg-gray-50/50 transition-colors">
                <span className="text-lg flex-shrink-0 w-7 text-center">{task.icon}</span>
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-semibold text-gray-900">{task.name}</span>
                  <div className="text-[11px] text-gray-400 truncate">{task.last_status}</div>
                </div>
                <div className="text-right flex-shrink-0">
                  <span className="text-[10px] font-medium text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
                    Admin Panel
                  </span>
                </div>
                <div className="text-right flex-shrink-0 w-16">
                  <div className="text-[11px] text-gray-400">{formatLastRun(task.last_run)}</div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
