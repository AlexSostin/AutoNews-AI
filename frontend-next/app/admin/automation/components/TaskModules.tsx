import Link from 'next/link';
import { AutomationSettings, AutomationStats } from '../types';
import { ModuleCard, SettingRow, NumberInput, ToggleSwitch } from './ui';

interface TaskModulesProps {
    settings: AutomationSettings;
    stats: AutomationStats | null;
    eligibleStats: AutomationStats['eligible'] | undefined;
    saving: boolean;
    triggering: string | null;
    updateSetting: (key: string, value: unknown) => void;
    triggerTask: (taskType: string) => void;
}

function formatTimeAgo(iso: string | null | undefined): string {
    if (!iso) return 'Never';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return 'Unknown';
    const diff = Date.now() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
}

export function TaskModules({
    settings,
    stats,
    eligibleStats,
    saving,
    triggering,
    updateSetting,
    triggerTask
}: TaskModulesProps) {
    const ml = stats?.ml_model;
    const enrichment = stats?.enrichment_report;

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

            {/* 🧠 ML Content Recommender */}
            <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-lg shadow-md border-2 border-purple-200 p-5 h-full flex flex-col">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-base font-black text-gray-900">🧠 ML Content Recommender</h3>
                    <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${ml?.trained
                        ? 'bg-emerald-100 text-emerald-700 border border-emerald-200'
                        : 'bg-gray-100 text-gray-500 border border-gray-200'
                        }`}>
                        {ml?.trained ? '✅ Trained' : '⏳ Not trained'}
                    </span>
                </div>
                {ml?.trained ? (
                    <div className="space-y-2 flex-1">
                        <div className="grid grid-cols-2 gap-2">
                            <div className="bg-white/70 rounded-lg px-3 py-2 border border-purple-100">
                                <p className="text-xs text-gray-500 font-medium">Articles</p>
                                <p className="text-lg font-black text-purple-700">{ml.article_count || 0}</p>
                            </div>
                            <div className="bg-white/70 rounded-lg px-3 py-2 border border-purple-100">
                                <p className="text-xs text-gray-500 font-medium">Features (TF-IDF)</p>
                                <p className="text-lg font-black text-purple-700">{(ml.vocabulary_size || 0).toLocaleString()}</p>
                            </div>
                            <div className="bg-white/70 rounded-lg px-3 py-2 border border-purple-100">
                                <p className="text-xs text-gray-500 font-medium">Tags</p>
                                <p className="text-lg font-black text-purple-700">{ml.unique_tags || 0}</p>
                            </div>
                            <div className="bg-white/70 rounded-lg px-3 py-2 border border-purple-100">
                                <p className="text-xs text-gray-500 font-medium">Last trained</p>
                                <p className="text-sm font-bold text-purple-700">{formatTimeAgo(ml.built_at)}</p>
                            </div>
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                            Powers similar articles, tag predictions, and content recommendations.
                        </p>
                    </div>
                ) : (
                    <p className="text-sm text-gray-600 flex-1">
                        ML model has not been trained yet. Click &quot;Retrain Now&quot; or run <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">python manage.py train_content_model</code>.
                    </p>
                )}
                <div className="mt-4 pt-4 border-t border-purple-200">
                    <button
                        onClick={() => triggerTask('ml-retrain')}
                        disabled={triggering === 'ml-retrain'}
                        className={`w-full py-2.5 rounded-lg font-bold text-sm transition-all ${triggering === 'ml-retrain'
                            ? 'bg-gray-100 text-gray-400 cursor-wait'
                            : 'bg-purple-100 text-purple-700 hover:bg-purple-200 border border-purple-300'
                            }`}
                    >
                        {triggering === 'ml-retrain' ? '⏳ Training...' : '🔄 Retrain Now'}
                    </button>
                </div>
            </div>

            {/* 📦 Bulk Enrichment Report */}
            <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-lg shadow-md border-2 border-amber-200 p-5 h-full flex flex-col">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-base font-black text-gray-900">📦 Bulk Enrichment</h3>
                    <span className="text-xs font-bold text-gray-500">
                        {enrichment ? formatTimeAgo(enrichment.last_run) : 'Never run'}
                    </span>
                </div>
                {enrichment ? (
                    <div className="space-y-2 flex-1">
                        <div className="grid grid-cols-2 gap-2">
                            <div className="bg-white/70 rounded-lg px-3 py-2 border border-amber-100">
                                <p className="text-xs text-gray-500 font-medium">Articles</p>
                                <p className="text-lg font-black text-amber-700">
                                    {enrichment.articles_processed}/{enrichment.articles_total}
                                </p>
                            </div>
                            <div className="bg-white/70 rounded-lg px-3 py-2 border border-amber-100">
                                <p className="text-xs text-gray-500 font-medium">Duration</p>
                                <p className="text-lg font-black text-amber-700">
                                    {enrichment.duration_seconds < 60
                                        ? `${enrichment.duration_seconds}s`
                                        : `${Math.round(enrichment.duration_seconds / 60)}m`}
                                </p>
                            </div>
                            <div className="bg-white/70 rounded-lg px-3 py-2 border border-amber-100">
                                <p className="text-xs text-gray-500 font-medium">Tags created</p>
                                <p className="text-lg font-black text-emerald-600">+{enrichment.tags_created}</p>
                            </div>
                            <div className="bg-white/70 rounded-lg px-3 py-2 border border-amber-100">
                                <p className="text-xs text-gray-500 font-medium">Tags matched</p>
                                <p className="text-lg font-black text-blue-600">+{enrichment.tags_matched}</p>
                            </div>
                        </div>
                        {enrichment.errors > 0 && (
                            <div className="bg-red-50 rounded-lg px-3 py-2 border border-red-200">
                                <p className="text-xs font-bold text-red-700">❌ {enrichment.errors} errors during enrichment</p>
                            </div>
                        )}
                        <p className="text-xs text-gray-500 mt-1">
                            Mode: <strong>{enrichment.mode}</strong>
                        </p>
                    </div>
                ) : (
                    <p className="text-sm text-gray-600 flex-1">
                        No enrichment reports yet. Run <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">python manage.py bulk_enrich</code> to enrich articles with Deep Specs, A/B Titles, and Smart Tags.
                    </p>
                )}
            </div>

            {/* 🧹 A/B Test Lifecycle */}
            <div className="bg-gradient-to-br from-rose-50 to-pink-50 rounded-lg shadow-md border-2 border-rose-200 p-5 h-full flex flex-col">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-base font-black text-gray-900">🧹 A/B Test Lifecycle</h3>
                    <button
                        onClick={() => triggerTask('ab-cleanup')}
                        disabled={triggering === 'ab-cleanup'}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${triggering === 'ab-cleanup'
                            ? 'bg-gray-100 text-gray-400 cursor-wait'
                            : 'bg-rose-100 text-rose-700 hover:bg-rose-200 border border-rose-300'
                            }`}
                    >
                        {triggering === 'ab-cleanup' ? '⏳ Running...' : '🔄 Run Now'}
                    </button>
                </div>
                <div className="space-y-2 flex-1">
                    <div className="flex items-start gap-2 text-sm text-gray-700">
                        <span className="shrink-0">📅</span>
                        <span><strong>Day 0-29:</strong> Test runs, data accumulates</span>
                    </div>
                    <div className="flex items-start gap-2 text-sm text-amber-700 bg-amber-50 rounded-lg px-3 py-2 border border-amber-200">
                        <span className="shrink-0">⚠️</span>
                        <span><strong>Day 30:</strong> No winner → notification «pick winner in 7 days»</span>
                    </div>
                    <div className="flex items-start gap-2 text-sm text-red-700 bg-red-50 rounded-lg px-3 py-2 border border-red-200">
                        <span className="shrink-0">🤖</span>
                        <span><strong>Day 37:</strong> Auto-pick winner by CTR → delete losers</span>
                    </div>
                    <div className="flex items-start gap-2 text-sm text-emerald-700 bg-emerald-50 rounded-lg px-3 py-2 border border-emerald-200">
                        <span className="shrink-0">✅</span>
                        <span><strong>Winner 30d+:</strong> Losers cleaned up automatically</span>
                    </div>
                </div>
                <div className="mt-3 pt-3 border-t border-rose-200">
                    <a href="/admin/ab-testing" className="text-xs font-bold text-rose-600 hover:text-rose-800 transition-colors">🧪 View A/B Tests →</a>
                </div>
            </div>

            {/* 🔍 Article Embeddings */}
            <div className="bg-gradient-to-br from-teal-50 to-cyan-50 rounded-lg shadow-md border-2 border-teal-200 p-5 h-full flex flex-col">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-base font-black text-gray-900">🔍 Article Embeddings</h3>
                    <button
                        onClick={() => triggerTask('index-articles')}
                        disabled={triggering === 'index-articles'}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${triggering === 'index-articles'
                            ? 'bg-gray-100 text-gray-400 cursor-wait'
                            : 'bg-teal-100 text-teal-700 hover:bg-teal-200 border border-teal-300'
                            }`}
                    >
                        {triggering === 'index-articles' ? '⏳ Indexing...' : '⚡ Index Articles'}
                    </button>
                </div>
                <p className="text-sm text-gray-600 leading-relaxed flex-1">
                    Vector embeddings power semantic search, ML recommendations, and deduplication.
                    Indexes all articles not yet embedded — check System Graph for current coverage.
                </p>
                <div className="mt-3 pt-3 border-t border-teal-200">
                    <a href="/admin/system-graph" className="text-xs font-bold text-teal-600 hover:text-teal-800 transition-colors">🌐 View System Graph →</a>
                </div>
            </div>

        </div>
    );
}
