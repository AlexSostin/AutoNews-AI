import { useEffect, useRef } from 'react';

/**
 * Custom hook to track true article engagement: Dwell Time and Scroll Depth.
 * Sends a beacon to the backend API when the user unmounts or leaves the page.
 */
export function useReadMetrics(articleId: string | number | undefined) {
    // Track start time for dwell calculation
    const startTimeRef = useRef<number>(Date.now());

    // Track maximum scroll depth percentage (0-100)
    const maxScrollRef = useRef<number>(0);

    // Flag to ensure we only send the beacon once per session
    const beaconSentRef = useRef<boolean>(false);

    useEffect(() => {
        if (!articleId) return;

        // Reset refs when articleID changes (e.g. client side navigation)
        startTimeRef.current = Date.now();
        maxScrollRef.current = 0;
        beaconSentRef.current = false;

        // --- 1. Track Scroll Depth ---
        const handleScroll = () => {
            // Calculate how far down the page the user has scrolled
            const scrollTop = window.scrollY || document.documentElement.scrollTop;
            const windowHeight = window.innerHeight || document.documentElement.clientHeight;
            const documentHeight = document.documentElement.scrollHeight;

            // Avoid division by zero on empty pages
            if (documentHeight <= windowHeight) {
                maxScrollRef.current = 100;
                return;
            }

            const scrollPercent = Math.round((scrollTop / (documentHeight - windowHeight)) * 100);

            // Only keep the maximum depth reached
            if (scrollPercent > maxScrollRef.current) {
                maxScrollRef.current = Math.min(scrollPercent, 100); // hard cap at 100
            }
        };

        // Throttle scroll listener to save CPU
        let ticking = false;
        const scrollListener = () => {
            if (!ticking) {
                window.requestAnimationFrame(() => {
                    handleScroll();
                    ticking = false;
                });
                ticking = true;
            }
        };

        window.addEventListener('scroll', scrollListener, { passive: true });

        // --- 2. Send Beacon on Exit ---
        const sendMetrics = () => {
            if (beaconSentRef.current || !articleId) return;

            const dwellTimeSeconds = Math.round((Date.now() - startTimeRef.current) / 1000);

            // Ignore extreme outliers (bounces < 2s with < 10% scroll, or tabs left open > 2 hours)
            if ((dwellTimeSeconds < 2 && maxScrollRef.current < 10) || dwellTimeSeconds > 7200) {
                beaconSentRef.current = true; // Mark as "handled" anyway
                return;
            }

            const payload = {
                article_id: articleId,
                dwell_time_seconds: dwellTimeSeconds,
                max_scroll_depth_pct: maxScrollRef.current
            };

            try {
                // Use sendBeacon for reliable delivery when the browser tab is closing
                const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
                const beaconUrl = `${backendUrl}/analytics/read-metrics/`;

                // sendBeacon requires FormData or a Blob/String, not a raw JSON object
                const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
                navigator.sendBeacon(beaconUrl, blob);

                beaconSentRef.current = true;
            } catch (e) {
                console.error('Failed to send read metrics beacon', e);
            }
        };

        // Send when closing tab, refreshing, or navigating away natively
        window.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                sendMetrics();
            }
        });

        // Send when component unmounts (Next.js client-side routing)
        return () => {
            window.removeEventListener('scroll', scrollListener);
            sendMetrics();
        };
    }, [articleId]);
}
