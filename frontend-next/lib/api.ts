import axios from 'axios';

// Runtime API URL detection
// For client-side: use window location to determine the API URL
// This ensures the correct URL is used even after deployment
const getApiUrl = () => {
  if (typeof window === 'undefined') {
    // Server-side: use environment variable or internal URL
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1';
  }
  
  // Client-side: check environment variable first, then derive from current domain
  if (process.env.NEXT_PUBLIC_API_URL && process.env.NEXT_PUBLIC_API_URL !== 'http://localhost:8001/api/v1') {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  
  // Fallback: derive API URL from current hostname
  const hostname = window.location.hostname;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8001/api/v1';
  }
  
  // Production: use Railway backend URL
  // Frontend: autonews-ai-production.up.railway.app
  // Backend: heroic-healing-production-2365.up.railway.app
  return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
};

// Export API URL for direct fetch calls
export const API_URL = getApiUrl();

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add JWT token
api.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('access_token='))
        ?.split('=')[1];
      
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle 401 and refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        if (typeof window === 'undefined') {
          return Promise.reject(error);
        }

        const refreshToken = document.cookie
          .split('; ')
          .find(row => row.startsWith('refresh_token='))
          ?.split('=')[1];

        if (refreshToken) {
          const response = await axios.post(
            `${getBaseURL()}/token/refresh/`,
            { refresh: refreshToken }
          );

          const { access } = response.data;
          
          // Update access token in cookie
          document.cookie = `access_token=${access}; path=/; max-age=3600; SameSite=Strict`;

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Refresh token expired - redirect to login
        if (typeof window !== 'undefined') {
          document.cookie = 'access_token=; path=/; max-age=0';
          document.cookie = 'refresh_token=; path=/; max-age=0';
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
