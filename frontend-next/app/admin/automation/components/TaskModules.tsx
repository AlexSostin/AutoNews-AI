import Link from 'next/link';
import { AutomationSettings, AutomationStats } from '../types';
import { ModuleCard, SettingRow, NumberInput, ToggleSwitch } from './ui';

interface TaskModulesProps {
    settings: AutomationSettings;
    eligibleStats: AutomationStats['eligible'] | undefined;
    saving: boolean;
    triggering: string | null;
    updateSetting: (key: string, value: unknown) => void;
    triggerTask: (taskType: string) => void;
}

export function TaskModules({
    settings,
    eligibleStats,
    saving,
    triggering,
    updateSetting,
    triggerTask
}: TaskModulesProps) {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* RSS Scanning */}
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

            {/* YouTube Scanning */}
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

            {/* Auto-Publish */}
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

            {/* Auto-Image (AI) */}
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

            {/* Google Indexing */}
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

            {/* VehicleSpecs Auto-Backfill */}
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

            {/* Quality Scoring */}
            <div className="bg-white rounded-lg shadow-md border border-gray-200 p-5 h-full flex flex-col">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-base font-black text-gray-900">📊 Quality Scoring</h3>
                    <button
                        onClick={() => triggerTask('score')}
                        disabled={triggering === 'score'}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${triggering === 'score'
                            ? 'bg-gray-100 text-gray-400 cursor-wait'
                            : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100'
                            }`}
                    >
                        {triggering === 'score' ? '⏳ Scoring...' : '🔄 Score Unscored'}
                    </button>
                </div>
                <p className="text-sm text-gray-600 leading-relaxed flex-1">
                    Evaluates pending articles on: content length, title quality, structure,
                    images, specs, tags, and red flags. Score 1-10. Articles ≥ <strong className="text-gray-800">{settings.auto_publish_min_quality}</strong> are
                    eligible for auto-publishing.
                </p>
            </div>
        </div>
    );
}
