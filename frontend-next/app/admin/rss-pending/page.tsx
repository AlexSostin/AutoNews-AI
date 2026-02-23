'use client';

import { useState, useEffect } from 'react';
import {
    Rss,
    Wand2,
    XCircle,
    ExternalLink,
    Loader2,
    Newspaper,
    Eye,
    CheckCircle2,
    Clock,
    Filter,
} from 'lucide-react';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface RSSFeed {
    id: number;
    name: string;
    feed_url: string;
    source_type: string;
    logo_url?: string;
    pending_count?: number;
}

interface RSSNewsItem {
    id: number;
    rss_feed: number;
    feed_name: string;
    feed_logo: string;
    feed_source_type: string;
    title: string;
    content: string;
    excerpt: string;
    source_url: string;
    image_url: string;
    published_at: string | null;
    status: 'new' | 'read' | 'generating' | 'generated' | 'dismissed';
    pending_article: number | null;
    created_at: string;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
    new: { label: 'New', color: 'from-blue-500 to-blue-600', icon: '🆕' },
    read: { label: 'Read', color: 'from-gray-400 to-gray-500', icon: '👁️' },
    generating: { label: 'Generating...', color: 'from-purple-500 to-purple-600', icon: '🤖' },
    generated: { label: 'Article Created', color: 'from-green-500 to-green-600', icon: '✅' },
    dismissed: { label: 'Dismissed', color: 'from-red-400 to-red-500', icon: '❌' },
};

