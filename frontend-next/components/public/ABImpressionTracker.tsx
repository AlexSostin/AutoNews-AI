'use client';

import { useEffect, useRef } from 'react';
import { trackImpression } from '@/lib/ab-tracking';

interface ABImpressionTrackerProps {
    variantId?: number | null;
    imageVariantId?: number | null;
}

/**
 * Fires a single impression event when the article page is rendered.
 * Only fires once per mount (StrictMode-safe via ref).
 */
export default function ABImpressionTracker({ variantId, imageVariantId }: ABImpressionTrackerProps) {
    const sentTitle = useRef(false);
    const sentImage = useRef(false);

    useEffect(() => {
        if (variantId && !sentTitle.current) {
            sentTitle.current = true;
            trackImpression(variantId, 'title');
        }
        if (imageVariantId && !sentImage.current) {
            sentImage.current = true;
            trackImpression(imageVariantId, 'image');
        }
    }, [variantId, imageVariantId]);

    return null;
}
