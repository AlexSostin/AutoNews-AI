'use client';

import { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Header from '@/components/public/Header';
import Footer from '@/components/public/Footer';
import ArticleCard from '@/components/public/ArticleCard';
import Pagination from '@/components/public/Pagination';
import { ArticleGridSkeleton } from '@/components/public/Skeletons';
import TagsDropdown from '@/components/public/TagsDropdown';
import CategoriesDropdown from '@/components/public/CategoriesDropdown';
import SearchInput from '@/components/public/SearchInput';
import AdBanner from '@/components/public/AdBanner';
import StickyBottomAd from '@/components/public/StickyBottomAd';

async function getArticles(page = 1, category = '', tag = '', search = '') {
  const params = new URLSearchParams();
  params.append('page', page.toString());
  params.append('page_size', '12');
  if (category) params.append('category', category);
  if (tag) params.append('tag', tag);
  if (search) params.append('search', search);

  const res = await fetch(`http://127.0.0.1:8001/api/v1/articles/?${params.toString()}`, {
    cache: 'no-store'
  });
  
  if (!res.ok) {
    return { results: [], count: 0, next: null, previous: null };
  }
  
  return res.json();
}

async function getCategories() {
  const res = await fetch('http://127.0.0.1:8001/api/v1/categories/', {
    cache: 'no-store'
  });
  
  if (!res.ok) {
    return [];
  }
  
  const data = await res.json();
  // Handle both array and paginated response
  return Array.isArray(data) ? data : data.results || [];
}

async function getTags() {
  const res = await fetch('http://127.0.0.1:8001/api/v1/tags/', {
    cache: 'no-store'
  });
  
  if (!res.ok) {
    return [];
  }
  
  const data = await res.json();
  // Handle both array and paginated response
  return Array.isArray(data) ? data : data.results || [];
}

export default async function ArticlesPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; category?: string; tag?: string; search?: string }>;
}) {
  const params = await searchParams;
  const page = parseInt(params.page || '1');
  const category = params.category || '';
  const tag = params.tag || '';
  const search = params.search || '';

  const [articlesData, categories, tags] = await Promise.all([
    getArticles(page, category, tag, search),
    getCategories(),
    getTags()
  ]);

  const totalPages = Math.ceil(articlesData.count / 12);

  return (
    <>
      <Header />
      
      <main className="flex-1 bg-gray-50">
        {/* Top Ad */}
        <div className="bg-white border-b border-gray-200 py-4">
          <div className="container mx-auto px-4 flex justify-center">
            <AdBanner format="leaderboard" />
          </div>
        </div>

        <div className="container mx-auto px-4 py-12">
          {/* Page Header */}
          <div className="mb-12 text-center">
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-gray-900 mb-4">All Articles</h1>
            <p className="text-lg sm:text-xl text-gray-600">
              {articlesData.count} {articlesData.count === 1 ? 'article' : 'articles'} found
            </p>
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
                      {categories.find((c: any) => c.slug === category)?.name} ✕
                    </Link>
                  )}
                  {tag && (
                    <Link
                      href={`/articles?${category ? `category=${category}&` : ''}${search ? `search=${search}` : ''}`}
                      className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm hover:bg-indigo-200 transition-colors"
                    >
                      {tags.find((t: any) => t.slug === tag)?.name} ✕
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

          {/* Main Content with Sidebar */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* Articles Grid */}
            <div className="lg:col-span-3">
              {/* Articles Grid */}
              {articlesData.results.length === 0 ? (
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
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8 mb-12">
                    {articlesData.results.slice(0, 6).map((article: any) => (
                      <ArticleCard key={article.id} article={article} />
                    ))}
                  </div>

                  {/* Mid-section Ad */}
                  {articlesData.results.length > 6 && (
                    <div className="flex justify-center my-12">
                      <AdBanner format="leaderboard" />
                    </div>
                  )}

                  {articlesData.results.length > 6 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8 mb-12">
                      {articlesData.results.slice(6).map((article: any) => (
                        <ArticleCard key={article.id} article={article} />
                      ))}
                    </div>
                  )}
                </>
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-center items-center gap-2">
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
                          className={`w-10 h-10 flex items-center justify-center rounded-lg font-medium transition-all ${
                            page === pageNum
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

            {/* Sidebar Ads */}
            <div className="lg:col-span-1 space-y-6">
              <div className="sticky top-24 space-y-6">
                <div className="bg-white rounded-xl shadow-md p-4 flex justify-center">
                  <AdBanner format="rectangle" />
                </div>
                <div className="bg-white rounded-xl shadow-md p-4 flex justify-center">
                  <AdBanner format="large-rectangle" />
                </div>
                <div className="bg-white rounded-xl shadow-md p-4 flex justify-center">
                  <AdBanner format="half-page" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      
      <Footer />
      <StickyBottomAd />
    </>
  );
}
