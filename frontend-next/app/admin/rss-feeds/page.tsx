'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
    Plus,
    RefreshCw,
    Trash2,
    Edit,
    Power,
    PowerOff,
    ExternalLink,
    Rss,
    Clock,
    FileText
} from 'lucide-react';
import api from '@/lib/api';

interface RSSFeed {
    id: number;
    name: string;
    feed_url: string;
    website_url: string;
    source_type: 'brand' | 'media' | 'blog';
    is_enabled: boolean;
    auto_publish: boolean;
    default_category: number | null;
    category_name: string | null;
    last_checked: string | null;
    last_entry_date: string | null;
    entries_processed: number;
    logo_url: string;
    description: string;
    pending_count: number;
    created_at: string;
    updated_at: string;
}

export default function RSSFeedsPage() {
    const router = useRouter();
    const [feeds, setFeeds] = useState<RSSFeed[]>([]);
    const [loading, setLoading] = useState(true);
    const [scanning, setScanning] = useState<number | null>(null);
    const [scanningAll, setScanningAll] = useState(false);

    useEffect(() => {
        fetchFeeds();
    }, []);

    const fetchFeeds = async () => {
        try {
            const response = await api.get('/rss-feeds/');
            // Handle both array response and paginated response
            const feedsData = Array.isArray(response.data) ? response.data : (response.data.results || []);
            setFeeds(feedsData);
        } catch (error) {
            console.error('Error fetching RSS feeds:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleScanNow = async (feedId: number) => {
        setScanning(feedId);
        try {
            const response = await api.post(`/rss-feeds/${feedId}/scan_now/`);
            alert(response.data.message);
            setTimeout(fetchFeeds, 3000);
        } catch (error: any) {
            console.error('Error scanning feed:', error);
            alert('Failed to start scan');
        } finally {
            setScanning(null);
        }
    };

    const handleScanAll = async () => {
        setScanningAll(true);
        try {
            const response = await api.post('/rss-feeds/scan_all/');
            alert(response.data.message);
            setTimeout(fetchFeeds, 3000);
        } catch (error: any) {
            console.error('Error scanning all feeds:', error);
            alert('Failed to start scan');
        } finally {
            setScanningAll(false);
        }
    };

    const handleToggleEnabled = async (feed: RSSFeed) => {
        try {
            await api.patch(`/rss-feeds/${feed.id}/`, { is_enabled: !feed.is_enabled });
            fetchFeeds();
        } catch (error: any) {
            console.error('Error toggling feed:', error);
        }
    };

    const handleDelete = async (feedId: number) => {
        if (!confirm('Are you sure you want to delete this RSS feed?')) return;

        try {
            await api.delete(`/rss-feeds/${feedId}/`);
            fetchFeeds();
        } catch (error: any) {
            console.error('Error deleting feed:', error);
        }
    };

    const formatDate = (dateString: string | null) => {
        if (!dateString) return 'Never';
        return new Date(dateString).toLocaleString();
    };

    const getSourceTypeBadge = (type: string) => {
        const colors = {
            brand: 'bg-blue-100 text-blue-800',
            media: 'bg-green-100 text-green-800',
            blog: 'bg-purple-100 text-purple-800',
        };
        return colors[type as keyof typeof colors] || 'bg-gray-100 text-gray-800';
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">RSS Feeds</h1>
                    <p className="text-gray-600 mt-1">Manage RSS feeds for automatic article generation</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={handleScanAll}
                        disabled={scanningAll}
                        className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                    >
                        <RefreshCw className={scanningAll ? 'animate-spin' : ''} size={20} />
                        {scanningAll ? 'Scanning...' : 'Scan All'}
                    </button>
                    <Link
                        href="/admin/rss-feeds/new"
                        className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                    >
                        <Plus size={20} />
                        Add RSS Feed
                    </Link>
                </div>
            </div>

            {feeds.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-lg shadow">
                    <Rss className="mx-auto h-12 w-12 text-gray-400" />
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No RSS feeds</h3>
                    <p className="mt-1 text-sm text-gray-500">Get started by adding a new RSS feed.</p>
                    <div className="mt-6">
                        <Link
                            href="/admin/rss-feeds/new"
                            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                        >
                            <Plus className="mr-2 h-5 w-5" />
                            Add RSS Feed
                        </Link>
                    </div>
                </div>
            ) : (
                <div className="grid gap-6">
                    {feeds.map((feed) => (
                        <div
                            key={feed.id}
                            className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex-1">
                                    <div className="flex items-center gap-3 mb-2">
                                        <h3 className="text-xl font-bold text-gray-900">{feed.name}</h3>
                                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getSourceTypeBadge(feed.source_type)}`}>
                                            {feed.source_type}
                                        </span>
                                        {feed.is_enabled ? (
                                            <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                                                Enabled
                                            </span>
                                        ) : (
                                            <span className="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
                                                Disabled
                                            </span>
                                        )}
                                    </div>

                                    <div className="space-y-2 text-sm text-gray-600">
                                        <div className="flex items-center gap-2">
                                            <Rss size={16} />
                                            <a href={feed.feed_url} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline">
                                                {feed.feed_url}
                                            </a>
                                            <ExternalLink size={14} />
                                        </div>

                                        {feed.website_url && (
                                            <div className="flex items-center gap-2">
                                                <ExternalLink size={16} />
                                                <a href={feed.website_url} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline">
                                                    {feed.website_url}
                                                </a>
                                            </div>
                                        )}

                                        <div className="flex items-center gap-2">
                                            <Clock size={16} />
                                            <span>Last checked: {formatDate(feed.last_checked)}</span>
                                        </div>

                                        <div className="flex items-center gap-2">
                                            <FileText size={16} />
                                            <span>Entries processed: {feed.entries_processed} | Pending: {feed.pending_count}</span>
                                        </div>

                                        {feed.category_name && (
                                            <div className="text-sm">
                                                <span className="font-semibold">Default Category:</span> {feed.category_name}
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div className="flex flex-col gap-2 ml-4">
                                    <button
                                        onClick={() => handleScanNow(feed.id)}
                                        disabled={scanning === feed.id}
                                        className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
                                    >
                                        <RefreshCw className={scanning === feed.id ? 'animate-spin' : ''} size={16} />
                                        {scanning === feed.id ? 'Scanning...' : 'Scan Now'}
                                    </button>

                                    <button
                                        onClick={() => handleToggleEnabled(feed)}
                                        className={`flex items-center gap-2 px-3 py-2 rounded text-sm ${feed.is_enabled
                                            ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200'
                                            : 'bg-green-100 text-green-800 hover:bg-green-200'
                                            }`}
                                    >
                                        {feed.is_enabled ? <PowerOff size={16} /> : <Power size={16} />}
                                        {feed.is_enabled ? 'Disable' : 'Enable'}
                                    </button>

                                    <Link
                                        href={`/admin/rss-feeds/${feed.id}/edit`}
                                        className="flex items-center gap-2 px-3 py-2 bg-gray-100 text-gray-800 rounded hover:bg-gray-200 text-sm"
                                    >
                                        <Edit size={16} />
                                        Edit
                                    </Link>

                                    <button
                                        onClick={() => handleDelete(feed.id)}
                                        className="flex items-center gap-2 px-3 py-2 bg-red-100 text-red-800 rounded hover:bg-red-200 text-sm"
                                    >
                                        <Trash2 size={16} />
                                        Delete
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
