// API Configuration with runtime detection
// Production URLs - hardcoded to avoid build-time issues
const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const PRODUCTION_MEDIA_URL = 'https://heroic-healing-production-2365.up.railway.app';
const LOCAL_API_URL = 'http://localhost:8000/api/v1';
const LOCAL_MEDIA_URL = 'http://localhost:8000';

// Check if running in production (Railway)
const isProduction = () => {
  // Server-side check
  if (typeof window === 'undefined') {
    return process.env.RAILWAY_ENVIRONMENT === 'production' || 
           process.env.NODE_ENV === 'production';
  }
  // Client-side check
  const hostname = window.location.hostname;
  return hostname !== 'localhost' && hostname !== '127.0.0.1';
};

const getRuntimeApiUrl = () => {
  if (isProduction()) {
    return PRODUCTION_API_URL;
  }
  return LOCAL_API_URL;
};

const getRuntimeMediaUrl = () => {
  if (isProduction()) {
    return PRODUCTION_MEDIA_URL;
  }
  return LOCAL_MEDIA_URL;
};

// Fix image URLs from backend (replace docker/localhost URLs with correct ones)
export const fixImageUrl = (url: string | null | undefined): string => {
  if (!url) return '/images/placeholder.jpg';
  
  const mediaUrl = isProduction() ? PRODUCTION_MEDIA_URL : LOCAL_MEDIA_URL;
  
  // Replace any backend:8000 or localhost:8000 with correct media URL
  let fixedUrl = url
    .replace('http://backend:8000', mediaUrl)
    .replace('http://localhost:8000', mediaUrl);
  
  // If it's a relative URL, prepend media URL
  if (!fixedUrl.startsWith('http')) {
    fixedUrl = `${mediaUrl}${fixedUrl.startsWith('/') ? '' : '/'}${fixedUrl}`;
  }
  
  return fixedUrl;
};

export const API_CONFIG = {
  get API_URL() { return getRuntimeApiUrl(); },
  get MEDIA_URL() { return getRuntimeMediaUrl(); },
  SITE_URL: process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000',
  PRODUCTION_API_URL,
  PRODUCTION_MEDIA_URL,
  LOCAL_API_URL,
  LOCAL_MEDIA_URL,
  isProduction,
} as const;

// For runtime checks in browser
export const getApiUrl = getRuntimeApiUrl;
export const getMediaUrl = getRuntimeMediaUrl;

export default API_CONFIG;
