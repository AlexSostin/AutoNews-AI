'use client';

import { useState, useEffect } from 'react';
import { getApiUrl } from '@/lib/api';

interface AdPlacement {
  id: number;
  name: string;
  position: string;
  ad_type: string;
  image: string | null;
  link: string;
  alt_text: string;
  html_code: string;
  sponsor_name: string;
  sponsor_text: string;
  is_active: boolean;
  impressions: number;
  clicks: number;
}

interface AdBannerProps {
  /** Position maps to backend AdPlacement.position */
  position?: 'header' | 'sidebar' | 'between_articles' | 'after_content' | 'footer';
  /** Legacy format prop — auto-mapped to position if position not provided */
  format?: 'leaderboard' | 'rectangle' | 'skyscraper' | 'mobile' | 'large-rectangle' | 'half-page';
  className?: string;
}

// Map legacy format strings to backend positions
const FORMAT_TO_POSITION: Record<string, string> = {
  'leaderboard': 'header',
  'rectangle': 'sidebar',
  'skyscraper': 'sidebar',
  'mobile': 'footer',
  'large-rectangle': 'after_content',
  'half-page': 'sidebar',
};

export default function AdBanner({
  position,
  format = 'rectangle',
  className = '',
}: AdBannerProps) {
  const [ads, setAds] = useState<AdPlacement[]>([]);
  const [loaded, setLoaded] = useState(false);

  const resolvedPosition = position || FORMAT_TO_POSITION[format] || 'header';

  useEffect(() => {
    const fetchAds = async () => {
      try {
        const apiUrl = getApiUrl();
        const res = await fetch(`${apiUrl}/ads/active/?position=${resolvedPosition}`);
        if (res.ok) {
          const data = await res.json();
          setAds(data.results || []);
        }
      } catch (error) {
        // Silently fail — don't break the page if ads API is down
        console.debug('Ad fetch failed:', error);
      } finally {
        setLoaded(true);
      }
    };
    fetchAds();
  }, [resolvedPosition]);

  // Don't render anything if no ads or still loading
  if (!loaded || ads.length === 0) return null;

  const handleAdClick = async (ad: AdPlacement) => {
    try {
      const apiUrl = getApiUrl();
      // Fire and forget click tracking
      fetch(`${apiUrl}/ads/${ad.id}/track-click/`, { method: 'POST' }).catch(() => { });
    } catch {
      // Ignore
    }
  };

  return (
    <div className={`ad-container ${className}`}>
      {ads.map(ad => (
        <div key={ad.id} className="relative">
          {/* Banner type */}
          {ad.ad_type === 'banner' && ad.image && (
            <a
              href={ad.link || '#'}
              target="_blank"
              rel="noopener noreferrer sponsored"
              onClick={() => handleAdClick(ad)}
              className="block rounded-xl overflow-hidden hover:opacity-95 transition-opacity"
            >
              <img
                src={ad.image.startsWith('http') ? ad.image : `${getApiUrl().replace('/api/v1', '')}/media/${ad.image}`}
                alt={ad.alt_text || ad.name}
                className="w-full h-auto object-cover"
                loading="lazy"
              />
              <span className="absolute top-2 right-2 text-[10px] text-gray-400 bg-white/80 backdrop-blur px-1.5 py-0.5 rounded font-medium uppercase tracking-wider">
                Ad
              </span>
            </a>
          )}

          {/* HTML/JS code type (AdSense, etc.) */}
          {ad.ad_type === 'html_code' && ad.html_code && (
            <div className="ad-html-container rounded-xl overflow-hidden">
              <div dangerouslySetInnerHTML={{ __html: ad.html_code }} />
              <span className="text-[10px] text-gray-400 mt-1 block text-right uppercase tracking-wider">
                Advertisement
              </span>
            </div>
          )}

          {/* Sponsored content type */}
          {ad.ad_type === 'sponsored' && (
            <a
              href={ad.link || '#'}
              target="_blank"
              rel="noopener noreferrer sponsored"
              onClick={() => handleAdClick(ad)}
              className="block bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-4 hover:shadow-md transition-all group"
            >
              <div className="flex items-center gap-1.5 mb-2">
                <span className="text-[10px] text-amber-600 font-semibold uppercase tracking-wider">
                  Sponsored
                </span>
                {ad.sponsor_name && (
                  <>
                    <span className="text-amber-300">•</span>
                    <span className="text-xs text-amber-700 font-medium">{ad.sponsor_name}</span>
                  </>
                )}
              </div>
              <div className="flex gap-4 items-start">
                {ad.image && (
                  <div className="w-20 h-20 rounded-lg overflow-hidden flex-shrink-0 bg-white">
                    <img
                      src={ad.image.startsWith('http') ? ad.image : `${getApiUrl().replace('/api/v1', '')}/media/${ad.image}`}
                      alt={ad.alt_text || ad.sponsor_name || ''}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  </div>
                )}
                {ad.sponsor_text && (
                  <p className="text-sm text-gray-700 leading-relaxed group-hover:text-gray-900 transition-colors">
                    {ad.sponsor_text}
                  </p>
                )}
              </div>
            </a>
          )}
        </div>
      ))}
    </div>
  );
}
