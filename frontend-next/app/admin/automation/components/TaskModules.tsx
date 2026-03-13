import Link from 'next/link';
import { AutomationSettings, AutomationStats } from '../types';
import { ModuleCard, SettingRow, NumberInput, ToggleSwitch } from './ui';
import { EmbeddingsCard } from './EmbeddingsCard';


interface TaskModulesProps {
    settings: AutomationSettings;
    stats: AutomationStats | null;
    eligibleStats: AutomationStats['eligible'] | undefined;
    saving: boolean;
    triggering: string | null;
    updateSetting: (key: string, value: unknown) => void;
    triggerTask: (taskType: string) => void;
}

function EnrichmentReportCard({ enrichment }: { enrichment: NonNullable<AutomationStats['enrichment_report']> }) {
    const articlesProcessed = enrichment.articles_processed ?? enrichment.current ?? 0;
    const articlesTotal = enrichment.articles_total ?? enrichment.total ?? 0;
    const durationSec = enrichment.duration_seconds ?? enrichment.elapsed_seconds ?? 0;
    const tagsCreated = enrichment.tags_created ?? 0;
    const tagsMatched = enrichment.tags_matched ?? 0;
    const errorCount = enrichment.errors ?? enrichment.error_count ?? 0;
    const mode = enrichment.mode ?? 'unknown';

    return (
        <div className="space-y-2 flex-1">
            <div className="grid grid-cols-2 gap-2">
                <div className="bg-white/70 rounded-lg px-3 py-2 border border-amber-100">
                    <p className="text-xs text-gray-500 font-medium">Articles</p>
                    <p className="text-lg font-black text-amber-700">{articlesProcessed}/{articlesTotal}</p>
                </div>
                <div className="bg-white/70 rounded-lg px-3 py-2 border border-amber-100">
                    <p className="text-xs text-gray-500 font-medium">Duration</p>
                    <p className="text-lg font-black text-amber-700">
                        {durationSec > 0 ? (durationSec < 60 ? `${durationSec}s` : `${Math.round(durationSec / 60)}m`) : '—'}
                    </p>
                </div>
                <div className="bg-white/70 rounded-lg px-3 py-2 border border-amber-100">
                    <p className="text-xs text-gray-500 font-medium">Tags created</p>
                    <p className="text-lg font-black text-emerald-600">+{tagsCreated}</p>
                </div>
                <div className="bg-white/70 rounded-lg px-3 py-2 border border-amber-100">
                    <p className="text-xs text-gray-500 font-medium">Tags matched</p>
                    <p className="text-lg font-black text-blue-600">+{tagsMatched}</p>
                </div>
            </div>
            {errorCount > 0 && (
                <div className="bg-red-50 rounded-lg px-3 py-2 border border-red-200">
                    <p className="text-xs font-bold text-red-700">❌ {errorCount} errors during enrichment</p>
                </div>
            )}
            <p className="text-xs text-gray-500 mt-1">
                Mode: <strong>{mode}</strong>
            </p>
        </div>
    );
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

            {/* 📱 Telegram Publishing */}
            <div className="bg-gradient-to-br from-sky-50 to-blue-50 rounded-lg shadow-md border-2 border-sky-200 p-5 h-full flex flex-col">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <h3 className="text-base font-black text-gray-900">📱 Telegram Publishing</h3>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${settings.telegram_enabled
                                ? 'bg-emerald-100 text-emerald-700 border border-emerald-200'
                                : 'bg-gray-100 text-gray-500 border border-gray-200'
                            }`}>
                            {settings.telegram_enabled ? '✅ AUTO' : '⏸️ OFF'}
                        </span>
                    </div>
                    <ToggleSwitch
                        checked={settings.telegram_enabled}
                        onChange={(v) => updateSetting('telegram_enabled', v)}
                    />
                </div>

                {/* Channel & stats */}
                <div className="grid grid-cols-2 gap-2 mb-3">
                    <div className="bg-white/70 rounded-lg px-3 py-2 border border-sky-100">
                        <p className="text-xs text-gray-500 font-medium">Channel</p>
                        <p className="text-sm font-bold text-sky-700 truncate">{settings.telegram_channel_id || '@freshmotors_news'}</p>
                    </div>
                    <div className="bg-white/70 rounded-lg px-3 py-2 border border-sky-100">
                        <p className="text-xs text-gray-500 font-medium">Today</p>
                        <p className="text-lg font-black text-sky-700">{settings.telegram_today_count || 0}</p>
                    </div>
                </div>

                {/* Last post */}
                {settings.telegram_last_run && (
                    <div className="text-xs text-gray-500 mb-2">
                        Last posted: <span className="font-semibold text-gray-700">{formatTimeAgo(settings.telegram_last_run)}</span>
                        {settings.telegram_last_status && (
                            <span className="ml-1 text-gray-400">— {settings.telegram_last_status.substring(0, 60)}</span>
                        )}
                    </div>
                )}

                {/* Settings */}
                <SettingRow label="Attach image">
                    <ToggleSwitch
                        checked={settings.telegram_post_with_image}
                        onChange={(v) => updateSetting('telegram_post_with_image', v)}
                    />
                </SettingRow>

                {/* Action buttons */}
                <div className="flex gap-2 mt-3 pt-3 border-t border-sky-200">
                    <button
                        onClick={() => triggerTask('telegram-test')}
                        disabled={triggering === 'telegram-test'}
                        className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${triggering === 'telegram-test'
                                ? 'bg-gray-100 text-gray-400 cursor-wait'
                                : 'bg-sky-100 text-sky-700 hover:bg-sky-200 border border-sky-300'
                            }`}
                    >
                        {triggering === 'telegram-test' ? '⏳ Sending...' : '🧪 Send Test'}
                    </button>
                    <button
                        onClick={() => triggerTask('telegram-send')}
                        disabled={triggering === 'telegram-send'}
                        className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${triggering === 'telegram-send'
                                ? 'bg-gray-100 text-gray-400 cursor-wait'
                                : 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200 border border-indigo-300'
                            }`}
                    >
                        {triggering === 'telegram-send' ? '⏳ Posting...' : '📤 Send Latest'}
                    </button>
                </div>

                {/* Recent posts */}
                {stats?.recent_social_posts && stats.recent_social_posts.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-sky-200">
                        <p className="text-xs font-bold text-gray-700 mb-2">Recent posts</p>
                        <div className="space-y-1.5 max-h-[140px] overflow-y-auto">
                            {stats.recent_social_posts.filter(p => p.platform === 'telegram').slice(0, 5).map((post) => (
                                <div key={post.id} className="flex items-center gap-2 text-xs bg-white/60 rounded-lg px-2.5 py-1.5 border border-sky-100">
                                    <span className={
                                        post.status === 'sent' ? 'text-emerald-600' :
                                            post.status === 'failed' ? 'text-red-600' :
                                                post.status === 'pending' ? 'text-amber-600' :
                                                    'text-gray-400'
                                    }>
                                        {post.status === 'sent' ? '✅' : post.status === 'failed' ? '❌' : post.status === 'pending' ? '⏳' : '⏩'}
                                    </span>
                                    <span className="truncate flex-1 text-gray-700 font-medium">{post.article_title}</span>
                                    <span className="text-gray-400 whitespace-nowrap">{formatTimeAgo(post.posted_at || post.created_at)}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

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
                    <EnrichmentReportCard enrichment={enrichment} />
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
            <EmbeddingsCard triggering={triggering} triggerTask={triggerTask} />

        </div>
    );
}
