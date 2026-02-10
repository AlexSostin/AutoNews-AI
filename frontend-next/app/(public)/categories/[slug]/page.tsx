import { notFound } from 'next/navigation';
import Link from 'next/link';
import ArticleCard from '@/components/public/ArticleCard';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Article, Category } from '@/types';
import { Metadata } from 'next';

// Production API URL
const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const LOCAL_API_URL = 'http://localhost:8000/api/v1';

const getApiUrl = () => {
  // 1. If running on server (Docker/Node), use internal Docker URL if available
  if (typeof window === 'undefined') {
    if (process.env.API_INTERNAL_URL) {
      return process.env.API_INTERNAL_URL;
    }
  }

  // 2. Custom domain API
  if (process.env.CUSTOM_DOMAIN_API) {
    return process.env.CUSTOM_DOMAIN_API;
  }

  // 3. Check if running on Railway (production)
  if (process.env.RAILWAY_ENVIRONMENT === 'production') {
    return PRODUCTION_API_URL;
  }

  // 4. Default fallback for client-side local dev
  return process.env.NEXT_PUBLIC_API_URL || LOCAL_API_URL;
};

async function getCategory(slug: string) {
  const res = await fetch(`${getApiUrl()}/categories/?search=${slug}`, {
    cache: 'no-store'
  });

  if (!res.ok) {
    return null;
  }

  const data = await res.json();
  const categories = Array.isArray(data) ? data : data.results || [];
  return categories.find((cat: any) => cat.slug === slug) || null;
}

async function getArticlesByCategory(categorySlug: string, page = 1) {
  const res = await fetch(
    `${getApiUrl()}/articles/?category=${categorySlug}&page=${page}&page_size=12`,
    { cache: 'no-store' }
  );

  if (!res.ok) {
    return { results: [], count: 0, next: null, previous: null };
  }

  return res.json();
}

export default async function CategoryPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const { slug } = await params;
  const category = await getCategory(slug);

  if (!category) {
    notFound();
  }

  const queryParams = await searchParams;
  const page = parseInt(queryParams.page || '1');
  const articlesData = await getArticlesByCategory(slug, page);
  const totalPages = Math.ceil(articlesData.count / 12);

  return (
    <>

      <main className="flex-1 bg-gray-50">
        {/* Category Header */}
        <section className="bg-gradient-to-br from-slate-900 via-purple-900 to-gray-900 text-white py-16 relative overflow-hidden">
          <div className="absolute inset-0 bg-black/10"></div>
          <div className="container mx-auto px-4 relative z-10">
            <div className="max-w-3xl">
              <div className="flex items-center gap-3 mb-4">
                <Link
                  href="/articles"
                  className="text-white/80 hover:text-white transition-colors"
                >
                  Articles
                </Link>
                <span className="text-white/60">/</span>
                <span className="text-white font-semibold">{category.name}</span>
              </div>
              <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-4 drop-shadow-lg">{category.name}</h1>
              {category.description && (
                <p className="text-base sm:text-lg md:text-xl text-white/90 leading-relaxed">{category.description}</p>
              )}
              <div className="mt-6">
                <span className="bg-white/20 backdrop-blur-sm px-6 py-2 rounded-full text-lg font-semibold">
                  {articlesData.count} {articlesData.count === 1 ? 'Article' : 'Articles'}
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Articles Grid */}
        <section className="container mx-auto px-4 py-16">
          {articlesData.results.length === 0 ? (
            <div className="text-center py-20 bg-white rounded-xl shadow-md">
              <div className="text-6xl mb-4">📰</div>
              <h3 className="text-2xl font-bold text-gray-800 mb-2">No articles in this category yet</h3>
              <p className="text-gray-600 mb-6">Check back later for new content</p>
              <Link
                href="/articles"
                className="inline-block px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
              >
                View all articles
              </Link>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-12">
                {articlesData.results.map((article: any) => (
                  <ArticleCard key={article.id} article={article} />
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-center items-center gap-2">
                  {page > 1 && (
                    <Link
                      href={`/categories/${slug}?page=${page - 1}`}
                      className="px-4 py-2 bg-white border-2 border-indigo-200 text-indigo-700 rounded-lg hover:bg-indigo-50 transition-colors flex items-center gap-2 font-medium"
                    >
                      <ChevronLeft size={20} />
                      Previous
                    </Link>
                  )}

                  <div className="flex gap-2">
                    {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                      let pageNum;
                      if (totalPages <= 7) {
                        pageNum = i + 1;
                      } else if (page <= 4) {
                        pageNum = i + 1;
                      } else if (page >= totalPages - 3) {
                        pageNum = totalPages - 6 + i;
                      } else {
                        pageNum = page - 3 + i;
                      }

                      return (
                        <Link
                          key={pageNum}
                          href={`/categories/${slug}?page=${pageNum}`}
                          className={`w-10 h-10 flex items-center justify-center rounded-lg font-medium transition-all ${page === pageNum
                            ? 'bg-indigo-600 text-white shadow-md'
                            : 'bg-white border-2 border-indigo-200 text-indigo-700 hover:bg-indigo-50'
                            }`}
                        >
                          {pageNum}
                        </Link>
                      );
                    })}
                  </div>

                  {page < totalPages && (
                    <Link
                      href={`/categories/${slug}?page=${page + 1}`}
                      className="px-4 py-2 bg-white border-2 border-indigo-200 text-indigo-700 rounded-lg hover:bg-indigo-50 transition-colors flex items-center gap-2 font-medium"
                    >
                      Next
                      <ChevronRight size={20} />
                    </Link>
                  )}
                </div>
              )}
            </>
          )}
        </section>
      </main>

    </>
  );
}
