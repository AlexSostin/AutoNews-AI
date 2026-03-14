import { AutomationStats } from '../types';
import { ActionCard } from './ui';
import { timeAgo } from '../utils';

interface Props {
    stats?: AutomationStats | null;
}

function EnrichmentReportDetails({ enrichment }: { enrichment: NonNullable<AutomationStats['enrichment_report']> }) {
    const articlesProcessed = enrichment.articles_processed ?? enrichment.current ?? 0;
    const articlesTotal = enrichment.articles_total ?? enrichment.total ?? 0;
    const durationSec = enrichment.duration_seconds ?? enrichment.elapsed_seconds ?? 0;
    const tagsCreated = enrichment.tags_created ?? 0;
    const tagsMatched = enrichment.tags_matched ?? 0;
    const errorCount = enrichment.errors ?? enrichment.error_count ?? 0;
    const mode = enrichment.mode ?? 'unknown';

    return (
        <div className="space-y-2 flex-1 mt-2">
            <div className="grid grid-cols-2 gap-2">
                <div className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                    <p className="text-xs text-gray-500 font-medium">Articles</p>
                    <p className="text-lg font-black text-indigo-700">{articlesProcessed}/{articlesTotal}</p>
                </div>
                <div className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                    <p className="text-xs text-gray-500 font-medium">Duration</p>
                    <p className="text-lg font-black text-indigo-700">
                        {durationSec > 0 ? (durationSec < 60 ? `${durationSec}s` : `${Math.round(durationSec / 60)}m`) : '—'}
                    </p>
                </div>
                <div className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                    <p className="text-xs text-gray-500 font-medium">Tags created</p>
                    <p className="text-lg font-black text-emerald-600">+{tagsCreated}</p>
                </div>
                <div className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                    <p className="text-xs text-gray-500 font-medium">Tags matched</p>
                    <p className="text-lg font-black text-blue-600">+{tagsMatched}</p>
                </div>
            </div>
            {errorCount > 0 && (
                <div className="bg-red-50 rounded-lg px-3 py-2 border border-red-200 mt-2">
                    <p className="text-xs font-bold text-red-700">❌ {errorCount} errors during enrichment</p>
                </div>
            )}
            <p className="text-xs text-gray-500 mt-2">
                Mode: <strong>{mode}</strong>
            </p>
        </div>
    );
}

export function BulkEnrichmentCard({
    stats,
}: Props) {
    const enrichment = stats?.enrichment_report;

    return (
        <ActionCard
            title="📦 Bulk Enrichment"
            lastRun={enrichment ? enrichment.last_run : null}
            lastStatus={enrichment ? 'Report available' : 'Never run'}
        >
            {enrichment ? (
                <EnrichmentReportDetails enrichment={enrichment} />
            ) : (
                <p className="text-sm text-gray-600 flex-1">
                    No enrichment reports yet. Run <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">python manage.py bulk_enrich</code> to enrich articles with Deep Specs, A/B Titles, and Smart Tags.
                </p>
            )}
        </ActionCard>
    );
}
