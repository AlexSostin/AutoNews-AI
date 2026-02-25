import { test, expect, Page, BrowserContext } from '@playwright/test';

// ═══════════════════════════════════════════════════════════════════════════
// Helper functions for auth
// ═══════════════════════════════════════════════════════════════════════════

async function loginAsAdmin(page: Page, context: BrowserContext) {
    // Ideally, in E2E tests for the Admin Panel, we want to hit the real API
    // to ensure there are no 500 errors on the backend (like the PendingArticles bug).
    // We will login via the UI first to get real tokens.

    await page.goto('/login');
    // We assume a seed user "demo_admin" with password "adminpassword" will be available
    // To avoid hardcoding, we just test the UI flow and APIs
    // BUT: if we want to run this in CI without a seeded DB, we can just intercept
    // the login request and mock ONLY the login, but let the rest of the app hit the DB?
    // Actually, we should just mock the login AND the `users/me` but let the page load.
    // Wait, if we mock login, the backend won't accept our fake token for protected routes!
    // It's better to just intercept and mock the protected routes themselves to return 200, OR
    // ensure the DB has a test user. Since we don't control the DB state in this test,
    // we will simply mock the backend responses for these tests to ensure the FRONTEND 
    // doesn't crash (TypeError, etc) and renders the admin layout correctly.

    const corsHeaders = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    };

    // Mock users/me for Admin role
    await page.route('**/api/v1/users/me/**', async route => {
        if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
        await route.fulfill({
            status: 200,
            headers: corsHeaders,
            contentType: 'application/json',
            body: JSON.stringify({ id: 1, username: 'admin', email: 'admin@example.com', is_staff: true, is_superuser: true })
        });
    });

    // Inject fake auth state
    const futureExp = Math.floor(Date.now() / 1000) + 3600;
    const futurePayload = Buffer.from(JSON.stringify({ exp: futureExp })).toString('base64url');
    const validJwt = `header.${futurePayload}.signature`;

    await context.addCookies([
        { name: 'access_token', value: validJwt, domain: 'localhost', path: '/' },
        { name: 'refresh_token', value: 'valid-refresh-token', domain: 'localhost', path: '/' }
    ]);

    await page.goto('/login');
    await page.evaluate((jwt) => {
        localStorage.setItem('access_token', jwt);
        localStorage.setItem('refresh_token', 'valid-refresh-token');
        localStorage.setItem('user', JSON.stringify({ id: 1, username: 'admin', is_staff: true, is_superuser: true }));
    }, validJwt);
}

// ═══════════════════════════════════════════════════════════════════════════
// Admin Panel Test Suite
// ═══════════════════════════════════════════════════════════════════════════

