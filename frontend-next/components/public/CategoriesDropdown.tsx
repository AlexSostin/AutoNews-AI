'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { ChevronDown, Folder, X } from 'lucide-react';

interface Category {
  id: number;
  name: string;
  slug: string;
  article_count?: number;
}

interface CategoriesDropdownProps {
  categories: Category[];
  currentCategory: string;
  currentTag?: string;
  currentSearch?: string;
}

export default function CategoriesDropdown({ categories, currentCategory, currentTag, currentSearch }: CategoriesDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedCategory = categories.find(c => c.slug === currentCategory);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close on escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, []);

  const clearCategory = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const params = new URLSearchParams();
    if (currentTag) params.append('tag', currentTag);
    if (currentSearch) params.append('search', currentSearch);
    window.location.href = params.toString() ? `/articles?${params.toString()}` : '/articles';
  };

  const buildUrl = (categorySlug: string) => {
    const params = new URLSearchParams();
    if (categorySlug) params.append('category', categorySlug);
    if (currentTag) params.append('tag', currentTag);
    if (currentSearch) params.append('search', currentSearch);
    return params.toString() ? `/articles?${params.toString()}` : '/articles';
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Dropdown Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full px-4 py-3 bg-white border-2 rounded-lg font-bold text-left flex items-center justify-between transition-all ${
          currentCategory
            ? 'border-brand-500 bg-brand-50'
            : 'border-gray-300 hover:border-brand-300'
        }`}
      >
        <div className="flex items-center gap-2">
          <Folder size={18} className={currentCategory ? 'text-brand-600' : 'text-gray-500'} />
          <span className={currentCategory ? 'text-brand-700' : 'text-gray-700'}>
            {selectedCategory ? selectedCategory.name : `All Categories`}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {currentCategory && (
            <button
              onClick={clearCategory}
              className="p-1 hover:bg-brand-200 rounded-full transition-colors"
              title="Clear category filter"
            >
              <X size={16} />
            </button>
          )}
          <ChevronDown 
            size={20} 
            className={`transition-transform ${isOpen ? 'rotate-180' : ''}`}
          />
        </div>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-2 bg-white border-2 border-gray-200 rounded-lg shadow-xl max-h-80 overflow-y-auto">
          {/* All Categories Option */}
          <Link
            href={buildUrl('')}
            onClick={() => setIsOpen(false)}
            className={`block px-4 py-3 transition-colors font-medium border-b border-gray-100 ${
              !currentCategory
                ? 'bg-brand-600 text-white'
                : 'hover:bg-gray-50 text-gray-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Folder size={18} />
                <span>All Categories</span>
              </div>
              <span className={`text-xs px-2 py-1 rounded-full ${
                !currentCategory
                  ? 'bg-brand-700 text-brand-100'
                  : 'bg-gray-200 text-gray-600'
              }`}>
                {categories.reduce((sum, cat) => sum + (cat.article_count || 0), 0)}
              </span>
            </div>
          </Link>

          {/* Categories List */}
          {categories.map((cat) => (
            <Link
              key={cat.id}
              href={buildUrl(cat.slug)}
              onClick={() => setIsOpen(false)}
              className={`block px-4 py-3 transition-colors font-medium border-b border-gray-100 ${
                currentCategory === cat.slug
                  ? 'bg-brand-600 text-white'
                  : 'hover:bg-gray-50 text-gray-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Folder size={18} />
                  <span>{cat.name}</span>
                </div>
                {cat.article_count !== undefined && (
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    currentCategory === cat.slug
                      ? 'bg-brand-700 text-brand-100'
                      : 'bg-gray-200 text-gray-600'
                  }`}>
                    {cat.article_count}
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
