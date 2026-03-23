import type { Metadata } from 'next';
import ClientArticleDetail from '@/components/public/ClientArticleDetail';
import InfiniteArticleScroll from '@/components/public/InfiniteArticleScroll';
import { Article } from '@/types';
import axios from 'axios';

// API URLs
const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const LOCAL_API_URL = 'http://localhost:8000/api/v1';

const getApiUrl = () => {
  // If we're inside Docker, API_INTERNAL_URL is usually 'http://backend:8000/api/v1'
  // But Axios will respect it. If we run via `npm run dev` in WSL, backend isn't resolvable.
  // We can just trust what's defined, or fallback to localhost.
  if (process.env.API_INTERNAL_URL) return process.env.API_INTERNAL_URL;
  if (process.env.RAILWAY_ENVIRONMENT === 'production') return PRODUCTION_API_URL;
  return process.env.NEXT_PUBLIC_API_URL || LOCAL_API_URL;
};

/** Fetch with Axios and up to `retries` retries and a per-attempt timeout.
 *  Reduces transient failures and bypasses Next.js 16 fetch/undici Docker DNS bugs. */
async function fetchWithRetry(url: string, retries = 2, delayMs = 500) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await axios.get(url, {
        headers: { 'User-Agent': 'FreshMotors-SSR/1.0 (Next.js)', 'Accept': 'application/json' },
        timeout: 8000,
        // Don't throw custom Error on 404 so we can catch it properly below
        validateStatus: (status) => status < 500,
      });
      
      if (res.status >= 200 && res.status < 300) return res.data;
      
      // Don't retry 4xx — article genuinely not found
      if (res.status >= 400 && res.status < 500) return null;
      
      console.warn(`[SSR] Article fetch attempt ${attempt + 1} failed: ${res.status} for ${url}`);
    } catch (err) {
      // Network error / timeout / Axios error — retry after delay
      const message = axios.isAxiosError(err) ? err.message : String(err);
      console.warn(`[SSR] Article fetch attempt ${attempt + 1} error: ${message} for ${url}`);
    }
    if (attempt < retries) await new Promise(r => setTimeout(r, delayMs));
  }
  console.warn(`[SSR] Article fetch FAILED after ${retries + 1} attempts: ${url} — falling back to client render`);
  return null;
}

async function getArticle(slug: string): Promise<Article | null> {
  try {
    const data = await fetchWithRetry(`${getApiUrl()}/articles/${slug}/`);
    if (!data) return null;
    return data as Article;
  } catch (err) {
    console.warn(`[SSR] getArticle('${slug}') error: ${err instanceof Error ? err.message : String(err)}`);
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
