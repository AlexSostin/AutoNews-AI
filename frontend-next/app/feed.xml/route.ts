import { NextResponse } from 'next/server';

const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const SITE_URL = 'https://www.freshmotors.net';

async function getArticles() {
  try {
    const res = await fetch(`${PRODUCTION_API_URL}/articles/?is_published=true&page_size=50`, {
      next: { revalidate: 3600 }, // Revalidate every hour
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.results || [];
  } catch (e) {
    console.error('Failed to fetch articles for RSS:', e);
    return [];
  }
}

export async function GET() {
  const articles = await getArticles();

  const rss = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Fresh Motors - Latest Automotive News</title>
    <link>${SITE_URL}</link>
    <description>Your source for the latest automotive news, car reviews, and industry insights.</description>
    <language>en-us</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    <atom:link href="${SITE_URL}/feed.xml" rel="self" type="application/rss+xml" />
    <image>
      <url>${SITE_URL}/logo.png</url>
      <title>Fresh Motors</title>
      <link>${SITE_URL}</link>
    </image>
    ${articles.map((article: any) => `
    <item>
      <title><![CDATA[${article.title}]]></title>
      <link>${SITE_URL}/articles/${article.slug}</link>
      <guid isPermaLink="true">${SITE_URL}/articles/${article.slug}</guid>
      <description><![CDATA[${article.summary}]]></description>
      <content:encoded><![CDATA[${article.summary}]]></content:encoded>
      <pubDate>${new Date(article.created_at).toUTCString()}</pubDate>
      ${article.image ? `<enclosure url="${article.image}" type="image/jpeg" />` : ''}
      ${article.category_names?.length > 0 ? article.category_names.map((name: string) => `<category>${name}</category>`).join('\n      ') : ''}
      ${article.tags ? article.tags.map((tag: any) => `<category>${tag.name}</category>`).join('\n      ') : ''}
    </item>
    `).join('')}
  </channel>
</rss>`;

  return new NextResponse(rss, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=86400',
    },
  });
}
