import Header from '@/components/public/Header';
import Footer from '@/components/public/Footer';
import ArticleCard from '@/components/public/ArticleCard';
import AdBanner from '@/components/public/AdBanner';
import StickyBottomAd from '@/components/public/StickyBottomAd';
import TrendingSection from '@/components/public/TrendingSection';
import EmptyState from '@/components/public/EmptyState';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

// Production API URL - hardcoded for server-side rendering
const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const LOCAL_API_URL = 'http://localhost:8001/api/v1';

// Get API URL - use production URL on Railway, localhost for local dev
const getApiUrl = () => {
  // Check if running on Railway (production)
  if (process.env.RAILWAY_ENVIRONMENT === 'production') {
    return PRODUCTION_API_URL;
  }
  // Check env vars
  if (process.env.NEXT_PUBLIC_API_URL && !process.env.NEXT_PUBLIC_API_URL.includes('localhost')) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  return LOCAL_API_URL;
};

async function getArticles() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
    
    const res = await fetch(`${getApiUrl()}/articles/?is_published=true`, {
      cache: 'no-store',
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
      next: { revalidate: 3600 },
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

export default async function Home() {
  const articlesData = await getArticles();
  const categories = await getCategories();
  const articles = articlesData.results || [];

  return (
    <>
      <Header />
      
      <main className="flex-1 bg-gradient-to-b from-gray-50 to-white">
        {/* Hero Section */}
        <section className="bg-gradient-to-br from-slate-900 via-purple-900 to-gray-900 text-white py-24 relative overflow-hidden">
          <div className="absolute inset-0 bg-black/10"></div>
          <div className="container mx-auto px-4 text-center relative z-10">
            <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-6 drop-shadow-lg">Welcome to AutoNews</h1>
            <p className="text-lg sm:text-xl md:text-2xl mb-10 text-white/90 max-w-2xl mx-auto">Your premier source for automotive news, reviews, and insights</p>
            <Link 
              href="/articles" 
              className="bg-white text-purple-900 px-6 sm:px-10 py-3 sm:py-4 rounded-full font-bold hover:bg-purple-50 hover:shadow-xl transition-all inline-block text-base sm:text-lg shadow-lg hover:scale-105 transform"
            >
              Explore Articles →
            </Link>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-gray-50 to-transparent"></div>
        </section>

        {/* Top Leaderboard Ad */}
        <div className="container mx-auto px-4 py-8 flex justify-center">
          <AdBanner format="leaderboard" />
        </div>

        {/* Categories */}
        {categories.length > 0 && (
          <section className="container mx-auto px-4 py-12">
            <h2 className="text-2xl font-bold text-center mb-8 text-gray-800">Browse by Category</h2>
            <div className="flex flex-wrap gap-4 justify-center">
              {categories.map((category: any) => (
                <Link
                  key={category.id}
                  href={`/categories/${category.slug}`}
                  className="px-4 sm:px-6 py-2 sm:py-3 bg-white border-2 border-indigo-200 text-indigo-700 rounded-full hover:bg-indigo-50 hover:border-indigo-400 hover:shadow-md transition-all font-medium"
                >
                  {category.name} <span className="text-indigo-400">({category.article_count})</span>
                </Link>
              ))}
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
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
                    {articles.slice(0, 6).map((article: any) => (
                      <ArticleCard key={article.id} article={article} />
                    ))}
                  </div>

                  {/* Mid-content Ad */}
                  {articles.length > 6 && (
                    <div className="flex justify-center my-12">
                      <AdBanner format="leaderboard" />
                    </div>
                  )}

                  {articles.length > 6 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
                      {articles.slice(6).map((article: any) => (
                        <ArticleCard key={article.id} article={article} />
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Sidebar - Trending */}
            <div className="lg:col-span-1">
              <TrendingSection />
            </div>
          </div>
        </section>

        {/* Bottom Ad before Footer */}
        <div className="container mx-auto px-4 pb-12 flex justify-center">
          <AdBanner format="leaderboard" />
        </div>
      </main>
      
      <Footer />
      <StickyBottomAd />
    </>
  );
}
