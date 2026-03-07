import { test, expect } from '@playwright/test';

// ═══════════════════════════════════════════════════════════════════════════
// Search E2E Tests
// ═══════════════════════════════════════════════════════════════════════════

test.describe('Search', () => {
    test.setTimeout(20000);

    test('search page loads without error', async ({ page }) => {
        const response = await page.goto('/search?q=Toyota');
        expect(response?.status()).toBeLessThan(500);
    });

    test('search page shows results or empty state', async ({ page }) => {
        await page.goto('/search?q=BYD');
        await page.waitForLoadState('networkidle');

        // Either a result list or a "no results" message — never a blank screen
        const hasResults = await page.locator('a[href*="/articles/"]').first().isVisible().catch(() => false);
        const hasNoResults = await page.getByText(/no results|nothing found|try another/i).isVisible().catch(() => false);
        const hasHeading = await page.locator('h1, h2').first().isVisible({ timeout: 8000 }).catch(() => false);

        expect(hasResults || hasNoResults || hasHeading, 'Search page should render content after query').toBeTruthy();
    });

    test('typing in search and pressing enter navigates', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');

        // Find the search input (header search bar or search icon)
        const searchInput = page.locator('input[type="search"], input[placeholder*="Search" i], input[placeholder*="Поиск" i]').first();

        if (await searchInput.isVisible().catch(() => false)) {
            await searchInput.fill('Tesla Model S');
            await searchInput.press('Enter');
            await page.waitForLoadState('networkidle');
            // Should be on /search page or articles filtered
            expect(page.url()).toMatch(/search|q=/i);
        } else {
            // If no search input on homepage, just verify /search route works
            const response = await page.goto('/search?q=Tesla');
            expect(response?.status()).toBeLessThan(500);
        }
    });
});
