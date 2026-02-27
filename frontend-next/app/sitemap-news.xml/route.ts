import { NextResponse } from 'next/server';

const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const SITE_URL = 'https://www.freshmotors.net';

/**
 * Google News Sitemap — recent articles for Google News indexing.
 * 
 * Format: https://developers.google.com/search/docs/crawling-indexing/sitemaps/news-sitemap
 * 
 * Google News requires:
 * - news:publication (name + language)
 * - news:publication_date (ISO 8601)
 * - news:title
 * 
 * Note: news:keywords was deprecated by Google in 2012 and excluded.
 * 
 * Articles from the last 7 days are included. Google News prioritises
 * content from the last 2 days, but older articles are still valid.
 * If no recent articles, we return a minimal valid XML with a comment
 * so Google doesn't flag it as an error.
 */
export async function GET() {
    let articles: any[] = [];

    try {
        const res = await fetch(
            `${PRODUCTION_API_URL}/articles/?is_published=true&ordering=-created_at&page_size=100`,
            {
                next: { revalidate: 600 }, // Revalidate every 10 minutes
                headers: {
                    'Accept': 'application/json',
                    'User-Agent': 'FreshMotors/Sitemap',
                },
            }
        );

        if (res.ok) {
            const data = await res.json();
            const allArticles = data.results || data || [];

            // Include articles from last 7 days (Google prioritises last 48h but accepts older)
            const cutoff = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
            articles = allArticles.filter((a: any) => new Date(a.created_at) >= cutoff);
        } else {
            console.error(`News Sitemap: API returned ${res.status} ${res.statusText}`);
        }
    } catch (e) {
        console.error('News Sitemap: Failed to fetch articles:', e);
    }

    // Escape XML entities in text content
    const escapeXml = (str: string) =>
        (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');

    const urlEntries = articles.map((article: any) => {
        const pubDate = new Date(article.created_at).toISOString();
        const title = escapeXml(article.title);
        const imageUrl = article.image || '';

        return `
  <url>
    <loc>${SITE_URL}/articles/${article.slug}</loc>
    <news:news>
      <news:publication>
        <news:name>Fresh Motors</news:name>
        <news:language>en</news:language>
      </news:publication>
      <news:publication_date>${pubDate}</news:publication_date>
      <news:title>${title}</news:title>
    </news:news>${imageUrl ? `
    <image:image>
      <image:loc>${escapeXml(imageUrl)}</image:loc>
      <image:title>${title}</image:title>
    </image:image>` : ''}
  </url>`;
    }).join('');

    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">${urlEntries || `
  <!-- No recent articles published in the last 7 days -->`}
</urlset>`;

    return new NextResponse(xml, {
        headers: {
            'Content-Type': 'application/xml; charset=utf-8',
            'Cache-Control': 'public, s-maxage=600, stale-while-revalidate=1800',
        },
    });
}
