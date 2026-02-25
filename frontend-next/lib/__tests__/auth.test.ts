import { describe, it, expect, vi, beforeEach } from 'vitest';
import { login, logout, isAuthenticated, getAccessToken, getCurrentUser, getUserFromStorage, isAdmin, isSuperuser } from '../auth';
import api from '../api';
import { authenticatedFetch } from '../authenticatedFetch';
import { setUserContext, clearUserContext } from '../errorTracking';

// Mock dependencies
vi.mock('../api', () => ({
    default: { post: vi.fn() },
    getApiUrl: vi.fn(),
}));

vi.mock('../authenticatedFetch', () => ({
    authenticatedFetch: vi.fn(),
}));

vi.mock('../errorTracking', () => ({
    setUserContext: vi.fn(),
    clearUserContext: vi.fn(),
}));

// Helper to create a fake JWT that expires in `seconds` from now
const createToken = (expiresInSeconds: number) => {
    const exp = Math.floor(Date.now() / 1000) + expiresInSeconds;
    const payload = btoa(JSON.stringify({ exp })).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    return `header.${payload}.signature`;
};

describe('Auth Utility Algorithms', () => {
    beforeEach(() => {
        // Reset DOM state
        localStorage.clear();
        document.cookie.split(";").forEach((c) => {
            document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
        });
        vi.clearAllMocks();
    });

    describe('login()', () => {
        it('stores tokens in cookies and localStorage on successful login', async () => {
            const mockResponse = { data: { access: 'access_mock', refresh: 'refresh_mock' } };
            vi.mocked(api.post).mockResolvedValueOnce(mockResponse);

            const mockUser = { id: 1, username: 'test', email: 'test@test.com', is_staff: true, is_superuser: false };
            vi.mocked(authenticatedFetch).mockResolvedValueOnce({
                ok: true,
                json: async () => mockUser,
            } as Response);

            const result = await login({ username: 'test', password: 'password' });

            expect(api.post).toHaveBeenCalledWith('/token/', { username: 'test', password: 'password' });
            expect(result).toEqual({ access: 'access_mock', refresh: 'refresh_mock' });

            expect(document.cookie).toContain('access_token=access_mock');
            expect(document.cookie).toContain('refresh_token=refresh_mock');
            expect(localStorage.getItem('access_token')).toBe('access_mock');
            expect(localStorage.getItem('refresh_token')).toBe('refresh_mock');
            expect(localStorage.getItem('user')).toEqual(JSON.stringify(mockUser));

            expect(setUserContext).toHaveBeenCalledWith({
                id: '1',
                email: 'test@test.com',
                username: 'test',
                is_staff: true
            });
        });
    });

    describe('logout()', () => {
        it('clears all auth data and triggers redirect', () => {
            localStorage.setItem('access_token', 'token');
            localStorage.setItem('user', '{}');
            document.cookie = 'access_token=token; path=/';

            // Mock window.location
            const originalLocation = window.location;
            delete (window as any).location;
            window.location = { href: '' } as any;

            logout();

            expect(localStorage.getItem('access_token')).toBeNull();
            expect(localStorage.getItem('user')).toBeNull();
            expect(document.cookie).not.toContain('access_token=token');
            expect(clearUserContext).toHaveBeenCalled();
            expect(window.location.href).toBe('/login');

            // Restore location
            (window as any).location = originalLocation;
        });
    });

    describe('isAuthenticated() & Token Expiry tracking', () => {
        it('returns true for a valid token in cookies', () => {
            const validToken = createToken(3600); // Expires in 1 hour
            document.cookie = `access_token=${validToken}; path=/`;
            expect(isAuthenticated()).toBe(true);
        });

        it('returns false for an expired token without a refresh token', () => {
            const expiredToken = createToken(-3600); // Expired 1 hour ago
            document.cookie = `access_token=${expiredToken}; path=/`;
            expect(isAuthenticated()).toBe(false);
            expect(localStorage.getItem('access_token')).toBeNull(); // Should clear it
        });

        it('returns true for an expired token IF a refresh token exists', () => {
            const expiredToken = createToken(-3600);
            document.cookie = `access_token=${expiredToken}; path=/`;
            document.cookie = `refresh_token=valid_refresh; path=/`;
            expect(isAuthenticated()).toBe(true);
        });

        it('restores cookies from localStorage if cookies are missing but localStorage has valid token', () => {
            const validToken = createToken(3600);
            localStorage.setItem('access_token', validToken);
            expect(isAuthenticated()).toBe(true);
            expect(document.cookie).toContain(`access_token=${validToken}`);
        });
    });

    describe('getAccessToken()', () => {
        it('retrieves access token from cookies if available', () => {
            const validToken = createToken(3600);
            document.cookie = `access_token=${validToken}; path=/`;
            expect(getAccessToken()).toBe(validToken);
        });

        it('falls back to localStorage if cookie is missing', () => {
            const validToken = createToken(3600);
            localStorage.setItem('access_token', validToken);
            expect(getAccessToken()).toBe(validToken);
        });
    });

    describe('User Info Helpers', () => {
        it('getCurrentUser fetches from API', async () => {
            const mockUser = { id: 2, username: 'api_user' };
            vi.mocked(authenticatedFetch).mockResolvedValueOnce({
                ok: true,
                json: async () => mockUser,
            } as Response);

            const user = await getCurrentUser('fake_token');
            expect(user).toEqual(mockUser);
            expect(authenticatedFetch).toHaveBeenCalledWith('/users/me/', {
                headers: { Authorization: 'Bearer fake_token' }
            });
        });

        it('getUserFromStorage retrieves parsed JSON', () => {
            localStorage.setItem('user', JSON.stringify({ id: 99, username: 'stored' }));
            expect(getUserFromStorage()).toEqual({ id: 99, username: 'stored' });
        });

        it('isAdmin returns true for staff', () => {
            localStorage.setItem('user', JSON.stringify({ is_staff: true, is_superuser: false }));
            expect(isAdmin()).toBe(true);
        });

        it('isSuperuser returns true only for superusers', () => {
            localStorage.setItem('user', JSON.stringify({ is_staff: true, is_superuser: false }));
            expect(isSuperuser()).toBe(false);

            localStorage.setItem('user', JSON.stringify({ is_staff: true, is_superuser: true }));
            expect(isSuperuser()).toBe(true);
        });
    });
});
