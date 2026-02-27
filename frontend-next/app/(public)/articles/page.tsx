'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import ArticleCard from '@/components/public/ArticleCard';
import AdBanner from '@/components/public/AdBanner';
import { ArticleGridSkeleton } from '@/components/public/Skeletons';
import TagsDropdown from '@/components/public/TagsDropdown';
import CategoriesDropdown from '@/components/public/CategoriesDropdown';
import SearchInput from '@/components/public/SearchInput';
import { usePageAnalytics, trackEvent } from '@/hooks/usePageAnalytics';
import { Article, Category, Tag } from '@/types';

// Runtime API URL detection for client components
const getApiUrl = () => {
  if (typeof window === 'undefined') return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
  const hostname = window.location.hostname;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8000/api/v1';
  }
  return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
};

export const dynamic = 'force-dynamic';

function ArticlesContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  usePageAnalytics('articles');

  const [articles, setArticles] = useState<Article[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const page = parseInt(searchParams.get('page') || '1');
  const category = searchParams.get('category') || '';
  const tag = searchParams.get('tag') || '';
  const search = searchParams.get('search') || '';

  const totalPages = Math.ceil(totalCount / 12);

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      setLoading(true);

      try {
        // Fetch articles
        const params = new URLSearchParams();
        params.append('page', page.toString());
        params.append('page_size', '12');
        if (category) params.append('category', category);
        if (tag) params.append('tag', tag);
        if (search) params.append('search', search);

        const articlesRes = await fetch(`${getApiUrl()}/articles/?${params.toString()}`);
        if (articlesRes.ok && isMounted) {
          const articlesData = await articlesRes.json();
          setArticles(articlesData.results || []);
          setTotalCount(articlesData.count || 0);
        }
      } catch (error) {
        console.error('Error loading articles:', error);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadData();

    return () => {
      isMounted = false;
    };
  }, [page, category, tag, search]);

  // Track search and filter usage for analytics
  useEffect(() => {
    if (search) {
      trackEvent('search', 'articles', { query: search, results_count: totalCount });
    }
    if (category) {
      trackEvent('filter_use', 'articles', { filter_type: 'category', filter_value: category });
    }
    if (tag) {
      trackEvent('filter_use', 'articles', { filter_type: 'tag', filter_value: tag });
    }
  }, [category, tag, search]);

  // Load categories and tags only once
  useEffect(() => {
    let isMounted = true;

    async function loadFilters() {
      try {
        const apiUrl = getApiUrl();
        const [categoriesRes, tagsRes] = await Promise.all([
          fetch(`${apiUrl}/categories/`),
          fetch(`${apiUrl}/tags/`)
        ]);

        if (categoriesRes.ok && isMounted) {
          const categoriesData = await categoriesRes.json();
          setCategories(Array.isArray(categoriesData) ? categoriesData : categoriesData.results || []);
        }

        if (tagsRes.ok && isMounted) {
          const tagsData = await tagsRes.json();
          setTags(Array.isArray(tagsData) ? tagsData : tagsData.results || []);
        }
      } catch (error) {
        console.error('Error loading filters:', error);
      }
    }

    loadFilters();

    return () => {
      isMounted = false;
    };
  }, []);

  if (loading) {
    return (
      <main className="flex-1 bg-gray-50">
        <div className="container mx-auto px-4 py-12">
          <ArticleGridSkeleton />
        </div>
      </main>
    );
  }

  return (
    <>
      <main className="flex-1 bg-gray-50">
        {/* Hero Header — full-width outside container */}
        <section className="bg-gradient-to-r from-slate-900 via-purple-900 to-slate-800 text-white py-16 relative overflow-hidden">
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSA2MCAwIEwgMCAwIDAgNjAiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgyNTUsMjU1LDI1NSwwLjAzKSIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')] opacity-50"></div>
          <div className="container mx-auto px-4 relative z-10 text-center">
            <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm px-5 py-1.5 rounded-full mb-5 text-sm font-semibold tracking-wide">
              📰 All Articles
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold mb-4 drop-shadow-lg">
              {totalCount} {totalCount === 1 ? 'Article' : 'Articles'}
            </h1>
            <p className="text-lg sm:text-xl text-white/80 max-w-2xl mx-auto">
              Browse our collection of automotive news, reviews, and analysis
            </p>
          </div>
        </section>

        <div className="container mx-auto px-4 py-12">

          {/* Top Ad */}
          <div className="flex justify-center mb-8">
            <AdBanner position="header" />
          </div>

          {/* Filters */}
          <div className="bg-white rounded-xl shadow-md p-6 mb-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Categories Filter */}
              <div>
                <label className="block text-sm font-black text-gray-950 mb-3">Category</label>
                <CategoriesDropdown
                  categories={categories}
                  currentCategory={category}
                  currentTag={tag}
                  currentSearch={search}
                />
              </div>

              {/* Tags Filter */}
              <div>
                <label className="block text-sm font-black text-gray-950 mb-3">Tag</label>
                <TagsDropdown
                  tags={tags}
                  currentTag={tag}
                  currentCategory={category}
                />
              </div>

              {/* Search */}
              <div>
                <label className="block text-sm font-black text-gray-950 mb-3">Search</label>
                <SearchInput
                  currentSearch={search}
                  currentCategory={category}
                  currentTag={tag}
                />
              </div>
            </div>

            {/* Active Filters */}
            {(category || tag || search) && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm text-gray-600 font-medium">Active filters:</span>
                  {category && (
                    <Link
                      href={`/articles?${tag ? `tag=${tag}&` : ''}${search ? `search=${search}` : ''}`}
                      className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm hover:bg-indigo-200 transition-colors"
                    >
                      {categories.find((c: Category) => c.slug === category)?.name} ✕
                    </Link>
                  )}
                  {tag && (
                    <Link
                      href={`/articles?${category ? `category=${category}&` : ''}${search ? `search=${search}` : ''}`}
                      className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm hover:bg-indigo-200 transition-colors"
                    >
                      {tags.find((t: Tag) => t.slug === tag)?.name} ✕
                    </Link>
                  )}
                  {search && (
                    <Link
                      href={`/articles?${category ? `category=${category}&` : ''}${tag ? `tag=${tag}` : ''}`}
                      className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm hover:bg-indigo-200 transition-colors"
                    >
                      &ldquo;{search}&rdquo; ✕
                    </Link>
                  )}
                  <Link
                    href="/articles"
                    className="px-3 py-1 text-indigo-600 hover:text-indigo-700 text-sm font-medium hover:underline"
                  >
                    Clear all
                  </Link>
                </div>
              </div>
            )}
          </div>

          {/* Main Content */}
          <div>
            {/* Articles Grid */}
            <div>
              {/* Articles Grid */}
              {articles.length === 0 ? (
                <div className="text-center py-20 bg-white rounded-xl shadow-md">
                  <div className="text-6xl mb-4">🔍</div>
                  <h3 className="text-2xl font-bold text-gray-800 mb-2">No articles found</h3>
                  <p className="text-gray-600 mb-6">Try adjusting your filters or search query</p>
                  <Link
                    href="/articles"
                    className="inline-block px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
                  >
                    View all articles
                  </Link>
                </div>
              ) : (
                <div className="space-y-8">
                  {/* Group articles into rows */}
                  {Array.from({ length: Math.ceil(articles.length / 4) }, (_, rowIndex) => {
                    const rowArticles = articles.slice(rowIndex * 4, rowIndex * 4 + 4);

                    return (
                      <div key={rowIndex}>
                        {/* Row of articles */}
                        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-8">
                          {rowArticles.map((article: Article, index: number) => (
                            <ArticleCard
                              key={article.id}
                              article={article}
                              priority={rowIndex === 0 && index < 4}
                            />
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-center items-center gap-2 mt-12 pt-8 border-t border-gray-200">
                  {page > 1 && (
                    <Link
                      href={`/articles?page=${page - 1}${category ? `&category=${category}` : ''}${tag ? `&tag=${tag}` : ''}${search ? `&search=${search}` : ''}`}
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
                          href={`/articles?page=${pageNum}${category ? `&category=${category}` : ''}${tag ? `&tag=${tag}` : ''}${search ? `&search=${search}` : ''}`}
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
                      href={`/articles?page=${page + 1}${category ? `&category=${category}` : ''}${tag ? `&tag=${tag}` : ''}${search ? `&search=${search}` : ''}`}
                      className="px-4 py-2 bg-white border-2 border-indigo-200 text-indigo-700 rounded-lg hover:bg-indigo-50 transition-colors flex items-center gap-2 font-medium"
                    >
                      Next
                      <ChevronRight size={20} />
                    </Link>
                  )}
                </div>
              )}
            </div>
          </div>
          {/* Bottom Ad */}
          <div className="flex justify-center mt-8">
            <AdBanner position="footer" />
          </div>
        </div>
      </main>
    </>
  );
}

export default function ArticlesPage() {
  return (
    <Suspense fallback={<ArticleGridSkeleton />}>
      <ArticlesContent />
    </Suspense>
  );
}
