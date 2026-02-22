'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { getApiUrl } from '@/lib/api';
import Link from 'next/link';
import toast from 'react-hot-toast';

const API_URL = getApiUrl();

interface AutomationSettings {
    site_theme: string;
    rss_scan_enabled: boolean;
    rss_scan_interval_minutes: number;
    rss_max_articles_per_scan: number;
    rss_last_run: string | null;
    rss_last_status: string;
    rss_articles_today: number;
    youtube_scan_enabled: boolean;
    youtube_scan_interval_minutes: number;
    youtube_max_videos_per_scan: number;
    youtube_last_run: string | null;
    youtube_last_status: string;
    youtube_articles_today: number;
    auto_publish_enabled: boolean;
    auto_publish_min_quality: number;
    auto_publish_max_per_hour: number;
    auto_publish_max_per_day: number;
    auto_publish_require_image: boolean;
    auto_publish_require_safe_feed: boolean;
    auto_publish_today_count: number;
    auto_publish_last_run: string | null;
    auto_image_mode: string;
    auto_image_prefer_press: boolean;
    auto_image_last_run: string | null;
    auto_image_last_status: string;
    auto_image_today_count: number;
    google_indexing_enabled: boolean;
    google_indexing_last_run: string | null;
    google_indexing_last_status: string;
    google_indexing_today_count: number;
    rss_lock: boolean;
    youtube_lock: boolean;
    auto_publish_lock: boolean;
    score_lock: boolean;
}

interface DecisionEntry {
    id: number;
    title: string;
    decision: string;
    reason: string;
    quality_score: number;
    safety_score: string;
    image_policy: string;
    feed_name: string;
    source_type: string;
    has_image: boolean;
    source_is_youtube: boolean;
    created_at: string;
}

interface AutomationStats {
    pending_total: number;
    pending_high_quality: number;
    published_today: number;
    auto_published_today: number;
    rss_articles_today: number;
    youtube_articles_today: number;
    safety_overview: {
        safety_counts: { safe: number; review: number; unsafe: number };
        image_policy_counts: { original: number; pexels_only: number; pexels_fallback: number; unchecked: number };
        total_feeds: number;
    };
    eligible: {
        total: number;
        safe: number;
        review: number;
        unsafe: number;
    };
    recent_decisions: DecisionEntry[];
    decision_breakdown: Record<string, number>;
    total_decisions: number;
    recent_auto_published: Array<{
        id: number;
        title: string;
        quality_score: number;
        published_at: string;
    }>;
}

