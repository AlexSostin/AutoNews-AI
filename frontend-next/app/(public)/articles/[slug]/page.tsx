import type { Metadata } from 'next';
import ClientArticleDetail from '@/components/public/ClientArticleDetail';
import InfiniteArticleScroll from '@/components/public/InfiniteArticleScroll';
import { Article } from '@/types';

// API URLs
const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const LOCAL_API_URL = 'http://localhost:8000/api/v1';

const getApiUrl = () => {
  if (process.env.API_INTERNAL_URL) return process.env.API_INTERNAL_URL;
  if (process.env.RAILWAY_ENVIRONMENT === 'production') return PRODUCTION_API_URL;
  return process.env.NEXT_PUBLIC_API_URL || LOCAL_API_URL;
};

/** Fetch with up to `retries` retries and a per-attempt timeout.
 *  Reduces transient Railway failures that cause unnecessary React #419 fallbacks. */
async function fetchWithRetry(url: string, retries = 2, delayMs = 500): Promise<Response | null> {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, {
        headers: { 'User-Agent': 'FreshMotors-SSR/1.0 (Next.js)', 'Accept': 'application/json' },
        next: { revalidate: 60 },
        signal: AbortSignal.timeout(8000),
      });
      if (res.ok) return res;
      // Don't retry 4xx — article genuinely not found
      if (res.status >= 400 && res.status < 500) return null;
      console.warn(`[SSR] Article fetch attempt ${attempt + 1} failed: ${res.status} for ${url}`);
    } catch (err) {
      // Network error / timeout — retry after delay
      console.warn(`[SSR] Article fetch attempt ${attempt + 1} error: ${err instanceof Error ? err.message : err} for ${url}`);
    }
    if (attempt < retries) await new Promise(r => setTimeout(r, delayMs));
  }
  console.error(`[SSR] Article fetch FAILED after ${retries + 1} attempts: ${url} — falling back to client render`);
  return null;
}

async function getArticle(slug: string): Promise<Article | null> {
  try {
    const res = await fetchWithRetry(`${getApiUrl()}/articles/${slug}/`);
    if (!res) return null;
    return res.json();
  } catch (err) {
    console.warn(`[SSR] getArticle('${slug}') error: ${err instanceof Error ? err.message : err}`);
    return null;
  }
}

// ── SEO metadata (SSR) ────────────────────────────────────────────────────────
export async function generateMetadata(
  { params }: { params: Promise<{ slug: string }> }
): Promise<Metadata> {
  const { slug } = await params;
  const article = await getArticle(slug);

  if (!article) {
    return {
      title: 'Article - Fresh Motors',
      description: 'Read the latest automotive news and reviews',
    };
  }

  const siteUrl = 'https://www.freshmotors.net';
  const seoDesc = article.seo_description || article.summary;

  return {
    title: `${article.title} - Fresh Motors`,
    description: seoDesc,
    alternates: {
      canonical: `${siteUrl}/articles/${slug}`,
    },
    openGraph: {
      title: article.title,
      description: article.summary || seoDesc,
      url: `${siteUrl}/articles/${slug}`,
      type: 'article',
      publishedTime: article.created_at,
      modifiedTime: article.updated_at,
      authors: ['Fresh Motors'],
      images: [
        {
          url: article.image || `${siteUrl}/logo.png`,
          width: 1200,
          height: 630,
          alt: article.title,
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: article.title,
      description: article.summary || seoDesc,
      images: [article.image || `${siteUrl}/logo.png`],
    },
  };
}

// ── Page component ────────────────────────────────────────────────────────────
export default async function ArticleDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = await getArticle(slug);

  // Docker dev: SSR fetch fails (DNS) → client-side fallback
  if (!article) {
    return <ClientArticleDetail slug={slug} />;
  }

  // Production / Railway: SSR success → hand off to InfiniteArticleScroll
  // InfiniteArticleScroll renders the article + loads subsequent articles on scroll
  return <InfiniteArticleScroll initialArticle={article} />;
}
