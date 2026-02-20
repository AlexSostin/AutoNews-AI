'use client';

import { useEffect, useRef } from 'react';
import { trackImpression } from '@/lib/ab-tracking';

interface ABImpressionTrackerProps {
    variantId: number | null | undefined;
}

/**
 * Fires a single impression event when the article page is rendered.
 * Only fires once per mount (StrictMode-safe via ref).
 */
export default function ABImpressionTracker({ variantId }: ABImpressionTrackerProps) {
    const sent = useRef(false);

    useEffect(() => {
        if (variantId && !sent.current) {
            sent.current = true;
            trackImpression(variantId);
        }
    }, [variantId]);

    return null;
}
