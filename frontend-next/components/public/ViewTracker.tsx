'use client';

import { useEffect, useRef, useCallback } from 'react';
import { trackArticleView, trackArticleRead } from '@/lib/analytics';

interface ViewTrackerProps {
  articleSlug: string;
  articleId: number;
  articleTitle: string;
  categoryName?: string;
}

export default function ViewTracker({ articleSlug, articleId, articleTitle, categoryName }: ViewTrackerProps) {
  const tracked = useRef(false);
  const scrollMilestones = useRef<Set<number>>(new Set());
  const startTime = useRef<number>(Date.now());

  // Send read time to GA4 on page unload
  const sendReadTime = useCallback(() => {
    const timeSpent = Math.round((Date.now() - startTime.current) / 1000);
    if (timeSpent > 3 && typeof window !== 'undefined' && window.gtag) {
      // Use sendBeacon-compatible approach for reliable unload tracking
      window.gtag('event', 'read_time', {
        article_id: articleId,
        article_title: articleTitle,
        time_seconds: timeSpent,
        transport_type: 'beacon',
      });
    }
  }, [articleId, articleTitle]);

  useEffect(() => {
    // Only track once per page load
    if (tracked.current) return;
    tracked.current = true;

    const getApiUrl = () => {
      if (typeof window !== 'undefined') {
        const host = window.location.hostname;
        if (host !== 'localhost' && host !== '127.0.0.1') {
          return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
        }
      }
      return 'http://localhost:8000/api/v1';
    };

    // Small delay to avoid counting quick bounces
    const timer = setTimeout(() => {
      // 1. Increment view count in our DB (existing)
      fetch(`${getApiUrl()}/articles/${articleSlug}/increment_views/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      }).catch(err => {
        console.debug('View tracking failed:', err);
      });

      // 2. GA4: Track article view
      trackArticleView(articleId, articleTitle, categoryName);
    }, 2000);

    return () => clearTimeout(timer);
  }, [articleSlug, articleId, articleTitle, categoryName]);

  // Scroll depth tracking — fires GA4 event at 25%, 50%, 75%, 100%
  useEffect(() => {
    const milestones = [25, 50, 75, 100];

    const handleScroll = () => {
      const windowHeight = window.innerHeight;
      const documentHeight = document.documentElement.scrollHeight - windowHeight;
      if (documentHeight <= 0) return;

      const scrollPercent = Math.round((window.scrollY / documentHeight) * 100);

      for (const milestone of milestones) {
        if (scrollPercent >= milestone && !scrollMilestones.current.has(milestone)) {
          scrollMilestones.current.add(milestone);
          trackArticleRead(articleId, milestone);
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [articleId]);

  // Read time tracking — send on page unload
  useEffect(() => {
    window.addEventListener('beforeunload', sendReadTime);
    // Also send on visibility change (mobile: user switches tabs/apps)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        sendReadTime();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      window.removeEventListener('beforeunload', sendReadTime);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [sendReadTime]);

  // This component renders nothing
  return null;
}
