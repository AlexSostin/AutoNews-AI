import { NextResponse } from 'next/server';

const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const SITE_URL = 'https://www.freshmotors.net';

/**
 * Google News Sitemap — only articles from last 48 hours.
 * 
 * Format: https://developers.google.com/search/docs/crawling-indexing/sitemaps/news-sitemap
 * 
 * Google News requires:
 * - news:publication (name + language)
 * - news:publication_date (ISO 8601)
 * - news:title
 * 
 * Only articles published within the last 2 days are included,
 * as Google News ignores older content in news sitemaps.
 */
export async function GET() {
    let articles: any[] = [];

    try {
        const res = await fetch(
            `${PRODUCTION_API_URL}/articles/?is_published=true&ordering=-created_at&page_size=50`,
            {
                next: { revalidate: 600 }, // Revalidate every 10 minutes
                headers: { 'Accept': 'application/json' },
            }
        );

        if (res.ok) {
            const data = await res.json();
            const allArticles = data.results || data || [];

            // Filter to last 48 hours only (Google News requirement)
            const cutoff = new Date(Date.now() - 48 * 60 * 60 * 1000);
            articles = allArticles.filter((a: any) => new Date(a.created_at) >= cutoff);
        }
    } catch (e) {
        console.error('News Sitemap: Failed to fetch articles:', e);
    }

    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  ${articles.map((article: any) => {
        const pubDate = new Date(article.created_at).toISOString();
        const title = (article.title || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        const categories = article.categories?.map((c: any) => c.name).join(', ') || 'Automotive';
        const tags = article.tag_names?.join(', ') || '';
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
      <news:title>${title}</news:title>${tags ? `
      <news:keywords>${tags.replace(/&/g, '&amp;')}</news:keywords>` : ''}
    </news:news>${imageUrl ? `
    <image:image>
      <image:loc>${imageUrl.replace(/&/g, '&amp;')}</image:loc>
      <image:title>${title}</image:title>
    </image:image>` : ''}
  </url>`;
    }).join('')}
</urlset>`;

    return new NextResponse(xml, {
        headers: {
            'Content-Type': 'application/xml; charset=utf-8',
            'Cache-Control': 'public, s-maxage=600, stale-while-revalidate=1800',
        },
    });
}
