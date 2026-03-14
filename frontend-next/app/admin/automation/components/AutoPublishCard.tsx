import Link from 'next/link';
import { AutomationSettings, AutomationStats } from '../types';
import { ModuleCard, SettingRow, NumberInput, ToggleSwitch } from './ui';

interface Props {
    settings: AutomationSettings;
    eligibleStats?: AutomationStats['eligible'];
    saving: boolean;
    triggering: string | null;
    updateSetting: (key: string, value: any) => void;
    triggerTask: (taskType: string) => void;
}

export function AutoPublishCard({
    settings,
    eligibleStats,
    saving,
    triggering,
    updateSetting,
    triggerTask,
}: Props) {
    return (
        <ModuleCard
            title="📝 Auto-Publish"
            enabled={settings.auto_publish_enabled}
            onToggle={(v) => updateSetting('auto_publish_enabled', v)}
            lastRun={settings.auto_publish_last_run}
            lastStatus={`${settings.auto_publish_today_count} / ${settings.auto_publish_max_per_day} today`}
            saving={saving}
            onTrigger={() => triggerTask('auto-publish')}
            triggering={triggering === 'auto-publish'}
        >
            <SettingRow label="Min quality">
                <div className="flex items-center gap-3">
                    <input
                        type="range"
                        min={1}
                        max={10}
                        value={settings.auto_publish_min_quality}
                        onChange={(e) => updateSetting('auto_publish_min_quality', parseInt(e.target.value))}
                        className="flex-1 accent-indigo-600"
                    />
                    <span className={`text-lg font-black min-w-[3rem] text-center ${settings.auto_publish_min_quality >= 7 ? 'text-emerald-600' :
                        settings.auto_publish_min_quality >= 5 ? 'text-amber-600' : 'text-red-600'
                        }`}>
                        {settings.auto_publish_min_quality}/10
                    </span>
                </div>
            </SettingRow>
            <SettingRow label="Max per hour">
                <NumberInput
                    min={1}
                    max={20}
                    value={settings.auto_publish_max_per_hour}
                    onSave={(v) => updateSetting('auto_publish_max_per_hour', v)}
                    fallback={3}
                />
            </SettingRow>
            <SettingRow label="Max per day">
                <NumberInput
                    min={1}
                    max={100}
                    value={settings.auto_publish_max_per_day}
                    onSave={(v) => updateSetting('auto_publish_max_per_day', v)}
                    fallback={20}
                />
            </SettingRow>
            <SettingRow label="Require image">
                <ToggleSwitch
                    checked={settings.auto_publish_require_image}
                    onChange={(v) => updateSetting('auto_publish_require_image', v)}
                />
            </SettingRow>
            <SettingRow label="Only safe feeds">
                <ToggleSwitch
                    checked={settings.auto_publish_require_safe_feed}
                    onChange={(v) => updateSetting('auto_publish_require_safe_feed', v)}
                />
            </SettingRow>
            <SettingRow label="Draft mode">
                <div className="flex items-center gap-3">
                    <ToggleSwitch
                        checked={settings.auto_publish_as_draft}
                        onChange={(v) => updateSetting('auto_publish_as_draft', v)}
                    />
                    <span className={`text-xs font-medium ${settings.auto_publish_as_draft ? 'text-amber-600' : 'text-emerald-600'}`}>
                        {settings.auto_publish_as_draft ? '📝 Drafts → you review' : '🚀 Direct publish'}
                    </span>
                </div>
            </SettingRow>

            {/* Eligibility indicator */}
            {eligibleStats && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                    <div className="bg-indigo-50 rounded-lg p-3 border border-indigo-100">
                        <p className="text-sm font-bold text-indigo-900 mb-1">
                            📊 {eligibleStats.total} articles eligible
                        </p>
                        <div className="flex flex-wrap gap-2 text-xs font-semibold">
                            <span className="text-emerald-700">✅ {eligibleStats.safe} safe</span>
                            <span className="text-amber-700">🟡 {eligibleStats.review} review</span>
                            {eligibleStats.unsafe > 0 && (
                                <span className="text-red-700">🔴 {eligibleStats.unsafe} unsafe{settings.auto_publish_require_safe_feed ? ' (blocked)' : ''}</span>
                            )}
                        </div>
                    </div>
                </div>
            )}

            <div className="mt-3 pt-3 border-t border-gray-100">
                <Link href="/admin/articles" className="text-xs font-bold text-indigo-600 hover:text-indigo-800 transition-colors">📝 View Articles →</Link>
            </div>
        </ModuleCard>
    );
}
