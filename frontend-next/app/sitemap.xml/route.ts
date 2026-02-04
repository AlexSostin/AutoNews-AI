import { NextResponse } from 'next/server';

const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const SITE_URL = 'https://freshmotors.net';
const FETCH_TIMEOUT = 5000; // 5 seconds timeout

async function fetchWithTimeout(url: string, timeout: number) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            signal: controller.signal,
            next: { revalidate: 3600 },
            headers: { 'Accept': 'application/json' },
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        throw error;
    }
}

async function getArticles() {
    try {
        const res = await fetchWithTimeout(
            `${PRODUCTION_API_URL}/articles/?is_published=true&page_size=100`,
            FETCH_TIMEOUT
        );

        if (!res.ok) return [];
        const data = await res.json();
        return data.results || data || [];
    } catch (e) {
        console.error('Sitemap: Failed to fetch articles');
        return [];
    }
}

async function getCategories() {
    try {
        const res = await fetchWithTimeout(
            `${PRODUCTION_API_URL}/categories/`,
            FETCH_TIMEOUT
        );

        if (!res.ok) return [];
        const data = await res.json();
        return Array.isArray(data) ? data : (data.results || []);
    } catch (e) {
        console.error('Sitemap: Failed to fetch categories');
        return [];
    }
}

export async function GET() {
    const [articles, categories] = await Promise.all([
        getArticles(),
        getCategories(),
    ]);

    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>${SITE_URL}</loc>
    <lastmod>${new Date().toISOString()}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>${SITE_URL}/articles</loc>
    <lastmod>${new Date().toISOString()}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  ${articles.map((article: any) => `
  <url>
    <loc>${SITE_URL}/articles/${article.slug}</loc>
    <lastmod>${new Date(article.updated_at || article.created_at).toISOString()}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>`).join('')}
  ${categories.map((category: any) => `
  <url>
    <loc>${SITE_URL}/categories/${category.slug}</loc>
    <lastmod>${new Date().toISOString()}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>`).join('')}
</urlset>`;

    return new NextResponse(xml, {
        headers: {
            'Content-Type': 'application/xml; charset=utf-8',
            'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=86400',
        },
    });
}
