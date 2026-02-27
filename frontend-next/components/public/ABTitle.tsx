'use client';

interface ABTitleProps {
    articleSlug: string;
    originalTitle: string;
    className?: string;
}

/**
 * A/B Title component — DISABLED.
 * Previously replaced article title with A/B variant.
 * Now just returns the original title to avoid stale title overrides.
 * Re-enable when traffic justifies A/B testing.
 */
export default function ABTitle({ originalTitle, className }: ABTitleProps) {
    return <span className={className}>{originalTitle}</span>;
}
