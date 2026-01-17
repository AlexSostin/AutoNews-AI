'use client';

import { useState, useEffect } from 'react';
import Header from '@/components/public/Header';
import Footer from '@/components/public/Footer';
import ArticleCard from '@/components/public/ArticleCard';
import Pagination from '@/components/public/Pagination';
import { ArticleGridSkeleton } from '@/components/public/Skeletons';
import { TrendingUp } from 'lucide-react';

export default function TrendingPage() {
  const [articles, setArticles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const pageSize = 12;

  useEffect(() => {
    const fetchTrendingArticles = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams({
          is_published: 'true',
          ordering: '-views',
          page: currentPage.toString(),
          page_size: pageSize.toString(),
        });

        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/articles/?${params}`);
        const data = await res.json();
        
        setArticles(data.results || []);
        setTotalPages(Math.ceil((data.count || 0) / pageSize));
      } catch (error) {
        console.error('Failed to load trending articles:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTrendingArticles();
  }, [currentPage]);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <>
      <Header />
      
      <main className="flex-1 bg-gray-50 min-h-screen">
        {/* Hero Header */}
        <section className="bg-gradient-to-br from-orange-500 via-pink-500 to-purple-600 text-white py-16 relative overflow-hidden">
          <div className="absolute inset-0 bg-black/10"></div>
          <div className="container mx-auto px-4 relative z-10 text-center">
            <div className="inline-flex items-center gap-3 bg-white/20 backdrop-blur-sm px-6 py-2 rounded-full mb-6">
              <TrendingUp className="w-6 h-6" />
              <span className="font-bold text-lg">Trending Now</span>
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold mb-4 drop-shadow-lg">Most Popular Articles</h1>
            <p className="text-lg sm:text-xl text-white/90 max-w-2xl mx-auto">
              Discover the most viewed automotive news and reviews
            </p>
          </div>
        </section>

        <div className="container mx-auto px-4 py-12">
          {loading ? (
            <ArticleGridSkeleton count={12} />
          ) : articles.length === 0 ? (
            <div className="text-center py-20 bg-white rounded-2xl shadow-sm">
              <div className="text-6xl mb-4">📊</div>
              <p className="text-gray-600 text-lg">No trending articles found.</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {articles.map((article, index) => (
                  <div key={article.id} className="relative">
                    {/* Ranking Badge */}
                    {currentPage === 1 && index < 3 && (
                      <div className="absolute -top-2 -left-2 z-10">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-white shadow-lg ${
                          index === 0 ? 'bg-gradient-to-br from-yellow-400 to-yellow-600' :
                          index === 1 ? 'bg-gradient-to-br from-gray-300 to-gray-500' :
                          'bg-gradient-to-br from-orange-400 to-orange-600'
                        }`}>
                          {index + 1}
                        </div>
                      </div>
                    )}
                    <ArticleCard article={article} />
                  </div>
                ))}
              </div>

              {totalPages > 1 && (
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  onPageChange={handlePageChange}
                />
              )}
            </>
          )}
        </div>
      </main>
      
      <Footer />
    </>
  );
}
