'use client';

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';

// ---------- Theme definitions ----------
export interface ThemeDef {
    id: string;
    name: string;
    color: string;  // preview dot color
    emoji: string;
}

export const THEMES: ThemeDef[] = [
    { id: '', name: 'Indigo', color: '#6366f1', emoji: '🟣' },
    { id: 'midnight-green', name: 'Emerald', color: '#10b981', emoji: '🟢' },
    { id: 'deep-ocean', name: 'Ocean Blue', color: '#3b82f6', emoji: '🔵' },
];

// ---------- API ----------
const getApiBase = () => {
    if (typeof window === 'undefined') return '';
    const h = window.location.hostname;
    return (h === 'localhost' || h === '127.0.0.1')
        ? 'http://localhost:8000/api/v1'
        : 'https://heroic-healing-production-2365.up.railway.app/api/v1';
};

// ---------- Context ----------
interface ThemeContextValue {
    theme: string;           // current active theme id ('' = default indigo)
    defaultTheme: string;    // admin-set default
    setTheme: (id: string) => void;
    themes: ThemeDef[];
}

const ThemeContext = createContext<ThemeContextValue>({
    theme: '',
    defaultTheme: '',
    setTheme: () => { },
    themes: THEMES,
});

export const useTheme = () => useContext(ThemeContext);

// ---------- Provider ----------
export default function ThemeContextProvider({ children }: { children: ReactNode }) {
    const [theme, setThemeState] = useState('');
    const [defaultTheme, setDefaultTheme] = useState('');

    // Apply theme to <html>
    const applyTheme = useCallback((id: string) => {
        if (id) {
            document.documentElement.setAttribute('data-theme', id);
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
    }, []);

    // User selects a theme
    const setTheme = useCallback((id: string) => {
        setThemeState(id);
        applyTheme(id);
        localStorage.setItem('user-theme-choice', id);

        // Fire analytics (fire-and-forget)
        try {
            const apiBase = getApiBase();
            if (apiBase) {
                fetch(`${apiBase}/site/theme-analytics/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ theme: id || 'default' }),
                }).catch(() => { });
            }
        } catch { }
    }, [applyTheme]);

    // On mount: resolve which theme to use
    useEffect(() => {
        const apiBase = getApiBase();

        // 1. Check if user previously chose a theme
        const userChoice = localStorage.getItem('user-theme-choice');

        // 2. Fetch admin default from API
        if (apiBase) {
            fetch(`${apiBase}/site/theme/`)
                .then(res => res.ok ? res.json() : null)
                .then(data => {
                    const adminTheme = data?.theme || '';
                    setDefaultTheme(adminTheme);

                    // Use user's choice if they made one, otherwise admin default
                    if (userChoice !== null) {
                        setThemeState(userChoice);
                        applyTheme(userChoice);
                    } else {
                        setThemeState(adminTheme);
                        applyTheme(adminTheme);
                    }
                })
                .catch(() => {
                    // API failed — use user choice or cached admin theme
                    const cached = localStorage.getItem('site-theme') || '';
                    const active = userChoice !== null ? userChoice : cached;
                    setThemeState(active);
                    applyTheme(active);
                });
        } else {
            // SSR or no API — use user choice or nothing
            const active = userChoice || '';
            setThemeState(active);
            applyTheme(active);
        }
    }, [applyTheme]);

    return (
        <ThemeContext.Provider value={{ theme, defaultTheme, setTheme, themes: THEMES }}>
            {children}
        </ThemeContext.Provider>
    );
}
