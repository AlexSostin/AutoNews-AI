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

export function YoutubeScanningCard({
    settings,
    saving,
    triggering,
    updateSetting,
    triggerTask,
}: Props) {
    return (
        <ModuleCard
            title="🎬 YouTube Scanning"
            enabled={settings.youtube_scan_enabled}
            onToggle={(v) => updateSetting('youtube_scan_enabled', v)}
            lastRun={settings.youtube_last_run}
            lastStatus={settings.youtube_last_status}
            saving={saving}
            onTrigger={() => triggerTask('youtube')}
            triggering={triggering === 'youtube'}
        >
            <SettingRow label="Scan interval">
                <select
                    value={settings.youtube_scan_interval_minutes}
                    onChange={(e) => updateSetting('youtube_scan_interval_minutes', parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 font-medium text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                >
                    <option value={60}>Every 1 hour</option>
                    <option value={120}>Every 2 hours</option>
                    <option value={240}>Every 4 hours</option>
                </select>
            </SettingRow>
            <SettingRow label="Max per scan">
                <NumberInput
                    min={1}
                    max={20}
                    value={settings.youtube_max_videos_per_scan}
                    onSave={(v) => updateSetting('youtube_max_videos_per_scan', v)}
                    fallback={3}
                />
            </SettingRow>
            <div className="mt-3 pt-3 border-t border-gray-100">
                <Link href="/admin/youtube-channels" className="text-xs font-bold text-indigo-600 hover:text-indigo-800 transition-colors">🎬 Manage Channels →</Link>
            </div>
        </ModuleCard>
    );
}
