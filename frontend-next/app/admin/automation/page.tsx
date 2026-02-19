'use client';

import { useState, useEffect, useCallback } from 'react';
import { getApiUrl } from '@/lib/api';
import toast from 'react-hot-toast';

const API_URL = getApiUrl();

interface AutomationSettings {
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
    auto_publish_today_count: number;
    auto_publish_today_date: string | null;
    auto_publish_last_run: string | null;
    auto_image_mode: string;
    auto_image_prefer_press: boolean;
    google_indexing_enabled: boolean;
}

interface AutomationStats {
    pending_total: number;
    pending_high_quality: number;
    published_today: number;
    auto_published_today: number;
    rss_articles_today: number;
    youtube_articles_today: number;
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
                        <input
                            type="number"
                            min={1}
                            max={50}
                            value={settings.rss_max_articles_per_scan}
                            onChange={(e) => updateSetting('rss_max_articles_per_scan', parseInt(e.target.value) || 10)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 font-medium text-sm text-center focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                        />
                    </SettingRow>
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
                        <input
                            type="number"
                            min={1}
                            max={20}
                            value={settings.youtube_max_videos_per_scan}
                            onChange={(e) => updateSetting('youtube_max_videos_per_scan', parseInt(e.target.value) || 3)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 font-medium text-sm text-center focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                        />
                    </SettingRow>
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
                        <input
                            type="number"
                            min={1}
                            max={20}
                            value={settings.auto_publish_max_per_hour}
                            onChange={(e) => updateSetting('auto_publish_max_per_hour', parseInt(e.target.value) || 3)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 font-medium text-sm text-center focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                        />
                    </SettingRow>
                    <SettingRow label="Max per day">
                        <input
                            type="number"
                            min={1}
                            max={100}
                            value={settings.auto_publish_max_per_day}
                            onChange={(e) => updateSetting('auto_publish_max_per_day', parseInt(e.target.value) || 20)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 font-medium text-sm text-center focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                        />
                    </SettingRow>
                    <SettingRow label="Require image">
                        <ToggleSwitch
                            checked={settings.auto_publish_require_image}
                            onChange={(v) => updateSetting('auto_publish_require_image', v)}
                        />
                    </SettingRow>
                </ModuleCard>

                {/* Auto-Image (AI) */}
                <ModuleCard
                    title="📸 Auto-Image (AI)"
                    enabled={settings.auto_image_mode !== 'off'}
                    onToggle={(v) => updateSetting('auto_image_mode', v ? 'search_first' : 'off')}
                    lastRun={null}
                    lastStatus={settings.auto_image_mode === 'off' ? 'Disabled' : 'Find reference → AI generate'}
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
                            <p>1️⃣ Searches for car photos (press or any available)</p>
                            <p>2️⃣ Uses found photo as <strong>reference</strong> for AI</p>
                            <p>3️⃣ Publishes <strong>only the AI-generated image</strong> (no copyright)</p>
                            <p>4️⃣ If no reference found → skips</p>
                        </div>
                    </div>
                </ModuleCard>

                {/* Google Indexing */}
                <ModuleCard
                    title="🔍 Google Indexing"
                    enabled={settings.google_indexing_enabled}
                    onToggle={(v) => updateSetting('google_indexing_enabled', v)}
                    lastRun={null}
                    lastStatus="Submits on publish"
                    saving={saving}
                >
                    <p className="text-sm text-gray-600">
                        When enabled, newly published articles are automatically submitted to the Google Indexing API
                        for faster crawling and indexing.
                    </p>
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

            {/* Recent Auto-Published */}
            {stats && stats.recent_auto_published.length > 0 && (
                <div className="mt-6">
                    <h3 className="text-lg font-black text-gray-950 mb-3">🕐 Recently Auto-Published</h3>
                    <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
                        {stats.recent_auto_published.map((item, i) => (
                            <div key={item.id} className={`px-4 py-3 flex items-center justify-between ${i < stats.recent_auto_published.length - 1 ? 'border-b border-gray-100' : ''
                                }`}>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-bold text-gray-900 truncate">{item.title}</p>
                                </div>
                                <div className="flex items-center gap-3 ml-4 flex-shrink-0">
                                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${item.quality_score >= 7
                                        ? 'bg-emerald-100 text-emerald-700'
                                        : 'bg-amber-100 text-amber-700'
                                        }`}>
                                        Q: {item.quality_score}/10
                                    </span>
                                    <span className="text-xs text-gray-500 font-semibold">
                                        {timeAgo(item.published_at)}
                                    </span>
                                </div>
                            </div>
                        ))}
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

            {/* Settings */}
            <div className={`flex flex-col gap-3 ${enabled ? '' : 'opacity-40 pointer-events-none'}`}>
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
