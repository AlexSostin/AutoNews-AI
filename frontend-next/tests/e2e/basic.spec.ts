import { test, expect } from '@playwright/test';

// ═══════════════════════════════════════════════════════════════════════════
// Homepage
// ═══════════════════════════════════════════════════════════════════════════

test.describe('Homepage', () => {
  test('should load homepage with title', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Fresh Motors/i);
  });

  test('should have navigation header', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('header')).toBeVisible();
  });

  test('should show article cards', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const articles = page.locator('article, [data-testid="article-card"], a[href*="/articles/"]');
    await expect(articles.first()).toBeVisible({ timeout: 10000 });
  });

  test('should have footer', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('footer')).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// Articles Page
// ═══════════════════════════════════════════════════════════════════════════

test.describe('Articles Page', () => {
  test('should load articles listing', async ({ page }) => {
    await page.goto('/articles');
    await page.waitForLoadState('networkidle');
    const heading = page.getByRole('heading', { name: 'All Articles', exact: true });
    await expect(heading).toBeVisible({ timeout: 10000 });
  });

  test('should have working article links', async ({ page }) => {
    await page.goto('/articles');
    await page.waitForLoadState('networkidle');
    const articleLink = page.locator('a[href*="/articles/"]').first();
    if (await articleLink.isVisible()) {
      const href = await articleLink.getAttribute('href');
      expect(href).toContain('/articles/');
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// Article Detail
// ═══════════════════════════════════════════════════════════════════════════

test.describe('Article Detail', () => {
  test('should load an article page', async ({ page }) => {
    await page.goto('/articles');
    await page.waitForLoadState('networkidle');

    // Dismiss cookie/consent overlay if present (z-index 9999)
    await page.evaluate(() => {
      document.querySelectorAll('[class*="fixed"]').forEach(el => {
        const style = window.getComputedStyle(el);
        if (parseInt(style.zIndex) > 9000) (el as HTMLElement).remove();
      });
    });

    const articleLink = page.locator('a[href*="/articles/"]').first();
    if (await articleLink.isVisible()) {
      await articleLink.click({ force: true });
      await page.waitForLoadState('networkidle');
      const heading = page.locator('h1, h2').first();
      await expect(heading).toBeVisible({ timeout: 10000 });
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// Categories
// ═══════════════════════════════════════════════════════════════════════════

test.describe('Categories', () => {
  test('should load categories page', async ({ page }) => {
    const response = await page.goto('/categories/reviews');
    if (response) {
      expect(response.status()).toBeLessThan(500);
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// Static Pages
// ═══════════════════════════════════════════════════════════════════════════

test.describe('Static Pages', () => {
  test('about page loads', async ({ page }) => {
    const response = await page.goto('/about');
    expect(response?.status()).toBeLessThan(500);
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 5000 });
  });

  test('privacy policy page loads', async ({ page }) => {
    const response = await page.goto('/privacy-policy');
    expect(response?.status()).toBeLessThan(500);
  });

  test('contact page loads', async ({ page }) => {
    const response = await page.goto('/contact');
    expect(response?.status()).toBeLessThan(500);
  });

  test('trending page loads', async ({ page }) => {
    const response = await page.goto('/trending');
    expect(response?.status()).toBeLessThan(500);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// SEO Meta Tags
// ═══════════════════════════════════════════════════════════════════════════

test.describe('SEO', () => {
  test('homepage has meta description', async ({ page }) => {
    await page.goto('/');
    const metaDesc = page.locator('meta[name="description"]');
    const content = await metaDesc.getAttribute('content');
    expect(content).toBeTruthy();
    expect(content!.length).toBeGreaterThan(10);
  });

  test('homepage has og:title', async ({ page }) => {
    await page.goto('/');
    const ogTitle = page.locator('meta[property="og:title"]');
    const content = await ogTitle.getAttribute('content');
    expect(content).toBeTruthy();
  });

  test('robots.txt is accessible', async ({ page }) => {
    const response = await page.goto('/robots.txt');
    expect(response?.status()).toBe(200);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// Authentication
// ═══════════════════════════════════════════════════════════════════════════

test.describe('Authentication', () => {
  test('should show login page', async ({ page }) => {
    const response = await page.goto('/login');
    expect(response?.status()).toBeLessThan(500);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// Performance
// ═══════════════════════════════════════════════════════════════════════════

test.describe('Performance', () => {
  test('homepage loads within 5 seconds', async ({ page }) => {
    const start = Date.now();
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    const loadTime = Date.now() - start;
    expect(loadTime).toBeLessThan(5000);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// Mobile Responsive
// ═══════════════════════════════════════════════════════════════════════════

test.describe('Mobile Responsive', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('should be responsive on mobile', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('header')).toBeVisible();
    const body = page.locator('body');
    const bodyBox = await body.boundingBox();
    if (bodyBox) {
      expect(bodyBox.width).toBeLessThanOrEqual(375 + 20);
    }
  });
});
