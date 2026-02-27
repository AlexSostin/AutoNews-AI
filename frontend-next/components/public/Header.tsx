'use client';

import Link from 'next/link';
import Image from 'next/image';
import { Menu, X, ChevronDown, User, Settings, LogOut, BookMarked, ArrowRight } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import SearchBar from './SearchBar';
import ThemeSwitcher from './ThemeSwitcher';
import { isAuthenticated, getUserFromStorage, logout, isAdmin } from '@/lib/auth';
import type { User as UserType } from '@/types';
import { getApiUrl } from '@/lib/config';

export default function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isCategoriesOpen, setIsCategoriesOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [categories, setCategories] = useState<any[]>([]);
  const [user, setUser] = useState<UserType | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isAdminUser, setIsAdminUser] = useState(false);

  const categoriesRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const mobileCategoriesRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    // Check authentication
    const updateAuthState = () => {
      setIsLoggedIn(isAuthenticated());
      setUser(getUserFromStorage());
      setIsAdminUser(isAdmin());
    };

    updateAuthState();

    // Listen for storage changes (login/logout events)
    const handleStorageChange = () => {
      updateAuthState();
    };

    window.addEventListener('storage', handleStorageChange);

    // Custom event for same-tab login/logout
    const handleAuthChange = () => {
      updateAuthState();
    };

    window.addEventListener('authChange', handleAuthChange);

    // Load categories
    fetch(`${getApiUrl()}/categories/`)
      .then(res => res.json())
      .then(data => {
        const cats = Array.isArray(data) ? data : data.results || [];
        setCategories(cats.slice(0, 10)); // Show top 10
      })
      .catch(err => console.error('Failed to load categories:', err));

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('authChange', handleAuthChange);
    };
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      // Close categories only if clicking outside BOTH desktop and mobile refs
      const insideDesktopCats = categoriesRef.current?.contains(target);
      const insideMobileCats = mobileCategoriesRef.current?.contains(target);
      if (!insideDesktopCats && !insideMobileCats) {
        setIsCategoriesOpen(false);
      }
      // Close user menu
      if (userMenuRef.current && !userMenuRef.current.contains(target)) {
        setIsUserMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close mobile menu when resizing to desktop
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setIsMenuOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Close categories when mobile menu closes
  useEffect(() => {
    if (!isMenuOpen) {
      setIsCategoriesOpen(false);
    }
  }, [isMenuOpen]);

  const handleLogout = () => {
    logout();
  };

  return (
    <header
      className="bg-gradient-to-r from-slate-900 via-purple-900 to-slate-800 text-white shadow-lg sticky top-0 z-50"
      data-is-logged-in={isLoggedIn}
      data-user-name={user?.username || 'none'}
    >
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between py-4">
          <Link href="/" className="hover:scale-105 transition-transform mr-6 lg:mr-16 shrink-0">
            <Image
              src="/logo.png"
              alt="Fresh Motors"
              width={200}
              height={50}
              className="h-12 w-auto object-contain scale-[2.2] lg:scale-[2.9] origin-left"
              priority
            />
          </Link>

          {/* ─── Desktop Navigation ─── */}
          <nav className="hidden lg:flex space-x-4 xl:space-x-6 items-center">
            <Link href="/" className="hover:text-purple-300 transition-colors">Home</Link>
            <Link href="/articles" className="hover:text-purple-300 transition-colors">Articles</Link>
            <Link href="/cars" className="hover:text-purple-300 transition-colors">Cars</Link>
            <Link href="/compare" className="hover:text-purple-300 transition-colors">Compare</Link>

            {/* Categories Dropdown */}
            <div className="relative" ref={categoriesRef}>
              <button
                onClick={() => setIsCategoriesOpen(!isCategoriesOpen)}
                className="flex items-center gap-1 hover:text-purple-300 transition-colors"
              >
                Categories
                <ChevronDown size={16} className={`transition-transform ${isCategoriesOpen ? 'rotate-180' : ''}`} />
              </button>

              {isCategoriesOpen && (
                <div className="absolute top-full left-0 mt-4 w-[480px] bg-white text-gray-900 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.2)] border border-gray-100 overflow-hidden z-50 animate-slide-up">
                  <div className="p-6">
                    <div className="grid grid-cols-2 gap-4">
                      {categories.map((category) => (
                        <Link
                          key={category.id}
                          href={`/categories/${category.slug}`}
                          onClick={() => setIsCategoriesOpen(false)}
                          className="group flex flex-col p-3 rounded-xl hover:bg-indigo-50 transition-all"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-bold text-gray-900 group-hover:text-indigo-600 transition-colors">{category.name}</span>
                            <span className="text-[10px] font-black bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full group-hover:bg-indigo-600 group-hover:text-white transition-all">
                              {category.article_count}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 line-clamp-1">{category.description || 'Explore the latest news in ' + category.name}</p>
                        </Link>
                      ))}
                    </div>
                    <Link
                      href="/articles"
                      onClick={() => setIsCategoriesOpen(false)}
                      className="flex items-center justify-center gap-2 py-3 mt-6 border-t border-gray-100 text-indigo-600 hover:text-indigo-700 font-bold transition-colors group"
                    >
                      Browse All Categories <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                    </Link>
                  </div>
                  {/* Bottom accented bar */}
                  <div className="h-1.5 bg-gradient-to-r from-indigo-600 to-purple-600 w-full"></div>
                </div>
              )}
            </div>

            {/* Theme Switcher */}
            <ThemeSwitcher />

            {/* Admin Link - Only for staff */}
            {isAdminUser && (
              <Link href="/admin" className="flex items-center gap-1 hover:text-purple-300 transition-colors">
                <Settings size={18} />
                Admin
              </Link>
            )}

            {/* User Menu */}
            {isLoggedIn ? (
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  className="flex items-center gap-2 hover:text-purple-300 transition-colors bg-purple-800 px-4 py-2 rounded-lg"
                >
                  <User size={18} />
                  <span>{user?.username || 'Account'}</span>
                  <ChevronDown size={16} className={`transition-transform ${isUserMenuOpen ? 'rotate-180' : ''}`} />
                </button>

                {isUserMenuOpen && (
                  <div className="absolute top-full right-0 mt-2 w-56 bg-white text-gray-900 rounded-lg shadow-xl border border-gray-200 overflow-hidden z-50">
                    <div className="py-2">
                      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                        <div className="font-bold text-gray-900">{user?.username}</div>
                        <div className="text-xs text-gray-500">{user?.email}</div>
                      </div>

                      <Link
                        href="/profile"
                        onClick={() => setIsUserMenuOpen(false)}
                        className="flex items-center gap-3 px-4 py-2 hover:bg-purple-50 transition-colors"
                      >
                        <User size={18} className="text-purple-600" />
                        <span className="font-medium">My Profile</span>
                      </Link>

                      <Link
                        href="/profile/favorites"
                        onClick={() => setIsUserMenuOpen(false)}
                        className="flex items-center gap-3 px-4 py-2 hover:bg-purple-50 transition-colors"
                      >
                        <BookMarked size={18} className="text-purple-600" />
                        <span className="font-medium">Favorites</span>
                      </Link>

                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-3 px-4 py-2 hover:bg-red-50 transition-colors border-t border-gray-200 text-red-600"
                      >
                        <LogOut size={18} />
                        <span className="font-medium">Logout</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <Link
                href="/login"
                className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg transition-colors font-medium"
              >
                <User size={18} />
                Login
              </Link>
            )}

            {/* Search */}
            <SearchBar />
          </nav>

          {/* ─── Mobile Controls (top bar) ─── */}
          <div className="flex items-center gap-3 lg:hidden">
            <SearchBar />
            <ThemeSwitcher />
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="text-white p-1.5 rounded-lg hover:bg-white/10 transition-colors"
              aria-label={isMenuOpen ? 'Close menu' : 'Open menu'}
            >
              {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>

        {/* ─── Mobile Menu ─── */}
        {isMenuOpen && (
          <div className="lg:hidden pb-4 border-t border-white/10 pt-3 animate-in slide-in-from-top duration-200">
            {/* Navigation Links */}
            <nav className="space-y-1">
              <Link href="/" className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-white/10 transition-colors" onClick={() => setIsMenuOpen(false)}>
                Home
              </Link>
              <Link href="/articles" className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-white/10 transition-colors" onClick={() => setIsMenuOpen(false)}>
                Articles
              </Link>
              <Link href="/cars" className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-white/10 transition-colors" onClick={() => setIsMenuOpen(false)}>
                Cars
              </Link>
              <Link href="/compare" className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-white/10 transition-colors" onClick={() => setIsMenuOpen(false)}>
                Compare
              </Link>

              {/* Mobile Categories Accordion */}
              <div ref={mobileCategoriesRef}>
                <button
                  onClick={() => setIsCategoriesOpen(!isCategoriesOpen)}
                  className="flex items-center justify-between w-full py-2.5 px-3 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <span>Categories</span>
                  <ChevronDown size={16} className={`transition-transform duration-200 ${isCategoriesOpen ? 'rotate-180' : ''}`} />
                </button>

                {isCategoriesOpen && (
                  <div className="ml-3 mt-1 space-y-0.5 border-l-2 border-purple-400/30 pl-3">
                    {categories.map((category) => (
                      <Link
                        key={category.id}
                        href={`/categories/${category.slug}`}
                        onClick={() => {
                          setIsMenuOpen(false);
                          setIsCategoriesOpen(false);
                        }}
                        className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-white/10 transition-colors text-sm"
                      >
                        <span className="text-purple-100">{category.name}</span>
                        {category.article_count > 0 && (
                          <span className="text-[10px] font-bold bg-white/10 text-purple-300 px-2 py-0.5 rounded-full">
                            {category.article_count}
                          </span>
                        )}
                      </Link>
                    ))}
                    <Link
                      href="/articles"
                      onClick={() => {
                        setIsMenuOpen(false);
                        setIsCategoriesOpen(false);
                      }}
                      className="flex items-center gap-2 py-2 px-3 text-purple-300 hover:text-purple-200 text-sm font-medium transition-colors"
                    >
                      View All <ArrowRight size={14} />
                    </Link>
                  </div>
                )}
              </div>
            </nav>

            {/* Admin Link - Only for staff */}
            {isAdminUser && (
              <div className="mt-2 pt-2 border-t border-white/10">
                <Link href="/admin" className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-white/10 transition-colors" onClick={() => setIsMenuOpen(false)}>
                  <Settings size={18} />
                  Admin Panel
                </Link>
              </div>
            )}

            {/* User Section */}
            <div className="mt-2 pt-2 border-t border-white/10">
              {isLoggedIn ? (
                <div className="space-y-1">
                  <div className="flex items-center gap-3 px-3 py-2 bg-white/5 rounded-lg mb-2">
                    <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center text-sm font-bold">
                      {user?.username?.charAt(0).toUpperCase() || 'U'}
                    </div>
                    <div>
                      <div className="font-medium text-sm">{user?.username}</div>
                      <div className="text-xs text-purple-300">{user?.email}</div>
                    </div>
                  </div>

                  <Link href="/profile" className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-white/10 transition-colors" onClick={() => setIsMenuOpen(false)}>
                    <User size={18} />
                    My Profile
                  </Link>

                  <Link href="/profile/favorites" className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-white/10 transition-colors" onClick={() => setIsMenuOpen(false)}>
                    <BookMarked size={18} />
                    Favorites
                  </Link>

                  <button
                    onClick={() => {
                      setIsMenuOpen(false);
                      handleLogout();
                    }}
                    className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-red-500/20 transition-colors text-red-300 w-full text-left"
                  >
                    <LogOut size={18} />
                    Logout
                  </button>
                </div>
              ) : (
                <Link
                  href="/login"
                  className="flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-500 px-4 py-3 rounded-lg transition-colors font-medium"
                  onClick={() => setIsMenuOpen(false)}
                >
                  <User size={18} />
                  Sign In
                </Link>
              )}
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
