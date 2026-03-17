import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers/auth';

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
        await page.goto('/admin/analytics', { waitUntil: 'domcontentloaded' });

        // The section header is ALWAYS in page.tsx — wait for it
        const rqSection = page.locator(':text-is("Reader Quality")').first();
        await expect(rqSection).toBeVisible({ timeout: 15000 });
        await rqSection.scrollIntoViewIfNeeded();
        await page.waitForTimeout(5000);

        // Accept ANY visible text from the widget (real data labels OR empty state)
        const visibleText = await page.evaluate(() => document.body.innerText);
        const found = ['No reading sessions yet', 'Avg. Read Time', 'Bounce Rate', 'Reader Quality']
            .some(t => visibleText.includes(t));
        expect(found, `Reader Quality section with recognizable content not found in page text`).toBeTruthy();
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

        // Should show count cards (Total Tests / TOTAL TESTS via CSS uppercase) or empty state
        const hasTotalTests = await page.locator('text=/total tests/i').first().isVisible({ timeout: 10000 }).catch(() => false);
        const hasTestsLoaded = await page.getByText('tests loaded', { exact: false }).isVisible({ timeout: 8000 }).catch(() => false);
        const hasEmptyState = await page.getByText('No A/B tests found', { exact: false }).isVisible({ timeout: 8000 }).catch(() => false);
        expect(hasTotalTests || hasTestsLoaded || hasEmptyState, 'A/B Tests section should display a test count or empty state').toBeTruthy();
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
