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
                setTimeout(fetchData, 5000); // Refresh after 5s
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
            <div style={{ padding: '2rem', display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
                <div style={{ fontSize: '1.2rem', color: '#a0a0b0' }}>Loading automation settings...</div>
            </div>
        );
    }

    if (!settings) {
        return (
            <div style={{ padding: '2rem', color: '#ff6b6b' }}>
                Failed to load automation settings. Make sure the backend is running and migrations are applied.
            </div>
        );
    }

    return (
        <div style={{ padding: '1.5rem', maxWidth: '1200px', margin: '0 auto' }}>
            {/* Header */}
            <div style={{ marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '1.8rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    🤖 Automation Control Panel
                </h1>
                <p style={{ color: '#a0a0b0', marginTop: '0.5rem' }}>
                    Control RSS scanning, YouTube scanning, and auto-publishing from one place.
                    Changes take effect on the next scheduler cycle.
                </p>
            </div>

            {/* Stats Overview */}
            {stats && (
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                    gap: '1rem',
                    marginBottom: '2rem'
                }}>
                    <StatCard label="Pending Total" value={stats.pending_total} icon="📋" />
                    <StatCard label="High Quality" value={stats.pending_high_quality} icon="⭐" color="#4ade80" />
                    <StatCard label="Published Today" value={stats.published_today} icon="📰" color="#60a5fa" />
                    <StatCard label="Auto-Published" value={stats.auto_published_today} icon="🤖" color="#a78bfa" />
                    <StatCard label="RSS Today" value={stats.rss_articles_today} icon="📡" color="#fb923c" />
                    <StatCard label="YouTube Today" value={stats.youtube_articles_today} icon="🎬" color="#f87171" />
                </div>
            )}

            {/* Module Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '1.5rem' }}>

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
                            style={selectStyle}
                        >
                            <option value={15}>Every 15 min</option>
                            <option value={30}>Every 30 min</option>
                            <option value={60}>Every 1 hour</option>
                            <option value={120}>Every 2 hours</option>
                        </select>
                    </SettingRow>
                    <SettingRow label="Max articles per scan">
                        <input
                            type="number"
                            min={1}
                            max={50}
                            value={settings.rss_max_articles_per_scan}
                            onChange={(e) => updateSetting('rss_max_articles_per_scan', parseInt(e.target.value) || 10)}
                            style={inputStyle}
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
                            style={selectStyle}
                        >
                            <option value={60}>Every 1 hour</option>
                            <option value={120}>Every 2 hours</option>
                            <option value={240}>Every 4 hours</option>
                        </select>
                    </SettingRow>
                    <SettingRow label="Max videos per scan">
                        <input
                            type="number"
                            min={1}
                            max={20}
                            value={settings.youtube_max_videos_per_scan}
                            onChange={(e) => updateSetting('youtube_max_videos_per_scan', parseInt(e.target.value) || 3)}
                            style={inputStyle}
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
                    <SettingRow label="Min quality score">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <input
                                type="range"
                                min={1}
                                max={10}
                                value={settings.auto_publish_min_quality}
                                onChange={(e) => updateSetting('auto_publish_min_quality', parseInt(e.target.value))}
                                style={{ flex: 1 }}
                            />
                            <span style={{
                                fontSize: '1.1rem',
                                fontWeight: 700,
                                color: settings.auto_publish_min_quality >= 7 ? '#4ade80' : settings.auto_publish_min_quality >= 5 ? '#fbbf24' : '#f87171',
                                minWidth: '2.5rem',
                                textAlign: 'center'
                            }}>
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
                            style={inputStyle}
                        />
                    </SettingRow>
                    <SettingRow label="Max per day">
                        <input
                            type="number"
                            min={1}
                            max={100}
                            value={settings.auto_publish_max_per_day}
                            onChange={(e) => updateSetting('auto_publish_max_per_day', parseInt(e.target.value) || 20)}
                            style={inputStyle}
                        />
                    </SettingRow>
                    <SettingRow label="Require image">
                        <ToggleSwitch
                            checked={settings.auto_publish_require_image}
                            onChange={(v) => updateSetting('auto_publish_require_image', v)}
                        />
                    </SettingRow>
                </ModuleCard>

                {/* Google Indexing */}
                <ModuleCard
                    title="🔍 Google Indexing"
                    enabled={settings.google_indexing_enabled}
                    onToggle={(v) => updateSetting('google_indexing_enabled', v)}
                    lastRun={null}
                    lastStatus="Submits to Google on publish"
                    saving={saving}
                >
                    <p style={{ color: '#a0a0b0', fontSize: '0.85rem', margin: 0 }}>
                        When enabled, newly published articles are automatically submitted to the Google Indexing API
                        for faster crawling and indexing.
                    </p>
                </ModuleCard>
            </div>

            {/* Quality Scoring */}
            <div style={{ marginTop: '1.5rem' }}>
                <div style={{
                    background: '#1a1a2e',
                    borderRadius: '12px',
                    border: '1px solid #2a2a4a',
                    padding: '1.25rem',
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                        <h3 style={{ margin: 0, fontSize: '1.1rem' }}>📊 Quality Scoring</h3>
                        <button
                            onClick={() => triggerTask('score')}
                            disabled={triggering === 'score'}
                            style={{
                                ...btnStyle,
                                background: triggering === 'score' ? '#333' : '#3b3b5c',
                                fontSize: '0.8rem',
                                padding: '0.4rem 0.8rem',
                            }}
                        >
                            {triggering === 'score' ? '⏳ Scoring...' : '🔄 Score Unscored'}
                        </button>
                    </div>
                    <p style={{ color: '#a0a0b0', fontSize: '0.85rem', margin: 0 }}>
                        Automatically evaluates pending articles on: content length, title quality, structure,
                        images, specs, tags, and red flags. Score range: 1-10. Articles scoring ≥ {settings.auto_publish_min_quality} are
                        eligible for auto-publishing.
                    </p>
                </div>
            </div>

            {/* Recent Auto-Published */}
            {stats && stats.recent_auto_published.length > 0 && (
                <div style={{ marginTop: '1.5rem' }}>
                    <h3 style={{ fontSize: '1.1rem', marginBottom: '0.75rem' }}>🕐 Recently Auto-Published</h3>
                    <div style={{
                        background: '#1a1a2e',
                        borderRadius: '12px',
                        border: '1px solid #2a2a4a',
                        overflow: 'hidden',
                    }}>
                        {stats.recent_auto_published.map((item, i) => (
                            <div key={item.id} style={{
                                padding: '0.75rem 1rem',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                borderBottom: i < stats.recent_auto_published.length - 1 ? '1px solid #2a2a4a' : 'none',
                            }}>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ fontSize: '0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                        {item.title}
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexShrink: 0, marginLeft: '1rem' }}>
                                    <span style={{
                                        fontSize: '0.75rem',
                                        padding: '0.2rem 0.5rem',
                                        borderRadius: '4px',
                                        background: item.quality_score >= 7 ? '#064e3b' : '#7c2d12',
                                        color: item.quality_score >= 7 ? '#4ade80' : '#fb923c',
                                    }}>
                                        Q: {item.quality_score}/10
                                    </span>
                                    <span style={{ fontSize: '0.75rem', color: '#a0a0b0' }}>
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
        <div style={{
            background: '#1a1a2e',
            borderRadius: '12px',
            border: '1px solid #2a2a4a',
            padding: '1rem',
            textAlign: 'center',
        }}>
            <div style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>{icon}</div>
            <div style={{ fontSize: '1.8rem', fontWeight: 700, color: color || '#fff' }}>{value}</div>
            <div style={{ fontSize: '0.75rem', color: '#a0a0b0' }}>{label}</div>
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
        <div style={{
            background: '#1a1a2e',
            borderRadius: '12px',
            border: `1px solid ${enabled ? '#3b5bdb' : '#2a2a4a'}`,
            padding: '1.25rem',
            transition: 'border-color 0.2s ease',
        }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{title}</h3>
                <ToggleSwitch checked={enabled} onChange={onToggle} disabled={saving} />
            </div>

            {/* Status */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: '0.8rem',
                color: '#a0a0b0',
                marginBottom: '1rem',
                padding: '0.5rem 0.75rem',
                background: '#13132a',
                borderRadius: '8px',
            }}>
                <span>
                    {lastStatus || 'No runs yet'}
                </span>
                <span>
                    {timeAgo(lastRun)}
                </span>
            </div>

            {/* Settings */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', opacity: enabled ? 1 : 0.5 }}>
                {children}
            </div>

            {/* Trigger button */}
            {onTrigger && (
                <button
                    onClick={onTrigger}
                    disabled={triggering || !enabled}
                    style={{
                        ...btnStyle,
                        marginTop: '1rem',
                        width: '100%',
                        background: triggering ? '#333' : enabled ? '#3b3b5c' : '#222',
                        opacity: enabled ? 1 : 0.5,
                    }}
                >
                    {triggering ? '⏳ Running...' : '▶️ Run Now'}
                </button>
            )}
        </div>
    );
}

function SettingRow({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
            <label style={{ fontSize: '0.85rem', color: '#c0c0d0', whiteSpace: 'nowrap' }}>{label}</label>
            <div style={{ minWidth: '140px' }}>{children}</div>
        </div>
    );
}

function ToggleSwitch({ checked, onChange, disabled }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
    return (
        <button
            onClick={() => !disabled && onChange(!checked)}
            style={{
                width: '48px',
                height: '26px',
                borderRadius: '13px',
                border: 'none',
                background: checked ? '#3b5bdb' : '#3a3a5a',
                position: 'relative',
                cursor: disabled ? 'not-allowed' : 'pointer',
                transition: 'background 0.2s ease',
                flexShrink: 0,
            }}
        >
            <div style={{
                width: '20px',
                height: '20px',
                borderRadius: '50%',
                background: '#fff',
                position: 'absolute',
                top: '3px',
                left: checked ? '25px' : '3px',
                transition: 'left 0.2s ease',
            }} />
        </button>
    );
}


// ========================
// Styles
// ========================

const selectStyle: React.CSSProperties = {
    background: '#13132a',
    border: '1px solid #3a3a5a',
    borderRadius: '6px',
    color: '#e0e0f0',
    padding: '0.4rem 0.5rem',
    fontSize: '0.85rem',
    width: '100%',
};

const inputStyle: React.CSSProperties = {
    background: '#13132a',
    border: '1px solid #3a3a5a',
    borderRadius: '6px',
    color: '#e0e0f0',
    padding: '0.4rem 0.5rem',
    fontSize: '0.85rem',
    width: '100%',
    textAlign: 'center',
};

const btnStyle: React.CSSProperties = {
    background: '#3b3b5c',
    border: '1px solid #4a4a7a',
    borderRadius: '8px',
    color: '#e0e0f0',
    padding: '0.5rem 1rem',
    fontSize: '0.85rem',
    cursor: 'pointer',
    transition: 'background 0.2s ease',
};
