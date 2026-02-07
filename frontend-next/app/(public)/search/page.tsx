'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';

interface Article {
    id: number;
    title: string;
    slug: string;
    summary: string;
    image: string | null;
    categories: { name: string; slug: string }[];
    views: number;
    created_at: string;
}

interface Category {
    id: number;
    name: string;
    slug: string;
}

interface SearchResponse {
    results: Article[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

function SearchContent() {
    const searchParams = useSearchParams();
    const [query, setQuery] = useState(searchParams.get('q') || '');
    const [category, setCategory] = useState(searchParams.get('category') || '');
    const [sortBy, setSortBy] = useState(searchParams.get('sort') || 'relevant');
    const [results, setResults] = useState<Article[]>([]);
    const [categories, setCategories] = useState<Category[]>([]);
    const [loading, setLoading] = useState(false);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);

    // Fetch categories on mount
    useEffect(() => {
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/categories/`)
            .then(res => res.json())
            .then(data => setCategories(data))
            .catch(err => console.error('Error loading categories:', err));
    }, []);

    // Perform search
    useEffect(() => {
        if (!query && !category) {
            setResults([]);
            return;
        }

        setLoading(true);
        const params = new URLSearchParams();
        if (query) params.append('q', query);
        if (category) params.append('category', category);
        if (sortBy) params.append('sort', sortBy);
        params.append('page', page.toString());

        fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/search/?${params}`)
            .then(res => res.json())
            .then((data: SearchResponse) => {
                setResults(data.results);
                setTotal(data.total);
                setTotalPages(data.total_pages);
                setLoading(false);
            })
            .catch(err => {
                console.error('Search error:', err);
                setLoading(false);
            });
    }, [query, category, sortBy, page]);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setPage(1);
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 py-12">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                {/* Search Header */}
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold text-gray-900 mb-2">🔍 Search Articles</h1>
                    <p className="text-gray-600">Find your next automotive review</p>
                </div>

                {/* Search Form */}
                <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
                    <form onSubmit={handleSearch} className="space-y-4">
                        {/* Search Input */}
                        <div>
                            <input
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Search for cars, reviews..."
                                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                        </div>

                        {/* Filters Row */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {/* Category Filter */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Category
                                </label>
                                <select
                                    value={category}
                                    onChange={(e) => { setCategory(e.target.value); setPage(1); }}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="">All Categories</option>
                                    {categories.map(cat => (
                                        <option key={cat.id} value={cat.slug}>{cat.name}</option>
                                    ))}
                                </select>
                            </div>

                            {/* Sort By */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Sort By
                                </label>
                                <select
                                    value={sortBy}
                                    onChange={(e) => { setSortBy(e.target.value); setPage(1); }}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="relevant">Most Relevant</option>
                                    <option value="newest">Newest First</option>
                                    <option value="popular">Most Popular</option>
                                </select>
                            </div>

                            {/* Search Button */}
                            <div className="flex items-end">
                                <button
                                    type="submit"
                                    className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-lg transition-colors"
                                >
                                    Search
                                </button>
                            </div>
                        </div>
                    </form>
                </div>

                {/* Results Count */}
                {total > 0 && (
                    <div className="mb-6 text-gray-600">
                        Found <span className="font-semibold text-gray-900">{total}</span> article{total !== 1 ? 's' : ''}
                    </div>
                )}

                {/* Loading State */}
                {loading && (
                    <div className="text-center py-12">
                        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                        <p className="mt-4 text-gray-600">Searching...</p>
                    </div>
                )}

                {/* Results Grid */}
                {!loading && results.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {results.map(article => (
                            <Link
                                key={article.id}
                                href={`/articles/${article.slug}`}
                                className="bg-white rounded-xl shadow-md hover:shadow-xl transition-shadow overflow-hidden group"
                            >
                                {/* Image */}
                                {article.image && (
                                    <div className="relative h-48 overflow-hidden">
                                        <img
                                            src={article.image}
                                            alt={article.title}
                                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                        />
                                    </div>
                                )}

                                {/* Content */}
                                <div className="p-5">
                                    {/* Category Badge */}
                                    <div className="mb-2">
                                        <span className="inline-block px-3 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded-full">
                                            {article.categories?.[0]?.name || 'News'}
                                        </span>
                                    </div>

                                    {/* Title */}
                                    <h3 className="text-lg font-bold text-gray-900 mb-2 line-clamp-2 group-hover:text-blue-600 transition-colors">
                                        {article.title}
                                    </h3>

                                    {/* Summary */}
                                    <p className="text-gray-600 text-sm mb-3 line-clamp-2">
                                        {article.summary}
                                    </p>

                                    {/* Meta */}
                                    <div className="flex items-center justify-between text-xs text-gray-500">
                                        <span>👁️ {article.views} views</span>
                                        <span>{new Date(article.created_at).toLocaleDateString()}</span>
                                    </div>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}

                {/* No Results */}
                {!loading && results.length === 0 && (query || category) && (
                    <div className="text-center py-12 bg-white rounded-xl shadow-md">
                        <div className="text-6xl mb-4">🔍</div>
                        <h3 className="text-xl font-semibold text-gray-900 mb-2">No results found</h3>
                        <p className="text-gray-600">Try adjusting your search or filters</p>
                    </div>
                )}

                {/* Pagination */}
                {totalPages > 1 && !loading && (
                    <div className="mt-8 flex justify-center gap-2">
                        <button
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                            className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Previous
                        </button>

                        <span className="px-4 py-2 bg-blue-600 text-white rounded-lg">
                            Page {page} of {totalPages}
                        </span>

                        <button
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page === totalPages}
                            className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Next
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

export default function SearchPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 py-12">
                <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                    <p className="mt-4 text-gray-600">Loading search...</p>
                </div>
            </div>
        }>
            <SearchContent />
        </Suspense>
    );
}
