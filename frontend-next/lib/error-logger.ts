/**
 * Frontend Telemetry & Error Logger
 * 
 * Core error shipping module — sends events to Django backend:
 *   POST /api/v1/frontend-events/
 * 
 * Global error handlers live in ErrorProvider.tsx (window.onerror,
 * unhandledrejection, hydration, fetch interceptor).
 * 
 * This module provides:
 * - logFrontendEvent() — core sender with dedup + rate limiting
 * - logApiError()      — called by ErrorProvider + axios interceptor
 * - logReactCrash()    — called by ErrorBoundary.componentDidCatch
 */
import { getApiUrl } from './config';

interface ErrorPayload {
    error_type: 'js_error' | 'network' | 'hydration' | 'resource_404' | 'performance' | 'react_crash' | 'api_4xx' | 'api_5xx' | 'unhandled_rejection' | 'other';
    message: string;
    stack_trace?: string;
    url: string;
    user_agent: string;
    metadata?: Record<string, unknown>;
}

// Deduplication: prevent identical errors from spamming within the same session
const errorCache = new Set<string>();
const MAX_CACHE_SIZE = 200;

// Rate limiting: max N errors per minute
let errorsThisMinute = 0;
const MAX_ERRORS_PER_MINUTE = 20;
let minuteResetTimer: ReturnType<typeof setTimeout> | null = null;

function startMinuteReset() {
    if (minuteResetTimer) return;
    minuteResetTimer = setTimeout(() => {
        errorsThisMinute = 0;
        minuteResetTimer = null;
    }, 60_000);
}

/**
 * Core: send an error event to the backend.
 * Handles deduplication, rate-limiting, and graceful failure.
 */
export const logFrontendEvent = async (payload: Omit<ErrorPayload, 'url' | 'user_agent'>) => {
    if (typeof window === 'undefined') return;

    // Rate limiting
    startMinuteReset();
    if (errorsThisMinute >= MAX_ERRORS_PER_MINUTE) return;
    errorsThisMinute++;

    // Deduplication by type + message
    const errorHash = `${payload.error_type}:${payload.message.slice(0, 200)}`;
    if (errorCache.has(errorHash)) return;

    // Prevent unbounded cache growth
    if (errorCache.size >= MAX_CACHE_SIZE) {
        errorCache.clear();
    }
    errorCache.add(errorHash);

    try {
        const fullPayload: ErrorPayload = {
            ...payload,
            url: window.location.href,
            user_agent: window.navigator.userAgent,
        };

        // Truncate stack trace to avoid huge payloads
        if (fullPayload.stack_trace && fullPayload.stack_trace.length > 4000) {
            fullPayload.stack_trace = fullPayload.stack_trace.slice(0, 4000) + '\n... (truncated)';
        }

        const apiUrl = getApiUrl() + '/frontend-events/';

        // Use sendBeacon for reliability (fires even on page unload)
        if (navigator.sendBeacon) {
            const blob = new Blob([JSON.stringify(fullPayload)], { type: 'application/json' });
            navigator.sendBeacon(apiUrl, blob);
        } else {
            await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(fullPayload),
                keepalive: true,
            });
        }
    } catch {
        // Silently fail — never let the error logger cause errors
    }
};

// ═══════════════════════════════════════════════════════════════
// Specific loggers
// ═══════════════════════════════════════════════════════════════

/** Log an API error (4xx or 5xx). Called from ErrorProvider fetch interceptor + axios interceptor. */
export const logApiError = (endpoint: string, statusCode: number, statusText: string) => {
    logFrontendEvent({
        error_type: statusCode >= 500 ? 'api_5xx' : 'api_4xx',
        message: `API ${statusCode} ${statusText}: ${endpoint}`,
    });
};

/** Log a React ErrorBoundary crash. Called from ErrorBoundary.componentDidCatch. */
export const logReactCrash = (error: Error, componentStack?: string) => {
    logFrontendEvent({
        error_type: 'react_crash',
        message: `React crash: ${error.message}`,
        stack_trace: (error.stack || '') + (componentStack ? `\n\nComponent Stack:\n${componentStack}` : ''),
    });
};
