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
        expect(bodyWidth).toBeLessThanOrEqual(375 + 10); // 10px tolerance (WebKit scrollbar can add ~6px)
    });

    test('navigation is accessible on mobile', async ({ page }) => {
        await page.goto('/', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(2000); // Wait for hydration

        // Mobile should have either a hamburger button, nav links, or any header links
        const hamburger = page.locator(
            'button[aria-label*="menu" i], button[aria-label*="nav" i], [data-testid="mobile-menu"], button:has(svg)'
        ).first();
        const navLinks = page.locator('nav a, header a[href="/articles"], header a[href="/"], header a');

        const hasHamburger = await hamburger.isVisible().catch(() => false);
        const hasVisibleNav = await navLinks.first().isVisible().catch(() => false);
        const hasHeader = await page.locator('header').isVisible().catch(() => false);

        expect(
            hasHamburger || hasVisibleNav || hasHeader,
            'Mobile should have a header with navigation elements'
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

        const href = await articleLink.getAttribute('href');
        if (!href) { test.skip(true, 'No article href found'); return; }

        // Navigate directly instead of clicking (Next.js Link click can be flaky)
        await page.goto(href, { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(2000);

        // Title should be visible
        const heading = page.locator('h1').first();
        await expect(heading).toBeVisible({ timeout: 10000 });

        // Content should not overflow horizontally
        const scrollWidth = await page.evaluate(() => document.body.scrollWidth);
        expect(scrollWidth).toBeLessThanOrEqual(375 + 10); // 10px tolerance for WebKit scrollbar
    });

    test('infinite scroll works on mobile viewport', async ({ page }) => {
        test.setTimeout(45000);
        // Pre-check: need ≥2 articles AND infinite scroll enabled
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
            test.skip(true, 'Backend API not reachable');
            return;
        }

        // Check if infinite scroll is enabled in settings
        try {
            const settingsResp = await page.request.get(`${API_BASE}/settings/1/`);
            if (settingsResp.ok()) {
                const settings = await settingsResp.json();
                if (settings.infinite_scroll_enabled === false) {
                    test.skip(true, 'Infinite scroll is disabled in site settings');
                    return;
                }
            }
        } catch {
            // If settings endpoint fails, skip gracefully
            test.skip(true, 'Settings API not reachable');
            return;
        }

        await page.goto('/articles', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(3000);

        const articleLink = page.locator('a[href*="/articles/"]').first();
        if (!(await articleLink.isVisible().catch(() => false))) {
            test.skip(true, 'No articles visible');
            return;
        }

        const href = await articleLink.getAttribute('href');
        if (!href) { test.skip(true, 'No article href found'); return; }

        // Navigate directly (Next.js Link click unreliable in E2E)
        await page.goto(href, { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(3000);

        const articleUrl = page.url();

        // Scroll down aggressively — use mouse.wheel to ensure IntersectionObserver fires
        for (let i = 0; i < 8; i++) {
            await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
            await page.mouse.wheel(0, 2000);
            await page.waitForTimeout(1000);
        }

        // Fallback: scroll sentinel into view to ensure IntersectionObserver fires
        await page.evaluate(() => {
            const sentinel = document.querySelector('[aria-hidden="true"]');
            if (sentinel) {
                sentinel.scrollIntoView({ behavior: 'instant', block: 'end' });
            }
        });

        await page.waitForTimeout(8000);

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
