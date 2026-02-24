/**
 * A/B Testing Frontend Tracking Utility
 * 
 * - Sets a persistent `ab_seed` cookie for consistent variant assignment
 * - Sends impression/click events via sendBeacon (fire-and-forget)
 */

import { getApiUrl } from './api';
const API_BASE = getApiUrl();

// ─── Cookie ─────────────────────────────────────────────────────────

/** Ensure the visitor has an `ab_seed` cookie (persists for 1 year) */
export function ensureABSeed(): string {
    if (typeof document === 'undefined') return '';

    const existing = document.cookie
        .split('; ')
        .find((c) => c.startsWith('ab_seed='))
        ?.split('=')[1];

    if (existing) return existing;

    // Generate a simple random seed
    const seed = Math.random().toString(36).slice(2) + Date.now().toString(36);
    document.cookie = `ab_seed=${seed}; path=/; max-age=${365 * 24 * 60 * 60}; SameSite=Lax`;
    return seed;
}

// ─── Tracking ───────────────────────────────────────────────────────

/** Fire an impression event for an A/B variant (non-blocking) */
export function trackImpression(variantId: number | null | undefined) {
    if (!variantId) return;

    const body = JSON.stringify({ variant_id: variantId });

    if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
        const blob = new Blob([body], { type: 'application/json' });
        navigator.sendBeacon(`${API_BASE}/ab/impression/`, blob);
    } else {
        // Fallback for older browsers
        fetch(`${API_BASE}/ab/impression/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body,
            keepalive: true,
        }).catch(() => { });
    }
}

/** Fire a click event for an A/B variant (non-blocking) */
export function trackClick(variantId: number | null | undefined) {
    if (!variantId) return;

    const body = JSON.stringify({ variant_id: variantId });

    if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
        const blob = new Blob([body], { type: 'application/json' });
        navigator.sendBeacon(`${API_BASE}/ab/click/`, blob);
    } else {
        fetch(`${API_BASE}/ab/click/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body,
            keepalive: true,
        }).catch(() => { });
    }
}
