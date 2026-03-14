import Link from 'next/link';
import { AutomationSettings } from '../types';
import { ModuleCard } from './ui';

interface Props {
    settings: AutomationSettings;
    saving: boolean;
    updateSetting: (key: string, value: unknown) => void;
}

export function GoogleIndexingCard({
    settings,
    saving,
    updateSetting,
}: Props) {
    return (
        <ModuleCard
            title="🔍 Google Indexing"
            enabled={settings.google_indexing_enabled}
            onToggle={(v) => updateSetting('google_indexing_enabled', v)}
            lastRun={settings.google_indexing_last_run}
            lastStatus={settings.google_indexing_last_status || `${settings.google_indexing_today_count || 0} indexed today`}
            saving={saving}
        >
            <p className="text-sm text-gray-600">
                When enabled, newly published articles are automatically submitted to the Google Indexing API
                for faster crawling and indexing.
            </p>
            <div className="mt-3 pt-3 border-t border-gray-100">
                <Link href="/admin/analytics" className="text-xs font-bold text-indigo-600 hover:text-indigo-800 transition-colors">📊 View Analytics →</Link>
            </div>
        </ModuleCard>
    );
}
