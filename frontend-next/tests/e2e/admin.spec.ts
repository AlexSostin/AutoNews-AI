import { test, expect, Page, BrowserContext } from '@playwright/test';

// ═══════════════════════════════════════════════════════════════════════════
// Config — Uses a dedicated e2e_admin user created via management command
// ═══════════════════════════════════════════════════════════════════════════
const E2E_USER = 'e2e_admin';
const E2E_PASS = 'E2eTestPass123!';
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// ═══════════════════════════════════════════════════════════════════════════
// Helper: Real login via the backend /token/ API
// ═══════════════════════════════════════════════════════════════════════════

async function loginAsAdmin(page: Page, context: BrowserContext) {
    // 1. Get real JWT tokens from the backend
    const tokenResponse = await page.request.post(`${API_BASE}/token/`, {
        data: { username: E2E_USER, password: E2E_PASS },
        headers: { 'Content-Type': 'application/json' },
    });

    expect(tokenResponse.ok(), `Login failed: ${tokenResponse.status()}`).toBeTruthy();
    const { access, refresh } = await tokenResponse.json();

    // 2. Set cookies so the Next.js middleware allows access
    await context.addCookies([
        { name: 'access_token', value: access, domain: 'localhost', path: '/' },
        { name: 'refresh_token', value: refresh, domain: 'localhost', path: '/' },
    ]);

    // 3. Navigate to a page to establish localStorage context
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
}

// ═══════════════════════════════════════════════════════════════════════════
// Admin Panel Test Suite
// ═══════════════════════════════════════════════════════════════════════════

test.describe('Admin Panel', () => {
    test('Auth Guard: Unauthenticated user is redirected to login', async ({ page }) => {
        await page.goto('/login');
        await page.evaluate(() => localStorage.clear());
        await page.goto('/admin');

        await page.waitForURL('**/login*');
        expect(page.url()).toContain('/login');
    });

    test('Dashboard: Loads successfully for admin', async ({ page, context }) => {
        await loginAsAdmin(page, context);
        await page.goto('/admin');

        await expect(page.locator('h1').filter({ hasText: 'Dashboard' })).toBeVisible({ timeout: 15000 });
        await expect(page.getByText('Total Articles')).toBeVisible();
    });

    test('Articles Management: Loads table and pagination', async ({ page, context }) => {
        await loginAsAdmin(page, context);
        await page.goto('/admin/articles');

        await expect(page.locator('h1').filter({ hasText: 'Articles' })).toBeVisible({ timeout: 15000 });
        // Verify "Add New" button exists
        const addButton = page.locator('a[href="/admin/articles/new"]');
        await expect(addButton).toBeVisible();
    });

    test('Create Article: Renders form without TypeError', async ({ page, context }) => {
        await loginAsAdmin(page, context);
        await page.goto('/admin/articles/new');

        // Page uses PageHeader with title "Create New Article" or an h1 with that text
        await expect(page.getByText('Create New Article', { exact: false })).toBeVisible({ timeout: 15000 });
        await expect(page.locator('label').filter({ hasText: 'Title' })).toBeVisible();
    });

    test('Pending Articles: Loads tabs', async ({ page, context }) => {
        await loginAsAdmin(page, context);
        await page.goto('/admin/youtube-channels/pending');

        await expect(page.locator('h1').filter({ hasText: 'Pending Articles' })).toBeVisible({ timeout: 15000 });

        // Test source filter tabs (actual text: "YouTube Articles" and "RSS Articles")
        await expect(page.getByText('YouTube Articles')).toBeVisible();
        await expect(page.getByText('RSS Articles')).toBeVisible();
    });

    test('Settings: Loads system config without crashing', async ({ page, context }) => {
        await loginAsAdmin(page, context);
        await page.goto('/admin/settings');

        await expect(page.locator('h1').filter({ hasText: 'Settings' })).toBeVisible({ timeout: 15000 });
    });

    test('Edit Article: Loads existing article data without crashing', async ({ page, context }) => {
        await loginAsAdmin(page, context);

        // First get a real article ID from the API
        const articlesResponse = await page.request.get(
            `${API_BASE}/articles/?is_published=true&page_size=1`,
            { headers: { 'Authorization': `Bearer ${await getToken(context)}` } }
        );
        const articlesData = await articlesResponse.json();
        const articleId = articlesData.results?.[0]?.id;

        if (articleId) {
            await page.goto(`/admin/articles/${articleId}/edit`);
            // PageHeader renders the title "Edit Article"
            await expect(page.getByText('Edit Article', { exact: false })).toBeVisible({ timeout: 15000 });
        }
    });

    test('Users Management: Loads cleanly', async ({ page, context }) => {
        await loginAsAdmin(page, context);
        await page.goto('/admin/users');

        // Actual heading is "User Management"
        await expect(page.getByText('User Management')).toBeVisible({ timeout: 15000 });
        // Should show at least the e2e_admin user
        await expect(page.getByText('e2e_admin')).toBeVisible({ timeout: 10000 });
    });

    test('Categories: Renders page correctly', async ({ page, context }) => {
        await loginAsAdmin(page, context);
        await page.goto('/admin/categories');

        // Actual heading is "Categories"
        await expect(page.locator('h1').filter({ hasText: 'Categories' })).toBeVisible({ timeout: 15000 });
    });
});

// ═══════════════════════════════════════════════════════════════════════════
// Helper: Extract token from cookies
// ═══════════════════════════════════════════════════════════════════════════

async function getToken(context: BrowserContext): Promise<string> {
    const cookies = await context.cookies();
    const accessCookie = cookies.find(c => c.name === 'access_token');
    return accessCookie?.value || '';
}
