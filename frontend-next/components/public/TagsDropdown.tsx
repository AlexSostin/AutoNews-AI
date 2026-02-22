'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { ChevronDown, Search, X } from 'lucide-react';

interface Tag {
  id: number;
  name: string;
  slug: string;
  article_count?: number;
}

interface TagsDropdownProps {
  tags: Tag[];
  currentTag: string;
  currentCategory: string;
}

export default function TagsDropdown({ tags, currentTag, currentCategory }: TagsDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedTag = tags.find(t => t.slug === currentTag);
  const filteredTags = tags.filter(tag => 
    tag.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

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

  const clearTag = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    window.location.href = currentCategory ? `/articles?category=${currentCategory}` : '/articles';
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Dropdown Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full px-4 py-3 bg-white border-2 rounded-lg font-bold text-left flex items-center justify-between transition-all ${
          currentTag
            ? 'border-indigo-500 bg-indigo-50'
            : 'border-gray-300 hover:border-indigo-300'
        }`}
      >
        <span className={currentTag ? 'text-indigo-700' : 'text-gray-700'}>
          {selectedTag ? selectedTag.name : `All Tags (${tags.length})`}
        </span>
        <div className="flex items-center gap-2">
          {currentTag && (
            <button
              onClick={clearTag}
              className="p-1 hover:bg-indigo-200 rounded-full transition-colors"
              title="Clear tag filter"
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
        <div className="absolute z-50 w-full mt-2 bg-white border-2 border-gray-200 rounded-lg shadow-xl max-h-96 flex flex-col">
          {/* Search Box */}
          <div className="p-3 border-b border-gray-200 sticky top-0 bg-white">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="text"
                placeholder="Search tags..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm"
                onClick={(e) => e.stopPropagation()}
              />
            </div>
          </div>

          {/* Tags List */}
          <div className="overflow-y-auto">
            {/* All Tags Option */}
            <Link
              href={currentCategory ? `/articles?category=${currentCategory}` : '/articles'}
              onClick={() => setIsOpen(false)}
              className={`block px-4 py-3 transition-colors font-medium border-b border-gray-100 ${
                !currentTag
                  ? 'bg-indigo-600 text-white'
                  : 'hover:bg-gray-50 text-gray-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <span>All Tags</span>
                <span className={`text-sm ${!currentTag ? 'text-indigo-200' : 'text-gray-500'}`}>
                  {tags.length} total
                </span>
              </div>
            </Link>

            {/* Filtered Tags */}
            {filteredTags.length === 0 ? (
              <div className="px-4 py-8 text-center text-gray-500">
                <p className="text-sm">No tags found</p>
                <p className="text-xs mt-1">Try a different search term</p>
              </div>
            ) : (
              filteredTags.map((tag) => (
                <Link
                  key={tag.id}
                  href={`/articles?${currentCategory ? `category=${currentCategory}&` : ''}tag=${tag.slug}`}
                  onClick={() => setIsOpen(false)}
                  className={`block px-4 py-3 transition-colors font-medium border-b border-gray-100 ${
                    currentTag === tag.slug
                      ? 'bg-indigo-600 text-white'
                      : 'hover:bg-gray-50 text-gray-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span>{tag.name}</span>
                    {tag.article_count !== undefined && (
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        currentTag === tag.slug
                          ? 'bg-indigo-700 text-indigo-100'
                          : 'bg-gray-200 text-gray-600'
                      }`}>
                        {tag.article_count}
                      </span>
                    )}
                  </div>
                </Link>
              ))
            )}
          </div>

          {/* Footer with count */}
          {searchQuery && filteredTags.length > 0 && (
            <div className="p-2 border-t border-gray-200 bg-gray-50 text-center text-xs text-gray-600">
              Showing {filteredTags.length} of {tags.length} tags
            </div>
          )}
        </div>
      )}
    </div>
  );
}
