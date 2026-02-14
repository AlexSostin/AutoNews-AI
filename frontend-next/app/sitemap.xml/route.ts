import { NextResponse } from 'next/server';

const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const SITE_URL = 'https://www.freshmotors.net';
const FETCH_TIMEOUT = 15000; // 15 seconds timeout (was 5, too aggressive)

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

async function getAllArticles(): Promise<any[]> {
    const allArticles: any[] = [];
    let page = 1;
    const maxPages = 20; // Safety limit

    try {
        while (page <= maxPages) {
            const res = await fetchWithTimeout(
                `${PRODUCTION_API_URL}/articles/?is_published=true&page=${page}`,
                FETCH_TIMEOUT
            );

            if (!res.ok) break;
            const data = await res.json();
            const results = data.results || data || [];

            if (results.length === 0) break;
            allArticles.push(...results);

            // If no next page, we're done
            if (!data.next) break;
            page++;
        }
    } catch (e) {
        console.error(`Sitemap: Failed to fetch articles (page ${page}):`, e);
    }

    console.log(`Sitemap: Fetched ${allArticles.length} articles across ${page} pages`);
    return allArticles;
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
        getAllArticles(),
        getCategories(),
    ]);

    const staticPages = [
        { loc: SITE_URL, changefreq: 'daily', priority: '1.0' },
        { loc: `${SITE_URL}/articles`, changefreq: 'daily', priority: '0.8' },
        { loc: `${SITE_URL}/about`, changefreq: 'monthly', priority: '0.4' },
        { loc: `${SITE_URL}/contact`, changefreq: 'monthly', priority: '0.4' },
        { loc: `${SITE_URL}/privacy-policy`, changefreq: 'monthly', priority: '0.3' },
        { loc: `${SITE_URL}/terms`, changefreq: 'monthly', priority: '0.3' },
    ];

    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  ${staticPages.map(p => `
  <url>
    <loc>${p.loc}</loc>
    <lastmod>${new Date().toISOString()}</lastmod>
    <changefreq>${p.changefreq}</changefreq>
    <priority>${p.priority}</priority>
  </url>`).join('')}
  ${articles.map((article: any) => `
  <url>
    <loc>${SITE_URL}/articles/${article.slug}</loc>
    <lastmod>${new Date(article.updated_at || article.created_at).toISOString()}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>`).join('')}
  ${categories.filter((category: any) => category.is_visible !== false && category.article_count > 0).map((category: any) => `
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
