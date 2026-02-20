'use client';

import { useEffect } from 'react';
import { ensureABSeed } from '@/lib/ab-tracking';

/**
 * Sets the `ab_seed` cookie on first visit.
 * Mount once in the root layout — it's a no-op after the first call.
 */
export default function ABSeedProvider() {
    useEffect(() => {
        ensureABSeed();
    }, []);

    return null;
}
