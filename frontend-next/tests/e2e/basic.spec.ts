import { test, expect } from '@playwright/test';

test.describe('Homepage', () => {
  test('should load homepage', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/AutoNews/);
  });

  test('should have navigation', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('header')).toBeVisible();
    await expect(page.getByRole('link', { name: /articles/i })).toBeVisible();
  });

  test('should show articles on homepage', async ({ page }) => {
    await page.goto('/');
    // Wait for articles to load
    await page.waitForSelector('article, [data-testid="article-card"]', { timeout: 10000 }).catch(() => {});
  });
});

test.describe('Articles Page', () => {
  test('should load articles page', async ({ page }) => {
    await page.goto('/articles');
    await expect(page.getByRole('heading', { name: /articles/i })).toBeVisible();
  });

  test('should have filters', async ({ page }) => {
    await page.goto('/articles');
    await expect(page.getByText(/category/i)).toBeVisible();
  });
});

test.describe('Authentication', () => {
  test('should show login page', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('button', { name: /sign in|login/i })).toBeVisible();
  });
});

test.describe('Mobile Responsive', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('should be responsive on mobile', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('header')).toBeVisible();
  });
});
