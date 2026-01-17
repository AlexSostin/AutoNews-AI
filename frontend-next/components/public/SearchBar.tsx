'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { Search, X, Loader2 } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface SearchResult {
  id: number;
  title: string;
  slug: string;
  summary: string;
  category_name: string;
}

export default function SearchBar() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    const delayDebounce = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/articles/?search=${encodeURIComponent(query)}&is_published=true`
        );
        const data = await res.json();
        setResults(data.results?.slice(0, 5) || []);
      } catch (error) {
        console.error('Search failed:', error);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [query]);

  const handleClose = () => {
    setIsOpen(false);
    setQuery('');
    setResults([]);
  };

  return (
    <>
      {/* Search Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        aria-label="Search"
      >
        <Search size={20} />
      </button>

      {/* Search Modal */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center pt-20">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 max-h-[70vh] flex flex-col">
            {/* Search Input */}
            <div className="p-4 border-b flex items-center gap-3">
              <Search size={20} className="text-gray-400" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search articles..."
                className="flex-1 outline-none text-lg"
                onKeyDown={(e) => {
                  if (e.key === 'Escape') handleClose();
                }}
              />
              {loading && <Loader2 size={20} className="animate-spin text-indigo-600" />}
              <button
                onClick={handleClose}
                className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Results */}
            <div className="overflow-y-auto flex-1 p-4">
              {query && !loading && results.length === 0 && (
                <p className="text-center text-gray-500 py-8">No results found</p>
              )}
              
              {results.length > 0 && (
                <div className="space-y-3">
                  {results.map((article) => (
                    <Link
                      key={article.id}
                      href={`/articles/${article.slug}`}
                      onClick={handleClose}
                      className="block p-4 hover:bg-gray-50 rounded-lg transition-colors border border-gray-100"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-gray-900 mb-1 line-clamp-1">
                            {article.title}
                          </h3>
                          <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                            {article.summary}
                          </p>
                          <span className="text-xs text-indigo-600 font-medium">
                            {article.category_name}
                          </span>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t bg-gray-50 text-xs text-gray-500 text-center">
              Press <kbd className="px-2 py-1 bg-white border rounded">Esc</kbd> to close
            </div>
          </div>
        </div>
      )}
    </>
  );
}