export default function RSSNewsPage() {
    const [feeds, setFeeds] = useState<RSSFeed[]>([]);
    const [newsItems, setNewsItems] = useState<RSSNewsItem[]>([]);
    const [selectedFeed, setSelectedFeed] = useState<number | null>(null);
    const [statusFilter, setStatusFilter] = useState<string>('new');
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [generatingId, setGeneratingId] = useState<number | null>(null);
    const [selectedItems, setSelectedItems] = useState<Set<number>>(new Set());
    const [bulkDismissing, setBulkDismissing] = useState(false);
    const [expandedItem, setExpandedItem] = useState<number | null>(null);
    const [nextPage, setNextPage] = useState<string | null>(null);
    const [totalCount, setTotalCount] = useState<number>(0);

    useEffect(() => {
        fetchFeeds();
    }, []);

    useEffect(() => {
        fetchNewsItems();
    }, [selectedFeed, statusFilter]);

    const fetchFeeds = async () => {
        try {
            const response = await api.get('/rss-feeds/');
            const feedsData = Array.isArray(response.data) ? response.data : (response.data.results || []);
            setFeeds(feedsData);
        } catch (error) {
            console.error('Error fetching RSS feeds:', error);
        }
    };

    const fetchNewsItems = async (loadMore = false) => {
        if (loadMore) {
            setLoadingMore(true);
        } else {
            setLoading(true);
        }
        try {
            let response;
            if (loadMore && nextPage) {
                // Load next page using the full URL from DRF
                response = await api.get(nextPage.replace(/^.*\/api\/v1/, ''));
            } else {
                const params: any = {};
                if (selectedFeed) params.feed = selectedFeed;
                if (statusFilter) params.status = statusFilter;
                if (statusFilter === 'dismissed') params.show_dismissed = 'true';
                response = await api.get('/rss-news-items/', { params });
            }

            const data = response.data;
            const items = Array.isArray(data) ? data : (data.results || []);

            if (loadMore) {
                setNewsItems(prev => [...prev, ...items]);
            } else {
                setNewsItems(items);
            }

            setNextPage(data.next || null);
            setTotalCount(data.count || items.length);
        } catch (error) {
            console.error('Error fetching news items:', error);
        } finally {
            setLoading(false);
            setLoadingMore(false);
        }
    };

    const handleGenerate = async (itemId: number) => {
        setGeneratingId(itemId);
        try {
            const response = await api.post(`/rss-news-items/${itemId}/generate/`, {
                provider: 'gemini',
            });
            if (response.data.success) {
                const title = response.data.message || 'Article generated';
                const pendingId = response.data.pending_article_id;
                toast.success(
                    (t) => (
                        <div>
                            <p className="font-semibold">✅ {title}</p>
                            {pendingId && (
                                <a
                                    href="/admin/pending-articles"
                                    className="inline-block mt-2 text-sm text-indigo-600 hover:text-indigo-800 font-medium underline"
                                    onClick={() => toast.dismiss(t.id)}
                                >
                                    View in Pending Articles →
                                </a>
                            )}
                        </div>
                    ),
                    { duration: 8000 }
                );
                fetchNewsItems();
            }
        } catch (error: any) {
            console.error('Error generating article:', error);
            const errorMsg = error.response?.data?.error || error.message;
            toast.error(`Generation failed: ${errorMsg}`, { duration: 6000 });
            fetchNewsItems();
        } finally {
            setGeneratingId(null);
        }
    };

    const handleDismiss = async (itemId: number) => {
        try {
            await api.post(`/rss-news-items/${itemId}/dismiss/`);
            setNewsItems(prev => prev.filter(item => item.id !== itemId));
        } catch (error) {
            console.error('Error dismissing item:', error);
        }
    };

    const handleBulkDismiss = async () => {
        if (selectedItems.size === 0) return;
        if (!confirm(`Dismiss ${selectedItems.size} selected item(s)?`)) return;

        setBulkDismissing(true);
        try {
            await api.post('/rss-news-items/bulk_dismiss/', {
                ids: Array.from(selectedItems),
            });
            setSelectedItems(new Set());
            fetchNewsItems();
        } catch (error) {
            console.error('Error bulk dismissing:', error);
        } finally {
            setBulkDismissing(false);
        }
    };

    const toggleItemSelection = (itemId: number) => {
        const newSelected = new Set(selectedItems);
        if (newSelected.has(itemId)) {
            newSelected.delete(itemId);
        } else {
            newSelected.add(itemId);
        }
        setSelectedItems(newSelected);
    };

    const toggleSelectAll = () => {
        if (selectedItems.size === newsItems.length) {
            setSelectedItems(new Set());
        } else {
            setSelectedItems(new Set(newsItems.map(i => i.id)));
        }
    };

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return 'Unknown date';
        return new Date(dateStr).toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
        });
    };

    return (
        <div className="p-6">
            <div className="mb-6">
                <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-br from-orange-500 to-red-500 rounded-xl shadow-lg">
                        <Newspaper className="text-white" size={28} />
                    </div>
                    RSS News Reader
                </h1>
                <p className="text-gray-600 mt-2">
                    Browse news from your RSS feeds. Select interesting articles to generate with AI.
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
                            <h2 className="text-lg font-bold text-gray-900">Sources</h2>
                        </div>

                        {/* All Feeds */}
                        <button
                            onClick={() => setSelectedFeed(null)}
                            className={`w-full text-left px-4 py-3 rounded-xl mb-3 flex items-center justify-between transition-all duration-200 ${selectedFeed === null
                                ? 'bg-gradient-to-r from-indigo-500 to-indigo-600 text-white shadow-md'
                                : 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 hover:border-indigo-300'
                                }`}
                        >
                            <div className="flex items-center gap-2">
                                <span className="text-xl">📊</span>
                                <span className="font-semibold">All Sources</span>
                            </div>
                        </button>

                        <div className="border-t border-gray-200 pt-3 mt-3 space-y-2">
                            {feeds.map((feed) => (
                                <button
                                    key={feed.id}
                                    onClick={() => setSelectedFeed(feed.id)}
                                    className={`w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 transition-all duration-200 ${selectedFeed === feed.id
                                        ? 'bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-md'
                                        : 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 hover:border-orange-300'
                                        }`}
                                >
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
                                </button>
                            ))}
                        </div>

                        {/* Status Filter */}
                        <div className="border-t border-gray-200 pt-4 mt-4">
                            <div className="flex items-center gap-2 mb-3">
                                <Filter size={16} className="text-gray-500" />
                                <span className="text-sm font-semibold text-gray-700">Filter by Status</span>
                            </div>
                            <div className="space-y-1">
                                {[
                                    { value: '', label: 'All', icon: '📋' },
                                    { value: 'new', label: 'New', icon: '🆕' },
                                    { value: 'generated', label: 'Generated', icon: '✅' },
                                    { value: 'dismissed', label: 'Dismissed', icon: '❌' },
                                ].map((option) => (
                                    <button
                                        key={option.value}
                                        onClick={() => setStatusFilter(option.value)}
                                        className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all ${statusFilter === option.value
                                            ? 'bg-indigo-100 text-indigo-700 font-semibold'
                                            : 'text-gray-600 hover:bg-gray-100'
                                            }`}
                                    >
                                        <span className="mr-2">{option.icon}</span>
                                        {option.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Main Content - News Items */}
                <div className="col-span-9">
                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="animate-spin text-indigo-600" size={32} />
                        </div>
                    ) : newsItems.length === 0 ? (
                        <div className="bg-white rounded-xl shadow-md p-12 text-center">
                            <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-orange-100 to-orange-200 rounded-full flex items-center justify-center">
                                <Newspaper className="text-orange-500" size={36} />
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">
                                No news items
                            </h3>
                            <p className="text-gray-600">
                                {selectedFeed
                                    ? 'No news from this feed yet. Try scanning it from the RSS Feeds page.'
                                    : 'No RSS news items found. Scan your feeds to get started.'}
                            </p>
                        </div>
                    ) : (
                        <>
                            {/* Bulk Actions Bar */}
                            <div className="bg-white rounded-xl shadow-md p-4 mb-4 flex items-center justify-between border border-gray-200">
                                <div className="flex items-center gap-3">
                                    <input
                                        type="checkbox"
                                        checked={selectedItems.size === newsItems.length && newsItems.length > 0}
                                        onChange={toggleSelectAll}
                                        className="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 cursor-pointer"
                                    />
                                    <span className="text-sm font-medium text-gray-700">
                                        {selectedItems.size > 0
                                            ? `${selectedItems.size} selected`
                                            : `${newsItems.length} items`}
                                    </span>
                                </div>
                                {selectedItems.size > 0 && (
                                    <button
                                        onClick={handleBulkDismiss}
                                        disabled={bulkDismissing}
                                        className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-all font-medium shadow-sm"
                                    >
                                        {bulkDismissing ? (
                                            <><Loader2 className="animate-spin" size={18} /> Dismissing...</>
                                        ) : (
                                            <><XCircle size={18} /> Dismiss Selected</>
                                        )}
                                    </button>
                                )}
                            </div>

                            {/* News Items Grid */}
                            <div className="space-y-4">
                                {newsItems.map((item) => {
                                    const statusCfg = STATUS_CONFIG[item.status] || STATUS_CONFIG.new;
                                    const isExpanded = expandedItem === item.id;

                                    return (
                                        <div
                                            key={item.id}
                                            className="bg-white rounded-xl shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden border border-gray-100"
                                        >
                                            <div className="p-5">
                                                <div className="flex gap-4">
                                                    {/* Checkbox */}
                                                    <div className="flex-shrink-0 flex items-start pt-1">
                                                        <input
                                                            type="checkbox"
                                                            checked={selectedItems.has(item.id)}
                                                            onChange={() => toggleItemSelection(item.id)}
                                                            className="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 cursor-pointer"
                                                        />
                                                    </div>

                                                    {/* Thumbnail */}
                                                    {item.image_url && (
                                                        <div className="flex-shrink-0">
                                                            <img
                                                                src={item.image_url}
                                                                alt={item.title}
                                                                className="w-44 h-28 object-cover rounded-lg shadow-md border border-gray-200"
                                                                onError={(e) => {
                                                                    e.currentTarget.style.display = 'none';
                                                                }}
                                                            />
                                                        </div>
                                                    )}

                                                    {/* Content */}
                                                    <div className="flex-1 min-w-0">
                                                        {/* Status + Source badges */}
                                                        <div className="flex items-center gap-2 mb-2 flex-wrap">
                                                            <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full bg-gradient-to-r ${statusCfg.color} text-white shadow-sm`}>
                                                                {statusCfg.icon} {statusCfg.label}
                                                            </span>
                                                            <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-orange-100 text-orange-700 border border-orange-200">
                                                                <Rss size={12} className="inline mr-1" />
                                                                {item.feed_name}
                                                            </span>
                                                        </div>

                                                        {/* Title */}
                                                        <h3
                                                            className="text-lg font-bold text-gray-900 mb-2 cursor-pointer hover:text-indigo-600 transition-colors line-clamp-2"
                                                            onClick={() => setExpandedItem(isExpanded ? null : item.id)}
                                                        >
                                                            {item.title}
                                                        </h3>

                                                        {/* Excerpt */}
                                                        <p className="text-sm text-gray-600 leading-relaxed line-clamp-2 mb-3">
                                                            {item.excerpt || 'No preview available'}
                                                        </p>

                                                        {/* Meta info */}
                                                        <div className="flex items-center gap-4 text-xs text-gray-500">
                                                            <div className="flex items-center gap-1">
                                                                <Clock size={14} />
                                                                {formatDate(item.published_at || item.created_at)}
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Action Buttons (right side) */}
                                                    <div className="flex-shrink-0 flex flex-col gap-2">
                                                        {item.status !== 'generated' && item.status !== 'generating' && (
                                                            <button
                                                                onClick={() => handleGenerate(item.id)}
                                                                disabled={generatingId === item.id}
                                                                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 transition-all text-sm font-medium shadow-sm hover:shadow-md whitespace-nowrap"
                                                            >
                                                                {generatingId === item.id ? (
                                                                    <><Loader2 className="animate-spin" size={16} /> Generating...</>
                                                                ) : (
                                                                    <><Wand2 size={16} /> Generate Article</>
                                                                )}
                                                            </button>
                                                        )}

                                                        {item.status === 'generated' && (
                                                            <span className="flex items-center gap-2 px-4 py-2 bg-green-100 text-green-700 rounded-lg text-sm font-medium whitespace-nowrap">
                                                                <CheckCircle2 size={16} /> Article Created
                                                            </span>
                                                        )}

                                                        {item.source_url && (
                                                            <a
                                                                href={item.source_url}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-all text-sm font-medium whitespace-nowrap"
                                                            >
                                                                <ExternalLink size={16} /> Open Original
                                                            </a>
                                                        )}

                                                        {item.status !== 'dismissed' && item.status !== 'generated' && (
                                                            <button
                                                                onClick={() => handleDismiss(item.id)}
                                                                className="flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-all text-sm font-medium whitespace-nowrap"
                                                            >
                                                                <XCircle size={16} /> Dismiss
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>

                                                {/* Expanded Content */}
                                                {isExpanded && (
                                                    <div className="mt-4 p-4 bg-gray-50 rounded-lg border-l-4 border-indigo-500">
                                                        <div className="flex items-center gap-2 mb-3">
                                                            <Eye size={16} className="text-indigo-600" />
                                                            <span className="text-sm font-semibold text-gray-700">Full Content Preview</span>
                                                        </div>
                                                        <div
                                                            className="prose prose-sm max-w-none text-gray-700"
                                                            dangerouslySetInnerHTML={{ __html: item.content || '<p>No content available</p>' }}
                                                        />
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Load More Button */}
                            {nextPage && (
                                <div className="flex flex-col items-center gap-2 mt-6">
                                    <p className="text-sm text-gray-500">
                                        Showing {newsItems.length} of {totalCount} items
                                    </p>
                                    <button
                                        onClick={() => fetchNewsItems(true)}
                                        disabled={loadingMore}
                                        className="px-8 py-3 bg-gradient-to-r from-indigo-500 to-indigo-600 text-white font-semibold rounded-xl shadow-md hover:shadow-lg hover:from-indigo-600 hover:to-indigo-700 transition-all duration-200 disabled:opacity-50 flex items-center gap-2"
                                    >
                                        {loadingMore ? (
                                            <>
                                                <Loader2 size={18} className="animate-spin" />
                                                Loading...
                                            </>
                                        ) : (
                                            <>
                                                Load More ({totalCount - newsItems.length} remaining)
                                            </>
                                        )}
                                    </button>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
