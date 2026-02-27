'use client';

import { useEffect, useRef } from 'react';

type PageType =
    | 'home' | 'articles' | 'article_detail' | 'trending'
    | 'cars' | 'car_detail' | 'compare' | 'categories'
    | 'category_detail' | 'other';

type EventType =
    | 'page_view' | 'page_leave' | 'card_click' | 'search'
    | 'filter_use' | 'recommended_impression' | 'recommended_click'
    | 'compare_use' | 'infinite_scroll' | 'ad_impression' | 'ad_click';

interface AnalyticsEvent {
    event_type: EventType;
    page_type: PageType;
    page_url?: string;
    metrics?: Record<string, unknown>;
    referrer_page?: string;
    device_type?: string;
    viewport_width?: number;
    session_hash?: string;
}

// Detect device type from viewport width
const getDeviceType = (): string => {
    if (typeof window === 'undefined') return 'unknown';
    const w = window.innerWidth;
    if (w < 768) return 'mobile';
    if (w < 1024) return 'tablet';
    return 'desktop';
};

// Generate session hash (anonymous, persistent per session)
const getSessionHash = (): string => {
    if (typeof window === 'undefined') return '';
    let hash = sessionStorage.getItem('_analytics_session');
    if (!hash) {
        hash = Math.random().toString(36).substring(2) + Date.now().toString(36);
        sessionStorage.setItem('_analytics_session', hash);
    }
    return hash;
};

// Get the internal referrer (what page the user came from within the site)
const getReferrer = (): string => {
    if (typeof document === 'undefined') return 'direct';
    const ref = document.referrer;
    if (!ref) return 'direct';
    try {
        const url = new URL(ref);
        if (url.hostname !== window.location.hostname) return 'external';
        const path = url.pathname;
        if (path === '/') return 'home';
        if (path.startsWith('/articles') && path.split('/').length > 2) return 'article_detail';
        if (path.startsWith('/articles')) return 'articles';
        if (path.startsWith('/trending')) return 'trending';
        if (path.startsWith('/cars')) return 'cars';
        if (path.startsWith('/compare')) return 'compare';
        if (path.startsWith('/categories')) return 'categories';
        return 'other';
    } catch {
        return 'direct';
    }
};

const getApiUrl = () => {
    if (typeof window === 'undefined') return 'http://localhost:8000/api/v1';
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://localhost:8000/api/v1';
    }
    return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
};

/**
 * Send analytics events to the backend.
 * Uses sendBeacon for page-leave events (reliable on tab close), fetch for others.
 */
export function sendAnalyticsEvent(events: AnalyticsEvent[]) {
    if (!events.length) return;

    const enrichedEvents = events.map(e => ({
        ...e,
        page_url: e.page_url || (typeof window !== 'undefined' ? window.location.pathname : ''),
        device_type: e.device_type || getDeviceType(),
        viewport_width: e.viewport_width || (typeof window !== 'undefined' ? window.innerWidth : 0),
        session_hash: e.session_hash || getSessionHash(),
        referrer_page: e.referrer_page || getReferrer(),
    }));

    const payload = JSON.stringify({ events: enrichedEvents });
    const url = `${getApiUrl()}/analytics/page-events/`;

    try {
        // For page_leave events, use sendBeacon (works during tab close)
        if (enrichedEvents.some(e => e.event_type === 'page_leave')) {
            const blob = new Blob([payload], { type: 'application/json' });
            navigator.sendBeacon(url, blob);
        } else {
            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: payload,
                keepalive: true, // Allows delivery even on page unload
            }).catch(() => { }); // Fire and forget
        }
    } catch {
        // Silently fail — analytics should never break the UI
    }
}

/**
 * Send a single analytics event. Convenience wrapper.
 */
export function trackEvent(
    eventType: EventType,
    pageType: PageType,
    metrics?: Record<string, unknown>
) {
    sendAnalyticsEvent([{
        event_type: eventType,
        page_type: pageType,
        metrics,
    }]);
}

/**
 * Hook for automatic page-level engagement tracking.
 * Tracks: page view, dwell time, scroll depth, device type on page leave.
 */
export function usePageAnalytics(pageType: PageType) {
    const startTimeRef = useRef<number>(Date.now());
    const maxScrollRef = useRef<number>(0);
    const beaconSentRef = useRef<boolean>(false);
    const infiniteLoadsRef = useRef<number>(0);

    useEffect(() => {
        if (typeof window === 'undefined') return;

        // Reset on pageType change
        startTimeRef.current = Date.now();
        maxScrollRef.current = 0;
        beaconSentRef.current = false;
        infiniteLoadsRef.current = 0;

        // Send page_view event
        sendAnalyticsEvent([{
            event_type: 'page_view',
            page_type: pageType,
        }]);

        // --- Track scroll depth ---
        let ticking = false;
        const onScroll = () => {
            if (!ticking) {
                window.requestAnimationFrame(() => {
                    const scrollTop = window.scrollY;
                    const windowHeight = window.innerHeight;
                    const docHeight = document.documentElement.scrollHeight;

                    if (docHeight <= windowHeight) {
                        maxScrollRef.current = 100;
                    } else {
                        const pct = Math.round((scrollTop / (docHeight - windowHeight)) * 100);
                        if (pct > maxScrollRef.current) {
                            maxScrollRef.current = Math.min(pct, 100);
                        }
                    }
                    ticking = false;
                });
                ticking = true;
            }
        };

        window.addEventListener('scroll', onScroll, { passive: true });

        // --- Send page_leave on exit ---
        const sendPageLeave = () => {
            if (beaconSentRef.current) return;

            const dwellSeconds = Math.round((Date.now() - startTimeRef.current) / 1000);

            // Skip bounces and zombie tabs
            if ((dwellSeconds < 2 && maxScrollRef.current < 5) || dwellSeconds > 7200) {
                beaconSentRef.current = true;
                return;
            }

            sendAnalyticsEvent([{
                event_type: 'page_leave',
                page_type: pageType,
                metrics: {
                    dwell_seconds: dwellSeconds,
                    scroll_depth_pct: maxScrollRef.current,
                    infinite_loads: infiniteLoadsRef.current,
                },
            }]);

            beaconSentRef.current = true;
        };

        const onVisibilityChange = () => {
            if (document.visibilityState === 'hidden') {
                sendPageLeave();
            }
        };

        window.addEventListener('visibilitychange', onVisibilityChange);

        return () => {
            window.removeEventListener('scroll', onScroll);
            window.removeEventListener('visibilitychange', onVisibilityChange);
            sendPageLeave();
        };
    }, [pageType]);

    // Expose a function to track infinite scroll loads from the listing component
    const trackInfiniteLoad = () => {
        infiniteLoadsRef.current += 1;
        sendAnalyticsEvent([{
            event_type: 'infinite_scroll',
            page_type: pageType,
            metrics: { load_number: infiniteLoadsRef.current },
        }]);
    };

    return { trackInfiniteLoad };
}
