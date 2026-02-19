declare module 'web-vitals' {
    export interface Metric {
        name: 'CLS' | 'FCP' | 'FID' | 'INP' | 'LCP' | 'TTFB';
        value: number;
        delta: number;
        id: string;
        rating: 'good' | 'needs-improvement' | 'poor';
        entries: PerformanceEntry[];
        navigationType: 'navigate' | 'reload' | 'back-forward' | 'back-forward-cache' | 'prerender';
    }

    type ReportCallback = (metric: Metric) => void;
    type ReportOpts = { reportAllChanges?: boolean };

    export function onCLS(callback: ReportCallback, opts?: ReportOpts): void;
    export function onFCP(callback: ReportCallback, opts?: ReportOpts): void;
    export function onFID(callback: ReportCallback, opts?: ReportOpts): void;
    export function onINP(callback: ReportCallback, opts?: ReportOpts): void;
    export function onLCP(callback: ReportCallback, opts?: ReportOpts): void;
    export function onTTFB(callback: ReportCallback, opts?: ReportOpts): void;
}
