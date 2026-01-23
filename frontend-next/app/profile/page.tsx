'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import Header from '@/components/public/Header';
import Footer from '@/components/public/Footer';
import { isAuthenticated, getUserFromStorage, getToken } from '@/lib/auth';
import { favoriteAPI } from '@/lib/favorites';
import { getApiUrl } from '@/lib/api';
import { User, Mail, Calendar, Shield, BookMarked, MessageSquare, Star, ChevronRight, X, ExternalLink, Clock, Trash2 } from 'lucide-react';
import type { User as UserType } from '@/types';

interface Comment {
  id: number;
  article: number;
  article_title: string;
  article_slug: string;
  article_image: string | null;
  article_category: string | null;
  name: string;
  content: string;
  created_at: string;
  is_approved: boolean;
}

interface Rating {
  id: number;
  article: number;
  article_title: string;
  article_slug: string;
  article_image: string | null;
  article_category: string | null;
  rating: number;
  created_at: string;
}

interface Favorite {
  id: number;
  article: number;
  article_title: string;
  article_slug: string;
  article_image: string | null;
  article_summary: string | null;
  article_category: string | null;
  created_at: string;
}

type ModalType = 'favorites' | 'comments' | 'ratings' | null;

export default function ProfilePage() {
  const [user, setUser] = useState<UserType | null>(null);
  const [loading, setLoading] = useState(true);
  const [favoritesCount, setFavoritesCount] = useState(0);
  const [commentsCount, setCommentsCount] = useState(0);
  const [ratingsCount, setRatingsCount] = useState(0);
  const [authChecked, setAuthChecked] = useState(false);
  const router = useRouter();
  
  // Modal state
  const [activeModal, setActiveModal] = useState<ModalType>(null);
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [ratings, setRatings] = useState<Rating[]>([]);
  const [modalLoading, setModalLoading] = useState(false);

  const loadFavoritesCount = async () => {
    const token = getToken();
    if (!token) return;

    try {
      const favoritesData = await favoriteAPI.getFavorites(token);
      setFavoritesCount(favoritesData.length);
    } catch (err) {
      console.error('Failed to load favorites count:', err);
    }
  };

  const loadCommentsCount = async () => {
    const token = getToken();
    if (!token) return;

    try {
      const response = await fetch(`${getApiUrl()}/comments/my_comments/`, {
        headers: {
          'Authorization': `Token ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setCommentsCount(data.count || 0);
      }
    } catch (err) {
      console.error('Failed to load comments count:', err);
    }
  };

  const loadRatingsCount = async () => {
    const token = getToken();
    if (!token) return;

    try {
      const response = await fetch(`${getApiUrl()}/ratings/my_ratings/`, {
        headers: {
          'Authorization': `Token ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setRatingsCount(data.count || 0);
      }
    } catch (err) {
      console.error('Failed to load ratings count:', err);
    }
  };

  const loadFavorites = async () => {
    const token = getToken();
    if (!token) return;

    setModalLoading(true);
    try {
      const favoritesData = await favoriteAPI.getFavorites(token);
      setFavorites(favoritesData);
    } catch (err) {
      console.error('Failed to load favorites:', err);
    } finally {
      setModalLoading(false);
    }
  };

  const loadComments = async () => {
    const token = getToken();
    if (!token) return;

    setModalLoading(true);
    try {
      const response = await fetch(`${getApiUrl()}/comments/my_comments/`, {
        headers: {
          'Authorization': `Token ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setComments(data.results || []);
      }
    } catch (err) {
      console.error('Failed to load comments:', err);
    } finally {
      setModalLoading(false);
    }
  };

  const loadRatings = async () => {
    const token = getToken();
    if (!token) return;

    setModalLoading(true);
    try {
      const response = await fetch(`${getApiUrl()}/ratings/my_ratings/`, {
        headers: {
          'Authorization': `Token ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setRatings(data.results || []);
      }
    } catch (err) {
      console.error('Failed to load ratings:', err);
    } finally {
      setModalLoading(false);
    }
  };

  const removeFavorite = async (articleId: number) => {
    const token = getToken();
    if (!token) return;

    try {
      await favoriteAPI.removeFavorite(articleId, token);
      setFavorites(favorites.filter(f => f.article !== articleId));
      setFavoritesCount(prev => Math.max(0, prev - 1));
    } catch (err) {
      console.error('Failed to remove favorite:', err);
    }
  };

  const openModal = (type: ModalType) => {
    setActiveModal(type);
    if (type === 'favorites') loadFavorites();
    else if (type === 'comments') loadComments();
    else if (type === 'ratings') loadRatings();
  };

  const closeModal = () => {
    setActiveModal(null);
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
        await Promise.all([
          loadFavoritesCount(),
          loadCommentsCount(),
          loadRatingsCount()
        ]);
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

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getImageUrl = (imagePath: string | null) => {
    if (!imagePath) return null;
    if (imagePath.startsWith('http')) return imagePath;
    const baseUrl = getApiUrl().replace('/api/v1', '');
    return `${baseUrl}${imagePath}`;
  };

  const renderStars = (rating: number) => {
    return (
      <div className="flex items-center gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            size={16}
            className={star <= rating ? 'text-amber-400 fill-amber-400' : 'text-gray-300'}
          />
        ))}
      </div>
    );
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
                <button
                  onClick={() => openModal('favorites')}
                  className="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow text-left group"
                >
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-indigo-100 rounded-lg group-hover:bg-indigo-200 transition-colors">
                      <BookMarked className="w-6 h-6 text-indigo-600" />
                    </div>
                    <div className="flex-1">
                      <div className="text-2xl font-bold text-gray-900">{favoritesCount}</div>
                      <div className="text-sm text-gray-600">Favorites</div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-indigo-600 transition-colors" />
                  </div>
                </button>

                <button
                  onClick={() => openModal('comments')}
                  className="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow text-left group"
                >
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-purple-100 rounded-lg group-hover:bg-purple-200 transition-colors">
                      <MessageSquare className="w-6 h-6 text-purple-600" />
                    </div>
                    <div className="flex-1">
                      <div className="text-2xl font-bold text-gray-900">{commentsCount}</div>
                      <div className="text-sm text-gray-600">Comments</div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-purple-600 transition-colors" />
                  </div>
                </button>

                <button
                  onClick={() => openModal('ratings')}
                  className="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow text-left group"
                >
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-amber-100 rounded-lg group-hover:bg-amber-200 transition-colors">
                      <Star className="w-6 h-6 text-amber-600" />
                    </div>
                    <div className="flex-1">
                      <div className="text-2xl font-bold text-gray-900">{ratingsCount}</div>
                      <div className="text-sm text-gray-600">Ratings Given</div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-amber-600 transition-colors" />
                  </div>
                </button>
              </div>

              {/* Account Features */}
              <div className="bg-white rounded-xl shadow-md p-8">
                <h3 className="text-2xl font-bold text-gray-900 mb-6">Account Features</h3>
                
                <div className="space-y-4">
                  <button
                    onClick={() => openModal('favorites')}
                    className="w-full flex items-start gap-4 p-4 bg-gray-50 rounded-lg hover:bg-indigo-50 transition-colors text-left group"
                  >
                    <BookMarked className="w-6 h-6 text-indigo-600 mt-1" />
                    <div className="flex-1">
                      <h4 className="font-bold text-gray-900 mb-1 group-hover:text-indigo-700">Favorite Articles</h4>
                      <p className="text-sm text-gray-600">View and manage your saved favorite articles</p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400 mt-1 group-hover:text-indigo-600" />
                  </button>

                  <button
                    onClick={() => openModal('comments')}
                    className="w-full flex items-start gap-4 p-4 bg-gray-50 rounded-lg hover:bg-purple-50 transition-colors text-left group"
                  >
                    <MessageSquare className="w-6 h-6 text-purple-600 mt-1" />
                    <div className="flex-1">
                      <h4 className="font-bold text-gray-900 mb-1 group-hover:text-purple-700">Comment History</h4>
                      <p className="text-sm text-gray-600">View all your comments and their approval status</p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400 mt-1 group-hover:text-purple-600" />
                  </button>

                  <button
                    onClick={() => openModal('ratings')}
                    className="w-full flex items-start gap-4 p-4 bg-gray-50 rounded-lg hover:bg-amber-50 transition-colors text-left group"
                  >
                    <Star className="w-6 h-6 text-amber-600 mt-1" />
                    <div className="flex-1">
                      <h4 className="font-bold text-gray-900 mb-1 group-hover:text-amber-700">Rating History</h4>
                      <p className="text-sm text-gray-600">See all the articles you&apos;ve rated</p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400 mt-1 group-hover:text-amber-600" />
                  </button>
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

      {/* Favorites Modal */}
      {activeModal === 'favorites' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-100 rounded-lg">
                  <BookMarked className="w-6 h-6 text-indigo-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900">Favorite Articles ({favoritesCount})</h2>
              </div>
              <button onClick={closeModal} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[calc(80vh-88px)]">
              {modalLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                </div>
              ) : favorites.length === 0 ? (
                <div className="text-center py-12">
                  <BookMarked className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">No favorite articles yet</p>
                  <Link href="/articles" className="text-indigo-600 hover:underline mt-2 inline-block">
                    Browse articles
                  </Link>
                </div>
              ) : (
                <div className="space-y-4">
                  {favorites.map((fav) => (
                    <div key={fav.id} className="flex gap-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                      {fav.article_image && (
                        <div className="flex-shrink-0 w-20 h-20 relative rounded-lg overflow-hidden">
                          <Image
                            src={getImageUrl(fav.article_image) || ''}
                            alt={fav.article_title}
                            fill
                            className="object-cover"
                          />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <Link 
                          href={`/articles/${fav.article_slug}`}
                          className="font-semibold text-gray-900 hover:text-indigo-600 line-clamp-2"
                        >
                          {fav.article_title}
                        </Link>
                        {fav.article_category && (
                          <span className="text-xs text-indigo-600 font-medium mt-1 inline-block">
                            {fav.article_category}
                          </span>
                        )}
                        <div className="flex items-center gap-2 text-xs text-gray-500 mt-2">
                          <Clock size={12} />
                          Added {formatDateTime(fav.created_at)}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Link
                          href={`/articles/${fav.article_slug}`}
                          className="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                          title="View article"
                        >
                          <ExternalLink size={18} />
                        </Link>
                        <button
                          onClick={() => removeFavorite(fav.article)}
                          className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Remove from favorites"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Comments Modal */}
      {activeModal === 'comments' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <MessageSquare className="w-6 h-6 text-purple-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900">My Comments ({commentsCount})</h2>
              </div>
              <button onClick={closeModal} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[calc(80vh-88px)]">
              {modalLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
                </div>
              ) : comments.length === 0 ? (
                <div className="text-center py-12">
                  <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">No comments yet</p>
                  <Link href="/articles" className="text-purple-600 hover:underline mt-2 inline-block">
                    Start commenting on articles
                  </Link>
                </div>
              ) : (
                <div className="space-y-4">
                  {comments.map((comment) => (
                    <div key={comment.id} className="p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-start justify-between mb-2">
                        <Link 
                          href={`/articles/${comment.article_slug}`}
                          className="font-semibold text-gray-900 hover:text-purple-600"
                        >
                          {comment.article_title}
                        </Link>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          comment.is_approved 
                            ? 'bg-green-100 text-green-700' 
                            : 'bg-yellow-100 text-yellow-700'
                        }`}>
                          {comment.is_approved ? 'Approved' : 'Pending'}
                        </span>
                      </div>
                      <p className="text-gray-700 text-sm mb-3 whitespace-pre-wrap">{comment.content}</p>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <Clock size={12} />
                        {formatDateTime(comment.created_at)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Ratings Modal */}
      {activeModal === 'ratings' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-100 rounded-lg">
                  <Star className="w-6 h-6 text-amber-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900">My Ratings ({ratingsCount})</h2>
              </div>
              <button onClick={closeModal} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[calc(80vh-88px)]">
              {modalLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-600"></div>
                </div>
              ) : ratings.length === 0 ? (
                <div className="text-center py-12">
                  <Star className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">No ratings yet</p>
                  <Link href="/articles" className="text-amber-600 hover:underline mt-2 inline-block">
                    Rate some articles
                  </Link>
                </div>
              ) : (
                <div className="space-y-4">
                  {ratings.map((rating) => (
                    <div key={rating.id} className="flex gap-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                      {rating.article_image && (
                        <div className="flex-shrink-0 w-20 h-20 relative rounded-lg overflow-hidden">
                          <Image
                            src={getImageUrl(rating.article_image) || ''}
                            alt={rating.article_title}
                            fill
                            className="object-cover"
                          />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <Link 
                          href={`/articles/${rating.article_slug}`}
                          className="font-semibold text-gray-900 hover:text-amber-600 line-clamp-2"
                        >
                          {rating.article_title}
                        </Link>
                        {rating.article_category && (
                          <span className="text-xs text-amber-600 font-medium mt-1 inline-block">
                            {rating.article_category}
                          </span>
                        )}
                        <div className="flex items-center gap-4 mt-2">
                          {renderStars(rating.rating)}
                          <span className="text-sm text-gray-500">
                            {rating.rating}/5
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-gray-500 mt-2">
                          <Clock size={12} />
                          Rated {formatDateTime(rating.created_at)}
                        </div>
                      </div>
                      <Link
                        href={`/articles/${rating.article_slug}`}
                        className="p-2 text-gray-400 hover:text-amber-600 hover:bg-amber-50 rounded-lg transition-colors self-center"
                        title="View article"
                      >
                        <ExternalLink size={18} />
                      </Link>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      
      <Footer />
    </>
  );
}
