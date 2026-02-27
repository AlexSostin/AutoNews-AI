'use client';

import { usePageAnalytics } from '@/hooks/usePageAnalytics';

type PageType =
    | 'home' | 'articles' | 'article_detail' | 'trending'
    | 'cars' | 'car_detail' | 'compare' | 'categories'
    | 'category_detail' | 'other';

/**
 * Drop-in client component for page-level analytics tracking.
 * Renders nothing — just activates the usePageAnalytics hook.
 * 
 * Usage in server components:
 *   <PageAnalyticsTracker pageType="home" />
 */
export default function PageAnalyticsTracker({ pageType }: { pageType: PageType }) {
    usePageAnalytics(pageType);
    return null;
}
