import Link from 'next/link';
import { AutomationSettings } from '../types';
import { ModuleCard, SettingRow, NumberInput } from './ui';

interface Props {
    settings: AutomationSettings;
    saving: boolean;
    updateSetting: (key: string, value: any) => void;
}

export function ComparisonsCard({
    settings,
    saving,
    updateSetting,
}: Props) {
    return (
        <ModuleCard
            title="🆚 Comparison Articles"
            enabled={settings.comparison_enabled}
            onToggle={(v) => updateSetting('comparison_enabled', v)}
            lastRun={settings.comparison_last_run}
            lastStatus={settings.comparison_last_status || `${settings.comparison_this_week_count || 0}/${settings.comparison_max_per_week || 2} this week`}
            saving={saving}
        >
            <SettingRow label="Max per week">
                <NumberInput
                    value={settings.comparison_max_per_week}
                    onSave={(v) => updateSetting('comparison_max_per_week', v)}
                    min={1} max={10} fallback={2}
                />
            </SettingRow>
            <SettingRow label="AI Provider">
                <select
                    value={settings.comparison_provider || 'gemini'}
                    onChange={(e) => updateSetting('comparison_provider', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 font-medium text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                >
                    <option value="gemini">Gemini</option>
                    <option value="groq">Groq (Free)</option>
                </select>
            </SettingRow>
            <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 leading-relaxed border border-gray-100 mt-2">
                <p className="font-bold text-gray-800 mb-1">How it works:</p>
                <div className="space-y-0.5 text-xs">
                    <p>1️⃣ Picks top-scoring pairs with <strong>different cars each week</strong></p>
                    <p>2️⃣ Generates comparison article with specs table + analysis</p>
                    <p>3️⃣ Adds photo credit + links to original reviews</p>
                    <p>4️⃣ Creates as <strong>draft</strong> for your review</p>
                </div>
            </div>
            <div className="mt-3 pt-3 border-t border-gray-100">
                <Link href="/admin/comparisons" className="text-xs font-bold text-indigo-600 hover:text-indigo-800 transition-colors">🆚 Manage Comparisons →</Link>
            </div>
        </ModuleCard>
    );
}
