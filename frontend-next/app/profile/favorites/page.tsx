'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/public/Header';
import Footer from '@/components/public/Footer';
import { getToken, getUserFromStorage } from '@/lib/auth';
import { Heart, ArrowLeft, Loader2 } from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';
import { favoriteAPI, Favorite } from '@/lib/favorites';

export default function FavoritesPage() {
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const loadFavorites = async () => {
    const token = getToken();
    if (!token) {
      router.push('/login');
      return;
    }

    try {
      setIsLoading(true);
      const data = await favoriteAPI.getFavorites(token);
      setFavorites(data);
    } catch (err) {
      setError('Failed to load favorites');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const user = getUserFromStorage();
    if (!user) {
      router.push('/login?redirect=/profile/favorites');
      return;
    }

    loadFavorites();
  }, []);

  const handleRemove = async (favoriteId: number) => {
    const token = getToken();
    if (!token) return;

    try {
      await favoriteAPI.removeFavorite(favoriteId, token);
      setFavorites(favorites.filter(f => f.id !== favoriteId));
    } catch (err) {
      console.error('Failed to remove favorite:', err);
    }
  };

  if (isLoading) {
    return (
      <>
        <Header />
        <main className="flex-1 bg-gray-50 flex items-center justify-center min-h-screen">
          <div className="text-center">
            <Loader2 className="inline-block animate-spin text-indigo-600" size={48} />
          </div>
        </main>
        <Footer />
      </>
    );
  }

  return (
    <>
      <Header />
      
      <main className="flex-1 bg-gray-50">
        <div className="container mx-auto px-4 py-12">
          {/* Back Button */}
          <Link 
            href="/profile"
            className="inline-flex items-center gap-2 text-indigo-600 hover:text-indigo-700 mb-6 font-medium"
          >
            <ArrowLeft size={20} />
            Back to Profile
          </Link>

          {/* Page Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-pink-600 rounded-xl flex items-center justify-center">
                <Heart size={24} className="text-white fill-white" />
              </div>
              <h1 className="text-4xl font-bold text-gray-900">My Favorites</h1>
            </div>
            <p className="text-gray-600">{favorites.length} saved articles</p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          {/* Favorites Grid */}
          {favorites.length === 0 ? (
            <div className="bg-white rounded-xl shadow-md p-12 text-center">
              <div className="inline-flex items-center justify-center w-24 h-24 bg-red-100 rounded-full mb-6">
                <Heart size={48} className="text-red-600" />
              </div>
              
              <h2 className="text-2xl font-bold text-gray-900 mb-3">No Favorites Yet</h2>
              <p className="text-gray-600 mb-6 max-w-md mx-auto">
                Start saving your favorite articles to easily find them later. 
                Click the heart icon on any article to add it to your favorites!
              </p>
              
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/"
                  className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
                >
                  Browse Articles
                </Link>
                
                <Link
                  href="/profile"
                  className="px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
                >
                  Back to Profile
                </Link>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {favorites.map((favorite) => {
                const imageUrl = favorite.article_image 
                  ? (favorite.article_image.startsWith('http') 
                      ? favorite.article_image.replace('http://backend:8001', 'http://localhost:8001')
                      : `${process.env.NEXT_PUBLIC_MEDIA_URL || 'http://localhost:8001'}${favorite.article_image}`)
                  : 'https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=800&h=400&fit=crop';

                return (
                  <div key={favorite.id} className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-xl transition-all hover:-translate-y-1">
                    <Link href={`/articles/${favorite.article_slug}`}>
                      <div className="relative h-48 w-full">
                        <Image
                          src={imageUrl}
                          alt={favorite.article_title}
                          fill
                          className="object-cover hover:scale-105 transition-transform duration-300"
                          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                        />
                      </div>
                    </Link>
                    
                    <div className="p-5">
                      <div className="flex items-start justify-between gap-2 mb-3">
                        <Link href={`/articles/${favorite.article_slug}`}>
                          <h3 className="text-lg font-bold text-gray-900 hover:text-indigo-600 transition-colors line-clamp-2">
                            {favorite.article_title}
                          </h3>
                        </Link>
                      </div>
                      
                      <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                        {favorite.article_summary}
                      </p>
                      
                      <div className="flex items-center justify-between">
                        <span className="text-xs bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full font-medium">
                          {favorite.article_category}
                        </span>
                        
                        <button
                          onClick={() => handleRemove(favorite.id)}
                          className="text-red-600 hover:text-red-700 transition-colors flex items-center gap-1 text-sm font-semibold"
                        >
                          <Heart size={16} className="fill-current" />
                          Remove
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
      
      <Footer />
    </>
  );
}