function timeAgo(dateStr: string | null): string {
    if (!dateStr) return 'Never';
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

export default function AutomationPage() {
    const [settings, setSettings] = useState<AutomationSettings | null>(null);
    const [stats, setStats] = useState<AutomationStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [triggering, setTriggering] = useState<string | null>(null);
    const [decisionFilter, setDecisionFilter] = useState<string>('all');

    const fetchData = useCallback(async () => {
        try {
            const token = localStorage.getItem('access_token');
            const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

            const [settingsRes, statsRes] = await Promise.all([
                fetch(`${API_URL}/automation/settings/`, { headers }),
                fetch(`${API_URL}/automation/stats/`, { headers }),
            ]);

            if (settingsRes.ok) setSettings(await settingsRes.json());
            if (statsRes.ok) setStats(await statsRes.json());
        } catch (err) {
            console.error('Failed to fetch automation data:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchData(); }, [fetchData]);

    // Auto-refresh every 30s
    useEffect(() => {
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, [fetchData]);

    const updateSetting = async (key: string, value: unknown) => {
        if (!settings) return;
        setSaving(true);
        try {
            const token = localStorage.getItem('access_token');
            const res = await fetch(`${API_URL}/automation/settings/`, {
                method: 'PUT',
                headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ [key]: value }),
            });
            if (res.ok) {
                const updated = await res.json();
                setSettings(updated);
                toast.success('Settings updated');
            } else {
                toast.error('Failed to update');
            }
        } catch {
            toast.error('Network error');
        } finally {
            setSaving(false);
        }
    };

    const triggerTask = async (taskType: string) => {
        setTriggering(taskType);
        try {
            const token = localStorage.getItem('access_token');
            const res = await fetch(`${API_URL}/automation/trigger/${taskType}/`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
            });
            if (res.ok) {
                toast.success(`${taskType} triggered!`);
                setTimeout(fetchData, 5000);
            } else if (res.status === 409) {
                toast.error(`${taskType} is already running`);
            } else {
                toast.error('Trigger failed');
            }
        } catch {
            toast.error('Network error');
        } finally {
            setTriggering(null);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[50vh]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    if (!settings) {
        return (
            <div className="p-8 text-center">
                <p className="text-red-600 font-semibold">
                    Failed to load automation settings. Make sure the backend is running and migrations are applied.
                </p>
            </div>
        );
    }

    const filteredDecisions = stats?.recent_decisions?.filter(d =>
        decisionFilter === 'all' ? true : d.decision === decisionFilter
    ) || [];

    return (
        <div>
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-2xl sm:text-3xl font-black text-gray-950">🤖 Automation</h1>
                    <p className="text-sm text-gray-600 font-medium mt-1">
                        Control RSS, YouTube, auto-publish, and AI image generation. Changes take effect on next cycle.
                    </p>
                </div>
            </div>

            {/* Stats Overview */}
            {stats && (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
                    <StatCard label="Pending Total" value={stats.pending_total} icon="📋" />
                    <StatCard label="High Quality" value={stats.pending_high_quality} icon="⭐" color="text-emerald-600" />
                    <StatCard label="Published Today" value={stats.published_today} icon="📰" color="text-blue-600" />
                    <StatCard label="Auto-Published" value={stats.auto_published_today} icon="🤖" color="text-purple-600" />
                    <StatCard label="RSS Today" value={stats.rss_articles_today} icon="📡" color="text-orange-600" />
                    <StatCard label="YouTube Today" value={stats.youtube_articles_today} icon="🎬" color="text-red-600" />
                </div>
            )}

            {/* Safety Overview Bar */}
            {stats?.safety_overview && (
                <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4 mb-6">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-black text-gray-900">🛡️ Feed Safety Overview</h3>
                        <Link href="/admin/rss-feeds" className="text-xs font-bold text-indigo-600 hover:text-indigo-800 transition-colors">
                            Manage Feeds →
                        </Link>
                    </div>
                    <div className="flex flex-wrap gap-3">
                        {/* Safety counts */}
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 rounded-lg border border-emerald-200">
                            <span className="text-sm">✅</span>
                            <span className="text-sm font-bold text-emerald-800">Safe: {stats.safety_overview.safety_counts.safe}</span>
                        </div>
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 rounded-lg border border-amber-200">
                            <span className="text-sm">🟡</span>
                            <span className="text-sm font-bold text-amber-800">Review: {stats.safety_overview.safety_counts.review}</span>
                        </div>
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 rounded-lg border border-red-200">
                            <span className="text-sm">🔴</span>
                            <span className="text-sm font-bold text-red-800">Unsafe: {stats.safety_overview.safety_counts.unsafe}</span>
                        </div>

                        <div className="w-px bg-gray-300 mx-1 self-stretch"></div>

                        {/* Image policy counts */}
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 rounded-lg border border-blue-200">
                            <span className="text-sm">📷</span>
                            <span className="text-sm font-bold text-blue-800">Original: {stats.safety_overview.image_policy_counts.original}</span>
                        </div>
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-50 rounded-lg border border-purple-200">
                            <span className="text-sm">🖼️</span>
                            <span className="text-sm font-bold text-purple-800">Pexels: {stats.safety_overview.image_policy_counts.pexels_only}</span>
                        </div>
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-indigo-50 rounded-lg border border-indigo-200">
                            <span className="text-sm">📷+🖼️</span>
                            <span className="text-sm font-bold text-indigo-800">Fallback: {stats.safety_overview.image_policy_counts.pexels_fallback}</span>
                        </div>
                        {stats.safety_overview.image_policy_counts.unchecked > 0 && (
                            <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 rounded-lg border border-gray-200">
                                <span className="text-sm">⚠️</span>
                                <span className="text-sm font-bold text-gray-600">Unchecked: {stats.safety_overview.image_policy_counts.unchecked}</span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Site Theme Picker */}
            <div className="bg-white rounded-lg shadow-md border border-gray-200 p-5 mb-6">
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h3 className="text-base font-black text-gray-900">🎨 Site Theme</h3>
                        <p className="text-xs text-gray-500 mt-1">Changes the brand color across the entire site for all visitors</p>
                    </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {[
                        { value: 'default', label: 'Default', desc: 'Indigo / Purple', colors: ['#4f46e5', '#6366f1', '#818cf8'] },
                        { value: 'midnight-green', label: 'Midnight Green', desc: 'Emerald / Teal', colors: ['#059669', '#10b981', '#34d399'] },
                        { value: 'deep-ocean', label: 'Deep Ocean', desc: 'Blue / Navy', colors: ['#2563eb', '#3b82f6', '#60a5fa'] },
                    ].map((theme) => (
                        <button
                            key={theme.value}
                            onClick={() => updateSetting('site_theme', theme.value)}
                            className={`relative p-4 rounded-xl border-2 transition-all text-left ${settings.site_theme === theme.value
                                    ? 'border-gray-900 shadow-lg scale-[1.02]'
                                    : 'border-gray-200 hover:border-gray-400 hover:shadow-md'
                                }`}
                        >
                            <div className="flex gap-1.5 mb-3">
                                {theme.colors.map((c, i) => (
                                    <div key={i} className="w-8 h-8 rounded-lg shadow-sm" style={{ backgroundColor: c }} />
                                ))}
                            </div>
                            <p className="text-sm font-black text-gray-900">{theme.label}</p>
                            <p className="text-xs text-gray-500">{theme.desc}</p>
                            {settings.site_theme === theme.value && (
                                <div className="absolute top-2 right-2 w-5 h-5 bg-gray-900 rounded-full flex items-center justify-center">
                                    <span className="text-white text-xs">✓</span>
                                </div>
                            )}
                        </button>
                    ))}
                </div>
            </div>

            {/* Module Cards Grid */}
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

                {/* Auto-Publish (upgraded) */}
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

                    {/* Eligibility indicator */}
                    {stats?.eligible && (
                        <div className="mt-3 pt-3 border-t border-gray-100">
                            <div className="bg-indigo-50 rounded-lg p-3 border border-indigo-100">
                                <p className="text-sm font-bold text-indigo-900 mb-1">
                                    📊 {stats.eligible.total} articles eligible
                                </p>
                                <div className="flex flex-wrap gap-2 text-xs font-semibold">
                                    <span className="text-emerald-700">✅ {stats.eligible.safe} safe</span>
                                    <span className="text-amber-700">🟡 {stats.eligible.review} review</span>
                                    {stats.eligible.unsafe > 0 && (
                                        <span className="text-red-700">🔴 {stats.eligible.unsafe} unsafe{settings.auto_publish_require_safe_feed ? ' (blocked)' : ''}</span>
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

                {/* Quality Scoring */}
                <div className="bg-white rounded-lg shadow-md border border-gray-200 p-5">
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
                    <p className="text-sm text-gray-600 leading-relaxed">
                        Evaluates pending articles on: content length, title quality, structure,
                        images, specs, tags, and red flags. Score 1-10. Articles ≥ <strong className="text-gray-800">{settings.auto_publish_min_quality}</strong> are
                        eligible for auto-publishing.
                    </p>
                </div>
            </div>

            {/* Decision Log */}
            {stats && (
                <div className="mt-6">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-lg font-black text-gray-950">📋 Auto-Publish Decision Log</h3>
                        <div className="flex items-center gap-2">
                            <select
                                value={decisionFilter}
                                onChange={(e) => setDecisionFilter(e.target.value)}
                                className="px-3 py-1.5 text-sm text-gray-800 font-medium border rounded-lg bg-white focus:ring-2 focus:ring-indigo-500"
                            >
                                <option value="all">All Decisions</option>
                                <option value="published">✅ Published</option>
                                <option value="skipped_quality">⏭️ Low Quality</option>
                                <option value="skipped_safety">🛡️ Unsafe Feed</option>
                                <option value="skipped_no_image">📷 No Image</option>
                                <option value="failed">❌ Failed</option>
                            </select>
                        </div>
                    </div>
                    <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
                        {filteredDecisions.length === 0 ? (
                            <div className="p-8 text-center text-gray-500">
                                <p className="text-lg mb-1">📭</p>
                                <p className="text-sm font-medium">No decisions logged yet</p>
                                <p className="text-xs text-gray-400 mt-1">Decisions will appear here after auto-publish runs</p>
                            </div>
                        ) : (
                            <div className="divide-y divide-gray-100 max-h-[400px] overflow-y-auto">
                                {filteredDecisions.map((d) => {
                                    const isPublished = d.decision === 'published';
                                    const isFailed = d.decision === 'failed';
                                    const rowBg = isPublished ? 'bg-emerald-50/50' : isFailed ? 'bg-red-50/50' : '';

                                    return (
                                        <div key={d.id} className={`px-4 py-3 flex items-center gap-3 ${rowBg}`}>
                                            {/* Decision icon */}
                                            <span className="text-lg flex-shrink-0">
                                                {isPublished ? '✅' : isFailed ? '❌' :
                                                    d.decision === 'skipped_safety' ? '🛡️' :
                                                        d.decision === 'skipped_quality' ? '⏭️' :
                                                            d.decision === 'skipped_no_image' ? '📷' : '⏸️'}
                                            </span>

                                            {/* Content */}
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-bold text-gray-900 truncate">{d.title}</p>
                                                <p className="text-xs text-gray-500 mt-0.5">{d.reason}</p>
                                            </div>

                                            {/* Meta badges */}
                                            <div className="flex items-center gap-2 flex-shrink-0">
                                                {/* Quality */}
                                                <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${d.quality_score >= 7 ? 'bg-emerald-100 text-emerald-700' :
                                                    d.quality_score >= 5 ? 'bg-amber-100 text-amber-700' :
                                                        'bg-red-100 text-red-700'
                                                    }`}>
                                                    Q:{d.quality_score}
                                                </span>

                                                {/* Safety */}
                                                {d.safety_score && (
                                                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${d.safety_score === 'safe' ? 'bg-emerald-100 text-emerald-700' :
                                                        d.safety_score === 'unsafe' ? 'bg-red-100 text-red-700' :
                                                            'bg-amber-100 text-amber-700'
                                                        }`}>
                                                        {d.safety_score === 'safe' ? '✅' : d.safety_score === 'unsafe' ? '🔴' : '🟡'}
                                                    </span>
                                                )}

                                                {/* Source type */}
                                                <span className="text-xs text-gray-400">
                                                    {d.source_is_youtube ? '🎬' : '📡'} {d.feed_name?.substring(0, 15)}
                                                </span>

                                                {/* Time */}
                                                <span className="text-xs text-gray-500 font-semibold whitespace-nowrap">
                                                    {timeAgo(d.created_at)}
                                                </span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ML Training Data Indicator */}
            {stats && stats.total_decisions > 0 && (
                <div className="mt-4 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg border border-purple-200 p-4">
                    <div className="flex items-center gap-3">
                        <span className="text-2xl">🧠</span>
                        <div className="flex-1">
                            <p className="text-sm font-black text-purple-900">ML Training Data</p>
                            <p className="text-xs text-purple-700 mt-0.5">
                                <strong>{stats.total_decisions.toLocaleString()}</strong> decisions logged
                                {stats.decision_breakdown && (
                                    <span>
                                        {' • '}
                                        <span className="text-emerald-700">{stats.decision_breakdown.published || 0} published</span>
                                        {' • '}
                                        <span className="text-amber-700">{
                                            (stats.decision_breakdown.skipped_quality || 0) +
                                            (stats.decision_breakdown.skipped_safety || 0) +
                                            (stats.decision_breakdown.skipped_no_image || 0) +
                                            (stats.decision_breakdown.skipped_limit || 0)
                                        } skipped</span>
                                        {(stats.decision_breakdown.failed || 0) > 0 && (
                                            <>
                                                {' • '}
                                                <span className="text-red-700">{stats.decision_breakdown.failed} failed</span>
                                            </>
                                        )}
                                    </span>
                                )}
                            </p>
                        </div>
                        <div className="text-right">
                            <p className="text-xs text-purple-600 font-medium">
                                Collecting features for future ML model
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}


// ========================
// Sub-components
// ========================

function StatCard({ label, value, icon, color }: { label: string; value: number; icon: string; color?: string }) {
    return (
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4 text-center">
            <div className="text-2xl mb-1">{icon}</div>
            <div className={`text-2xl font-black ${color || 'text-gray-900'}`}>{value}</div>
            <div className="text-xs text-gray-600 font-bold mt-0.5">{label}</div>
        </div>
    );
}

function ModuleCard({
    title,
    enabled,
    onToggle,
    lastRun,
    lastStatus,
    saving,
    children,
    onTrigger,
    triggering,
}: {
    title: string;
    enabled: boolean;
    onToggle: (v: boolean) => void;
    lastRun: string | null;
    lastStatus: string;
    saving: boolean;
    children: React.ReactNode;
    onTrigger?: () => void;
    triggering?: boolean;
}) {
    return (
        <div className={`bg-white rounded-lg shadow-md border-2 p-5 transition-colors ${enabled ? 'border-indigo-400' : 'border-gray-200'
            }`}>
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-base font-black text-gray-900">{title}</h3>
                <ToggleSwitch checked={enabled} onChange={onToggle} disabled={saving} />
            </div>

            {/* Status bar */}
            <div className="flex items-center justify-between text-xs font-bold bg-gray-50 rounded-lg px-3 py-2 mb-4 border border-gray-100">
                <span className="text-gray-600">{lastStatus || 'No runs yet'}</span>
                <span className="text-gray-500">{timeAgo(lastRun)}</span>
            </div>

            {/* Settings — always editable, just dimmed when OFF */}
            <div className={`flex flex-col gap-3 ${enabled ? '' : 'opacity-60'}`}>
                {children}
            </div>

            {/* Trigger button */}
            {onTrigger && (
                <button
                    onClick={onTrigger}
                    disabled={triggering || !enabled}
                    className={`mt-4 w-full py-2.5 rounded-lg font-bold text-sm transition-all ${triggering
                        ? 'bg-gray-100 text-gray-400 cursor-wait'
                        : enabled
                            ? 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200'
                            : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                        }`}
                >
                    {triggering ? '⏳ Running...' : '▶️ Run Now'}
                </button>
            )}
        </div>
    );
}

function SettingRow({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="flex items-center justify-between gap-4">
            <label className="text-sm font-bold text-gray-800 whitespace-nowrap">{label}</label>
            <div className="min-w-[140px]">{children}</div>
        </div>
    );
}

function ToggleSwitch({ checked, onChange, disabled }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
    return (
        <button
            onClick={() => !disabled && onChange(!checked)}
            className={`relative w-12 h-7 rounded-full flex-shrink-0 transition-colors ${checked ? 'bg-indigo-600' : 'bg-gray-300'
                } ${disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
        >
            <div className={`absolute top-[3px] w-5 h-5 rounded-full bg-white shadow-md transition-all ${checked ? 'left-[26px]' : 'left-[3px]'
                }`} />
        </button>
    );
}

function NumberInput({ value, onSave, min, max, fallback }: {
    value: number; onSave: (v: number) => void; min: number; max: number; fallback: number
}) {
    const [local, setLocal] = useState(String(value));
    const prevValue = useRef(value);

    // Sync from parent when settings re-fetch (e.g. 30s auto-refresh)
    useEffect(() => {
        if (value !== prevValue.current) {
            setLocal(String(value));
            prevValue.current = value;
        }
    }, [value]);

    const commit = () => {
        const num = parseInt(local) || fallback;
        const clamped = Math.max(min, Math.min(max, num));
        setLocal(String(clamped));
        if (clamped !== value) {
            onSave(clamped);
        }
    };

    return (
        <input
            type="number"
            min={min}
            max={max}
            value={local}
            onChange={(e) => setLocal(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => { if (e.key === 'Enter') commit(); }}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 font-medium text-sm text-center focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
        />
    );
}
