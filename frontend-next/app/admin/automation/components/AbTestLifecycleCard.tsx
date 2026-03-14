import Link from 'next/link';
import { ActionCard } from './ui';

interface Props {
    triggering: string | null;
    triggerTask: (taskType: string) => void;
}

export function AbTestLifecycleCard({
    triggering,
    triggerTask,
}: Props) {
    return (
        <ActionCard
            title="🧹 A/B Test Lifecycle"
            onTrigger={() => triggerTask('ab-cleanup')}
            triggering={triggering === 'ab-cleanup'}
            actionButtonText="🔄 Run Now"
            actionButtonLoadingText="⏳ Running..."
        >
            <div className="space-y-2 flex-1 mt-1">
                <div className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="shrink-0">📅</span>
                    <span><strong>Day 0-29:</strong> Test runs, data accumulates</span>
                </div>
                <div className="flex items-start gap-2 text-sm text-gray-700 bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                    <span className="shrink-0">⚠️</span>
                    <span><strong>Day 30:</strong> No winner → notification «pick winner in 7 days»</span>
                </div>
                <div className="flex items-start gap-2 text-sm text-gray-700 bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                    <span className="shrink-0">🤖</span>
                    <span><strong>Day 37:</strong> Auto-pick winner by CTR → delete losers</span>
                </div>
                <div className="flex items-start gap-2 text-sm text-gray-700 bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                    <span className="shrink-0">✅</span>
                    <span><strong>Winner 30d+:</strong> Losers cleaned up automatically</span>
                </div>
            </div>
            <div className="mt-3 pt-3 border-t border-gray-100">
                <Link href="/admin/ab-testing" className="text-xs font-bold text-indigo-600 hover:text-indigo-800 transition-colors">🧪 View A/B Tests →</Link>
            </div>
        </ActionCard>
    );
}
