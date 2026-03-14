import { AutomationSettings } from '../types';
import { ModuleCard, SettingRow, NumberInput } from './ui';

interface Props {
    settings: AutomationSettings;
    saving: boolean;
    triggering: string | null;
    updateSetting: (key: string, value: unknown) => void;
    triggerTask: (taskType: string) => void;
}

export function VehicleSpecsCard({
    settings,
    saving,
    triggering,
    updateSetting,
    triggerTask,
}: Props) {
    return (
        <ModuleCard
            title="🚗 VehicleSpecs Cards"
            enabled={settings.deep_specs_enabled}
            onToggle={(v) => updateSetting('deep_specs_enabled', v)}
            lastRun={settings.deep_specs_last_run}
            lastStatus={settings.deep_specs_last_status || `${settings.deep_specs_today_count || 0} cards created today`}
            saving={saving}
            onTrigger={() => triggerTask('deep-specs')}
            triggering={triggering === 'deep-specs'}
        >
            <SettingRow label="Check every (hours)">
                <NumberInput
                    value={settings.deep_specs_interval_hours}
                    onSave={(v) => updateSetting('deep_specs_interval_hours', v)}
                    min={2} max={48} fallback={6}
                />
            </SettingRow>
            <SettingRow label="Max per cycle">
                <NumberInput
                    value={settings.deep_specs_max_per_cycle}
                    onSave={(v) => updateSetting('deep_specs_max_per_cycle', v)}
                    min={1} max={10} fallback={3}
                />
            </SettingRow>
            <p className="text-sm text-gray-600 mt-2 flex-1">
                Auto-generates <strong className="text-gray-800">/cars/&#123;brand&#125;/&#123;model&#125;</strong> pages for published articles
                older than 24 hours that don&apos;t have a VehicleSpecs card yet. Prioritizes most-viewed articles.
            </p>
        </ModuleCard>
    );
}
