'use client';

import { useState, useEffect, useRef } from 'react';
import { getApiUrl } from '@/lib/config';
import api from '@/lib/api';

interface EmbeddingStats {
    indexed: number;
    total: number;
    not_indexed: number;
    pct: number;
}

interface Props {
    triggering: string | null;
    triggerTask: (taskType: string) => void;
}

export function EmbeddingsCard({ triggering, triggerTask }: Props) {
    const [stats, setStats] = useState<EmbeddingStats | null>(null);
    const [loading, setLoading] = useState(true);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const apiUrl = getApiUrl();

    const fetchStats = async () => {
        try {
            const { data } = await api.get(`${apiUrl}/health/embedding-stats/`);
            setStats(data);
        } catch {
            // ignore
        } finally {
            setLoading(false);
        }
    };

    // Fetch on mount
    useEffect(() => { fetchStats(); }, []);

    // Poll every 3s while indexing is running
    useEffect(() => {
        if (triggering === 'index-articles') {
            intervalRef.current = setInterval(fetchStats, 3000);
        } else {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
                // Final fetch to show result
                setTimeout(fetchStats, 1500);
            }
        }
        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, [triggering]);

    const isClearing = triggering === 'clear-embeddings';
    const isIndexing = triggering === 'index-articles';
    const isRunning = isIndexing || isClearing;

    const pct = stats?.pct ?? 0;
    const barColor =
        pct >= 80 ? 'bg-gradient-to-r from-emerald-400 to-emerald-600' :
            pct >= 50 ? 'bg-gradient-to-r from-amber-400 to-amber-600' :
                'bg-gradient-to-r from-red-400 to-red-600';
    const pctColor =
        pct >= 80 ? 'text-emerald-600' :
            pct >= 50 ? 'text-amber-600' :
                'text-red-600';

    const handleClear = () => {
        if (window.confirm(
            '⚠️ Clear all article embeddings?\n\n' +
            'This will delete all stored vectors (model v1 are incompatible with v2).\n' +
            'After clearing, click "Index Articles" to re-index with the new model.'
        )) {
            triggerTask('clear-embeddings');
        }
    };

    return (
        <div className="bg-gradient-to-br from-teal-50 to-cyan-50 rounded-lg shadow-md border-2 border-teal-200 p-5 h-full flex flex-col">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-base font-black text-gray-900">🔍 Article Embeddings</h3>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleClear}
                        disabled={isRunning}
                        title="Clear all embeddings (needed after model migration)"
                        className={`px-2.5 py-1.5 rounded-lg text-xs font-bold transition-all ${isRunning
                            ? 'bg-gray-100 text-gray-300 cursor-wait'
                            : 'bg-red-50 text-red-600 hover:bg-red-100 border border-red-200'
                            }`}
                    >
                        {isClearing ? '⏳...' : '🗑️'}
                    </button>
                    <button
                        onClick={() => triggerTask('index-articles')}
                        disabled={isRunning}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${isRunning
                            ? 'bg-gray-100 text-gray-400 cursor-wait'
                            : 'bg-teal-100 text-teal-700 hover:bg-teal-200 border border-teal-300'
                            }`}
                    >
                        {isIndexing ? '⏳ Indexing...' : isClearing ? '⏳ Clearing...' : '⚡ Index Articles'}
                    </button>
                </div>
            </div>

            {/* Progress bar */}
            <div className="bg-white rounded-xl border border-teal-200 p-4 mb-3">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-gray-600 uppercase tracking-wider">
                        {isRunning ? '⚡ Indexing...' : 'Embedding Coverage'}
                    </span>
                    {loading ? (
                        <span className="text-xs text-gray-400">Loading...</span>
                    ) : (
                        <span className={`text-lg font-black ${pctColor}`}>{pct}%</span>
                    )}
                </div>

                <div className="h-4 bg-gray-100 rounded-full overflow-hidden mb-2 relative">
                    <div
                        className={`h-full rounded-full transition-all duration-700 ${barColor} ${isRunning ? 'animate-pulse' : ''}`}
                        style={{ width: `${pct}%` }}
                    />
                    {/* Striped overlay while running */}
                    {isRunning && (
                        <div className="absolute inset-0 overflow-hidden rounded-full opacity-20"
                            style={{
                                backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 8px, rgba(255,255,255,0.8) 8px, rgba(255,255,255,0.8) 16px)',
                                backgroundSize: '22px 22px',
                            }}
                        />
                    )}
                </div>

                {stats && (
                    <div className="flex justify-between text-[11px] font-semibold text-gray-500">
                        <span>
                            <span className="text-teal-700 font-black">{stats.indexed.toLocaleString()}</span> indexed
                        </span>
                        <span>
                            <span className="text-red-500 font-black">{stats.not_indexed.toLocaleString()}</span> remaining
                        </span>
                        <span>
                            <span className="font-black">{stats.total.toLocaleString()}</span> total
                        </span>
                    </div>
                )}
            </div>

            <p className="text-xs text-gray-500 leading-relaxed flex-1">
                Vector embeddings power semantic search, ML recommendations, and deduplication.
                <br />
                {pct < 80 && !isRunning && (
                    <span className="inline-flex items-center gap-1 mt-1 text-amber-600 font-semibold">
                        ⚠️ Coverage below 80% — click Index Articles to improve ML accuracy
                    </span>
                )}
                {pct >= 80 && (
                    <span className="inline-flex items-center gap-1 mt-1 text-emerald-600 font-semibold">
                        ✅ Good coverage — ML features are fully operational
                    </span>
                )}
            </p>

            <div className="mt-3 pt-3 border-t border-teal-200">
                <a href="/admin/system-graph" className="text-xs font-bold text-teal-600 hover:text-teal-800 transition-colors">
                    🌐 View System Graph →
                </a>
            </div>
        </div>
    );
}
