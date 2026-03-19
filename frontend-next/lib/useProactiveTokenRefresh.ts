'use client';

import { useEffect } from 'react';
import { getAccessToken, getTokenExpiresInMs, refreshAccessToken, logout } from './auth';

const REFRESH_THRESHOLD_MS = 10 * 60 * 1000; // 10 minutes

/**
 * Proactively refreshes the JWT access token before it expires.
 *
 * Triggers refresh when:
 * - Component mounts (page load / navigation)
 * - Window regains focus (returning from another tab/app)
 *
 * If the token has less than REFRESH_THRESHOLD_MS (10 min) remaining,
 * silently refreshes via refreshAccessToken(). If refresh fails → logout().
 *
 * Mount in admin/layout.tsx for all admin pages.
 */
export function useProactiveTokenRefresh(enabled: boolean = true) {
  useEffect(() => {
    if (!enabled || typeof window === 'undefined') return;

    const checkAndRefresh = async () => {
      const token = getAccessToken();
      if (!token) return; // Not logged in — let layout.tsx handle redirect

      const expiresInMs = getTokenExpiresInMs(token);

      // Token expired or expiring soon → refresh now
      if (expiresInMs < REFRESH_THRESHOLD_MS) {
        console.log(`🔄 Token expires in ${Math.round(expiresInMs / 1000)}s — refreshing proactively`);
        const newToken = await refreshAccessToken();
        if (!newToken) {
          console.warn('⚠️ Proactive refresh failed — logging out');
          logout();
        }
      }
    };

    // Check on mount
    checkAndRefresh();

    // Check when user returns to the tab
    window.addEventListener('focus', checkAndRefresh);
    return () => window.removeEventListener('focus', checkAndRefresh);
  }, [enabled]);
}
