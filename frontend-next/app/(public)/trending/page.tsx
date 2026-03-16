import type { Metadata } from 'next';
import TrendingClient from './TrendingClient';
import { Article } from '@/types';

export const metadata: Metadata = {
  title: 'Trending Articles | Fresh Motors',
  description: 'Discover the most viewed automotive news and reviews on Fresh Motors. Our most popular articles about EVs, hybrids, and the latest car technology.',
  openGraph: {
    title: 'Trending Articles | Fresh Motors',
    description: 'Discover the most viewed automotive news and reviews on Fresh Motors.',
  },
};

const API_BASE = 'https://heroic-healing-production-2365.up.railway.app/api/v1';

async function getTrendingArticles(): Promise<{ results: Article[]; count: number }> {
  try {
    const res = await fetch(
      `${API_BASE}/articles/?is_published=true&ordering=-views&page=1&page_size=12`,
      { next: { revalidate: 300 } } // cache 5 min
    );
    if (!res.ok) return { results: [], count: 0 };
    return res.json();
  } catch {
    return { results: [], count: 0 };
  }
}

export default async function TrendingPage() {
  const data = await getTrendingArticles();

  return <TrendingClient initialArticles={data.results} initialCount={data.count} />;
}
