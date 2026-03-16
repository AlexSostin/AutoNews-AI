'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';

/* ═══════════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════════ */

interface CallerStats {
  caller: string;
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

interface ModelStats {
  model: string;
  calls: number;
  total_tokens: number;
  cost_usd: number;
}

interface SummaryData {
  period_hours: number;
  total_calls: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  by_caller: CallerStats[];
  by_model: ModelStats[];
}

/* Transform API dict → array and normalize field names */
function normalizeSummary(raw: Record<string, unknown>): SummaryData {
  const byCaller: CallerStats[] = [];
  const rawCaller = (raw.by_caller || {}) as Record<string, Record<string, number>>;
  if (rawCaller && typeof rawCaller === 'object' && !Array.isArray(rawCaller)) {
    for (const [name, stats] of Object.entries(rawCaller)) {
      byCaller.push({
        caller: name,
        calls: stats.calls || 0,
        prompt_tokens: stats.prompt_tokens || 0,
        completion_tokens: stats.completion_tokens || 0,
        total_tokens: stats.total_tokens || 0,
        cost_usd: stats.cost_usd ?? stats.cost ?? 0,
      });
    }
  } else if (Array.isArray(rawCaller)) {
    byCaller.push(...(rawCaller as unknown as CallerStats[]));
  }

  const byModel: ModelStats[] = [];
  const rawModel = (raw.by_model || {}) as Record<string, Record<string, number>>;
  if (rawModel && typeof rawModel === 'object' && !Array.isArray(rawModel)) {
    for (const [name, stats] of Object.entries(rawModel)) {
      byModel.push({
        model: name,
        calls: stats.calls || 0,
        total_tokens: stats.total_tokens || 0,
        cost_usd: stats.cost_usd ?? stats.cost ?? 0,
      });
    }
  } else if (Array.isArray(rawModel)) {
    byModel.push(...(rawModel as unknown as ModelStats[]));
  }

  return {
    period_hours: (raw.period_hours ?? raw.hours ?? 24) as number,
    total_calls: (raw.total_calls || 0) as number,
    total_prompt_tokens: (raw.total_prompt_tokens || 0) as number,
    total_completion_tokens: (raw.total_completion_tokens || 0) as number,
    total_tokens: (raw.total_tokens || 0) as number,
    estimated_cost_usd: ((raw.estimated_cost_usd ?? raw.total_cost ?? 0) as number),
    by_caller: byCaller,
    by_model: byModel,
  };
}

interface RealtimeEntry {
  timestamp: string;
  caller: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

/* ═══════════════════════════════════════════════════════════════
   Helper: format numbers nicely
   ═══════════════════════════════════════════════════════════════ */
function fmtNum(n: number): string {
  n = n || 0;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function fmtCost(c: number): string {
  c = c || 0;
  if (c < 0.01) return `$${c.toFixed(4)}`;
  return `$${c.toFixed(2)}`;
}

function timeAgo(ts: string): string {
  const diff = (Date.now() - new Date(ts).getTime()) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  return `${Math.round(diff / 3600)}h ago`;
}

/* Bar component for inline percentages */
function Bar({ pct, color }: { pct: number; color: string }) {
  return (
    <div className="w-full h-2 bg-gray-800/50 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-500 ${color}`}
        style={{ width: `${Math.min(pct, 100)}%` }}
      />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Main page
   ═══════════════════════════════════════════════════════════════ */
export default function TokenUsagePage() {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [realtime, setRealtime] = useState<RealtimeEntry[]>([]);
  const [hours, setHours] = useState(24);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<'total_tokens' | 'calls' | 'cost_usd'>('total_tokens');
  const [sortAsc, setSortAsc] = useState(false);

  const fetchSummary = useCallback(async () => {
    try {
      const { data } = await api.get(`/admin/token-usage/summary/?hours=${hours}`);
      if (data && typeof data === 'object') {
        setSummary(normalizeSummary(data));
      }
    } catch (err) {
      console.error('[token_usage] summary fetch failed', err);
    }
  }, [hours]);

  const fetchRealtime = useCallback(async () => {
    try {
      const { data } = await api.get('/admin/token-usage/realtime/?minutes=10');
      setRealtime(Array.isArray(data?.entries) ? data.entries : []);
    } catch (err) {
      console.error('[token_usage] realtime fetch failed', err);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchSummary(), fetchRealtime()]).finally(() => setLoading(false));
    const interval = setInterval(() => {
      fetchSummary();
      fetchRealtime();
    }, 15_000);
    return () => clearInterval(interval);
  }, [fetchSummary, fetchRealtime]);

  /* Sorted caller table */
  const sortedCallers = (summary?.by_caller || []).slice().sort((a, b) => {
    const va = a[sortKey];
    const vb = b[sortKey];
    return sortAsc ? va - vb : vb - va;
  });

  const maxTokens = Math.max(...(sortedCallers.map((c) => c.total_tokens) || [1]));

  const handleSort = (key: typeof sortKey) => {
    if (key === sortKey) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  };

  const callerColors: Record<string, string> = {
    article_generate: 'bg-violet-500',
    article_review: 'bg-indigo-500',
    article_verdict: 'bg-blue-500',
    article_fallback: 'bg-sky-500',
    fact_check: 'bg-rose-500',
    fact_check_fix: 'bg-red-500',
    deep_specs: 'bg-emerald-500',
    deep_specs_refill: 'bg-teal-500',
    comparison: 'bg-amber-500',
    translate: 'bg-orange-500',
    title_seo: 'bg-lime-500',
    title_variants: 'bg-green-500',
    transcript_analyze: 'bg-cyan-500',
    transcript_specs: 'bg-cyan-600',
    categorize: 'bg-fuchsia-500',
    license_tos: 'bg-gray-500',
    license_images: 'bg-gray-400',
    license_homepage: 'bg-gray-600',
  };

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-gray-950">
            🪙 Token Usage Dashboard
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Real-time AI token consumption, cost breakdown by function & model
          </p>
        </div>
        <select
          value={hours}
          onChange={(e) => setHours(Number(e.target.value))}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white text-gray-900 font-medium focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value={1}>Last 1 hour</option>
          <option value={6}>Last 6 hours</option>
          <option value={24}>Last 24 hours</option>
          <option value={72}>Last 3 days</option>
          <option value={168}>Last 7 days</option>
          <option value={720}>Last 30 days</option>
        </select>
      </div>

      {loading && !summary ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin h-8 w-8 border-4 border-indigo-500 border-t-transparent rounded-full" />
        </div>
      ) : !summary || summary.total_calls === 0 ? (
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-5xl mb-4">📭</p>
          <p className="text-lg font-semibold text-gray-700">No token usage data yet</p>
          <p className="text-gray-500 text-sm mt-1">
            Data will appear here once AI functions are called (article generation, fact-checking, etc.)
          </p>
        </div>
      ) : (
        <>
          {/* ═══ Summary Cards ═══ */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <SummaryCard
              emoji="📊"
              label="Total Calls"
              value={fmtNum(summary.total_calls)}
              sub={`in ${hours}h`}
              gradient="from-violet-500 to-indigo-600"
            />
            <SummaryCard
              emoji="📝"
              label="Prompt Tokens"
              value={fmtNum(summary.total_prompt_tokens)}
              sub={`${Math.round((summary.total_prompt_tokens / (summary.total_tokens || 1)) * 100)}%`}
              gradient="from-sky-500 to-blue-600"
            />
            <SummaryCard
              emoji="💬"
              label="Completion Tokens"
              value={fmtNum(summary.total_completion_tokens)}
              sub={`${Math.round((summary.total_completion_tokens / (summary.total_tokens || 1)) * 100)}%`}
              gradient="from-emerald-500 to-teal-600"
            />
            <SummaryCard
              emoji="💰"
              label="Estimated Cost"
              value={fmtCost(summary.estimated_cost_usd)}
              sub={`${fmtNum(summary.total_tokens)} tokens total`}
              gradient="from-amber-500 to-orange-600"
            />
          </div>

          {/* ═══ By Function Table ═══ */}
          <section>
            <h2 className="text-lg font-bold text-gray-900 mb-3 border-l-4 border-violet-500 pl-3">
              🔍 Usage by Function
            </h2>
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-3 text-left">Function</th>
                      <th
                        className="px-4 py-3 text-right cursor-pointer hover:text-indigo-600 select-none"
                        onClick={() => handleSort('calls')}
                      >
                        Calls {sortKey === 'calls' && (sortAsc ? '↑' : '↓')}
                      </th>
                      <th
                        className="px-4 py-3 text-right cursor-pointer hover:text-indigo-600 select-none"
                        onClick={() => handleSort('total_tokens')}
                      >
                        Tokens {sortKey === 'total_tokens' && (sortAsc ? '↑' : '↓')}
                      </th>
                      <th className="px-4 py-3 text-right hidden sm:table-cell">Prompt</th>
                      <th className="px-4 py-3 text-right hidden sm:table-cell">Completion</th>
                      <th
                        className="px-4 py-3 text-right cursor-pointer hover:text-indigo-600 select-none"
                        onClick={() => handleSort('cost_usd')}
                      >
                        Cost {sortKey === 'cost_usd' && (sortAsc ? '↑' : '↓')}
                      </th>
                      <th className="px-4 py-3 w-32 hidden lg:table-cell">Share</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {sortedCallers.map((c) => (
                      <tr key={c.caller} className="hover:bg-gray-50/80 transition-colors">
                        <td className="px-4 py-3 font-medium text-gray-900 flex items-center gap-2">
                          <span
                            className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${callerColors[c.caller] || 'bg-gray-400'}`}
                          />
                          <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">
                            {c.caller}
                          </code>
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-gray-700">
                          {c.calls.toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums font-semibold text-gray-900">
                          {fmtNum(c.total_tokens)}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-gray-500 hidden sm:table-cell">
                          {fmtNum(c.prompt_tokens)}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-gray-500 hidden sm:table-cell">
                          {fmtNum(c.completion_tokens)}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-gray-700">
                          {fmtCost(c.cost_usd)}
                        </td>
                        <td className="px-4 py-3 hidden lg:table-cell">
                          <Bar
                            pct={(c.total_tokens / maxTokens) * 100}
                            color={callerColors[c.caller] || 'bg-gray-400'}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          {/* ═══ Two-column: By Model + Realtime ═══ */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {/* By Model */}
            <section>
              <h2 className="text-lg font-bold text-gray-900 mb-3 border-l-4 border-emerald-500 pl-3">
                🤖 Usage by Model
              </h2>
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4">
                {(summary.by_model || []).length === 0 ? (
                  <p className="text-gray-400 text-sm text-center py-4">No model data yet</p>
                ) : (
                  summary.by_model.map((m) => (
                    <div key={m.model} className="space-y-1.5">
                      <div className="flex justify-between text-sm">
                        <span className="font-medium text-gray-800">{m.model}</span>
                        <span className="text-gray-500">
                          {fmtNum(m.total_tokens)} tokens · {fmtCost(m.cost_usd)} · {m.calls} calls
                        </span>
                      </div>
                      <Bar
                        pct={(m.total_tokens / (summary.total_tokens || 1)) * 100}
                        color="bg-emerald-500"
                      />
                    </div>
                  ))
                )}
              </div>
            </section>

            {/* Realtime Feed */}
            <section>
              <h2 className="text-lg font-bold text-gray-900 mb-3 border-l-4 border-rose-500 pl-3">
                ⚡ Recent Calls
                <span className="text-xs font-normal text-gray-400 ml-2">auto-refreshes every 15s</span>
              </h2>
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden max-h-[420px] overflow-y-auto">
                {realtime.length === 0 ? (
                  <p className="text-gray-400 text-sm text-center py-8">No recent calls</p>
                ) : (
                  <div className="divide-y divide-gray-100">
                    {realtime.map((entry, i) => (
                      <div key={i} className="px-4 py-3 hover:bg-gray-50/60 transition-colors flex items-center gap-3">
                        <span
                          className={`w-2 h-2 rounded-full flex-shrink-0 ${callerColors[entry.caller] || 'bg-gray-400'}`}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-gray-900 truncate">
                            <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{entry.caller}</code>
                            <span className="text-gray-400 text-xs ml-2">{entry.model}</span>
                          </div>
                          <div className="text-xs text-gray-500 mt-0.5">
                            {fmtNum(entry.total_tokens)} tokens · {fmtCost(entry.cost_usd)}
                          </div>
                        </div>
                        <span className="text-xs text-gray-400 whitespace-nowrap flex-shrink-0">
                          {timeAgo(entry.timestamp)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Summary Card component
   ═══════════════════════════════════════════════════════════════ */
function SummaryCard({
  emoji,
  label,
  value,
  sub,
  gradient,
}: {
  emoji: string;
  label: string;
  value: string;
  sub: string;
  gradient: string;
}) {
  return (
    <div className={`bg-gradient-to-br ${gradient} rounded-xl p-5 text-white shadow-lg`}>
      <div className="text-sm font-medium opacity-80">{emoji} {label}</div>
      <div className="text-2xl sm:text-3xl font-black mt-1 tracking-tight">{value}</div>
      <div className="text-xs opacity-70 mt-1">{sub}</div>
    </div>
  );
}
