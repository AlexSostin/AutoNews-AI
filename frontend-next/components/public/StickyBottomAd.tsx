'use client';

/**
 * StickyBottomAd shows a fixed advertisement at the bottom of the screen.
 * Currently disabled — footer ads are handled inline by AdBanner components.
 * To enable a sticky bottom ad, uncomment the code below.
 */
export default function StickyBottomAd() {
  // Disabled to avoid duplicate footer ads.
  // Footer position ads are already shown inline on each page.
  return null;

  /* Uncomment to enable sticky bottom ad:
  import AdBanner from '@/components/public/AdBanner';
  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 flex justify-center pointer-events-none">
      <div className="pointer-events-auto">
        <AdBanner position="footer" className="max-w-[728px]" />
      </div>
    </div>
  );
  */
}
