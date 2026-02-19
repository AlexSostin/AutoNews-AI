'use client';

import { useEffect } from 'react';
import { onCLS, onFCP, onLCP, onTTFB, onINP, type Metric } from 'web-vitals';

/**
 * Reports Core Web Vitals metrics to Google Analytics 4.
 * Metrics tracked: LCP, FCP, CLS, TTFB, INP
 * 
 * These appear in GA4 under Events → web_vitals
 * and feed into Google's Core Web Vitals assessment.
 */
function sendToGA(metric: Metric) {
    if (typeof window === 'undefined' || !(window as any).gtag) return;

    (window as any).gtag('event', metric.name, {
        event_category: 'Web Vitals',
        event_label: metric.id,
        // Google Analytics expects integers, round to nearest ms
        value: Math.round(metric.name === 'CLS' ? metric.value * 1000 : metric.value),
        // Send as non-interaction so it doesn't affect bounce rate
        non_interaction: true,
        // Custom dimensions for detailed analysis
        metric_id: metric.id,
        metric_value: metric.value,
        metric_delta: metric.delta,
        metric_rating: metric.rating, // 'good', 'needs-improvement', 'poor'
    });
}

export default function WebVitals() {
    useEffect(() => {
        // Core Web Vitals
        onCLS(sendToGA);
        onLCP(sendToGA);
        onINP(sendToGA);

        // Additional metrics
        onFCP(sendToGA);
        onTTFB(sendToGA);
    }, []);

    return null;
}
