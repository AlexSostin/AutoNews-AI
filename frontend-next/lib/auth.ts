import api from './api';
import { AuthTokens, LoginCredentials, User } from '@/types';
import { setUserContext, clearUserContext } from './errorTracking';

// Helper to set cookies with proper security flags
const setCookie = (name: string, value: string, maxAgeSeconds: number = 7 * 24 * 60 * 60) => {
  const isSecure = typeof window !== 'undefined' && window.location.protocol === 'https:';
  const secureFlag = isSecure ? '; Secure' : '';
  document.cookie = `${name}=${value}; path=/; max-age=${maxAgeSeconds}; SameSite=Lax${secureFlag}`;
};

export const login = async (credentials: LoginCredentials): Promise<AuthTokens> => {
  const response = await api.post('/token/', credentials);
  const { access, refresh } = response.data;

  // Store tokens in cookies (needed for middleware)
  // Access token cookie lives 7 days (cookie presence allows middleware to pass)
  // The actual token validation happens on the backend
  setCookie('access_token', access);
  setCookie('refresh_token', refresh);
  
  // Also store in localStorage for client-side access
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);

  // Store user data
  const userData = await getCurrentUser(access);
  if (userData) {
    localStorage.setItem('user', JSON.stringify(userData));
    
    // Установить пользователя в Sentry для отслеживания ошибок
    setUserContext({
      id: userData.id.toString(),
      email: userData.email,
      username: userData.username,
      is_staff: userData.is_staff
    });
  }

  // Trigger auth change event for Header update
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('authChange'));
  }

  return { access, refresh };
};

export const logout = () => {
  // Clear localStorage
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  
  // Clear cookies
  document.cookie = 'access_token=; path=/; max-age=0';
  document.cookie = 'refresh_token=; path=/; max-age=0';
  
  // Очистить пользователя из Sentry
  clearUserContext();
  
  // Trigger auth change event
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('authChange'));
  }
  
  window.location.href = '/login';
};

export const isAuthenticated = (): boolean => {
  if (typeof window === 'undefined') return false;
  
  // Check cookies first (middleware uses cookies)
  const cookieToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('access_token='));
  
  if (cookieToken) return true;
  
  // Fallback to localStorage - if found, restore the cookie!
  const tokenFromStorage = localStorage.getItem('access_token');
  if (tokenFromStorage) {
    // Restore the cookie for middleware
    setCookie('access_token', tokenFromStorage);
    const refreshFromStorage = localStorage.getItem('refresh_token');
    if (refreshFromStorage) {
      setCookie('refresh_token', refreshFromStorage);
    }
    return true;
  }
  
  return false;
};

export const getAccessToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  
  // Check cookies first (middleware uses cookies)
  const token = document.cookie
    .split('; ')
    .find(row => row.startsWith('access_token='));
  
  if (token) return token.split('=')[1];
  
  // Fallback to localStorage - if found, restore the cookie!
  const tokenFromStorage = localStorage.getItem('access_token');
  if (tokenFromStorage) {
    // Restore the cookie for middleware
    setCookie('access_token', tokenFromStorage);
  }
  return tokenFromStorage;
};

// Alias for convenience
export const getToken = getAccessToken;

export const getCurrentUser = async (token?: string): Promise<User | null> => {
  try {
    const accessToken = token || getAccessToken();
    if (!accessToken) return null;

    // Runtime API URL detection
    const getApiUrl = () => {
      if (typeof window !== 'undefined') {
        const host = window.location.hostname;
        if (host !== 'localhost' && host !== '127.0.0.1') {
          return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
        }
      }
      return 'http://localhost:8000/api/v1';
    };

    const response = await fetch(`${getApiUrl()}/users/me/`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) return null;
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching user:', error);
    return null;
  }
};

export const getUserFromStorage = (): User | null => {
  if (typeof window === 'undefined') return null;
  
  const userData = localStorage.getItem('user');
  return userData ? JSON.parse(userData) : null;
};

export const isAdmin = (): boolean => {
  const user = getUserFromStorage();
  return user?.is_staff || user?.is_superuser || false;
};
