import Link from 'next/link';
import { AutomationSettings } from '../types';
import { ModuleCard, SettingRow, NumberInput } from './ui';

interface Props {
    settings: AutomationSettings;
    saving: boolean;
    triggering: string | null;
    updateSetting: (key: string, value: unknown) => void;
    triggerTask: (taskType: string) => void;
}

export function RssScanningCard({
    settings,
    saving,
    triggering,
    updateSetting,
    triggerTask,
}: Props) {
    return (
        <ModuleCard
            title="📡 RSS Scanning"
            enabled={settings.rss_scan_enabled}
            onToggle={(v) => updateSetting('rss_scan_enabled', v)}
            lastRun={settings.rss_last_run}
            lastStatus={settings.rss_last_status}
            saving={saving}
            onTrigger={() => triggerTask('rss')}
            triggering={triggering === 'rss'}
        >
            <SettingRow label="Scan interval">
                <select
                    value={settings.rss_scan_interval_minutes}
                    onChange={(e) => updateSetting('rss_scan_interval_minutes', parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 font-medium text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                >
                    <option value={15}>Every 15 min</option>
                    <option value={30}>Every 30 min</option>
                    <option value={60}>Every 1 hour</option>
                    <option value={120}>Every 2 hours</option>
                </select>
            </SettingRow>
            <SettingRow label="Max per scan">
                <NumberInput
                    min={1}
                    max={50}
                    value={settings.rss_max_articles_per_scan}
                    onSave={(v) => updateSetting('rss_max_articles_per_scan', v)}
                    fallback={10}
                />
            </SettingRow>
            <div className="mt-3 pt-3 border-t border-gray-100 flex items-center gap-3">
                <Link href="/admin/rss-feeds" className="text-xs font-bold text-indigo-600 hover:text-indigo-800 transition-colors">📡 Manage Feeds →</Link>
                <Link href="/admin/rss-pending" className="text-xs font-bold text-indigo-600 hover:text-indigo-800 transition-colors">📰 View RSS News →</Link>
            </div>
        </ModuleCard>
    );
}
