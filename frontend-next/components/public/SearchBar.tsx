'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Search, X, Loader2, ArrowRight, Sparkles } from 'lucide-react';

interface SearchResult {
  id: number;
  title: string;
  slug: string;
  summary: string;
  categories: { id: number; name: string; slug: string }[];
  image?: string;
  thumbnail_url?: string;
}

export default function SearchBar() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  const getApiUrl = () => {
    if (typeof window !== 'undefined') {
      const host = window.location.hostname;
      if (host !== 'localhost' && host !== '127.0.0.1') {
        return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
      }
    }
    return 'http://localhost:8000/api/v1';
  };

  const getMediaUrl = () => {
    if (typeof window !== 'undefined') {
      const host = window.location.hostname;
      if (host !== 'localhost' && host !== '127.0.0.1') {
        return 'https://heroic-healing-production-2365.up.railway.app';
      }
    }
    return 'http://localhost:8000';
  };

  const handleClose = useCallback(() => {
    setIsOpen(false);
    setQuery('');
    setResults([]);
    setSelectedIndex(-1);
  }, []);

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Handle keyboard shortcut (Cmd/Ctrl + K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
      }
      if (e.key === 'Escape' && isOpen) {
        handleClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, handleClose]);

  // Search with debounce
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setSelectedIndex(-1);
      return;
    }

    const delayDebounce = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(
          `${getApiUrl()}/articles/?search=${encodeURIComponent(query)}&is_published=true&page_size=6`
        );
        const data = await res.json();
        setResults(data.results || []);
        setSelectedIndex(-1);
      } catch (error) {
        console.error('Search failed:', error);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [query]);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => Math.min(prev + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => Math.max(prev - 1, -1));
    } else if (e.key === 'Enter' && selectedIndex >= 0 && results[selectedIndex]) {
      handleClose();
      window.location.href = `/articles/${results[selectedIndex].slug}`;
    }
  };

  const getImageUrl = (article: SearchResult) => {
    const mediaUrl = getMediaUrl();
    const imgSrc = article.thumbnail_url || article.image;
    if (!imgSrc) return null;
    if (imgSrc.startsWith('http')) {
      return imgSrc.replace('http://backend:8000', mediaUrl).replace('http://localhost:8000', mediaUrl);
    }
    return `${mediaUrl}${imgSrc}`;
  };

  return (
    <>
      {/* Search Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 p-2 hover:bg-gray-100 rounded-xl transition-all text-gray-600 hover:text-gray-900"
        aria-label="Search"
      >
        <Search size={20} />
      </button>

      {/* Search Modal */}
      {isOpen && (
        <div
          className="fixed inset-0 z-[100] overflow-y-auto"
          role="dialog"
          aria-modal="true"
        >
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
            onClick={handleClose}
          />

          {/* Modal */}
          <div className="flex min-h-full items-start justify-center p-2 sm:p-4 pt-[10vh] sm:pt-[15vh]">
            <div
              ref={modalRef}
              className="relative w-full max-w-2xl transform overflow-hidden rounded-2xl bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 shadow-2xl transition-all border border-brand-500/20"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header with gradient */}
              <div className="bg-gradient-to-r from-brand-600/20 to-brand-600/20 p-1">
                <div className="bg-gray-900/80 rounded-xl">
                  {/* Search Input */}
                  <div className="flex items-center gap-2 sm:gap-4 p-3 sm:p-4">
                    <div className="flex-shrink-0">
                      {loading ? (
                        <Loader2 size={20} className="animate-spin text-brand-400" />
                      ) : (
                        <Search size={20} className="text-brand-400" />
                      )}
                    </div>
                    <input
                      ref={inputRef}
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Search articles..."
                      className="flex-1 min-w-0 bg-transparent outline-none text-base sm:text-lg text-white placeholder-gray-500"
                      autoComplete="off"
                    />
                    <button
                      onClick={handleClose}
                      className="flex-shrink-0 p-1.5 sm:p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
                    >
                      <X size={20} />
                    </button>
                  </div>
                </div>
              </div>

              {/* Results */}
              <div className="max-h-[60vh] overflow-y-auto">
                {/* Empty state */}
                {!query && (
                  <div className="p-8 text-center">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-brand-500/20 rounded-full mb-4">
                      <Sparkles size={32} className="text-brand-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-white mb-2">Search Fresh Motors</h3>
                    <p className="text-gray-400 text-sm">
                      Find articles about cars, EVs, reviews and more
                    </p>
                  </div>
                )}

                {/* No results */}
                {query && !loading && results.length === 0 && (
                  <div className="p-8 text-center">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-700 rounded-full mb-4">
                      <Search size={32} className="text-gray-500" />
                    </div>
                    <h3 className="text-lg font-semibold text-white mb-2">No results found</h3>
                    <p className="text-gray-400 text-sm">
                      Try different keywords or check spelling
                    </p>
                  </div>
                )}

                {/* Results list */}
                {results.length > 0 && (
                  <div className="p-2">
                    {results.map((article, index) => {
                      const imageUrl = getImageUrl(article);
                      return (
                        <Link
                          key={article.id}
                          href={`/articles/${article.slug}`}
                          onClick={handleClose}
                          className={`flex items-center gap-4 p-3 rounded-xl transition-all group ${selectedIndex === index
                              ? 'bg-brand-600/30 border border-brand-500/50'
                              : 'hover:bg-white/5 border border-transparent'
                            }`}
                        >
                          {/* Thumbnail */}
                          <div className="relative w-16 h-16 flex-shrink-0 rounded-lg overflow-hidden bg-gray-700">
                            {imageUrl ? (
                              <Image
                                src={imageUrl}
                                alt={article.title}
                                fill
                                className="object-cover"
                                unoptimized
                              />
                            ) : (
                              <div className="w-full h-full flex items-center justify-center">
                                <Search size={20} className="text-gray-500" />
                              </div>
                            )}
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <h4 className={`font-semibold line-clamp-1 transition-colors ${selectedIndex === index ? 'text-white' : 'text-gray-200 group-hover:text-white'
                              }`}>
                              {article.title}
                            </h4>
                            <p className="text-sm text-gray-400 line-clamp-1 mt-0.5">
                              {article.summary}
                            </p>
                            <span className="inline-block mt-1 text-xs px-2 py-0.5 bg-brand-500/20 text-brand-300 rounded-full">
                              {article.categories?.[0]?.name || 'News'}
                            </span>
                          </div>

                          {/* Arrow */}
                          <ArrowRight size={18} className={`flex-shrink-0 transition-all ${selectedIndex === index
                              ? 'text-brand-400 translate-x-0 opacity-100'
                              : 'text-gray-600 -translate-x-2 opacity-0 group-hover:translate-x-0 group-hover:opacity-100'
                            }`} />
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="border-t border-gray-700 px-4 py-3 bg-gray-900/50">
                <p className="text-xs text-gray-500 text-center">
                  Tap outside or X to close
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
