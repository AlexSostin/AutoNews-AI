import axios from 'axios';

// Use backend service name for server-side requests (inside Docker)
// Use localhost for client-side requests (from browser)
const getBaseURL = () => {
  // Server-side (inside Docker container)
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL_SERVER || 'http://backend:8001/api/v1';
  }
  // Client-side (browser)
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1';
};

const api = axios.create({
  baseURL: getBaseURL(),
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
        const refreshToken = document.cookie
          .split('; ')
          .find(row => row.startsWith('refresh_token='))
          ?.split('=')[1];

        if (refreshToken) {
          const response = await axios.post(
            `${process.env.NEXT_PUBLIC_API_URL}/auth/token/refresh/`,
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
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
