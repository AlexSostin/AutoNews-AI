import { Suspense } from 'react';
import Link from 'next/link';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import ArticleCard from '@/components/public/ArticleCard';
import AdBanner from '@/components/public/AdBanner';
import { ArticleGridSkeleton } from '@/components/public/Skeletons';
import TagsDropdown from '@/components/public/TagsDropdown';
import CategoriesDropdown from '@/components/public/CategoriesDropdown';
import SearchInput from '@/components/public/SearchInput';
import { Article, Category, Tag } from '@/types';
import PageAnalyticsTracker from '@/components/public/PageAnalyticsTracker';

// Runtime API URL detection for server components
const getApiUrl = () => {
    if (process.env.API_INTERNAL_URL) return process.env.API_INTERNAL_URL;
    if (process.env.RAILWAY_ENVIRONMENT === 'production') return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
};

export const dynamic = 'force-dynamic';
export const revalidate = 60;

async function ArticlesContent({ searchParams }: { searchParams: Promise<{ [key: string]: string | string[] | undefined }> }) {
  const resolvedParams = await searchParams;
  const pageStr = typeof resolvedParams.page === 'string' ? resolvedParams.page : '1';
  const page = parseInt(pageStr) || 1;
  const category = typeof resolvedParams.category === 'string' ? resolvedParams.category : '';
  const tag = typeof resolvedParams.tag === 'string' ? resolvedParams.tag : '';
  const search = typeof resolvedParams.search === 'string' ? resolvedParams.search : '';

  let articles: Article[] = [];
  let totalCount = 0;
  let categories: Category[] = [];
  let tagsObj: Tag[] = [];

  try {
    const apiUrl = getApiUrl();
    
    // Fetch articles
    const queryParams = new URLSearchParams();
    queryParams.append('page', page.toString());
    queryParams.append('page_size', '12');
    queryParams.append('is_published', 'true');
    if (category) queryParams.append('category', category);
    if (tag) queryParams.append('tag', tag);
    if (search) queryParams.append('search', search);

    const SSR_HEADERS = { 'User-Agent': 'FreshMotors-SSR/1.0 (Next.js)', 'Accept': 'application/json' };

    const [articlesRes, categoriesRes, tagsRes] = await Promise.all([
      fetch(`${apiUrl}/articles/?${queryParams.toString()}`, { headers: SSR_HEADERS, next: { revalidate: 60 } }),
      fetch(`${apiUrl}/categories/`, { headers: SSR_HEADERS, next: { revalidate: 300 } }),
      fetch(`${apiUrl}/tags/`, { headers: SSR_HEADERS, next: { revalidate: 300 } })
    ]);

    if (articlesRes.ok) {
        const articlesData = await articlesRes.json();
        articles = articlesData.results || [];
        totalCount = articlesData.count || 0;
    }

    if (categoriesRes.ok) {
        const categoriesData = await categoriesRes.json();
        categories = Array.isArray(categoriesData) ? categoriesData : categoriesData.results || [];
    }

    if (tagsRes.ok) {
        const tagsData = await tagsRes.json();
        tagsObj = Array.isArray(tagsData) ? tagsData : tagsData.results || [];
    }
  } catch (error) {
    console.error('Error fetching data for Articles API:', error);
  }

  const totalPages = Math.ceil(totalCount / 12);

  return (
    <>
      {/* Client-side tracking logic */}
      <PageAnalyticsTracker pageType="articles" />
      
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
                  tags={tagsObj}
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
                      {tagsObj.find((t: Tag) => t.slug === tag)?.name} ✕
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

export default function ArticlesPage({ searchParams }: { searchParams: Promise<{ [key: string]: string | string[] | undefined }> }) {
  return (
    <Suspense fallback={<ArticleGridSkeleton />}>
      <ArticlesContent searchParams={searchParams} />
    </Suspense>
  );
}
