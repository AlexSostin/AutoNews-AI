import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
    login, logout, isAuthenticated, getAccessToken,
    getCurrentUser, getUserFromStorage, isAdmin, isSuperuser,
    refreshAccessToken, verifyAndRefreshSession,
} from '../auth';
import api from '../api';
import { authenticatedFetch } from '../authenticatedFetch';
import { setUserContext, clearUserContext } from '../errorTracking';

// Mock dependencies
vi.mock('../api', () => ({
    default: { post: vi.fn() },
    getApiUrl: vi.fn(() => 'http://localhost:8000/api/v1'),
}));

vi.mock('../authenticatedFetch', () => ({
    authenticatedFetch: vi.fn(),
}));

vi.mock('../errorTracking', () => ({
    setUserContext: vi.fn(),
    clearUserContext: vi.fn(),
}));

// Mock global fetch for token verify/refresh calls
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Helper to create a fake JWT that expires in `seconds` from now
const createToken = (expiresInSeconds: number) => {
    const exp = Math.floor(Date.now() / 1000) + expiresInSeconds;
    const payload = btoa(JSON.stringify({ exp })).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    return `header.${payload}.signature`;
};

describe('Auth Utility Algorithms', () => {
    beforeEach(() => {
        localStorage.clear();
        document.cookie.split(';').forEach((c) => {
            document.cookie = c.replace(/^ +/, '').replace(/=.*/, '=;expires=' + new Date().toUTCString() + ';path=/');
        });
        vi.clearAllMocks();
        mockFetch.mockReset();
    });

    // ─── login() ─────────────────────────────────────────────────────────────

    describe('login()', () => {
        it('stores tokens in cookies on successful login', async () => {
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

            // Tokens must be in cookies
            expect(document.cookie).toContain('access_token=access_mock');
            expect(document.cookie).toContain('refresh_token=refresh_mock');

            // User must be in localStorage
            expect(localStorage.getItem('user')).toEqual(JSON.stringify(mockUser));

            // Sentry context set
            expect(setUserContext).toHaveBeenCalledWith({
                id: '1',
                email: 'test@test.com',
                username: 'test',
                is_staff: true
            });
        });

        it('refresh_token is NOT stored in localStorage after login', async () => {
            const mockResponse = { data: { access: 'access_mock', refresh: 'refresh_mock' } };
            vi.mocked(api.post).mockResolvedValueOnce(mockResponse);
            vi.mocked(authenticatedFetch).mockResolvedValueOnce({ ok: false } as Response);

            await login({ username: 'test', password: 'password' });

            // refresh_token must NOT be in localStorage — cookies only
            expect(localStorage.getItem('refresh_token')).toBeNull();
        });
    });

    // ─── logout() ────────────────────────────────────────────────────────────

    describe('logout()', () => {
        it('clears auth cookies, localStorage and redirects', () => {
            localStorage.setItem('access_token', 'token');
            localStorage.setItem('user', '{}');
            document.cookie = 'access_token=token; path=/';
            document.cookie = 'refresh_token=refresh; path=/';

            const originalLocation = window.location;
            delete (window as any).location;
            window.location = { href: '' } as any;

            logout();

            expect(localStorage.getItem('access_token')).toBeNull();
            expect(localStorage.getItem('user')).toBeNull();
            expect(document.cookie).not.toContain('access_token=token');
            expect(clearUserContext).toHaveBeenCalled();
            expect(window.location.href).toBe('/login');

            (window as any).location = originalLocation;
        });
    });

    // ─── isAuthenticated() ───────────────────────────────────────────────────

    describe('isAuthenticated()', () => {
        it('returns true for a valid token in cookies', () => {
            document.cookie = `access_token=${createToken(3600)}; path=/`;
            expect(isAuthenticated()).toBe(true);
        });

        it('returns false for expired token without refresh token', () => {
            document.cookie = `access_token=${createToken(-3600)}; path=/`;
            expect(isAuthenticated()).toBe(false);
        });

        it('returns true for expired access token IF refresh_token cookie exists', () => {
            document.cookie = `access_token=${createToken(-3600)}; path=/`;
            document.cookie = 'refresh_token=valid_refresh; path=/';
            expect(isAuthenticated()).toBe(true);
        });

        it('restores cookie from localStorage if cookie missing but localStorage has valid token', () => {
            const validToken = createToken(3600);
            localStorage.setItem('access_token', validToken);
            expect(isAuthenticated()).toBe(true);
            expect(document.cookie).toContain(`access_token=${validToken}`);
        });
    });

    // ─── getAccessToken() ────────────────────────────────────────────────────

    describe('getAccessToken()', () => {
        it('retrieves access token from cookies', () => {
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

    // ─── refreshAccessToken() ────────────────────────────────────────────────

    describe('refreshAccessToken()', () => {
        it('returns null when no refresh_token cookie exists', async () => {
            const result = await refreshAccessToken();
            expect(result).toBeNull();
            expect(mockFetch).not.toHaveBeenCalled();
        });

        it('updates access_token cookie on success', async () => {
            document.cookie = 'refresh_token=valid_refresh; path=/';
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ access: 'new_access', refresh: 'new_refresh' }),
            });

            const result = await refreshAccessToken();

            expect(result).toBe('new_access');
            expect(document.cookie).toContain('access_token=new_access');
            expect(document.cookie).toContain('refresh_token=new_refresh');
        });

        it('returns null when refresh endpoint returns non-ok', async () => {
            document.cookie = 'refresh_token=expired_refresh; path=/';
            mockFetch.mockResolvedValueOnce({ ok: false });

            const result = await refreshAccessToken();
            expect(result).toBeNull();
        });

        it('returns null on network error', async () => {
            document.cookie = 'refresh_token=valid_refresh; path=/';
            mockFetch.mockRejectedValueOnce(new Error('Network error'));

            const result = await refreshAccessToken();
            expect(result).toBeNull();
        });
    });

    // ─── verifyAndRefreshSession() ───────────────────────────────────────────

    describe('verifyAndRefreshSession()', () => {
        it('returns true when token verify succeeds', async () => {
            document.cookie = `access_token=${createToken(3600)}; path=/`;
            mockFetch.mockResolvedValueOnce({ ok: true });

            const result = await verifyAndRefreshSession();
            expect(result).toBe(true);
        });

        it('refreshes and returns true when access expired but refresh valid', async () => {
            document.cookie = `access_token=${createToken(-60)}; path=/`;
            document.cookie = 'refresh_token=valid_refresh; path=/';

            // First call: verify fails
            mockFetch.mockResolvedValueOnce({ ok: false });
            // Second call: refresh succeeds
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ access: 'new_access', refresh: 'new_refresh' }),
            });

            const result = await verifyAndRefreshSession();
            expect(result).toBe(true);
        });

        it('returns false when both tokens are invalid', async () => {
            document.cookie = `access_token=${createToken(-60)}; path=/`;
            document.cookie = 'refresh_token=expired_refresh; path=/';

            // verify fails
            mockFetch.mockResolvedValueOnce({ ok: false });
            // refresh fails
            mockFetch.mockResolvedValueOnce({ ok: false });

            const result = await verifyAndRefreshSession();
            expect(result).toBe(false);
        });

        it('returns true on network error if tokens exist (graceful: no logout during deploy)', async () => {
            document.cookie = `access_token=${createToken(3600)}; path=/`;
            document.cookie = 'refresh_token=some_refresh; path=/';
            mockFetch.mockRejectedValueOnce(new Error('502 Bad Gateway'));

            const result = await verifyAndRefreshSession();
            expect(result).toBe(true);
        });

        it('returns false when no token cookie exists and refresh also fails', async () => {
            // No cookies at all
            const result = await verifyAndRefreshSession();
            expect(result).toBe(false);
        });
    });

    // ─── User helpers ─────────────────────────────────────────────────────────

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
