import { AutomationSettings } from '../types';
import { ModuleCard, SettingRow, ToggleSwitch } from './ui';

interface Props {
    settings: AutomationSettings;
    saving: boolean;
    updateSetting: (key: string, value: unknown) => void;
}

export function AutoImageCard({
    settings,
    saving,
    updateSetting,
}: Props) {
    return (
        <ModuleCard
            title="📸 Auto-Image (AI)"
            enabled={settings.auto_image_mode !== 'off'}
            onToggle={(v) => updateSetting('auto_image_mode', v ? 'search_first' : 'off')}
            lastRun={settings.auto_image_last_run}
            lastStatus={settings.auto_image_mode === 'off' ? 'Disabled' : (settings.auto_image_last_status || `${settings.auto_image_today_count || 0} images today`)}
            saving={saving}
        >
            <SettingRow label="Prefer press photos">
                <ToggleSwitch
                    checked={settings.auto_image_prefer_press}
                    onChange={(v) => updateSetting('auto_image_prefer_press', v)}
                />
            </SettingRow>
            <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 leading-relaxed border border-gray-100">
                <p className="font-bold text-gray-800 mb-1">How it works:</p>
                <div className="space-y-0.5">
                    <p>1️⃣ Uses feed&apos;s <strong>image_policy</strong> to decide source</p>
                    <p>2️⃣ <strong>Original</strong>: uses press photos directly</p>
                    <p>3️⃣ <strong>Pexels</strong>: searches Pexels for matching photo</p>
                    <p>4️⃣ <strong>Fallback</strong>: tries original, falls back to Pexels</p>
                </div>
            </div>
        </ModuleCard>
    );
}
