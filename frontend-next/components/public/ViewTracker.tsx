'use client';

import { useEffect, useRef } from 'react';

interface ViewTrackerProps {
  articleSlug: string;
}

export default function ViewTracker({ articleSlug }: ViewTrackerProps) {
  const tracked = useRef(false);

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
      return 'http://localhost:8001/api/v1';
    };

    // Small delay to avoid counting quick bounces
    const timer = setTimeout(() => {
      fetch(`${getApiUrl()}/articles/${articleSlug}/increment_views/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      }).catch(err => {
        // Silent fail - view tracking is not critical
        console.debug('View tracking failed:', err);
      });
    }, 2000); // 2 second delay before counting view

    return () => clearTimeout(timer);
  }, [articleSlug]);

  // This component renders nothing
  return null;
}