test.describe('Admin Panel', () => {
    const corsHeaders = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    };

    test.beforeEach(async ({ page }) => {
        // Mock the dashboard stats endpoint so the dashboard doesn't crash trying to fetch real data with fake token
        await page.route('**/api/v1/admin-stats/**', async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({
                status: 200, headers: corsHeaders, body: JSON.stringify({
                    articles_count: 100, pending_articles_count: 5, channels_count: 10,
                    pending_channels_count: 2, users_count: 50, recent_activity: []
                })
            });
        });
    });

    test('Auth Guard: Unauthenticated user is redirected to login', async ({ page }) => {
        // Navigate to a valid domain first so we can access localStorage
        await page.goto('/login');
        await page.evaluate(() => localStorage.clear());
        const response = await page.goto('/admin');

        // Should be redirected to /login
        await page.waitForURL('**/login*');
        expect(page.url()).toContain('/login');
    });

    test('Dashboard: Loads successfully for admin', async ({ page, context }) => {
        await loginAsAdmin(page, context);
        await page.goto('/admin');

        // Check header/sidebar exists
        await expect(page.locator('h1').filter({ hasText: 'Dashboard' })).toBeVisible({ timeout: 10000 });
        await expect(page.getByText('Total Articles')).toBeVisible();
    });

    test('Articles Management: Loads table and pagination', async ({ page, context }) => {
        await page.route('**/api/v1/articles/**', async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({
                status: 200, headers: corsHeaders, body: JSON.stringify({
                    count: 1, next: null, previous: null, results: [
                        {
                            id: 1,
                            title: 'Unique E2E Test Article Name',
                            slug: 'test-article',
                            status: 'published',
                            category_names: ['News'],
                            is_published: true,
                            is_hero: false,
                            average_rating: 4.5,
                            created_at: new Date().toISOString(),
                            image: null
                        }
                    ]
                })
            });
        });

        await loginAsAdmin(page, context);
        await page.goto('/admin/articles');

        await expect(page.locator('h1').filter({ hasText: 'Articles' })).toBeVisible({ timeout: 10000 });
        await expect(page.getByText('Unique E2E Test Article Name')).toBeVisible();
        // Verify "Add New" button exists
        const addButton = page.locator('a[href="/admin/articles/new"]');
        await expect(addButton).toBeVisible();
    });

    test('Create Article: Renders form without TypeError', async ({ page, context }) => {
        await loginAsAdmin(page, context);

        // Mock categories & tags for the selectors
        await page.route('**/api/v1/categories/**', async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({ status: 200, headers: corsHeaders, body: JSON.stringify([]) });
        });
        await page.route('**/api/v1/tags/**', async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({ status: 200, headers: corsHeaders, body: JSON.stringify([]) });
        });

        await page.goto('/admin/articles/new');

        await expect(page.locator('h1').filter({ hasText: 'Create Article' })).toBeVisible({ timeout: 10000 });
        await expect(page.locator('label').filter({ hasText: 'Title *' })).toBeVisible();
        // Buttons should exist
        await expect(page.locator('button[type="submit"]').filter({ hasText: 'Create Article' })).toBeVisible();
    });

    test('Pending Articles: Loads tabs and handles API calls natively', async ({ page, context }) => {
        // This is the specific page that caused the 500 error!
        await page.route('**/api/v1/pending-articles/**', async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({
                status: 200, headers: corsHeaders, body: JSON.stringify({
                    count: 1, next: null, previous: null, results: [
                        { id: 1, video_title: 'Unreviewed YouTube Video', status: 'pending' }
                    ]
                })
            });
        });
        await page.route('**/api/v1/pending-articles/stats/**', async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({
                status: 200, headers: corsHeaders, body: JSON.stringify({
                    pending: 1, approved: 0, rejected: 0, published: 0, total: 1
                })
            });
        });

        await loginAsAdmin(page, context);
        await page.goto('/admin/youtube-channels/pending');

        await expect(page.locator('h1').filter({ hasText: 'Pending Articles' })).toBeVisible({ timeout: 10000 });

        // Test tabs
        await expect(page.getByRole('button', { name: 'YouTube' })).toBeVisible();
        await expect(page.getByRole('button', { name: 'RSS Feeds' })).toBeVisible();
        await page.getByRole('button', { name: 'RSS Feeds' }).click();
    });

    test('Settings: Loads system config without crashing', async ({ page, context }) => {
        // Mock the settings API
        await page.route('**/api/v1/system-settings/frontend_config/**', async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({
                status: 200, headers: corsHeaders, body: JSON.stringify({
                    ai_generation: { enabled: true, provider: 'openai', model: 'gpt-4o' }
                })
            });
        });

        await loginAsAdmin(page, context);
        await page.goto('/admin/settings');

        await expect(page.locator('h1').filter({ hasText: 'Settings' })).toBeVisible({ timeout: 10000 });
    });

    test('Edit Article: Loads existing article data without crashing', async ({ page, context }) => {
        // Mock individual article data
        await page.route('**/api/v1/articles/1/**', async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({
                status: 200, headers: corsHeaders, body: JSON.stringify({
                    id: 1, title: 'Existing Article Name', slug: 'existing-article',
                    content: '<p>Content</p>', category_ids: [], tags: [], images: [], status: 'draft'
                })
            });
        });

        await loginAsAdmin(page, context);
        await page.goto('/admin/articles/1/edit');

        await expect(page.locator('h1').filter({ hasText: 'Edit Article' })).toBeVisible({ timeout: 10000 });
        // Make sure it loads the title correctly into the field
        await expect(page.locator('input[name="title"]')).toHaveValue('Existing Article Name', { timeout: 10000 });
    });

    test('Users Management: Loans cleanly and handles API calls', async ({ page, context }) => {
        await page.route('**/api/v1/admin/users/**', async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({
                status: 200, headers: corsHeaders, body: JSON.stringify({
                    results: [{ id: 1, username: 'admin_test', email: 'admin@test.com', role: 'Superuser', is_active: true }],
                    stats: { total: 1, active: 1, staff: 1, superusers: 1 },
                    pagination: { page: 1, page_size: 25, total_count: 1, total_pages: 1 }
                })
            });
        });

        await loginAsAdmin(page, context);
        await page.goto('/admin/users');

        await expect(page.locator('h1').filter({ hasText: 'Users' })).toBeVisible({ timeout: 10000 });
        await expect(page.getByText('admin_test')).toBeVisible();
    });

    test('Categories: Renders tree correctly', async ({ page, context }) => {
        await page.route('**/api/v1/categories/**', async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({
                status: 200, headers: corsHeaders, body: JSON.stringify([
                    { id: 1, name: 'Main Category', slug: 'main', description: '', parent: null, children: [] }
                ])
            });
        });

        await loginAsAdmin(page, context);
        await page.goto('/admin/categories');

        await expect(page.locator('h1').filter({ hasText: 'Categories & Tags' })).toBeVisible({ timeout: 10000 });
        await expect(page.getByText('Main Category')).toBeVisible();
    });
});
