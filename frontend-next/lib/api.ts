import axios from 'axios';

// Production API URL - hardcoded to avoid build-time issues
const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const LOCAL_API_URL = 'http://localhost:8001/api/v1';

// Runtime API URL detection - called on each request
export const getApiUrl = (): string => {
  // Server-side rendering
  if (typeof window === 'undefined') {
    return PRODUCTION_API_URL;
  }
  
  // Client-side: detect based on hostname
  const hostname = window.location.hostname;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return LOCAL_API_URL;
  }
  
  // Production - return hardcoded URL
  return PRODUCTION_API_URL;
};

// Export getter function for runtime detection
export const API_URL = getApiUrl();

// Create axios instance with interceptor that sets baseURL dynamically
const api = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - set baseURL and add JWT token
api.interceptors.request.use(
  (config) => {
    // Set baseURL dynamically on each request
    const baseURL = getApiUrl();
    config.baseURL = baseURL;
    
    // Log for debugging (will show in browser console)
    console.log(`[API Request] ${config.method?.toUpperCase()} ${baseURL}${config.url}`);
    
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
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// Response interceptor - handle 401 and refresh token
api.interceptors.response.use(
  (response) => {
    console.log(`[API Response] ${response.status} ${response.config.url}`);
    return response;
  },
  async (error) => {
    console.error(`[API Error] ${error.response?.status || 'Network Error'} ${error.config?.url}`, error.message);
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
            `${getApiUrl()}/token/refresh/`,
            { refresh: refreshToken }
          );

          const { access } = response.data;
          
          // Update access token in cookie (7 days to match login)
          const isSecure = window.location.protocol === 'https:';
          const secureFlag = isSecure ? '; Secure' : '';
          document.cookie = `access_token=${access}; path=/; max-age=${7 * 24 * 60 * 60}; SameSite=Lax${secureFlag}`;
          
          // Also update localStorage
          localStorage.setItem('access_token', access);

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
