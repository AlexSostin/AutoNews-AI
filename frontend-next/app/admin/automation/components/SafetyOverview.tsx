import Link from 'next/link';
import { AutomationStats } from '../types';

interface SafetyOverviewProps {
    stats: AutomationStats | null;
}

export function SafetyOverview({ stats }: SafetyOverviewProps) {
    if (!stats?.safety_overview) return null;

    const { safety_counts, image_policy_counts } = stats.safety_overview;

    return (
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4 mb-6">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-black text-gray-900">🛡️ Feed Safety Overview</h3>
                <Link href="/admin/rss-feeds" className="text-xs font-bold text-indigo-600 hover:text-indigo-800 transition-colors">
                    Manage Feeds →
                </Link>
            </div>
            <div className="flex flex-wrap gap-3">
                {/* Safety counts */}
                <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 rounded-lg border border-emerald-200">
                    <span className="text-sm">✅</span>
                    <span className="text-sm font-bold text-emerald-800">Safe: {safety_counts.safe}</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 rounded-lg border border-amber-200">
                    <span className="text-sm">🟡</span>
                    <span className="text-sm font-bold text-amber-800">Review: {safety_counts.review}</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 rounded-lg border border-red-200">
                    <span className="text-sm">🔴</span>
                    <span className="text-sm font-bold text-red-800">Unsafe: {safety_counts.unsafe}</span>
                </div>

                <div className="w-px bg-gray-300 mx-1 self-stretch"></div>

                {/* Image policy counts */}
                <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 rounded-lg border border-blue-200">
                    <span className="text-sm">📷</span>
                    <span className="text-sm font-bold text-blue-800">Original: {image_policy_counts.original}</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-50 rounded-lg border border-purple-200">
                    <span className="text-sm">🖼️</span>
                    <span className="text-sm font-bold text-purple-800">Pexels: {image_policy_counts.pexels_only}</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-indigo-50 rounded-lg border border-indigo-200">
                    <span className="text-sm">📷+🖼️</span>
                    <span className="text-sm font-bold text-indigo-800">Fallback: {image_policy_counts.pexels_fallback}</span>
                </div>
                {image_policy_counts.unchecked > 0 && (
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 rounded-lg border border-gray-200">
                        <span className="text-sm">⚠️</span>
                        <span className="text-sm font-bold text-gray-600">Unchecked: {image_policy_counts.unchecked}</span>
                    </div>
                )}
            </div>
        </div>
    );
}
