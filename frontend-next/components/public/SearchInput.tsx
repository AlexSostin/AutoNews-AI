'use client';

import { useState, useRef, useEffect } from 'react';
import { Search, X } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface SearchInputProps {
  currentSearch: string;
  currentCategory?: string;
  currentTag?: string;
}

export default function SearchInput({ currentSearch, currentCategory, currentTag }: SearchInputProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchValue, setSearchValue] = useState(currentSearch);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

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

  // Close on Escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, []);

  const buildUrl = (search: string) => {
    const params = new URLSearchParams();
    if (currentCategory) params.append('category', currentCategory);
    if (currentTag) params.append('tag', currentTag);
    if (search) params.append('search', search);
    return `/articles${params.toString() ? `?${params.toString()}` : ''}`;
  };

  const handleSearch = () => {
    if (searchValue.trim()) {
      const url = buildUrl(searchValue);
      router.push(url);
      setIsOpen(false);
    }
  };

  const handleClear = () => {
    setSearchValue('');
    const url = buildUrl('');
    router.push(url);
    setIsOpen(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSearch();
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Search Input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Search size={18} className="text-gray-500" />
        </div>
        <input
          ref={inputRef}
          type="text"
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          onFocus={() => setIsOpen(true)}
          onKeyPress={handleKeyPress}
          placeholder="Search articles..."
          className="w-full pl-11 pr-10 py-2.5 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent text-gray-900 font-medium placeholder:text-gray-500 transition-colors"
        />
        {searchValue && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute inset-y-0 right-0 pr-3 flex items-center"
            aria-label="Clear search"
          >
            <X size={18} className="text-gray-500 hover:text-gray-700" />
          </button>
        )}
      </div>

      {/* Dropdown */}
      {isOpen && searchValue && (
        <div className="absolute z-50 mt-2 w-full bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden">
          <div className="p-3">
            <button
              type="button"
              onClick={handleSearch}
              className="w-full px-4 py-2.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors font-medium flex items-center justify-center gap-2"
            >
              <Search size={18} />
              Search for &ldquo;{searchValue}&rdquo;
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
