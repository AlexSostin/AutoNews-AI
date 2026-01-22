'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/public/Header';
import Footer from '@/components/public/Footer';
import { isAuthenticated, getUserFromStorage, getToken } from '@/lib/auth';
import { favoriteAPI } from '@/lib/favorites';
import { User, Mail, Calendar, Shield, BookMarked, MessageSquare, Star } from 'lucide-react';
import type { User as UserType } from '@/types';

export default function ProfilePage() {
  const [user, setUser] = useState<UserType | null>(null);
  const [loading, setLoading] = useState(true);
  const [favoritesCount, setFavoritesCount] = useState(0);
  const [authChecked, setAuthChecked] = useState(false);
  const router = useRouter();

  const loadFavoritesCount = async () => {
    const token = getToken();
    if (!token) return;

    try {
      const favorites = await favoriteAPI.getFavorites(token);
      setFavoritesCount(favorites.length);
    } catch (err) {
      console.error('Failed to load favorites count:', err);
    }
  };

  useEffect(() => {
    // Check authentication
    const checkAuth = async () => {
      if (!isAuthenticated()) {
        router.push('/login?redirect=/profile');
        return;
      }

      const userData = getUserFromStorage();
      if (userData) {
        setUser(userData);
        await loadFavoritesCount();
      } else {
        // No user data - redirect to login
        router.push('/login?redirect=/profile');
        return;
      }
      
      setAuthChecked(true);
      setLoading(false);
    };
    
    checkAuth();
  }, [router]);

  if (loading || !authChecked) {
    return (
      <>
        <Header />
        <main className="flex-1 bg-gray-50 flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            <p className="mt-4 text-gray-600">Loading profile...</p>
          </div>
        </main>
        <Footer />
      </>
    );
  }

  if (!user) {
    // Should not happen as we redirect in useEffect, but just in case show loading
    return (
      <>
        <Header />
        <main className="flex-1 bg-gray-50 flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            <p className="mt-4 text-gray-600">Redirecting...</p>
          </div>
        </main>
        <Footer />
      </>
    );
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  return (
    <>
      <Header />
      
      <main className="flex-1 bg-gray-50">
        <div className="container mx-auto px-4 py-12">
          {/* Page Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">My Profile</h1>
            <p className="text-gray-600">Manage your account information and preferences</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Profile Card */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-xl shadow-md p-6">
                <div className="text-center mb-6">
                  <div className="inline-flex items-center justify-center w-24 h-24 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full mb-4">
                    <User size={48} className="text-white" />
                  </div>
                  <h2 className="text-2xl font-bold text-gray-900">{user.username}</h2>
                  {user.is_staff && (
                    <span className="inline-flex items-center gap-1 mt-2 px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-semibold">
                      <Shield size={14} />
                      Administrator
                    </span>
                  )}
                </div>

                <div className="space-y-4 border-t border-gray-200 pt-6">
                  <div className="flex items-center gap-3 text-gray-600">
                    <Mail size={20} className="text-indigo-600" />
                    <div>
                      <div className="text-xs text-gray-500 uppercase">Email</div>
                      <div className="font-medium text-gray-900">{user.email}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 text-gray-600">
                    <Calendar size={20} className="text-indigo-600" />
                    <div>
                      <div className="text-xs text-gray-500 uppercase">Member Since</div>
                      <div className="font-medium text-gray-900">{formatDate(user.date_joined)}</div>
                    </div>
                  </div>

                  {user.first_name && (
                    <div className="flex items-center gap-3 text-gray-600">
                      <User size={20} className="text-indigo-600" />
                      <div>
                        <div className="text-xs text-gray-500 uppercase">Full Name</div>
                        <div className="font-medium text-gray-900">
                          {user.first_name} {user.last_name}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Activity & Stats */}
            <div className="lg:col-span-2 space-y-6">
              {/* Quick Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white rounded-xl shadow-md p-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-indigo-100 rounded-lg">
                      <BookMarked className="w-6 h-6 text-indigo-600" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-gray-900">{favoritesCount}</div>
                      <div className="text-sm text-gray-600">Favorites</div>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-xl shadow-md p-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-purple-100 rounded-lg">
                      <MessageSquare className="w-6 h-6 text-purple-600" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-gray-900">0</div>
                      <div className="text-sm text-gray-600">Comments</div>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-xl shadow-md p-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-amber-100 rounded-lg">
                      <Star className="w-6 h-6 text-amber-600" />
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-gray-900">0</div>
                      <div className="text-sm text-gray-600">Ratings Given</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Coming Soon Features */}
              <div className="bg-white rounded-xl shadow-md p-8">
                <h3 className="text-2xl font-bold text-gray-900 mb-6">Account Features</h3>
                
                <div className="space-y-4">
                  <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                    <BookMarked className="w-6 h-6 text-indigo-600 mt-1" />
                    <div>
                      <h4 className="font-bold text-gray-900 mb-1">Favorite Articles</h4>
                      <p className="text-sm text-gray-600">Save your favorite articles for easy access later. Coming soon!</p>
                    </div>
                  </div>

                  <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                    <MessageSquare className="w-6 h-6 text-purple-600 mt-1" />
                    <div>
                      <h4 className="font-bold text-gray-900 mb-1">Comment History</h4>
                      <p className="text-sm text-gray-600">View and manage all your comments in one place. Coming soon!</p>
                    </div>
                  </div>

                  <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                    <Star className="w-6 h-6 text-amber-600 mt-1" />
                    <div>
                      <h4 className="font-bold text-gray-900 mb-1">Rating History</h4>
                      <p className="text-sm text-gray-600">See all the articles you&apos;ve rated and update your ratings. Coming soon!</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Account Actions */}
              <div className="bg-white rounded-xl shadow-md p-8">
                <h3 className="text-2xl font-bold text-gray-900 mb-6">Account Settings</h3>
                
                <div className="space-y-3">
                  <button className="w-full px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium text-left">
                    Edit Profile (Coming Soon)
                  </button>
                  
                  <button className="w-full px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium text-left">
                    Change Password (Coming Soon)
                  </button>
                  
                  <button className="w-full px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium text-left">
                    Email Preferences (Coming Soon)
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      
      <Footer />
    </>
  );
}
