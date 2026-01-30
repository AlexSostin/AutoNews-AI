'use client';

import { useEffect, useState } from 'react';
import AdBanner from './AdBanner';
import { createRoot } from 'react-dom/client';

interface AdInjectorProps {
  contentId: string;
}

export default function AdInjector({ contentId }: AdInjectorProps) {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    // Check if mobile
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);

    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    // Ad injection disabled in favor of Google Auto Ads
    return;
    /*
    const articleContent = document.getElementById(contentId);
    if (!articleContent) return;
    */

    // Find all h2 headings
    const headings = articleContent.querySelectorAll('h2');

    if (headings.length < 2) return; // Need at least 2 sections

    // Mobile: insert after every 2nd h2 (indices 1, 3, 5, 7...)
    // Desktop: insert after 2nd and 4th h2 (indices 1, 3)
    const insertAfter = isMobile
      ? Array.from({ length: Math.floor(headings.length / 2) }, (_, i) => i * 2 + 1)
      : [1, 3];

    let insertedCount = 0;
    const maxAds = isMobile ? 4 : 2; // More ads on mobile

    headings.forEach((heading, index) => {
      if (insertAfter.includes(index) && insertedCount < maxAds) {
        // Find next sibling or end of section
        let insertPoint = heading.nextElementSibling;

        // Skip one paragraph after heading
        if (insertPoint && insertPoint.tagName === 'P') {
          insertPoint = insertPoint.nextElementSibling;
        }

        if (insertPoint) {
          // Create ad container
          const adContainer = document.createElement('div');
          adContainer.className = 'my-8 fade-in';
          adContainer.innerHTML = `
            <div class="text-center mb-2">
              <small class="text-gray-400 text-xs uppercase tracking-wider">Advertisement</small>
            </div>
          `;

          // Insert before the next element
          insertPoint.parentNode?.insertBefore(adContainer, insertPoint);

          // Create ad component container
          const adComponentContainer = document.createElement('div');
          adContainer.appendChild(adComponentContainer);

          // Render React component
          const root = createRoot(adComponentContainer);
          root.render(<AdBanner format="rectangle" />);

          insertedCount++;
        }
      }
    });

    // Cleanup function
    return () => {
      // Clean up injected ads
      const injectedAds = articleContent.querySelectorAll('.fade-in');
      injectedAds.forEach(ad => ad.remove());
    };
  }, [contentId, isMobile]);

  return null; // This component doesn't render anything itself
}
