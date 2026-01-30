'use client';

interface AdBannerProps {
  slot?: string;
  format?: 'leaderboard' | 'rectangle' | 'skyscraper' | 'mobile' | 'large-rectangle' | 'half-page';
  className?: string;
  responsive?: boolean;
}

export default function AdBanner({
  slot = 'ad-slot',
  format = 'rectangle',
  className = '',
  responsive = true
}: AdBannerProps) {

  const sizeClasses = {
    'leaderboard': 'w-full h-[90px] max-w-[728px]', // 728x90
    'rectangle': 'w-full h-[250px] max-w-[300px]', // 300x250
    'skyscraper': 'w-[160px] h-[600px]', // 160x600
    'mobile': 'w-full h-[50px] max-w-[320px]', // 320x50
    'large-rectangle': 'w-full h-[280px] max-w-[336px]', // 336x280
    'half-page': 'w-full h-[600px] max-w-[300px]', // 300x600
  };

  // Placeholder is hidden until actual ad slot is configured
  return null;

  /* Original placeholder UI - kept for future reference
  return (
    <div className={`flex items-center justify-center bg-gray-100 border border-gray-200 rounded-lg overflow-hidden ${sizeClasses[format]} ${className}`}>
      <div className="text-center p-4">
        <div className="text-xs text-gray-400 uppercase mb-2">Advertisement</div>
        <div className="text-sm text-gray-500 font-medium">
          {format === 'leaderboard' && '728 × 90'}
          {format === 'rectangle' && '300 × 250'}
          {format === 'skyscraper' && '160 × 600'}
          {format === 'mobile' && '320 × 50'}
          {format === 'large-rectangle' && '336 × 280'}
          {format === 'half-page' && '300 × 600'}
        </div>
        <div className="text-xs text-gray-400 mt-2">
          Ad Space
        </div>
      </div>
    </div>
  );
  */
}
