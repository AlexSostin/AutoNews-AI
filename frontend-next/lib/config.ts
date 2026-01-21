// API Configuration
export const API_CONFIG = {
  // These are replaced at build time by Next.js
  API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1',
  MEDIA_URL: process.env.NEXT_PUBLIC_MEDIA_URL || 'http://localhost:8001',
  SITE_URL: process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000',
} as const;

// For runtime checks in browser
export const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    // В браузере используем встроенное значение
    return API_CONFIG.API_URL;
  }
  return API_CONFIG.API_URL;
};

export default API_CONFIG;
