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
    error_type: 'js_error' | 'network' | 'hydration' | 'resource_404' | 'performance' | 'react_crash' | 'api_4xx' | 'api_5xx' | 'unhandled_rejection' | 'caught_error' | 'other';
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
 * Handles deduplication, rate-limiting, offline queue, and graceful failure.
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

    const fullPayload: ErrorPayload = {
        ...payload,
        url: window.location.href,
        user_agent: window.navigator.userAgent,
    };

    // Truncate stack trace to avoid huge payloads
    if (fullPayload.stack_trace && fullPayload.stack_trace.length > 4000) {
        fullPayload.stack_trace = fullPayload.stack_trace.slice(0, 4000) + '\n... (truncated)';
    }

    await sendOrQueue(fullPayload);
};

// ═══════════════════════════════════════════════════════════════
// Offline Queue — store unsent events in localStorage
// ═══════════════════════════════════════════════════════════════
const QUEUE_KEY = 'fm_error_queue';
const MAX_QUEUE_SIZE = 50;

async function sendOrQueue(payload: ErrorPayload) {
    try {
        const apiUrl = getApiUrl() + '/frontend-events/';

        // Use sendBeacon for reliability (fires even on page unload)
        if (navigator.sendBeacon) {
            const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
            const sent = navigator.sendBeacon(apiUrl, blob);
            if (!sent) throw new Error('sendBeacon returned false');
        } else {
            const res = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                keepalive: true,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
        }
    } catch {
        // Network failed — queue for later
        queueEvent(payload);
    }
}

function queueEvent(payload: ErrorPayload) {
    try {
        const raw = localStorage.getItem(QUEUE_KEY);
        const queue: ErrorPayload[] = raw ? JSON.parse(raw) : [];
        if (queue.length >= MAX_QUEUE_SIZE) queue.shift(); // drop oldest
        queue.push(payload);
        localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
    } catch { /* localStorage full or unavailable */ }
}

/** Flush any queued events (called on page load and on reconnect) */
export async function flushErrorQueue() {
    if (typeof window === 'undefined') return;
    try {
        const raw = localStorage.getItem(QUEUE_KEY);
        if (!raw) return;
        const queue: ErrorPayload[] = JSON.parse(raw);
        if (queue.length === 0) return;

        const apiUrl = getApiUrl() + '/frontend-events/';
        const remaining: ErrorPayload[] = [];

        for (const evt of queue) {
            try {
                const res = await fetch(apiUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(evt),
                });
                if (!res.ok) remaining.push(evt);
            } catch {
                remaining.push(evt);
                break; // still offline, stop trying
            }
        }

        if (remaining.length > 0) {
            localStorage.setItem(QUEUE_KEY, JSON.stringify(remaining));
        } else {
            localStorage.removeItem(QUEUE_KEY);
        }
    } catch { /* ignore */ }
}

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

/**
 * Log a caught error from a try/catch block.
 * Use this in every catch block across the site to capture "silent" failures.
 *
 * @param source - Where the error happened (e.g. 'brand_move_article', 'article_generate')
 * @param error  - The caught error object
 * @param extra  - Optional metadata (response data, IDs, etc.)
 *
 * @example
 * } catch (err) {
 *   logCaughtError('brand_move', err, { specId: 123 });
 *   setError('Move failed');
 * }
 */
export const logCaughtError = (source: string, error: unknown, extra?: Record<string, unknown>) => {
    let message = 'Unknown error';
    let stack_trace: string | undefined;

    if (error instanceof Error) {
        message = error.message;
        stack_trace = error.stack;
    } else if (typeof error === 'string') {
        message = error;
    } else {
        try { message = JSON.stringify(error); } catch { message = String(error); }
    }

    // Extract response data from axios errors
    const axiosData = (error as any)?.response?.data;
    const status = (error as any)?.response?.status;

    logFrontendEvent({
        error_type: 'caught_error',
        message: `[${source}] ${message}`,
        stack_trace,
        metadata: {
            source,
            status,
            response_data: axiosData,
            ...extra,
        },
    });
};
