import { useState } from 'react';
import { AutomationStats } from '../types';
import { timeAgo } from '../utils';

interface DecisionLogProps {
    stats: AutomationStats | null;
}

export function DecisionLog({ stats }: DecisionLogProps) {
    const [decisionFilter, setDecisionFilter] = useState<string>('all');

    if (!stats) return null;

    const filteredDecisions = stats.recent_decisions?.filter((d) =>
        decisionFilter === 'all' ? true : d.decision === decisionFilter
    ) || [];

    return (
        <div className="mt-6">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-black text-gray-950">📋 Auto-Publish Decision Log</h3>
                <div className="flex items-center gap-2">
                    <select
                        value={decisionFilter}
                        onChange={(e) => setDecisionFilter(e.target.value)}
                        className="px-3 py-1.5 text-sm text-gray-800 font-medium border rounded-lg bg-white focus:ring-2 focus:ring-indigo-500"
                    >
                        <option value="all">All Decisions</option>
                        <option value="published">✅ Published</option>
                        <option value="skipped_quality">⏭️ Low Quality</option>
                        <option value="skipped_safety">🛡️ Unsafe Feed</option>
                        <option value="skipped_no_image">📷 No Image</option>
                        <option value="failed">❌ Failed</option>
                    </select>
                </div>
            </div>

            <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
                {filteredDecisions.length === 0 ? (
                    <div className="p-8 text-center text-gray-500">
                        <p className="text-lg mb-1">📭</p>
                        <p className="text-sm font-medium">No decisions logged yet</p>
                        <p className="text-xs text-gray-400 mt-1">Decisions will appear here after auto-publish runs</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-100 max-h-[400px] overflow-y-auto">
                        {filteredDecisions.map((d) => {
                            const isPublished = d.decision === 'published';
                            const isFailed = d.decision === 'failed';
                            const rowBg = isPublished ? 'bg-emerald-50/50' : isFailed ? 'bg-red-50/50' : '';

                            return (
                                <div key={d.id} className={`px-4 py-3 flex items-center gap-3 ${rowBg}`}>
                                    {/* Decision icon */}
                                    <span className="text-lg flex-shrink-0">
                                        {isPublished ? '✅' : isFailed ? '❌' :
                                            d.decision === 'skipped_safety' ? '🛡️' :
                                                d.decision === 'skipped_quality' ? '⏭️' :
                                                    d.decision === 'skipped_no_image' ? '📷' : '⏸️'}
                                    </span>

                                    {/* Content */}
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-bold text-gray-900 truncate">{d.title}</p>
                                        <p className="text-xs text-gray-500 mt-0.5">{d.reason}</p>
                                    </div>

                                    {/* Meta badges */}
                                    <div className="flex items-center gap-2 flex-shrink-0">
                                        {/* Quality */}
                                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${d.quality_score >= 7 ? 'bg-emerald-100 text-emerald-700' :
                                            d.quality_score >= 5 ? 'bg-amber-100 text-amber-700' :
                                                'bg-red-100 text-red-700'
                                            }`}>
                                            Q:{d.quality_score}
                                        </span>

                                        {/* Safety */}
                                        {d.safety_score && (
                                            <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${d.safety_score === 'safe' ? 'bg-emerald-100 text-emerald-700' :
                                                d.safety_score === 'unsafe' ? 'bg-red-100 text-red-700' :
                                                    'bg-amber-100 text-amber-700'
                                                }`}>
                                                {d.safety_score === 'safe' ? '✅' : d.safety_score === 'unsafe' ? '🔴' : '🟡'}
                                            </span>
                                        )}

                                        {/* Source type */}
                                        <span className="text-xs text-gray-400">
                                            {d.source_is_youtube ? '🎬' : '📡'} {d.feed_name?.substring(0, 15)}
                                        </span>

                                        {/* Time */}
                                        <span className="text-xs text-gray-500 font-semibold whitespace-nowrap">
                                            {timeAgo(d.created_at)}
                                        </span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* ML Training Data Indicator */}
            {stats.total_decisions > 0 && (
                <div className="mt-4 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg border border-purple-200 p-4">
                    <div className="flex items-center gap-3">
                        <span className="text-2xl">🧠</span>
                        <div className="flex-1">
                            <p className="text-sm font-black text-purple-900">ML Training Data</p>
                            <p className="text-xs text-purple-700 mt-0.5">
                                <strong>{stats.total_decisions.toLocaleString()}</strong> decisions logged
                                {stats.decision_breakdown && (
                                    <span>
                                        {' • '}
                                        <span className="text-emerald-700">{stats.decision_breakdown.published || 0} published</span>
                                        {' • '}
                                        <span className="text-amber-700">{
                                            (stats.decision_breakdown.skipped_quality || 0) +
                                            (stats.decision_breakdown.skipped_safety || 0) +
                                            (stats.decision_breakdown.skipped_no_image || 0) +
                                            (stats.decision_breakdown.skipped_limit || 0)
                                        } skipped</span>
                                        {(stats.decision_breakdown.failed || 0) > 0 && (
                                            <>
                                                {' • '}
                                                <span className="text-red-700">{stats.decision_breakdown.failed} failed</span>
                                            </>
                                        )}
                                    </span>
                                )}
                            </p>
                        </div>
                        <div className="text-right">
                            <p className="text-xs text-purple-600 font-medium">
                                Collecting features for future ML model
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
