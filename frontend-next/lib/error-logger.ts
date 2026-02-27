/**
 * Frontend Telemetry & Error Logger
 * 
 * Silently catches and ships unhandled frontend exceptions,
 * network failures, and hydration mismatches to the Django backend.
 */
import { getApiUrl } from './config';

interface ErrorPayload {
    error_type: 'js_error' | 'network' | 'hydration' | 'resource_404' | 'performance' | 'other';
    message: string;
    stack_trace?: string;
    url: string;
    user_agent: string;
}

// Simple memory store to throttle identical errors from spamming the backend
// within the same session/page load.
const errorCache = new Set<string>();

export const logFrontendEvent = async (payload: Omit<ErrorPayload, 'url' | 'user_agent'>) => {
    if (typeof window === 'undefined') return;

    // Create a unique hash for deduplication
    const errorHash = `${payload.error_type}:${payload.message}`;

    if (errorCache.has(errorHash)) {
        return; // Already logged this specific error during this session
    }

    errorCache.add(errorHash);

    try {
        const fullPayload: ErrorPayload = {
            ...payload,
            url: window.location.href,
            user_agent: window.navigator.userAgent,
        };

        const apiUrl = getApiUrl() + '/frontend-events/';

        // We strictly use `keepalive: true` or `sendBeacon` to ensure the 
        // request fires even if the user is actively navigating away or closing the tab.
        if (navigator.sendBeacon) {
            const blob = new Blob([JSON.stringify(fullPayload)], { type: 'application/json' });
            navigator.sendBeacon(apiUrl, blob);
        } else {
            await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(fullPayload),
                keepalive: true,
            });
        }
    } catch (err) {
        // We silently suppress errors from our own error logger to avoid infinite loops
        console.error('Failed to log telemetry event:', err);
    }
};

/**
 * Log an API 5xx error. Called from the global fetch interceptor in ErrorProvider.
 */
export const logApiError = (endpoint: string, statusCode: number, statusText: string) => {
    logFrontendEvent({
        error_type: 'network',
        message: `API ${statusCode} ${statusText}: ${endpoint}`,
    });
};
