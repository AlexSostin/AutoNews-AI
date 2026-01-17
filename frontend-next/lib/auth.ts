import api from './api';
import { AuthTokens, LoginCredentials } from '@/types';

export const login = async (credentials: LoginCredentials): Promise<AuthTokens> => {
  const response = await api.post('/token/', credentials);
  const { access, refresh } = response.data;

  // Store tokens in httpOnly-like cookies
  document.cookie = `access_token=${access}; path=/; max-age=3600; SameSite=Strict`;
  document.cookie = `refresh_token=${refresh}; path=/; max-age=${7 * 24 * 60 * 60}; SameSite=Strict`;

  return { access, refresh };
};

export const logout = () => {
  document.cookie = 'access_token=; path=/; max-age=0';
  document.cookie = 'refresh_token=; path=/; max-age=0';
  window.location.href = '/login';
};

export const isAuthenticated = (): boolean => {
  if (typeof window === 'undefined') return false;
  
  const token = document.cookie
    .split('; ')
    .find(row => row.startsWith('access_token='));
  
  return !!token;
};
