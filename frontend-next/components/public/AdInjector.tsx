'use client';

interface AdInjectorProps {
  contentId: string;
}

/**
 * AdInjector handles manual injection of ad units into article content.
 * Currently disabled in favor of Google AdSense Auto Ads.
 */
export default function AdInjector({ contentId }: AdInjectorProps) {
  // Manual ad injection is disabled while using Google Auto Ads
  return null;
}
