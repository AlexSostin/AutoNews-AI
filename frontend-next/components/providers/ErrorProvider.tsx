'use client';

import { useEffect, type ReactNode } from 'react';
import { logFrontendEvent, logApiError } from '@/lib/error-logger';

export default function ErrorProvider({ children }: { children: ReactNode }) {
    useEffect(() => {
        // 1. Catch unhandled JS Exceptions (Syntax, runtime, third-party)
        const handleWindowError = (event: ErrorEvent) => {
            // Ignore cross-origin scripting errors (too noisy, no stack trace)
            if (event.message === 'Script error.') return;

            logFrontendEvent({
                error_type: 'js_error',
                message: event.message || 'Unknown JS Error',
                stack_trace: event.error?.stack || undefined,
            });
        };

        // 2. Catch unhandled Promises (Fetch failures, async exceptions)
        const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
            let message = 'Unhandled Promise Rejection';
            let stack_trace = undefined;
            let error_type: 'network' | 'js_error' | 'other' = 'other';

            if (event.reason instanceof Error) {
                message = event.reason.message;
                stack_trace = event.reason.stack;
                if (message.includes('fetch') || message.includes('network')) {
                    error_type = 'network';
                } else {
                    error_type = 'js_error';
                }
            } else if (typeof event.reason === 'string') {
                message = event.reason;
            } else {
                message = JSON.stringify(event.reason);
            }

            logFrontendEvent({
                error_type,
                message,
                stack_trace,
            });
        };

        // 3. Catch Next.js Hydration Mismatches
        // Hydration errors are tricky. They often fire as console.error before boundaries catch them.
        const originalConsoleError = console.error;
        console.error = (...args: any[]) => {
            originalConsoleError.apply(console, args);

            const message = args.join(' ');
            if (
                message.includes('Hydration failed') ||
                message.includes('React Hydration Error') ||
                message.includes('Text content does not match server-rendered HTML')
            ) {
                logFrontendEvent({
                    error_type: 'hydration',
                    message: 'React Hydration Mismatch',
                    stack_trace: args.join('\n'),
                });
            }
        };

        // 4. Global fetch interceptor — catch ALL 4xx/5xx API responses silently
        const originalFetch = window.fetch;
        window.fetch = async (...args: Parameters<typeof fetch>) => {
            const response = await originalFetch(...args);
            if (response.status >= 400 && response.status !== 401) {
                const input = args[0];
                const url = typeof input === 'string' ? input : input instanceof Request ? input.url : input.toString();
                // Skip logging requests to /frontend-events/ to avoid infinite loops
                if (!url.includes('frontend-events')) {
                    logApiError(url, response.status, response.statusText);
                }
            }
            return response;
        };

        window.addEventListener('error', handleWindowError);
        window.addEventListener('unhandledrejection', handleUnhandledRejection);

        return () => {
            window.removeEventListener('error', handleWindowError);
            window.removeEventListener('unhandledrejection', handleUnhandledRejection);
            console.error = originalConsoleError;
            window.fetch = originalFetch;
        };
    }, []);

    return <>{children}</>;
}
