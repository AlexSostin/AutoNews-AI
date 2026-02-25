import axios from 'axios';

// Production API URL - hardcoded to avoid build-time issues
const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const CUSTOM_DOMAIN_API_URL = 'https://api.freshmotors.net/api/v1';
const LOCAL_API_URL = 'http://localhost:8000/api/v1';

// Runtime API URL detection - called on each request
export const getApiUrl = (): string => {
  // Server-side rendering
  if (typeof window === 'undefined') {
    return PRODUCTION_API_URL;
  }

  // Client-side: detect based on hostname
  const hostname = window.location.hostname;

  // Also match local LAN IPs (e.g. 192.168.x.x, 10.x.x.x) for local network testing
  const isLocalNetwork = /^(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)$/.test(hostname);

  if (isLocalNetwork) {
    // If the hostname is an IP, we need to construct a local URL with it
    // otherwise if it's localhost we just return LOCAL_API_URL
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      return `http://${hostname}:8000/api/v1`;
    }
    return LOCAL_API_URL;
  }

  // Custom domain - use api subdomain
  if (hostname.includes('freshmotors.net')) {
    return CUSTOM_DOMAIN_API_URL;
  }

  // Railway production fallback
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
    config.baseURL = getApiUrl();

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
    return Promise.reject(error);
  }
);

// Keep track of refresh state to prevent race conditions
let isRefreshing = false;
let failedQueue: any[] = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Response interceptor - handle 401 and refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // If already refreshing, add this request to the queue
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

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

          const { access, refresh: newRefresh } = response.data;

          // Update access token in cookie (7 days to match login)
          const isSecure = window.location.protocol === 'https:';
          const secureFlag = isSecure ? '; Secure' : '';
          document.cookie = `access_token=${access}; path=/; max-age=${7 * 24 * 60 * 60}; SameSite=Lax${secureFlag}`;

          // 🔄 CRITICAL: Update refresh token if it was rotated (SIMPLE_JWT['ROTATE_REFRESH_TOKENS'] = True)
          if (newRefresh) {
            document.cookie = `refresh_token=${newRefresh}; path=/; max-age=${30 * 24 * 60 * 60}; SameSite=Lax${secureFlag}`;
          }

          // Also update localStorage
          localStorage.setItem('access_token', access);

          // Resolve the queue
          processQueue(null, access);

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Reject the queue
        processQueue(refreshError, null);

        // Refresh token expired - redirect to login
        if (typeof window !== 'undefined') {
          document.cookie = 'access_token=; path=/; max-age=0';
          document.cookie = 'refresh_token=; path=/; max-age=0';
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
