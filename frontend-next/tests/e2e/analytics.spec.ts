import { test, expect, Page, BrowserContext } from '@playwright/test';

// ═══════════════════════════════════════════════════════════════════════════
// Config
// ═══════════════════════════════════════════════════════════════════════════
const E2E_USER = 'e2e_admin';
const E2E_PASS = 'E2eTestPass123!';
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

async function loginAsAdmin(page: Page, context: BrowserContext) {
    const tokenResponse = await page.request.post(`${API_BASE}/token/`, {
        data: { username: E2E_USER, password: E2E_PASS },
        headers: { 'Content-Type': 'application/json' },
    });
    if (!tokenResponse.ok()) return; // Skip silently if backend not running
    const { access, refresh } = await tokenResponse.json();
    await context.addCookies([
        { name: 'access_token', value: access, domain: 'localhost', path: '/' },
        { name: 'refresh_token', value: refresh, domain: 'localhost', path: '/' },
    ]);
    await page.goto('/login');
    await page.evaluate(({ access, refresh }) => {
        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);
        localStorage.setItem('user', JSON.stringify({ id: 1, username: 'e2e_admin', is_staff: true, is_superuser: true }));
    }, { access, refresh });
}

// ═══════════════════════════════════════════════════════════════════════════
// Analytics Dashboard
// ═══════════════════════════════════════════════════════════════════════════

test.describe('Analytics Dashboard', () => {
    test.setTimeout(30000);

    test('loads without JS crash', async ({ page, context }) => {
        const jsErrors: string[] = [];
        page.on('pageerror', err => jsErrors.push(err.message));

        await loginAsAdmin(page, context);
        await page.goto('/admin/analytics');
        await page.waitForLoadState('networkidle');

        // Wait 3s to catch async crashes
        await page.waitForTimeout(3000);

        const criticalErrors = jsErrors.filter(e =>
            e.includes('Cannot read properties') ||
            e.includes('TypeError') ||
            e.includes('is not a function')
        );
        expect(criticalErrors, `JS errors on analytics: ${criticalErrors.join(', ')}`).toHaveLength(0);
    });

    test('shows Analytics Dashboard heading', async ({ page, context }) => {
        await loginAsAdmin(page, context);
        await page.goto('/admin/analytics');
        await expect(page.getByText('Analytics Dashboard', { exact: false })).toBeVisible({ timeout: 15000 });
    });

    test('Reader Quality section is visible (real data or empty state)', async ({ page, context }) => {
        await loginAsAdmin(page, context);
        await page.goto('/admin/analytics');
        await page.waitForLoadState('networkidle');

        // The section header is always rendered unconditionally
        await expect(page.getByText('Reader Quality', { exact: false })).toBeVisible({ timeout: 15000 });

        // Either real widget data OR one of the friendly empty states is shown
        const hasRealData = await page.getByText('sessions tracked').isVisible().catch(() => false);
        const hasEmptyState = await page.getByText('No reading sessions yet').isVisible().catch(() => false);
        expect(hasRealData || hasEmptyState, 'Reader Quality widget should show data or a friendly empty state').toBeTruthy();
    });

    test('ML Health widget renders a score', async ({ page, context }) => {
        await loginAsAdmin(page, context);
        await page.goto('/admin/analytics');
        await page.waitForLoadState('networkidle');

        // Scroll to ML section
        await page.getByText('ML Model Health', { exact: false }).scrollIntoViewIfNeeded().catch(() => { });

        // MLHealthWidget shows the overall score and level labels
        const hasScore = await page.getByText('Overall Score', { exact: false }).isVisible().catch(() => false);
        const hasLevel = await page.getByText('Rookie', { exact: false })
            .or(page.getByText('Learning', { exact: false }))
            .or(page.getByText('Competent', { exact: false }))
            .first()
            .isVisible({ timeout: 10000 })
            .catch(() => false);
        expect(hasScore || hasLevel, 'ML Health widget should show a score or level').toBeTruthy();
    });

    test('A/B Tests section shows test count', async ({ page, context }) => {
        await loginAsAdmin(page, context);
        await page.goto('/admin/analytics');
        await page.waitForLoadState('networkidle');

        await page.getByText('A/B Tests', { exact: false }).first().scrollIntoViewIfNeeded().catch(() => { });

        // Should show "X tests loaded" or "TOTAL TESTS"
        const hasTotalTests = await page.getByText('TOTAL TESTS', { exact: false }).isVisible({ timeout: 10000 }).catch(() => false);
        const hasTestsLoaded = await page.getByText('tests loaded', { exact: false }).isVisible({ timeout: 8000 }).catch(() => false);
        expect(hasTotalTests || hasTestsLoaded, 'A/B Tests section should display a test count').toBeTruthy();
    });

    test('AI Pipeline section renders (real or empty state)', async ({ page, context }) => {
        await loginAsAdmin(page, context);
        await page.goto('/admin/analytics');
        await page.waitForLoadState('networkidle');

        await expect(page.getByText('AI Pipeline Health', { exact: false })).toBeVisible({ timeout: 15000 });

        const hasEnrichment = await page.getByText('Enrichment Coverage', { exact: false }).isVisible().catch(() => false);
        const hasEmptyState = await page.getByText('AI pipeline data unavailable').isVisible().catch(() => false);
        expect(hasEnrichment || hasEmptyState, 'AI Pipeline section should show data or empty state').toBeTruthy();
    });
});
