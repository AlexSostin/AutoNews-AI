import ArticleCard from '@/components/public/ArticleCard';
import AdBanner from '@/components/public/AdBanner';
import TrendingSection from '@/components/public/TrendingSection';
import EmptyState from '@/components/public/EmptyState';
import MaintenancePage from '@/components/public/MaintenancePage';
import MaintenanceGuard from '@/components/public/MaintenanceGuard';
import Hero from '@/components/public/Hero';
import InfiniteArticleList from '@/components/public/InfiniteArticleList';
import JsonLd from '@/components/public/JsonLd';
import PageAnalyticsTracker from '@/components/public/PageAnalyticsTracker';
import Link from 'next/link';
import { fixImageUrl } from '@/lib/config';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  alternates: {
    canonical: '/',
  },
};

export const revalidate = 120; // Revalidate every 2 minutes (was 30s — too frequent, triggers 4 API calls each time)

// Production API URL - hardcoded for server-side rendering
const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const LOCAL_API_URL = 'http://localhost:8000/api/v1';

// Get API URL - use production URL on Railway, localhost for local dev
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

async function getSettings() {
  try {
    const res = await fetch(`${getApiUrl()}/settings/`, {
      next: { revalidate: 300 },  // Settings rarely change — cache 5 min
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

// checkIsAdmin removed — now handled client-side by MaintenanceGuard

async function getArticles() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const res = await fetch(`${getApiUrl()}/articles/?is_published=true`, {
      next: { revalidate: 120 }, // refresh every 2 minutes
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) return { results: [] };
    return await res.json();
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      console.warn('API request timed out - backend may not be running');
    } else {
      console.warn('Backend API not available yet:', error instanceof Error ? error.message : error);
    }
    return { results: [] };
  }
}

async function getCategories() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const res = await fetch(`${getApiUrl()}/categories/`, {
      next: { revalidate: 3600 }, // refresh every hour
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : data.results || [];
  } catch (error) {
    console.warn('Backend API not available for categories');
    return [];
  }
}

async function getBrands() {
  try {
    const res = await fetch(`${getApiUrl()}/cars/brands/`, { next: { revalidate: 3600 } });
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data.slice(0, 8) : [];
  } catch {
    return [];
  }
}

export default async function Home() {
  // Fetch all data in parallel (no auth needed — maintenance guard is client-side)
  const [settings, articlesData, categories, brands] = await Promise.all([
    getSettings(),
    getArticles(),
    getCategories(),
    getBrands(),
  ]);
  const articles = articlesData.results || [];

  return (
    <MaintenanceGuard
      maintenanceMode={settings?.maintenance_mode || false}
      maintenanceMessage={settings?.maintenance_message}
      fallback={<MaintenancePage message={settings?.maintenance_message} />}
    >
      <main className="flex-1 bg-gradient-to-b from-gray-50 to-white">
        <PageAnalyticsTracker pageType="home" />
        {/* Schema.org JSON-LD for Home Page */}
        <JsonLd data={{
          "@context": "https://schema.org",
          "@type": "WebSite",
          "name": "Fresh Motors",
          "url": "https://www.freshmotors.net",
          "description": "AI-powered automotive news, reviews, and vehicle specifications",
          "potentialAction": {
            "@type": "SearchAction",
            "target": {
              "@type": "EntryPoint",
              "urlTemplate": "https://www.freshmotors.net/articles?search={search_term_string}"
            },
            "query-input": "required name=search_term_string"
          }
        }} />
        <JsonLd data={{
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "Fresh Motors",
          "url": "https://www.freshmotors.net",
          "logo": "https://www.freshmotors.net/logo.png",
          "description": "AI-powered automotive news and vehicle reviews",
          "sameAs": [],
          "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "customer service",
            "url": "https://www.freshmotors.net/contact"
          }
        }} />
        {/* Hero Section */}
        <Hero articles={articles} settings={settings} />

        {/* Top Leaderboard Ad */}
        <div className="container mx-auto px-4 py-8 flex justify-center">
          <AdBanner position="header" />
        </div>

        {/* Categories Section - Refined & Premium */}
        {categories.length > 0 && (
          <section className="relative py-16 overflow-hidden">
            {/* Background Decoration */}
            <div className="absolute top-1/2 left-0 -translate-y-1/2 w-64 h-64 bg-indigo-100/50 rounded-full blur-3xl -z-10"></div>
            <div className="absolute top-1/2 right-0 -translate-y-1/2 w-96 h-96 bg-purple-100/30 rounded-full blur-3xl -z-10"></div>

            <div className="container mx-auto px-4">
              <div className="text-center mb-12">
                <h2 className="text-3xl sm:text-4xl font-black text-gray-900 mb-4 tracking-tight">
                  Browse by Category
                </h2>
                <div className="w-20 h-1.5 bg-indigo-600 mx-auto rounded-full"></div>
              </div>

              <div className="flex flex-wrap gap-4 sm:gap-6 justify-center">
                {categories.map((category: any) => (
                  <Link
                    key={category.id}
                    href={`/categories/${category.slug}`}
                    className="group relative px-6 sm:px-8 py-3 sm:py-4 bg-white/70 backdrop-blur-md border border-gray-200 rounded-2xl transition-all duration-300 hover:border-indigo-500 hover:shadow-[0_20px_40px_rgba(79,70,229,0.15)] hover:-translate-y-1 overflow-hidden"
                  >
                    {/* Hover Glow */}
                    <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>

                    <div className="relative flex items-center gap-3">
                      <span className="text-gray-900 font-bold text-lg sm:text-xl group-hover:text-indigo-600 transition-colors">
                        {category.name}
                      </span>
                      <span className="flex items-center justify-center bg-gray-100 text-gray-500 text-xs font-black min-w-[28px] h-[28px] px-1.5 rounded-lg group-hover:bg-indigo-600 group-hover:text-white transition-all shadow-inner">
                        {category.article_count}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* Browse by Brand Section */}
        {brands.length > 0 && settings?.show_browse_by_brand !== false && (
          <section className="py-12">
            <div className="container mx-auto px-4">
              <div className="text-center mb-10">
                <h2 className="text-3xl sm:text-4xl font-black text-gray-900 mb-4 tracking-tight">
                  Browse by Brand
                </h2>
                <div className="w-20 h-1.5 bg-purple-600 mx-auto rounded-full" />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
                {brands.map((brand: any) => (
                  <Link
                    key={brand.slug}
                    href={`/cars/${brand.slug}`}
                    className="group flex items-center gap-3 bg-white/70 backdrop-blur-md border border-gray-200 rounded-xl px-4 py-3 transition-all duration-300 hover:border-purple-400 hover:shadow-lg hover:-translate-y-0.5"
                  >
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-100 to-indigo-100 flex items-center justify-center text-lg group-hover:from-purple-200 group-hover:to-indigo-200 transition-all overflow-hidden flex-shrink-0">
                      {brand.image ? (
                        <img src={fixImageUrl(brand.image)} alt="" className="w-full h-full object-cover rounded-lg" />
                      ) : (
                        <span>🚗</span>
                      )}
                    </div>
                    <div className="min-w-0">
                      <div className="font-bold text-gray-900 group-hover:text-purple-600 transition-colors truncate">
                        {brand.name}
                      </div>
                      <div className="text-xs text-gray-500">
                        {brand.model_count} {brand.model_count === 1 ? 'model' : 'models'}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>

              <div className="text-center mt-8">
                <Link
                  href="/cars"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 text-white rounded-xl font-bold hover:bg-purple-700 transition-colors"
                >
                  View All Brands →
                </Link>
              </div>
            </div>
          </section>
        )}

        {/* Latest Articles */}
        <section className="container mx-auto px-4 py-16">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* Main Content - Articles */}
            <div className="lg:col-span-3">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-10 gap-4">
                <h2 className="text-3xl sm:text-4xl font-bold text-gray-800">Latest Articles</h2>
                <Link href="/articles" className="text-indigo-600 hover:text-indigo-700 font-semibold hover:underline text-base sm:text-lg whitespace-nowrap">
                  View All →
                </Link>
              </div>

              {articles.length === 0 ? (
                <EmptyState />
              ) : (
                <InfiniteArticleList
                  initialArticles={articles.slice(0, 18)}
                  initialPage={1}
                  pageSize={18}
                  mobileRecommendedSlot={<TrendingSection />}
                />
              )}
            </div>

            {/* Sidebar - Trending (hidden on mobile, shown inline after 6th article instead) */}
            <div className="hidden lg:block lg:col-span-1 space-y-6">
              <TrendingSection />
              <AdBanner position="sidebar" />
            </div>
          </div>
        </section>

        {/* Bottom Ad before Footer */}
        <div className="container mx-auto px-4 pb-12 flex justify-center">
          <AdBanner position="footer" />
        </div>
      </main>
    </MaintenanceGuard>
  );
}
