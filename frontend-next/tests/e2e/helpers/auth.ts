import { Page, BrowserContext } from '@playwright/test';

// ═══════════════════════════════════════════════════════════════════════════
// Shared Auth Helper — single source of truth for admin login in E2E tests
// ═══════════════════════════════════════════════════════════════════════════

export const E2E_USER = 'e2e_admin';
export const E2E_PASS = 'E2eTestPass123!';
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

/**
 * Log in as admin by getting real JWT tokens from the backend,
 * then setting cookies + localStorage so Next.js recognises the session.
 */
export async function loginAsAdmin(page: Page, context: BrowserContext): Promise<boolean> {
    const tokenResponse = await page.request.post(`${API_BASE}/token/`, {
        data: { username: E2E_USER, password: E2E_PASS },
        headers: { 'Content-Type': 'application/json' },
    });

    if (!tokenResponse.ok()) {
        console.warn(`[auth] Login failed: ${tokenResponse.status()} — backend may not be running`);
        return false;
    }

    const { access, refresh } = await tokenResponse.json();

    // Set cookies so the Next.js middleware allows access
    await context.addCookies([
        { name: 'access_token', value: access, domain: 'localhost', path: '/' },
        { name: 'refresh_token', value: refresh, domain: 'localhost', path: '/' },
    ]);

    // Navigate to a page to establish localStorage context
    await page.goto('/login');
    await page.evaluate(
        ({ access, refresh }) => {
            localStorage.setItem('access_token', access);
            localStorage.setItem('refresh_token', refresh);
            localStorage.setItem(
                'user',
                JSON.stringify({ id: 1, username: 'e2e_admin', is_staff: true, is_superuser: true })
            );
        },
        { access, refresh }
    );

    return true;
}

/**
 * Extract the access token from cookies.
 */
export async function getToken(context: BrowserContext): Promise<string> {
    const cookies = await context.cookies();
    const accessCookie = cookies.find(c => c.name === 'access_token');
    return accessCookie?.value || '';
}
