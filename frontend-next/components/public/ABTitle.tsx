'use client';

import { useState, useEffect } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ABTitleProps {
    articleSlug: string;
    originalTitle: string;
    className?: string;
}

/**
 * A/B Title component — dynamically replaces article title with
 * the assigned A/B variant (client-side only, SSR shows original for SEO).
 */
export default function ABTitle({ articleSlug, originalTitle, className }: ABTitleProps) {
    const [displayTitle, setDisplayTitle] = useState(originalTitle);

    useEffect(() => {
        const fetchABTitle = async () => {
            try {
                const res = await fetch(`${API_BASE}/articles/${articleSlug}/ab-title/`, {
                    credentials: 'include', // Send cookies
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.ab_active && data.title) {
                        setDisplayTitle(data.title);
                    }
                }
            } catch {
                // Silently fallback to original title
            }
        };

        fetchABTitle();
    }, [articleSlug]);

    return <span className={className}>{displayTitle}</span>;
}
