'use client';

import { useState, useRef, useEffect } from 'react';
import { useTheme } from './ThemeProvider';
import { Check, Palette } from 'lucide-react';

/**
 * ThemeSwitcher — compact color-dot dropdown for switching site themes.
 * Shows 3 colored dots; active theme has a checkmark.
 */
export default function ThemeSwitcher() {
    const { theme, setTheme, themes } = useTheme();
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    // Close on outside click
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    return (
        <div ref={ref} className="relative">
            <button
                onClick={() => setOpen(!open)}
                className="flex items-center gap-1.5 px-2.5 py-2 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-all"
                title="Change color theme"
                aria-label="Change color theme"
            >
                <Palette size={18} />
            </button>

            {open && (
                <div className="absolute right-0 top-full mt-2 bg-white rounded-xl shadow-2xl border border-gray-200 p-3 min-w-[180px] z-50 animate-in fade-in slide-in-from-top-2 duration-200">
                    <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2 px-1">
                        Color Theme
                    </div>
                    {themes.map((t) => (
                        <button
                            key={t.id}
                            onClick={() => {
                                setTheme(t.id);
                                setOpen(false);
                            }}
                            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${theme === t.id
                                ? 'bg-gray-100 font-bold text-gray-900'
                                : 'text-gray-600 hover:bg-gray-50'
                                }`}
                        >
                            <span
                                className="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0"
                                style={{
                                    backgroundColor: t.color,
                                    borderColor: theme === t.id ? t.color : 'transparent',
                                    boxShadow: theme === t.id ? `0 0 0 2px white, 0 0 0 4px ${t.color}` : 'none',
                                }}
                            >
                                {theme === t.id && (
                                    <Check size={12} className="text-white" strokeWidth={3} />
                                )}
                            </span>
                            <span>{t.name}</span>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
