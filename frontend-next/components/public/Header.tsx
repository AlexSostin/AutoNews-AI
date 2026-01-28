'use client';

import Link from 'next/link';
import { Menu, X, ChevronDown, User, Settings, LogOut, BookMarked } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import SearchBar from './SearchBar';
import { isAuthenticated, getUserFromStorage, logout, isAdmin } from '@/lib/auth';
import type { User as UserType } from '@/types';

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
  const mobileMenuRef = useRef<HTMLDivElement>(null);
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
    const getApiUrl = () => {
      if (typeof window !== 'undefined') {
        const host = window.location.hostname;
        if (host !== 'localhost' && host !== '127.0.0.1') {
          return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
        }
      }
      return 'http://localhost:8001/api/v1';
    };
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
      if (categoriesRef.current && !categoriesRef.current.contains(event.target as Node)) {
        setIsCategoriesOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
      if (mobileMenuRef.current && mobileMenuRef.current.contains(event.target as Node)) {
        return;
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
  };

  return (
    <header className="bg-gradient-to-r from-slate-900 via-purple-900 to-slate-800 text-white shadow-lg sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between py-4">
          <Link href="/" className="text-2xl font-bold hover:scale-105 transition-transform">
            🚗 Fresh Motors
          </Link>
          
          <nav className="hidden md:flex space-x-6 items-center">
            <Link href="/" className="hover:text-purple-300 transition-colors">Home</Link>
            <Link href="/articles" className="hover:text-purple-300 transition-colors">Articles</Link>
            
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
                <div className="absolute top-full left-0 mt-2 w-64 bg-white text-gray-900 rounded-lg shadow-xl border border-gray-200 overflow-hidden z-50">
                  <div className="py-2">
                    {categories.map((category) => (
                      <Link
                        key={category.id}
                        href={`/categories/${category.slug}`}
                        onClick={() => setIsCategoriesOpen(false)}
                        className="block px-4 py-2 hover:bg-purple-50 transition-colors"
                      >
                        <div className="font-medium text-gray-900">{category.name}</div>
                        {category.article_count > 0 && (
                          <div className="text-xs text-gray-500">{category.article_count} articles</div>
                        )}
                      </Link>
                    ))}
                    <Link
                      href="/articles"
                      onClick={() => setIsCategoriesOpen(false)}
                      className="block px-4 py-2 mt-1 border-t border-gray-200 text-purple-600 hover:bg-purple-50 font-medium transition-colors"
                    >
                      View All Categories →
                    </Link>
                  </div>
                </div>
              )}
            </div>
            
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

          <div className="flex items-center gap-2">
            {/* Mobile Search */}
            <div className="md:hidden">
              <SearchBar />
            </div>
            
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="md:hidden text-gray-900"
            >
              {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {isMenuOpen && (
          <div ref={mobileMenuRef} className="md:hidden pb-4 space-y-2">
            <Link href="/" className="block py-2 hover:text-purple-300" onClick={() => setIsMenuOpen(false)}>Home</Link>
            <Link href="/articles" className="block py-2 hover:text-purple-300" onClick={() => setIsMenuOpen(false)}>Articles</Link>
            
            {/* Mobile Categories */}
            <div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setIsCategoriesOpen(!isCategoriesOpen);
                }}
                className="flex items-center gap-1 py-2 hover:text-purple-300 transition-colors w-full text-left"
              >
                Categories
                <ChevronDown size={16} className={`transition-transform ${isCategoriesOpen ? 'rotate-180' : ''}`} />
              </button>
              {isCategoriesOpen && (
                <div className="mt-2 bg-white/10 backdrop-blur-sm rounded-lg border border-white/20 overflow-hidden shadow-lg">
                  <div className="py-1">
                    {categories.map((category) => (
                      <a
                        key={category.id}
                        href={`/categories/${category.slug}`}
                        onMouseDown={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          const slug = category.slug;
                          setIsMenuOpen(false); 
                          setIsCategoriesOpen(false);
                          router.push(`/categories/${slug}`);
                        }}
                        className="block px-4 py-2 text-white hover:bg-white/20 transition-colors cursor-pointer"
                      >
                        <div className="font-medium">{category.name}</div>
                        {category.article_count > 0 && (
                          <div className="text-xs text-purple-200 opacity-80">{category.article_count} articles</div>
                        )}
                      </a>
                    ))}
                    <a
                      href="/articles"
                      onMouseDown={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setIsMenuOpen(false);
                        setIsCategoriesOpen(false);
                        router.push('/articles');
                      }}
                      className="block px-4 py-2 mt-1 border-t border-white/20 text-purple-300 hover:bg-white/20 font-medium transition-colors cursor-pointer"
                    >
                      View All Categories →
                    </a>
                  </div>
                </div>
              )}
            </div>
            
            {/* Mobile Admin Link - Only for staff */}
            {isAdminUser && (
              <Link href="/admin" className="flex items-center gap-2 py-2 hover:text-purple-300" onClick={() => setIsMenuOpen(false)}>
                <Settings size={18} />
                Admin
              </Link>
            )}
            
            {/* Mobile User Menu */}
            {isLoggedIn ? (
              <div className="border-t border-white/20 pt-2 mt-2">
                <div className="bg-white/10 backdrop-blur-sm rounded-lg p-3 mb-2">
                  <div className="font-bold">{user?.username}</div>
                  <div className="text-xs text-purple-200">{user?.email}</div>
                </div>
                
                <Link 
                  href="/profile" 
                  className="flex items-center gap-2 py-2 hover:text-purple-300" 
                  onClick={() => setIsMenuOpen(false)}
                >
                  <User size={18} />
                  My Profile
                </Link>
                
                <Link 
                  href="/profile/favorites" 
                  className="flex items-center gap-2 py-2 hover:text-purple-300" 
                  onClick={() => setIsMenuOpen(false)}
                >
                  <BookMarked size={18} />
                  Favorites
                </Link>
                
                <button
                  onClick={() => {
                    setIsMenuOpen(false);
                    handleLogout();
                  }}
                  className="flex items-center gap-2 py-2 text-red-300 hover:text-red-200 w-full"
                >
                  <LogOut size={18} />
                  Logout
                </button>
              </div>
            ) : (
              <Link 
                href="/login" 
                className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg transition-colors font-medium mt-2"
                onClick={() => setIsMenuOpen(false)}
              >
                <User size={18} />
                Login
              </Link>
            )}
            
            {/* Mobile Search */}
            <div className="mt-2">
              <SearchBar />
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
