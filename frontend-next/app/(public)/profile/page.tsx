'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { isAuthenticated, getUserFromStorage, getToken } from '@/lib/auth';
import { favoriteAPI } from '@/lib/favorites';
import { getApiUrl } from '@/lib/api';
import { authenticatedFetch } from '@/lib/authenticatedFetch';
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

interface EmailPreferences {
  newsletter_enabled: boolean;
  new_articles_enabled: boolean;
  comment_replies_enabled: boolean;
  favorite_updates_enabled: boolean;
  marketing_enabled: boolean;
}

type ModalType = 'favorites' | 'comments' | 'ratings' | 'editProfile' | 'changePassword' | 'emailPreferences' | null;

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

  // Edit Profile state
  const [editFirstName, setEditFirstName] = useState('');
  const [editLastName, setEditLastName] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState('');
  const [profileSuccess, setProfileSuccess] = useState('');

  // Change Password state
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword1, setNewPassword1] = useState('');
  const [newPassword2, setNewPassword2] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');

  // Email Preferences state
  const [emailPrefs, setEmailPrefs] = useState<EmailPreferences>({
    newsletter_enabled: true,
    new_articles_enabled: false,
    comment_replies_enabled: true,
    favorite_updates_enabled: false,
    marketing_enabled: false,
  });
  const [prefsSaving, setPrefsSaving] = useState(false);
  const [prefsSuccess, setPrefsSuccess] = useState('');

  // Email Verification state (NEW)
  const [emailVerificationModal, setEmailVerificationModal] = useState(false);
  const [emailVerificationStep, setEmailVerificationStep] = useState<'request' | 'verify'>('request');
  const [newEmailAddress, setNewEmailAddress] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [emailVerifError, setEmailVerifError] = useState('');
  const [emailVerifSuccess, setEmailVerifSuccess] = useState('');
  const [emailVerifSaving, setEmailVerifSaving] = useState(false);
  const [codeExpiresIn, setCodeExpiresIn] = useState(0);

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
    try {
      const response = await authenticatedFetch('/comments/my_comments/');
      if (response.ok) {
        const data = await response.json();
        setCommentsCount(data.count || 0);
      }
    } catch (err) {
      console.error('Failed to load comments count:', err);
    }
  };

  const loadRatingsCount = async () => {
    try {
      const response = await authenticatedFetch('/ratings/my_ratings/');
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
    setModalLoading(true);
    try {
      const response = await authenticatedFetch('/comments/my_comments/');
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
    setModalLoading(true);
    try {
      const response = await authenticatedFetch('/ratings/my_ratings/');
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

  // Account Settings functions
  const openEditProfile = () => {
    if (user) {
      setEditFirstName(user.first_name || '');
      setEditLastName(user.last_name || '');
      setEditEmail(user.email || '');
      setProfileError('');
      setProfileSuccess('');
    }
    setActiveModal('editProfile');
  };

  const saveProfile = async () => {
    setProfileSaving(true);
    setProfileError('');
    setProfileSuccess('');

    try {
      const response = await authenticatedFetch('/auth/user/', {
        method: 'PATCH',
        body: JSON.stringify({
          first_name: editFirstName,
          last_name: editLastName,
          // Email removed - now requires separate verification
        }),
      });

      if (response.ok) {
        const data = await response.json();
        // Update user email in state and localStorage
        setUser(prev => prev ? { ...prev, ...data } : null);
        // Update localStorage
        const stored = getUserFromStorage();
        if (stored) {
          localStorage.setItem('user', JSON.stringify({ ...stored, ...data }));
        }
        setProfileSuccess('Profile updated successfully!');
        setTimeout(() => closeModal(), 1500);
      } else {
        const error = await response.json();
        setProfileError(error.detail || 'Failed to update profile');
      }
    } catch (err) {
      setProfileError('Network error. Please try again.');
    } finally {
      setProfileSaving(false);
    }
  };

  const openChangePassword = () => {
    setOldPassword('');
    setNewPassword1('');
    setNewPassword2('');
    setPasswordError('');
    setPasswordSuccess('');
    setActiveModal('changePassword');
  };

  const changePassword = async () => {
    setPasswordSaving(true);
    setPasswordError('');
    setPasswordSuccess('');

    if (newPassword1 !== newPassword2) {
      setPasswordError('Passwords do not match');
      setPasswordSaving(false);
      return;
    }

    if (newPassword1.length < 8) {
      setPasswordError('Password must be at least 8 characters');
      setPasswordSaving(false);
      return;
    }

    try {
      const response = await authenticatedFetch('/auth/password/change/', {
        method: 'POST',
        body: JSON.stringify({
          old_password: oldPassword,
          new_password1: newPassword1,
          new_password2: newPassword2,
        }),
      });

      if (response.ok) {
        setPasswordSuccess('Password changed successfully!');
        setTimeout(() => closeModal(), 1500);
      } else {
        const error = await response.json();
        setPasswordError(error.old_password?.[0] || error.new_password1?.[0] || error.detail || 'Failed to change password');
      }
    } catch (err) {
      setPasswordError('Network error. Please try again.');
    } finally {
      setPasswordSaving(false);
    }
  };

  const openEmailPreferences = async () => {
    setActiveModal('emailPreferences');
    setPrefsSuccess('');

    try {
      const response = await authenticatedFetch('/auth/email-preferences/');
      if (response.ok) {
        const data = await response.json();
        setEmailPrefs(data);
      }
    } catch (err) {
      console.error('Failed to load email preferences:', err);
    }
  };

  const saveEmailPreferences = async () => {
    setPrefsSaving(true);
    setPrefsSuccess('');

    try {
      const response = await authenticatedFetch('/auth/email-preferences/', {
        method: 'PATCH',
        body: JSON.stringify(emailPrefs),
      });

      if (response.ok) {
        setPrefsSuccess('Preferences saved!');
        setTimeout(() => setPrefsSuccess(''), 2000);
      }
    } catch (err) {
      console.error('Failed to save email preferences:', err);
    } finally {
      setPrefsSaving(false);
    }
  };

  // Email Verification Handlers (NEW)
  const openEmailVerification = () => {
    setEmailVerificationModal(true);
    setEmailVerificationStep('request');
    setNewEmailAddress('');
    setVerificationCode('');
    setEmailVerifError('');
    setEmailVerifSuccess('');
    setCodeExpiresIn(0);
  };

  const requestEmailChange = async () => {
    setEmailVerifSaving(true);
    setEmailVerifError('');

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(newEmailAddress)) {
      setEmailVerifError('Please enter a valid email address');
      setEmailVerifSaving(false);
      return;
    }

    try {
      const response = await authenticatedFetch('/auth/email/request-change/', {
        method: 'POST',
        body: JSON.stringify({
          new_email: newEmailAddress,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setEmailVerificationStep('verify');
        setCodeExpiresIn(data.expires_in || 900); // 15 minutes

        // Start countdown timer
        const interval = setInterval(() => {
          setCodeExpiresIn(prev => {
            if (prev <= 1) {
              clearInterval(interval);
              return 0;
            }
            return prev - 1;
          });
        }, 1000);

        setEmailVerifSuccess(`Verification code sent to ${newEmailAddress}! Check your email.`);
      } else {
        const error = await response.json();
        setEmailVerifError(error.new_email?.[0] || error.detail || 'Failed to send verification code');
      }
    } catch (err) {
      setEmailVerifError('Network error. Please try again.');
    } finally {
      setEmailVerifSaving(false);
    }
  };

  const verifyEmailChange = async () => {
    setEmailVerifSaving(true);
    setEmailVerifError('');

    if (!verificationCode || verificationCode.length !== 6) {
      setEmailVerifError('Please enter the 6-digit code');
      setEmailVerifSaving(false);
      return;
    }

    try {
      const response = await authenticatedFetch('/auth/email/verify-code/', {
        method: 'POST',
        body: JSON.stringify({
          code: verificationCode,
        }),
      });

      if (response.ok) {
        const data = await response.json();

        // Update user email in state and localStorage
        setUser(prev => prev ? { ...prev, email: data.new_email } : null);
        const stored = getUserFromStorage();
        if (stored) {
          stored.email = data.new_email;
          localStorage.setItem('user', JSON.stringify(stored));
        }

        setEmailVerifSuccess('Email changed successfully!');
        setTimeout(() => {
          setEmailVerificationModal(false);
          setEmailVerificationStep('request');
        }, 1500);
      } else {
        const error = await response.json();
        setEmailVerifError(error.code?.[0] || error.detail || 'Invalid or expired code');
      }
    } catch (err) {
      setEmailVerifError('Network error. Please try again.');
    } finally {
      setEmailVerifSaving(false);
    }
  };

  const closeEmailVerificationModal = () => {
    setEmailVerificationModal(false);
    setEmailVerificationStep('request');
    setNewEmailAddress('');
    setVerificationCode('');
    setEmailVerifError('');
    setEmailVerifSuccess('');
    setCodeExpiresIn(0);
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
      <main className="flex-1 bg-gray-50 flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          <p className="mt-4 text-gray-600">Loading profile...</p>
        </div>
      </main>
    );
  }

  if (!user) {
    // Should not happen as we redirect in useEffect, but just in case show loading
    return (
      <main className="flex-1 bg-gray-50 flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          <p className="mt-4 text-gray-600">Redirecting...</p>
        </div>
      </main>
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
                      <div className="font-medium text-gray-900">{user.date_joined ? formatDate(user.date_joined) : 'N/A'}</div>
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
                  <button
                    onClick={openEditProfile}
                    className="w-full px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium text-left flex items-center justify-between"
                  >
                    <span>Edit Profile</span>
                    <ChevronRight className="w-5 h-5" />
                  </button>

                  <button
                    onClick={openEmailVerification}
                    className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-left flex items-center justify-between"
                  >
                    <span>Change Email</span>
                    <Mail className="w-5 h-5" />
                  </button>

                  <button
                    onClick={openChangePassword}
                    className="w-full px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium text-left flex items-center justify-between"
                  >
                    <span>Change Password</span>
                    <ChevronRight className="w-5 h-5" />
                  </button>

                  <button
                    onClick={openEmailPreferences}
                    className="w-full px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium text-left flex items-center justify-between"
                  >
                    <span>Email Preferences</span>
                    <ChevronRight className="w-5 h-5" />
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
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${comment.is_approved
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

      {/* Edit Profile Modal */}
      {activeModal === 'editProfile' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-100 rounded-lg">
                  <User className="w-6 h-6 text-indigo-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900">Edit Profile</h2>
              </div>
              <button onClick={closeModal} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
                  <input
                    type="text"
                    value={editFirstName}
                    onChange={(e) => setEditFirstName(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                    placeholder="Enter first name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
                  <input
                    type="text"
                    value={editLastName}
                    onChange={(e) => setEditLastName(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                    placeholder="Enter last name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email"
                    value={editEmail}
                    onChange={(e) => setEditEmail(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                    placeholder="Enter email"
                  />
                </div>

                {profileError && (
                  <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">
                    {profileError}
                  </div>
                )}
                {profileSuccess && (
                  <div className="p-3 bg-green-50 text-green-700 rounded-lg text-sm">
                    {profileSuccess}
                  </div>
                )}

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={closeModal}
                    className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={saveProfile}
                    disabled={profileSaving}
                    className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50"
                  >
                    {profileSaving ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Change Password Modal */}
      {activeModal === 'changePassword' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-100 rounded-lg">
                  <Shield className="w-6 h-6 text-amber-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900">Change Password</h2>
              </div>
              <button onClick={closeModal} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Current Password</label>
                  <input
                    type="password"
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent text-gray-900"
                    placeholder="Enter current password"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
                  <input
                    type="password"
                    value={newPassword1}
                    onChange={(e) => setNewPassword1(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent text-gray-900"
                    placeholder="Enter new password (min 8 characters)"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Confirm New Password</label>
                  <input
                    type="password"
                    value={newPassword2}
                    onChange={(e) => setNewPassword2(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent text-gray-900"
                    placeholder="Confirm new password"
                  />
                </div>

                {passwordError && (
                  <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">
                    {passwordError}
                  </div>
                )}
                {passwordSuccess && (
                  <div className="p-3 bg-green-50 text-green-700 rounded-lg text-sm">
                    {passwordSuccess}
                  </div>
                )}

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={closeModal}
                    className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={changePassword}
                    disabled={passwordSaving}
                    className="flex-1 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors font-medium disabled:opacity-50"
                  >
                    {passwordSaving ? 'Changing...' : 'Change Password'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Email Preferences Modal */}
      {activeModal === 'emailPreferences' && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Mail className="w-6 h-6 text-purple-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900">Email Preferences</h2>
              </div>
              <button onClick={closeModal} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors">
                  <div>
                    <div className="font-medium text-gray-900">Weekly Newsletter</div>
                    <div className="text-sm text-gray-500">Receive top articles every week</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={emailPrefs.newsletter_enabled}
                    onChange={(e) => setEmailPrefs({ ...emailPrefs, newsletter_enabled: e.target.checked })}
                    className="w-5 h-5 text-purple-600 rounded focus:ring-purple-500"
                  />
                </label>

                <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors">
                  <div>
                    <div className="font-medium text-gray-900">New Articles</div>
                    <div className="text-sm text-gray-500">Get notified when new articles are published</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={emailPrefs.new_articles_enabled}
                    onChange={(e) => setEmailPrefs({ ...emailPrefs, new_articles_enabled: e.target.checked })}
                    className="w-5 h-5 text-purple-600 rounded focus:ring-purple-500"
                  />
                </label>

                <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors">
                  <div>
                    <div className="font-medium text-gray-900">Comment Replies</div>
                    <div className="text-sm text-gray-500">Get notified when someone replies to your comment</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={emailPrefs.comment_replies_enabled}
                    onChange={(e) => setEmailPrefs({ ...emailPrefs, comment_replies_enabled: e.target.checked })}
                    className="w-5 h-5 text-purple-600 rounded focus:ring-purple-500"
                  />
                </label>

                <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors">
                  <div>
                    <div className="font-medium text-gray-900">Favorite Updates</div>
                    <div className="text-sm text-gray-500">Updates to your favorite articles</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={emailPrefs.favorite_updates_enabled}
                    onChange={(e) => setEmailPrefs({ ...emailPrefs, favorite_updates_enabled: e.target.checked })}
                    className="w-5 h-5 text-purple-600 rounded focus:ring-purple-500"
                  />
                </label>

                <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors">
                  <div>
                    <div className="font-medium text-gray-900">Marketing Emails</div>
                    <div className="text-sm text-gray-500">Promotional offers and special deals</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={emailPrefs.marketing_enabled}
                    onChange={(e) => setEmailPrefs({ ...emailPrefs, marketing_enabled: e.target.checked })}
                    className="w-5 h-5 text-purple-600 rounded focus:ring-purple-500"
                  />
                </label>

                {prefsSuccess && (
                  <div className="p-3 bg-green-50 text-green-700 rounded-lg text-sm">
                    {prefsSuccess}
                  </div>
                )}

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={closeModal}
                    className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
                  >
                    Close
                  </button>
                  <button
                    onClick={saveEmailPreferences}
                    disabled={prefsSaving}
                    className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium disabled:opacity-50"
                  >
                    {prefsSaving ? 'Saving...' : 'Save Preferences'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Email Verification Modal (NEW) */}
      {emailVerificationModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Mail className="w-6 h-6 text-blue-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-900">
                  {emailVerificationStep === 'request' ? 'Change Email' : 'Verify Email'}
                </h2>
              </div>
              <button onClick={closeEmailVerificationModal} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Step Indicator */}
            <div className="px-6 pt-4">
              <div className="flex items-center justify-center gap-2 mb-6">
                <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${emailVerificationStep === 'request' ? 'bg-blue-600 text-white' : 'bg-green-600 text-white'
                  }`}>
                  1
                </div>
                <div className="w-12 h-1 bg-gray-300"></div>
                <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${emailVerificationStep === 'verify' ? 'bg-blue-600 text-white' : 'bg-gray-300 text-gray-500'
                  }`}>
                  2
                </div>
              </div>
            </div>

            <div className="p-6">
              {emailVerificationStep === 'request' ? (
                /* Step 1: Request Email Change */
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Current Email
                    </label>
                    <div className="px-4 py-3 bg-gray-100 rounded-lg text-gray-600">
                      {user?.email}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      New Email Address
                    </label>
                    <input
                      type="email"
                      value={newEmailAddress}
                      onChange={(e) => setNewEmailAddress(e.target.value)}
                      placeholder="Enter new email address"
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                    />
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-sm text-blue-800">
                      <strong>🔒 Secure Verification:</strong> You'll receive a 6-digit code
                      at your new email address to confirm this change.
                    </p>
                  </div>

                  {emailVerifError && (
                    <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">
                      {emailVerifError}
                    </div>
                  )}

                  <button
                    onClick={requestEmailChange}
                    disabled={emailVerifSaving || !newEmailAddress}
                    className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {emailVerifSaving ? 'Sending Code...' : 'Send Verification Code'}
                  </button>
                </div>
              ) : (
                /* Step 2: Verify with Code */
                <div className="space-y-4">
                  <div className="text-center mb-4">
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-50 text-green-700 rounded-lg text-sm mb-2">
                      <span className="w-2 h-2 bg-green-600 rounded-full animate-pulse"></span>
                      Code sent to {newEmailAddress}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Verification Code
                    </label>
                    <input
                      type="text"
                      value={verificationCode}
                      onChange={(e) => setVerificationCode(e.target.value.replace(/[^0-9]/g, '').slice(0, 6))}
                      placeholder="Enter 6-digit code"
                      maxLength={6}
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-400 focus:border-green-500 focus:ring-2 focus:ring-green-200 transition-all text-center text-2xl font-mono tracking-widest"
                    />
                  </div>

                  {codeExpiresIn > 0 && (
                    <div className="flex items-center justify-center gap-2 text-sm text-gray-600">
                      <Clock className="w-4 h-4" />
                      <span>
                        Code expires in {Math.floor(codeExpiresIn / 60)}:{String(codeExpiresIn % 60).padStart(2, '0')}
                      </span>
                    </div>
                  )}

                  {emailVerifError && (
                    <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">
                      {emailVerifError}
                    </div>
                  )}

                  {emailVerifSuccess && (
                    <div className="p-3 bg-green-50 text-green-700 rounded-lg text-sm">
                      {emailVerifSuccess}
                    </div>
                  )}

                  <div className="flex gap-3">
                    <button
                      onClick={() => setEmailVerificationStep('request')}
                      className="flex-1 px-4 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
                    >
                      Back
                    </button>
                    <button
                      onClick={verifyEmailChange}
                      disabled={emailVerifSaving || verificationCode.length !== 6}
                      className="flex-1 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {emailVerifSaving ? 'Verifying...' : 'Verify & Change Email'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </>
  );
}
