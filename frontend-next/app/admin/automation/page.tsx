'use client';

import { useState, useEffect, useCallback } from 'react';
import { getApiUrl } from '@/lib/api';
import toast from 'react-hot-toast';

import { AutomationSettings, AutomationStats } from './types';
import { StatsOverview } from './components/StatsOverview';
import { SafetyOverview } from './components/SafetyOverview';
import { SiteThemePicker } from './components/SiteThemePicker';
import { TaskModules } from './components/TaskModules';
import { DecisionLog } from './components/DecisionLog';

const API_URL = getApiUrl();

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

            <StatsOverview stats={stats} />
            <SafetyOverview stats={stats} />
            
            <SiteThemePicker 
                currentTheme={settings.site_theme} 
                onUpdateTheme={(v) => updateSetting('site_theme', v)} 
            />

            <TaskModules
                settings={settings}
                eligibleStats={stats?.eligible}
                saving={saving}
                triggering={triggering}
                updateSetting={updateSetting}
                triggerTask={triggerTask}
            />

            <DecisionLog stats={stats} />
        </div>
    );
}
