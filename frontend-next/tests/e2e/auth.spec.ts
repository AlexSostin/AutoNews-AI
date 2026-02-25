import { test, expect } from '@playwright/test';

test.describe('Authentication and Session', () => {
    test.setTimeout(60000); // 60 seconds timeout

    // Common headers for CORS used in all tests
    const corsHeaders = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    };

    test('should login successfully and show user profile', async ({ page }) => {
        // Mock Login endpoint
        await page.route(url => url.href.includes('/token/'), async route => {
            console.log('INTERCEPT LOGIN:', route.request().url());
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({
                status: 200,
                headers: corsHeaders,
                contentType: 'application/json',
                body: JSON.stringify({
                    access: `header.${Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url')}.signature`,
                    refresh: 'fake-refresh-token',
                    user: { id: 1, username: 'testuser' }
                })
            });
        });

        // Mock users/me endpoint for Header
        await page.route(url => url.href.includes('/users/me'), async route => {
            console.log('INTERCEPT USERS ME:', route.request().url());
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({
                status: 200,
                headers: corsHeaders,
                contentType: 'application/json',
                body: JSON.stringify({ id: 1, username: 'testuser', email: 'test@example.com' })
            });
        });

        // Mock favorites/check so homepage doesn't hit real Django server with fake JWT and trigger auto-logout
        await page.route(url => url.href.includes('/favorites/check'), async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({ status: 200, headers: corsHeaders, body: JSON.stringify({ is_favorite: false }) });
        });

        page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
        page.on('response', response => console.log('RESPONSE TRACE:', response.status(), response.url()));
        page.route('**/*', async route => {
            // Just a silent sniffer if needed, but playwright logs are enough.
            route.fallback();
        });

        // 3. Navigate to login and submit form
        await page.goto('/login', { waitUntil: 'domcontentloaded' });
        // Ensure hydration
        await page.waitForTimeout(1500);

        await page.locator('#username').first().fill('testuser');
        await page.locator('#password').first().fill('password123');
        await page.click('button[type="submit"]');

        // 4. Verify we are redirected to homepage and header updates
        await page.waitForURL('/', { waitUntil: 'domcontentloaded', timeout: 30000 });

        await expect(page.locator('header')).toContainText('testuser', { timeout: 10000 });
    });

    test('should seamlessly refresh token without logging out', async ({ page, context }) => {
        page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
        page.on('response', response => {
            if (response.status() === 401 || response.status() === 500) {
                console.log('ERROR RESPONSE:', response.status(), response.url());
            }
        });

        // Helper to create a fake JWT.
        const pastExp = Math.floor(Date.now() / 1000) - 3600; // 1 hour ago
        const pastPayload = Buffer.from(JSON.stringify({ exp: pastExp })).toString('base64url');
        const expiredJwt = `header.${pastPayload}.signature`;

        // 1. Initial Static Mocks for Page Load
        await page.route('**/api/v1/users/me/**', async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({ status: 200, headers: corsHeaders, body: JSON.stringify({ id: 1, username: 'testuser' }) });
        });

        // Mock favorites/check to always return false so the heart buttons appear grey
        await page.route('**/api/v1/favorites/check/**', async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({ status: 200, headers: corsHeaders, body: '{"is_favorite": false}' });
        });

        // 2. Catch all other endpoints first (Playwright matches last-registered first)
        await page.route('**/api/v1/favorites/**', async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });
            await route.fulfill({ status: 200, headers: corsHeaders, body: '[]' });
        });

        // Mock favorites/toggle/ to trigger the 401 Interceptor
        let toggleCount = 0;
        await page.route('**/api/v1/favorites/toggle/**', async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });

            toggleCount++;
            if (toggleCount === 1) {
                // First attempt: Token is formally rejected
                await route.fulfill({ status: 401, headers: corsHeaders, body: '{"detail":"Token is invalid or expired"}' });
            } else {
                // Second attempt: Token has been refreshed, accept the favorite!
                await route.fulfill({ status: 200, headers: corsHeaders, body: '{"is_favorited": true}' });
            }
        });

        await page.route('**/api/v1/token/refresh/**', async route => {
            if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 200, headers: corsHeaders });

            const futureExp = Math.floor(Date.now() / 1000) + 3600;
            const futurePayload = Buffer.from(JSON.stringify({ exp: futureExp })).toString('base64url');

            await route.fulfill({
                status: 200,
                headers: corsHeaders,
                contentType: 'application/json',
                body: JSON.stringify({
                    access: `header.${futurePayload}.signature`,
                    refresh: 'new-refresh-token',
                })
            });
        });

        // 3. Inject State and Navigate
        await page.goto('/', { waitUntil: 'domcontentloaded' });

        await context.addCookies([
            { name: 'access_token', value: expiredJwt, domain: 'localhost', path: '/' },
            { name: 'refresh_token', value: 'valid-refresh-token', domain: 'localhost', path: '/' }
        ]);

        await page.evaluate((jwt) => {
            localStorage.setItem('access_token', jwt);
            localStorage.setItem('refresh_token', 'valid-refresh-token');
            localStorage.setItem('user', JSON.stringify({ id: 1, username: 'testuser' }));
        }, expiredJwt);

        await page.reload({ waitUntil: 'domcontentloaded' });

        // Wait for hydration by checking if the header successfully reads localStorage state via React useEffect
        await expect(page.locator('header')).toContainText('testuser', { timeout: 10000 });

        // 4. Set up the intercept promise
        const refreshPromise = page.waitForResponse(response =>
            response.url().includes('token/refresh') && response.status() === 200,
            { timeout: 10000 }
        );

        // 5. Trigger the action! Click the first available favorite button
        const favButton = page.locator('button[aria-label="Add to favorites"]').first();
        await favButton.waitFor({ state: 'visible' });
        await favButton.click();

        // 6. Wait for the refresh negotiation to complete
        await refreshPromise;

        const details = await page.evaluate(() => ({
            url: window.location.href,
            cookies: document.cookie,
            ls: Object.keys(localStorage).reduce((acc, k) => ({ ...acc, [k]: localStorage.getItem(k) }), {})
        }));
        console.error("\n\n=============== DEBUG DUMP ===============");
        console.error("PAGE URL:", details.url);
        console.error("COOKIES:", details.cookies);
        console.error("LOCALSTORAGE:", JSON.stringify(details.ls, null, 2));
        console.error("==========================================\n\n");

        // Verify cookies were updated
        const cookies = await page.context().cookies();
        const newAccess = cookies.find(c => c.name === 'access_token')?.value;
        expect(newAccess).not.toBe(expiredJwt);
    });
});
