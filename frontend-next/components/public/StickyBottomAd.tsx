'use client';

import { useState } from 'react';
import { X } from 'lucide-react';
import AdBanner from './AdBanner';

export default function StickyBottomAd() {
  // Hidden until actual ad is configured
  return null;

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-white shadow-2xl border-t-2 border-gray-200 py-2 px-4">
      <div className="container mx-auto flex items-center justify-center relative">
        <AdBanner format="leaderboard" />
        <button
          onClick={() => setIsVisible(false)}
          className="absolute right-0 top-1/2 -translate-y-1/2 p-2 hover:bg-gray-100 rounded-full transition-colors"
          aria-label="Close ad"
        >
          <X size={20} className="text-gray-600" />
        </button>
      </div>
    </div>
  );
}
