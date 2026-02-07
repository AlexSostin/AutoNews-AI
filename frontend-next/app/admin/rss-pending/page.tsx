'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Rss, CheckCircle, XCircle, Edit, Eye, Loader2, AlertCircle } from 'lucide-react';
import api from '@/lib/api';

interface RSSFeed {
    id: number;
    name: string;
    feed_url: string;
    source_type: string;
    logo_url?: string;
    pending_count?: number;
}

interface PendingArticle {
    id: number;
    title: string;
    content: string;
    excerpt: string;
    status: string;
    rss_feed: {
        id: number;
        name: string;
        logo_url?: string;
    };
    source_url: string;
    suggested_category?: {
        id: number;
        name: string;
    };
    images: string[];
    created_at: string;
}

export default function RSSPendingPage() {
    const [feeds, setFeeds] = useState<RSSFeed[]>([]);
    const [articles, setArticles] = useState<PendingArticle[]>([]);
    const [selectedFeed, setSelectedFeed] = useState<number | null>(null);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState<number | null>(null);
    const [selectedArticles, setSelectedArticles] = useState<Set<number>>(new Set());
    const [bulkDeleting, setBulkDeleting] = useState(false);

    useEffect(() => {
        fetchFeeds();
        fetchArticles();
    }, [selectedFeed]);

    const fetchFeeds = async () => {
        try {
            const response = await api.get('/rss-feeds/with_pending_counts/');
            const feedsData = Array.isArray(response.data) ? response.data : (response.data.results || []);
            setFeeds(feedsData);
        } catch (error) {
            console.error('Error fetching RSS feeds:', error);
        }
    };

    const fetchArticles = async () => {
        setLoading(true);
        try {
            const params: any = {
                only_rss: 'true',
                status: 'pending',
            };

            if (selectedFeed) {
                params.rss_feed = selectedFeed;
            }

            const response = await api.get('/pending-articles/', { params });
            const articlesData = Array.isArray(response.data) ? response.data : (response.data.results || []);
            setArticles(articlesData);
        } catch (error) {
            console.error('Error fetching pending articles:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleApprove = async (articleId: number) => {
        if (!confirm('Approve this article as draft? You can publish it later from Articles page.')) return;

        setActionLoading(articleId);
        try {
            await api.post(`/pending-articles/${articleId}/approve/`, { publish: false });
            fetchArticles();
            fetchFeeds();
        } catch (error: any) {
            console.error('Error approving article:', error);
            const errorMsg = error.response?.data?.error || error.message;
            alert(`Failed to approve article:\n\n${errorMsg}`);
        } finally {
            setActionLoading(null);
        }
    };

    const handleReject = async (articleId: number) => {
        if (!confirm('Reject this article? This action cannot be undone.')) return;

        setActionLoading(articleId);
        try {
            await api.post(`/pending-articles/${articleId}/reject/`);
            fetchArticles();
            fetchFeeds();
        } catch (error: any) {
            console.error('Error rejecting article:', error);
            alert(`Failed to reject article: ${error.response?.data?.error || error.message}`);
        } finally {
            setActionLoading(null);
        }
    };

    const handleBulkDelete = async () => {
        if (selectedArticles.size === 0) {
            alert('Please select articles to delete');
            return;
        }

        if (!confirm(`Delete ${selectedArticles.size} selected article(s)?`)) return;

        setBulkDeleting(true);
        try {
            // Delete each selected article
            await Promise.all(
                Array.from(selectedArticles).map(id =>
                    api.delete(`/pending-articles/${id}/`)
                )
            );

            setSelectedArticles(new Set());
            fetchArticles();
            fetchFeeds();
        } catch (error) {
            console.error('Error deleting articles:', error);
            alert('Failed to delete some articles');
        } finally {
            setBulkDeleting(false);
        }
    };

    const toggleArticleSelection = (articleId: number) => {
        const newSelected = new Set(selectedArticles);
        if (newSelected.has(articleId)) {
            newSelected.delete(articleId);
        } else {
            newSelected.add(articleId);
        }
        setSelectedArticles(newSelected);
    };

    const toggleSelectAll = () => {
        if (selectedArticles.size === articles.length) {
            setSelectedArticles(new Set());
        } else {
            setSelectedArticles(new Set(articles.map(a => a.id)));
        }
    };

    const totalPending = feeds.reduce((sum, feed) => sum + (feed.pending_count || 0), 0);

    return (
        <div className="p-6">
            <div className="mb-6">
                <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                    <Rss className="text-orange-600" size={32} />
                    RSS Pending Articles
                </h1>
                <p className="text-gray-600 mt-1">
                    Review and approve articles from RSS feeds before publishing
                </p>
            </div>

            <div className="grid grid-cols-12 gap-6">
                {/* Sidebar - RSS Feeds */}
                <div className="col-span-3">
                    <div className="bg-gradient-to-br from-white to-gray-50 rounded-xl shadow-lg p-5 sticky top-6 border border-gray-200">
                        <div className="flex items-center gap-2 mb-5">
                            <div className="p-2 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg shadow-md">
                                <Rss size={20} className="text-white" />
                            </div>
                            <h2 className="text-lg font-bold text-gray-900">RSS Feeds</h2>
                        </div>

                        {/* All RSS */}
                        <button
                            onClick={() => setSelectedFeed(null)}
                            className={`w-full text-left px-4 py-3 rounded-xl mb-3 flex items-center justify-between transition-all duration-200 ${selectedFeed === null
                                ? 'bg-gradient-to-r from-indigo-500 to-indigo-600 text-white shadow-md transform scale-105'
                                : 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 hover:border-indigo-300 hover:shadow-sm'
                                }`}
                        >
                            <div className="flex items-center gap-2">
                                <span className="text-xl">📊</span>
                                <span className="font-semibold">All RSS Feeds</span>
                            </div>
                            <span className={`text-xs px-2.5 py-1 rounded-full font-bold ${selectedFeed === null
                                ? 'bg-white/20 text-white'
                                : 'bg-indigo-100 text-indigo-700'
                                }`}>
                                {totalPending}
                            </span>
                        </button>

                        <div className="border-t border-gray-200 pt-3 mt-3 space-y-2">
                            {feeds.map((feed) => (
                                <button
                                    key={feed.id}
                                    onClick={() => setSelectedFeed(feed.id)}
                                    className={`w-full text-left px-4 py-3 rounded-xl flex items-center justify-between transition-all duration-200 group ${selectedFeed === feed.id
                                        ? 'bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-md transform scale-105'
                                        : 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 hover:border-orange-300 hover:shadow-sm'
                                        }`}
                                >
                                    <div className="flex items-center gap-3 flex-1 min-w-0">
                                        {feed.logo_url ? (
                                            <div className="w-7 h-7 rounded-lg bg-white p-1 flex items-center justify-center flex-shrink-0 shadow-sm">
                                                <img
                                                    src={feed.logo_url}
                                                    alt={feed.name}
                                                    className="w-full h-full object-contain"
                                                />
                                            </div>
                                        ) : (
                                            <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${selectedFeed === feed.id ? 'bg-white/20' : 'bg-orange-100'
                                                }`}>
                                                <Rss size={16} className={selectedFeed === feed.id ? 'text-white' : 'text-orange-600'} />
                                            </div>
                                        )}
                                        <span className="truncate text-sm font-medium">{feed.name}</span>
                                    </div>
                                    {(feed.pending_count || 0) > 0 && (
                                        <span className={`text-xs px-2.5 py-1 rounded-full flex-shrink-0 font-bold ${selectedFeed === feed.id
                                            ? 'bg-white/20 text-white'
                                            : 'bg-orange-100 text-orange-700 group-hover:bg-orange-200'
                                            }`}>
                                            {feed.pending_count}
                                        </span>
                                    )}
                                </button>
                            ))}
                        </div>

                        {feeds.length === 0 && (
                            <div className="text-center text-gray-400 text-sm py-8">
                                <div className="w-16 h-16 mx-auto mb-3 bg-gray-100 rounded-full flex items-center justify-center">
                                    <Rss size={32} className="opacity-50" />
                                </div>
                                <p className="font-medium">No RSS feeds configured</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Main Content - Pending Articles */}
                <div className="col-span-9">
                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="animate-spin text-indigo-600" size={32} />
                        </div>
                    ) : articles.length === 0 ? (
                        <div className="bg-white rounded-lg shadow-md p-12 text-center">
                            <CheckCircle className="mx-auto text-green-600 mb-4" size={48} />
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">
                                All caught up!
                            </h3>
                            <p className="text-gray-600">
                                {selectedFeed
                                    ? 'No pending articles from this feed'
                                    : 'No pending RSS articles to review'}
                            </p>
                        </div>
                    ) : (
                        <>
                            {/* Bulk Actions Bar */}
                            {articles.length > 0 && (
                                <div className="bg-white rounded-lg shadow-md p-4 mb-4 flex items-center justify-between border border-gray-200">
                                    <div className="flex items-center gap-3">
                                        <input
                                            type="checkbox"
                                            checked={selectedArticles.size === articles.length && articles.length > 0}
                                            onChange={toggleSelectAll}
                                            className="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 cursor-pointer"
                                        />
                                        <span className="text-sm font-medium text-gray-700">
                                            {selectedArticles.size > 0
                                                ? `${selectedArticles.size} selected`
                                                : 'Select all'}
                                        </span>
                                    </div>
                                    {selectedArticles.size > 0 && (
                                        <button
                                            onClick={handleBulkDelete}
                                            disabled={bulkDeleting}
                                            className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium shadow-sm hover:shadow-md"
                                        >
                                            {bulkDeleting ? (
                                                <>
                                                    <Loader2 className="animate-spin" size={18} />
                                                    Deleting...
                                                </>
                                            ) : (
                                                <>
                                                    <XCircle size={18} />
                                                    Delete Selected
                                                </>
                                            )}
                                        </button>
                                    )}
                                </div>
                            )}
                            <div className="space-y-6">
                                {articles.map((article) => (
                                    <div
                                        key={article.id}
                                        className="bg-white rounded-xl shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden border border-gray-100"
                                    >
                                        <div className="p-6">
                                            <div className="flex gap-6">
                                                {/* Checkbox for selection */}
                                                <div className="flex-shrink-0 flex items-start pt-1">
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedArticles.has(article.id)}
                                                        onChange={() => toggleArticleSelection(article.id)}
                                                        className="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 cursor-pointer"
                                                    />
                                                </div>

                                                {/* Thumbnail Image */}
                                                {article.images && article.images.length > 0 && (
                                                    <div className="flex-shrink-0">
                                                        <img
                                                            src={article.images[0]}
                                                            alt={article.title}
                                                            className="w-40 h-28 object-cover rounded-lg shadow-md border border-gray-200"
                                                            onError={(e) => {
                                                                e.currentTarget.style.display = 'none';
                                                            }}
                                                        />
                                                    </div>
                                                )}

                                                {/* Content */}
                                                <div className="flex-1 min-w-0">
                                                    {/* Header with badges */}
                                                    <div className="flex items-start justify-between mb-4">
                                                        <div className="flex-1">
                                                            {/* Status and AI badges */}
                                                            <div className="flex items-center gap-2 mb-3">
                                                                <span className="px-3 py-1 text-xs font-bold rounded-full bg-gradient-to-r from-orange-500 to-orange-600 text-white animate-pulse shadow-sm">
                                                                    NEW
                                                                </span>
                                                                <span className="px-3 py-1 text-xs font-semibold rounded-full bg-purple-100 text-purple-700 border border-purple-200">
                                                                    🤖 AI Generated
                                                                </span>
                                                                {article.suggested_category && (
                                                                    <span className="px-3 py-1 text-xs font-semibold rounded-full bg-indigo-100 text-indigo-700 border border-indigo-200">
                                                                        {article.suggested_category.name}
                                                                    </span>
                                                                )}
                                                            </div>

                                                            {/* Title */}
                                                            <h3 className="text-2xl font-bold text-gray-900 mb-3 hover:text-indigo-600 transition-colors">
                                                                {article.title}
                                                            </h3>

                                                            {/* Meta info */}
                                                            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
                                                                <div className="flex items-center gap-2 bg-orange-50 px-3 py-1 rounded-lg">
                                                                    <Rss size={16} className="text-orange-600" />
                                                                    <span className="font-medium">{article.rss_feed?.name || 'Unknown Feed'}</span>
                                                                </div>
                                                                <div className="flex items-center gap-1 text-gray-500">
                                                                    <span>📅</span>
                                                                    <span>{new Date(article.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                                                                </div>
                                                                <div className="flex items-center gap-1 text-gray-500">
                                                                    <span>📝</span>
                                                                    <span>{Math.round(article.content.length / 5)} words</span>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Excerpt with better styling */}
                                            <div className="mb-4 p-4 bg-gray-50 rounded-lg border-l-4 border-indigo-500">
                                                <p className="text-gray-700 leading-relaxed line-clamp-3">
                                                    {article.excerpt || article.content.substring(0, 250)}...
                                                </p>
                                            </div>

                                            {/* Source Link */}
                                            {article.source_url && (
                                                <a
                                                    href={article.source_url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="inline-flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-800 font-medium mb-4 group"
                                                >
                                                    <span>View original article</span>
                                                    <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                                                    </svg>
                                                </a>
                                            )}

                                            {/* Actions with improved styling */}
                                            <div className="flex flex-wrap gap-3 pt-4 border-t border-gray-200">
                                                <Link
                                                    href={`/admin/pending-articles/${article.id}`}
                                                    className="flex items-center gap-2 px-5 py-2.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-all font-medium shadow-sm hover:shadow"
                                                >
                                                    <Eye size={18} />
                                                    Preview
                                                </Link>
                                                <button
                                                    onClick={() => handleApprove(article.id)}
                                                    disabled={actionLoading === article.id}
                                                    className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-green-600 to-green-700 text-white rounded-lg hover:from-green-700 hover:to-green-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium shadow-sm hover:shadow-md"
                                                >
                                                    {actionLoading === article.id ? (
                                                        <Loader2 className="animate-spin" size={18} />
                                                    ) : (
                                                        <CheckCircle size={18} />
                                                    )}
                                                    Approve as Draft
                                                </button>
                                                <button
                                                    onClick={() => handleReject(article.id)}
                                                    disabled={actionLoading === article.id}
                                                    className="flex items-center gap-2 px-5 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium shadow-sm hover:shadow-md"
                                                >
                                                    <XCircle size={18} />
                                                    Reject
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
