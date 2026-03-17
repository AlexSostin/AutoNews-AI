import { test, expect } from '@playwright/test';

// ═══════════════════════════════════════════════════════════════════════════
// Mobile E2E Tests — runs on iPhone/Pixel viewport
// Covers: responsive layout, navigation, infinite scroll on mobile
// ═══════════════════════════════════════════════════════════════════════════

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

test.describe('Mobile Experience', () => {
    // Force mobile viewport for all tests in this describe
    test.use({ viewport: { width: 375, height: 667 } });
    test.setTimeout(30000);

    test('homepage renders without horizontal overflow', async ({ page }) => {
        await page.goto('/', { waitUntil: 'domcontentloaded' });
        await expect(page.locator('header')).toBeVisible();

        // Body should not overflow the viewport width
        const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
        expect(bodyWidth).toBeLessThanOrEqual(375 + 5); // 5px tolerance
    });

    test('navigation is accessible on mobile', async ({ page }) => {
        await page.goto('/', { waitUntil: 'domcontentloaded' });

        // Mobile should have either a hamburger button OR visible nav links
        const hamburger = page.locator(
            'button[aria-label*="menu" i], button[aria-label*="nav" i], [data-testid="mobile-menu"], button:has(svg)'
        ).first();
        const navLinks = page.locator('nav a, header a[href="/articles"]');

        const hasHamburger = await hamburger.isVisible().catch(() => false);
        const hasVisibleNav = await navLinks.first().isVisible().catch(() => false);

        expect(
            hasHamburger || hasVisibleNav,
            'Mobile should have either a hamburger menu or visible navigation links'
        ).toBeTruthy();
    });

    test('article cards display in single column', async ({ page }) => {
        await page.goto('/articles', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(3000);

        const cards = page.locator('article, [data-testid="article-card"], a[href*="/articles/"]');
        const cardCount = await cards.count();

        if (cardCount >= 2) {
            const first = await cards.nth(0).boundingBox();
            const second = await cards.nth(1).boundingBox();

            if (first && second) {
                // In single-column layout, cards should be stacked vertically
                // (second card's top should be below first card's bottom)
                expect(second.y).toBeGreaterThanOrEqual(first.y + first.height - 10); // 10px overlap tolerance
            }
        }
    });

    test('article page is readable on mobile', async ({ page }) => {
        await page.goto('/articles', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(3000);

        const articleLink = page.locator('a[href*="/articles/"]').first();
        if (!(await articleLink.isVisible().catch(() => false))) {
            test.skip(true, 'No articles available');
            return;
        }

        await articleLink.click({ force: true });
        await page.waitForLoadState('domcontentloaded');
        await page.waitForTimeout(2000);

        // Title should be visible
        const heading = page.locator('h1').first();
        await expect(heading).toBeVisible({ timeout: 10000 });

        // Content should not overflow horizontally
        const scrollWidth = await page.evaluate(() => document.body.scrollWidth);
        expect(scrollWidth).toBeLessThanOrEqual(375 + 5);
    });

    test('infinite scroll works on mobile viewport', async ({ page }) => {
        // Pre-check: need ≥2 articles
        try {
            const resp = await page.request.get(`${API_BASE}/articles/?is_published=true&page_size=1`);
            if (resp.ok()) {
                const data = await resp.json();
                const count = data.count ?? 0;
                if (count < 2) {
                    test.skip(true, `Only ${count} article(s) — need ≥2`);
                    return;
                }
            }
        } catch {
            // Backend not reachable — skip gracefully
            test.skip(true, 'Backend API not reachable');
            return;
        }

        await page.goto('/articles', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(3000);

        const articleLink = page.locator('a[href*="/articles/"]').first();
        if (!(await articleLink.isVisible().catch(() => false))) {
            test.skip(true, 'No articles visible');
            return;
        }

        await articleLink.click({ force: true });
        await page.waitForLoadState('domcontentloaded');
        await page.waitForTimeout(3000);

        const articleUrl = page.url();

        // Scroll down aggressively — mobile scrolls faster
        for (let i = 0; i < 10; i++) {
            await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
            await page.waitForTimeout(800);
        }
        await page.waitForTimeout(5000);

        const finalUrl = page.url();
        const articleCount = await page.locator('article').count();
        const h1Count = await page.locator('h1').count();

        // On mobile, infinite scroll should load the next article
        const scrollWorked = finalUrl !== articleUrl || articleCount > 1 || h1Count > 1;

        expect(
            scrollWorked,
            `Mobile infinite scroll: URL unchanged (${articleUrl} → ${finalUrl}), articles: ${articleCount}, h1s: ${h1Count}`
        ).toBeTruthy();
    });

    test('footer is reachable on mobile', async ({ page }) => {
        await page.goto('/', { waitUntil: 'domcontentloaded' });

        // Scroll all the way down
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(1000);

        await expect(page.locator('footer')).toBeVisible({ timeout: 5000 });
    });
});
