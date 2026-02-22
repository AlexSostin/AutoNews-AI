'use client';

import { useEffect, useState } from 'react';

const API_BASE = typeof window !== 'undefined'
    ? (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
        ? 'http://localhost:8000/api/v1'
        : 'https://heroic-healing-production-2365.up.railway.app/api/v1'
    : '';

/**
 * ThemeProvider — fetches site theme from backend and sets data-theme on <html>.
 * Cached in localStorage for instant load, updated from API on mount.
 */
export default function ThemeProvider() {
    const [loaded, setLoaded] = useState(false);

    useEffect(() => {
        // 1. Apply cached theme immediately
        const cached = localStorage.getItem('site-theme');
        if (cached) {
            document.documentElement.setAttribute('data-theme', cached);
        }

        // 2. Fetch fresh theme from API
        fetch(`${API_BASE}/site/theme/`)
            .then(res => res.json())
            .then(data => {
                const theme = data.theme || '';
                if (theme) {
                    document.documentElement.setAttribute('data-theme', theme);
                    localStorage.setItem('site-theme', theme);
                } else {
                    document.documentElement.removeAttribute('data-theme');
                    localStorage.removeItem('site-theme');
                }
            })
            .catch(() => {
                // Silently fail — use cached or default
            })
            .finally(() => setLoaded(true));
    }, []);

    return null; // This component renders nothing
}
