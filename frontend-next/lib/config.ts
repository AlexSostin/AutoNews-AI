// API Configuration with runtime detection
const getRuntimeApiUrl = () => {
  // Check build-time env var first
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl !== 'http://localhost:8001/api/v1') {
    return envUrl;
  }
  
  // Runtime detection for browser
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      // Production: hardcode the Railway backend URL
      return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
    }
  }
  
  return 'http://localhost:8001/api/v1';
};

const getRuntimeMediaUrl = () => {
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      return 'https://heroic-healing-production-2365.up.railway.app';
    }
  }
  return process.env.NEXT_PUBLIC_MEDIA_URL || 'http://localhost:8001';
};

export const API_CONFIG = {
  get API_URL() { return getRuntimeApiUrl(); },
  get MEDIA_URL() { return getRuntimeMediaUrl(); },
  SITE_URL: process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000',
} as const;

// For runtime checks in browser
export const getApiUrl = getRuntimeApiUrl;

export default API_CONFIG;
