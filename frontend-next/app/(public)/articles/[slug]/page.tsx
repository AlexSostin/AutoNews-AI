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

async function getArticle(slug: string): Promise<Article | null> {
  try {
    const res = await fetch(`${getApiUrl()}/articles/${slug}/`, {
      next: { revalidate: 30 }
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    // SSR fetch failed (Docker dev Turbopack/webpack DNS issue) — fallback to client
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

  return {
    title: `${article.title} - Fresh Motors`,
    description: article.summary,
    alternates: {
      canonical: `${siteUrl}/articles/${slug}`,
    },
    openGraph: {
      title: article.title,
      description: article.summary,
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
      description: article.summary,
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
