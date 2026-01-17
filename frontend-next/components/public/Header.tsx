'use client';

import Link from 'next/link';
import { Menu, X, ChevronDown } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import SearchBar from './SearchBar';

export default function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isCategoriesOpen, setIsCategoriesOpen] = useState(false);
  const [categories, setCategories] = useState<any[]>([]);
  const categoriesRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    // Load categories
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/categories/`)
      .then(res => res.json())
      .then(data => {
        const cats = Array.isArray(data) ? data : data.results || [];
        setCategories(cats.slice(0, 10)); // Show top 10
      })
      .catch(err => console.error('Failed to load categories:', err));
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (categoriesRef.current && !categoriesRef.current.contains(event.target as Node)) {
        setIsCategoriesOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="bg-gradient-to-r from-slate-900 via-purple-900 to-slate-800 text-white shadow-lg sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between py-4">
          <Link href="/" className="text-2xl font-bold hover:scale-105 transition-transform">
            🚗 AutoNews
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
                <div className="absolute top-full left-0 mt-2 w-64 bg-white text-gray-900 rounded-lg shadow-xl border border-gray-200 overflow-hidden">
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
            
            <Link href="/admin" className="hover:text-purple-300 transition-colors">Admin</Link>
            
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
              className="md:hidden"
            >
              {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {isMenuOpen && (
          <div className="md:hidden pb-4 space-y-2">
            <Link href="/" className="block py-2 hover:text-purple-300" onClick={() => setIsMenuOpen(false)}>Home</Link>
            <Link href="/articles" className="block py-2 hover:text-purple-300" onClick={() => setIsMenuOpen(false)}>Articles</Link>
            
            {/* Mobile Categories */}
            <div>
              <button
                onClick={() => setIsCategoriesOpen(!isCategoriesOpen)}
                className="flex items-center gap-1 py-2 hover:text-purple-300 transition-colors w-full"
              >
                Categories
                <ChevronDown size={16} className={`transition-transform ${isCategoriesOpen ? 'rotate-180' : ''}`} />
              </button>
              {isCategoriesOpen && (
                <div className="pl-4 space-y-1 mt-1">
                  {categories.map((category) => (
                    <Link
                      key={category.id}
                      href={`/categories/${category.slug}`}
                      onClick={() => { setIsMenuOpen(false); setIsCategoriesOpen(false); }}
                      className="block py-1 text-sm text-purple-200 hover:text-purple-300"
                    >
                      {category.name}
                    </Link>
                  ))}
                </div>
              )}
            </div>
            
            <Link href="/admin" className="block py-2 hover:text-purple-300" onClick={() => setIsMenuOpen(false)}>Admin</Link>
            
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
