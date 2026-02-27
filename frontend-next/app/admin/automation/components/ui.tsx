import { useState, useRef, useEffect } from 'react';
import { timeAgo } from '../utils';

export function StatCard({ label, value, icon, color }: { label: string; value: number; icon: string; color?: string }) {
    return (
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4 text-center">
            <div className="text-2xl mb-1">{icon}</div>
            <div className={`text-2xl font-black ${color || 'text-gray-900'}`}>{value}</div>
            <div className="text-xs text-gray-600 font-bold mt-0.5">{label}</div>
        </div>
    );
}

export function ModuleCard({
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
        <div className={`bg-white rounded-lg shadow-md border-2 p-5 transition-colors flex flex-col h-full ${enabled ? 'border-indigo-400' : 'border-gray-200'}`}>
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
            <div className={`flex flex-col gap-3 flex-1 ${enabled ? '' : 'opacity-60'}`}>
                {children}
            </div>

            {/* Trigger button */}
            {onTrigger && (
                <div className="mt-4 pt-4 border-t border-gray-100">
                    <button
                        onClick={onTrigger}
                        disabled={triggering || !enabled}
                        className={`w-full py-2.5 rounded-lg font-bold text-sm transition-all ${triggering
                            ? 'bg-gray-100 text-gray-400 cursor-wait'
                            : enabled
                                ? 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200'
                                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                            }`}
                    >
                        {triggering ? '⏳ Running...' : '▶️ Run Now'}
                    </button>
                </div>
            )}
        </div>
    );
}

export function SettingRow({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="flex items-center justify-between gap-4">
            <label className="text-sm font-bold text-gray-800 whitespace-nowrap">{label}</label>
            <div className="min-w-[140px] flex-shrink-0">{children}</div>
        </div>
    );
}

export function ToggleSwitch({ checked, onChange, disabled }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
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

export function NumberInput({ value, onSave, min, max, fallback }: {
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
