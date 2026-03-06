'use client';

import { useEffect, useRef, useCallback } from 'react';

// Admin idle timeout: 60 minutes of inactivity → auto-logout
const IDLE_TIMEOUT_MS = 60 * 60 * 1000;   // 60 min
const WARN_BEFORE_MS = 2 * 60 * 1000;   // show warning 2 min before logout
const ACTIVITY_EVENTS = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart', 'click'];
const LAST_ACTIVE_KEY = 'admin_last_active';

interface Options {
    /** Called 2 minutes before logout — show your warning modal */
    onWarn: () => void;
    /** Called on logout */
    onLogout: () => void;
    /** Whether the hook should be active (e.g. only for is_staff users) */
    enabled: boolean;
}

export function useIdleTimeout({ onWarn, onLogout, enabled }: Options) {
    const logoutTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
    const warnTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
    const warned = useRef(false);

    const clearTimers = useCallback(() => {
        if (logoutTimer.current) clearTimeout(logoutTimer.current);
        if (warnTimer.current) clearTimeout(warnTimer.current);
    }, []);

    const resetTimers = useCallback(() => {
        if (!enabled) return;

        clearTimers();
        warned.current = false;

        // Persist last activity time across tabs
        localStorage.setItem(LAST_ACTIVE_KEY, Date.now().toString());

        // Warning fires 2 min before the logout deadline
        warnTimer.current = setTimeout(() => {
            warned.current = true;
            onWarn();
        }, IDLE_TIMEOUT_MS - WARN_BEFORE_MS);

        // Logout fires at deadline
        logoutTimer.current = setTimeout(() => {
            onLogout();
        }, IDLE_TIMEOUT_MS);
    }, [enabled, clearTimers, onWarn, onLogout]);

    useEffect(() => {
        if (!enabled) return;

        // Check if we're already past the idle deadline (e.g. returning to tab after long absence)
        const lastActive = parseInt(localStorage.getItem(LAST_ACTIVE_KEY) || '0', 10);
        const elapsed = Date.now() - lastActive;
        if (lastActive > 0 && elapsed >= IDLE_TIMEOUT_MS) {
            onLogout();
            return;
        }

        // Attach activity listeners
        const handler = () => resetTimers();
        ACTIVITY_EVENTS.forEach(evt => window.addEventListener(evt, handler, { passive: true }));

        // Also listen for storage changes (activity in another tab resets our timer too)
        const storageHandler = (e: StorageEvent) => {
            if (e.key === LAST_ACTIVE_KEY) {
                clearTimers();
                warned.current = false;
                // Recalculate remaining time from the updated timestamp
                const ts = parseInt(e.newValue || '0', 10);
                const remaining = IDLE_TIMEOUT_MS - (Date.now() - ts);
                if (remaining > WARN_BEFORE_MS) {
                    warnTimer.current = setTimeout(() => { warned.current = true; onWarn(); }, remaining - WARN_BEFORE_MS);
                    logoutTimer.current = setTimeout(onLogout, remaining);
                } else if (remaining > 0) {
                    // Already past warning threshold
                    onWarn();
                    logoutTimer.current = setTimeout(onLogout, remaining);
                } else {
                    onLogout();
                }
            }
        };
        window.addEventListener('storage', storageHandler);

        // Start timers from now
        resetTimers();

        return () => {
            ACTIVITY_EVENTS.forEach(evt => window.removeEventListener(evt, handler));
            window.removeEventListener('storage', storageHandler);
            clearTimers();
        };
    }, [enabled]);  // eslint-disable-line react-hooks/exhaustive-deps

    /** Call this when the user clicks "Stay logged in" in the warning modal */
    const extendSession = useCallback(() => {
        resetTimers();
    }, [resetTimers]);

    return { extendSession };
}
