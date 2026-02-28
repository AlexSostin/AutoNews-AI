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
    FileText,
    Shield,
    ShieldCheck,
    ShieldAlert,
    ShieldX,
    ShieldQuestion,
    Search,
    Check,
    Globe,
    X
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
    license_status: 'unchecked' | 'green' | 'yellow' | 'red';
    license_details: string;
    license_checked_at: string | null;
    image_policy: 'original' | 'pexels_only' | 'pexels_fallback';
    safety_score: 'safe' | 'review' | 'unsafe';
    safety_checks: Record<string, { passed: boolean; detail: string }>;
    created_at: string;
    updated_at: string;
}

interface DiscoveredFeed {
    name: string;
    website_url: string;
    feed_url: string | null;
    source_type: string;
    feed_valid: boolean;
    feed_title: string;
    entry_count: number;
    license_status: string;
    license_details: string;
    image_policy: string;
    already_added: boolean;
}

export default function RSSFeedsPage() {
    const router = useRouter();
    const [feeds, setFeeds] = useState<RSSFeed[]>([]);
    const [loading, setLoading] = useState(true);
    const [scanning, setScanning] = useState<number | null>(null);
    const [scanningAll, setScanningAll] = useState(false);
    const [checkingLicense, setCheckingLicense] = useState<number | null>(null);
    const [checkingAllLicenses, setCheckingAllLicenses] = useState(false);
    const [feedsBeingChecked, setFeedsBeingChecked] = useState<Set<number>>(new Set());
    const [discovering, setDiscovering] = useState(false);
    const [discoveredFeeds, setDiscoveredFeeds] = useState<DiscoveredFeed[]>([]);
    const [showDiscovery, setShowDiscovery] = useState(false);
    const [addingFeed, setAddingFeed] = useState<string | null>(null);
    const [toast, setToast] = useState<{ message: string; type: 'success' | 'info' } | null>(null);
    const [sortBy, setSortBy] = useState<string>('name');
    const [filterSource, setFilterSource] = useState<string>('all');
    const [filterSafety, setFilterSafety] = useState<string>('all');
    const [filterImagePolicy, setFilterImagePolicy] = useState<string>('all');
    const [searchQuery, setSearchQuery] = useState('');

    // Feed URL finder
    const [findUrl, setFindUrl] = useState('');
    const [finding, setFinding] = useState(false);
    const [foundFeed, setFoundFeed] = useState<DiscoveredFeed | null>(null);
    const [findError, setFindError] = useState('');

    // Feed stats
    const [feedStats, setFeedStats] = useState<Record<number, { total_items: number; generated_count: number; dismissed_count: number; pending_count_items: number }>>({});

    const showToast = (message: string, type: 'success' | 'info' = 'success') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 5000);
    };

    const pollForCompletion = (feedIds: number[], originalTimestamps: Record<number, string | null>) => {
        setFeedsBeingChecked(prev => new Set([...prev, ...feedIds]));
        let remaining = [...feedIds];

        const interval = setInterval(async () => {
            try {
                const response = await api.get('/rss-feeds/');
                const feedsData = Array.isArray(response.data) ? response.data : (response.data.results || []);
                setFeeds(feedsData);

                const completedIds: number[] = [];
                for (const id of remaining) {
                    const feed = feedsData.find((f: RSSFeed) => f.id === id);
                    if (feed && feed.license_checked_at !== originalTimestamps[id]) {
                        completedIds.push(id);
                    }
                }

                if (completedIds.length > 0) {
                    setFeedsBeingChecked(prev => {
                        const next = new Set(prev);
                        completedIds.forEach(id => next.delete(id));
                        return next;
                    });
                    remaining = remaining.filter(id => !completedIds.includes(id));
                }

                if (remaining.length === 0) {
                    clearInterval(interval);
                    setCheckingAllLicenses(false);
                    showToast(`✅ License check complete for ${feedIds.length} feed(s)`);
                }
            } catch (e) { /* continue polling */ }
        }, 3000);

        setTimeout(() => {
            clearInterval(interval);
            setFeedsBeingChecked(new Set());
            setCheckingAllLicenses(false);
            fetchFeeds();
        }, 120000);
    };

    useEffect(() => {
        fetchFeeds();
        fetchStats();
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

    const fetchStats = async () => {
        try {
            const response = await api.get('/rss-feeds/stats/');
            const statsMap: Record<number, any> = {};
            for (const s of response.data) {
                statsMap[s.id] = s;
            }
            setFeedStats(statsMap);
        } catch (error) {
            console.error('Error fetching feed stats:', error);
        }
    };

    const handleFindFeed = async () => {
        if (!findUrl.trim()) return;
        setFinding(true);
        setFoundFeed(null);
        setFindError('');
        try {
            const response = await api.post('/rss-feeds/find_feed/', { url: findUrl.trim() });
            setFoundFeed(response.data);
            if (!response.data.feed_valid) {
                setFindError('No RSS feed found at this URL');
            }
        } catch (error: any) {
            setFindError(error.response?.data?.error || 'Failed to find feed');
        } finally {
            setFinding(false);
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

    const handleCheckLicense = async (feedId: number) => {
        setCheckingLicense(feedId);
        try {
            const feed = feeds.find(f => f.id === feedId);
            const originalTimestamp = feed?.license_checked_at || null;

            await api.post(`/rss-feeds/${feedId}/check_license/`);
            showToast(`🔍 Checking license for ${feed?.name || 'feed'}...`, 'info');

            pollForCompletion([feedId], { [feedId]: originalTimestamp });
        } catch (error: any) {
            console.error('Error checking license:', error);
            alert('Failed to start license check');
        } finally {
            setCheckingLicense(null);
        }
    };

    const handleCheckAllLicenses = async () => {
        setCheckingAllLicenses(true);
        try {
            const uncheckedFeeds = feeds.filter(f => f.license_status === 'unchecked');
            const timestamps: Record<number, string | null> = {};
            const ids = uncheckedFeeds.map(f => {
                timestamps[f.id] = f.license_checked_at;
                return f.id;
            });

            await api.post('/rss-feeds/check_all_licenses/');
            showToast(`🔍 Checking licenses for ${ids.length} feed(s)...`, 'info');

            if (ids.length > 0) {
                pollForCompletion(ids, timestamps);
            } else {
                setCheckingAllLicenses(false);
                showToast('All feeds already checked');
            }
        } catch (error: any) {
            console.error('Error checking all licenses:', error);
            alert('Failed to start license check');
            setCheckingAllLicenses(false);
        }
    };

    const handleDiscoverFeeds = async () => {
        setDiscovering(true);
        setShowDiscovery(true);
        setDiscoveredFeeds([]);
        try {
            const response = await api.post('/rss-feeds/discover_feeds/');
            setDiscoveredFeeds(response.data.results || []);
        } catch (error: any) {
            console.error('Error discovering feeds:', error);
            alert('Failed to discover feeds');
        } finally {
            setDiscovering(false);
        }
    };

    const handleAddDiscovered = async (feed: DiscoveredFeed) => {
        if (!feed.feed_url) return;
        setAddingFeed(feed.feed_url);
        try {
            await api.post('/rss-feeds/add_discovered/', {
                name: feed.name,
                feed_url: feed.feed_url,
                website_url: feed.website_url,
                source_type: feed.source_type,
                license_status: feed.license_status,
                license_details: feed.license_details,
                image_policy: feed.image_policy,
            });
            // Mark as added in local state
            setDiscoveredFeeds(prev => prev.map(f =>
                f.feed_url === feed.feed_url ? { ...f, already_added: true } : f
            ));
            fetchFeeds();
        } catch (error: any) {
            console.error('Error adding feed:', error);
            alert(error.response?.data?.error || 'Failed to add feed');
        } finally {
            setAddingFeed(null);
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

    const getLicenseBadge = (status: string) => {
        const badges: Record<string, { color: string; icon: typeof ShieldCheck; label: string }> = {
            green: { color: 'bg-emerald-100 text-emerald-800 border border-emerald-200', icon: ShieldCheck, label: 'Free to Use' },
            yellow: { color: 'bg-amber-100 text-amber-800 border border-amber-200', icon: ShieldAlert, label: 'Caution' },
            red: { color: 'bg-red-100 text-red-800 border border-red-200', icon: ShieldX, label: 'Restricted' },
            unchecked: { color: 'bg-gray-100 text-gray-500 border border-gray-200', icon: ShieldQuestion, label: 'Not Checked' },
        };
        return badges[status] || badges.unchecked;
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
                <div className="flex gap-3 flex-wrap">
                    <button
                        onClick={handleDiscoverFeeds}
                        disabled={discovering}
                        className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                    >
                        <Search className={discovering ? 'animate-pulse' : ''} size={20} />
                        {discovering ? 'Discovering...' : 'Discover Feeds'}
                    </button>
                    <button
                        onClick={handleCheckAllLicenses}
                        disabled={checkingAllLicenses}
                        className="flex items-center gap-2 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50"
                    >
                        <Shield className={checkingAllLicenses ? 'animate-pulse' : ''} size={20} />
                        {checkingAllLicenses ? 'Checking...' : 'Check All Licenses'}
                    </button>
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

            {/* Find RSS by URL */}
            <div className="mb-6 bg-white rounded-lg shadow-sm p-4 border border-gray-200">
                <div className="flex items-center gap-3">
                    <div className="flex-1 relative">
                        <Globe size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Paste any website URL to find its RSS feed..."
                            value={findUrl}
                            onChange={(e) => setFindUrl(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleFindFeed()}
                            className="w-full pl-9 pr-3 py-2 text-sm text-gray-800 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                        />
                    </div>
                    <button
                        onClick={handleFindFeed}
                        disabled={finding || !findUrl.trim()}
                        className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 text-sm font-medium"
                    >
                        {finding ? (
                            <><RefreshCw className="animate-spin" size={16} /> Finding...</>
                        ) : (
                            <><Search size={16} /> Find RSS</>
                        )}
                    </button>
                </div>
                {findError && !foundFeed?.feed_valid && (
                    <p className="mt-2 text-sm text-red-600">{findError}</p>
                )}
                {foundFeed && foundFeed.feed_valid && (
                    <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center justify-between">
                        <div>
                            <span className="font-medium text-green-800">{foundFeed.feed_title || foundFeed.name}</span>
                            <span className="text-xs text-green-600 ml-2">✅ RSS found ({foundFeed.entry_count} entries)</span>
                            <div className="text-xs text-gray-500 mt-0.5">{foundFeed.feed_url}</div>
                        </div>
                        {foundFeed.already_added ? (
                            <span className="text-sm text-gray-500 flex items-center gap-1"><Check size={14} /> Already Added</span>
                        ) : (
                            <button
                                onClick={() => {
                                    if (foundFeed.feed_url) {
                                        handleAddDiscovered(foundFeed);
                                        setFoundFeed(null);
                                        setFindUrl('');
                                    }
                                }}
                                className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm"
                            >
                                <Plus size={14} /> Add Feed
                            </button>
                        )}
                    </div>
                )}
            </div>

            {/* Sort & Filter Toolbar */}
            <div className="flex flex-wrap gap-3 mb-6 items-center bg-white rounded-lg shadow-sm p-4">
                {/* Search */}
                <div className="relative flex-1 min-w-[200px]">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search feeds..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-9 pr-3 py-2 text-sm text-gray-800 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    />
                </div>

                {/* Sort */}
                <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="px-3 py-2 text-sm text-gray-800 border rounded-lg bg-white focus:ring-2 focus:ring-indigo-500"
                >
                    <option value="name">Sort: Name</option>
                    <option value="safety_asc">Sort: Safety ↑ (unsafe first)</option>
                    <option value="safety_desc">Sort: Safety ↓ (safe first)</option>
                    <option value="license">Sort: License Status</option>
                    <option value="entries">Sort: Most Articles</option>
                    <option value="recent">Sort: Recently Checked</option>
                </select>

                {/* Filter: Source Type */}
                <select
                    value={filterSource}
                    onChange={(e) => setFilterSource(e.target.value)}
                    className="px-3 py-2 text-sm text-gray-800 border rounded-lg bg-white focus:ring-2 focus:ring-indigo-500"
                >
                    <option value="all">All Types</option>
                    <option value="brand">🏢 Brands</option>
                    <option value="media">📰 Media</option>
                    <option value="blog">✍️ Blogs</option>
                </select>

                {/* Filter: Safety */}
                <select
                    value={filterSafety}
                    onChange={(e) => setFilterSafety(e.target.value)}
                    className="px-3 py-2 text-sm text-gray-800 border rounded-lg bg-white focus:ring-2 focus:ring-indigo-500"
                >
                    <option value="all">All Safety</option>
                    <option value="safe">✅ Safe</option>
                    <option value="review">🟡 Review</option>
                    <option value="unsafe">🔴 Unsafe</option>
                </select>

                {/* Filter: Image Policy */}
                <select
                    value={filterImagePolicy}
                    onChange={(e) => setFilterImagePolicy(e.target.value)}
                    className="px-3 py-2 text-sm text-gray-800 border rounded-lg bg-white focus:ring-2 focus:ring-indigo-500"
                >
                    <option value="all">All Images</option>
                    <option value="original">📷 Original</option>
                    <option value="pexels_only">🖼️ Pexels</option>
                    <option value="pexels_fallback">📷+🖼️ Fallback</option>
                </select>

                {/* Feed count */}
                <span className="text-sm text-gray-500 ml-auto">
                    {(() => {
                        const filtered = feeds.filter(f => {
                            if (filterSource !== 'all' && f.source_type !== filterSource) return false;
                            if (filterSafety !== 'all' && f.safety_score !== filterSafety) return false;
                            if (filterImagePolicy !== 'all' && f.image_policy !== filterImagePolicy) return false;
                            if (searchQuery && !f.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
                            return true;
                        });
                        return filtered.length === feeds.length
                            ? `${feeds.length} feeds`
                            : `${filtered.length} / ${feeds.length} feeds`;
                    })()}
                </span>
            </div>

            {/* Discovery Results Section */}
            {showDiscovery && (
                <div className="mb-8 bg-white rounded-lg shadow-lg overflow-hidden">
                    <div className="flex items-center justify-between p-4 bg-purple-50 border-b">
                        <div>
                            <h2 className="text-lg font-semibold text-purple-900 flex items-center gap-2">
                                <Globe size={20} />
                                Discovered Automotive RSS Feeds
                            </h2>
                            <p className="text-sm text-purple-700 mt-1">
                                {discovering ? 'Scanning curated sources...' : `Found ${discoveredFeeds.length} sources (${discoveredFeeds.filter(f => f.feed_valid).length} with valid RSS)`}
                            </p>
                        </div>
                        <button onClick={() => setShowDiscovery(false)} className="text-purple-400 hover:text-purple-600">
                            <X size={20} />
                        </button>
                    </div>

                    {discovering ? (
                        <div className="p-8 text-center">
                            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-600 mx-auto"></div>
                            <p className="mt-3 text-gray-600">Checking ~40 automotive sources for RSS feeds...</p>
                            <p className="text-sm text-gray-400 mt-1">This may take 30-60 seconds</p>
                        </div>
                    ) : (
                        <div className="divide-y max-h-[600px] overflow-y-auto">
                            {discoveredFeeds
                                .filter(feed => feed.feed_valid || feed.already_added)
                                .map((feed, idx) => {
                                    const badge = getLicenseBadge(feed.license_status);
                                    const BadgeIcon = badge.icon;
                                    return (
                                        <div key={idx} className={`p-4 flex items-center justify-between hover:bg-gray-50 ${feed.already_added ? 'opacity-60' : ''}`}>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="font-medium text-gray-900">{feed.name}</span>
                                                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full ${badge.color}`}>
                                                        <BadgeIcon size={10} />
                                                        {badge.label}
                                                    </span>
                                                    {feed.feed_valid ? (
                                                        <span className="text-xs text-green-600 flex items-center gap-1">
                                                            <Rss size={10} /> RSS OK ({feed.entry_count} entries)
                                                        </span>
                                                    ) : (
                                                        <span className="text-xs text-gray-400">No RSS detected</span>
                                                    )}
                                                    {feed.already_added && (
                                                        <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">Already Added</span>
                                                    )}
                                                </div>
                                                <div className="text-xs text-gray-500 mt-1 truncate">
                                                    {feed.website_url}
                                                    {feed.feed_url && feed.feed_url !== feed.website_url && (
                                                        <span className="ml-2 text-gray-400">→ {feed.feed_url}</span>
                                                    )}
                                                </div>
                                            </div>
                                            <div className="ml-4 flex-shrink-0">
                                                {feed.feed_valid && !feed.already_added && feed.feed_url ? (
                                                    <button
                                                        onClick={() => handleAddDiscovered(feed)}
                                                        disabled={addingFeed === feed.feed_url}
                                                        className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 text-sm"
                                                    >
                                                        {addingFeed === feed.feed_url ? (
                                                            <RefreshCw className="animate-spin" size={14} />
                                                        ) : (
                                                            <Plus size={14} />
                                                        )}
                                                        Add
                                                    </button>
                                                ) : feed.already_added ? (
                                                    <span className="flex items-center gap-1 text-green-600 text-sm">
                                                        <Check size={14} /> Added
                                                    </span>
                                                ) : null}
                                            </div>
                                        </div>
                                    );
                                })}
                            {discoveredFeeds.filter(f => !f.feed_valid && !f.already_added).length > 0 && (
                                <div className="p-3 text-center text-xs text-gray-400 bg-gray-50">
                                    {discoveredFeeds.filter(f => !f.feed_valid && !f.already_added).length} sources without RSS feeds hidden
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

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
                    {feeds
                        .filter(feed => {
                            if (filterSource !== 'all' && feed.source_type !== filterSource) return false;
                            if (filterSafety !== 'all' && feed.safety_score !== filterSafety) return false;
                            if (filterImagePolicy !== 'all' && feed.image_policy !== filterImagePolicy) return false;
                            if (searchQuery && !feed.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
                            return true;
                        })
                        .sort((a, b) => {
                            const safetyOrder: Record<string, number> = { unsafe: 0, review: 1, safe: 2 };
                            const licenseOrder: Record<string, number> = { red: 0, yellow: 1, unchecked: 2, green: 3 };
                            switch (sortBy) {
                                case 'safety_asc': return (safetyOrder[a.safety_score] ?? 1) - (safetyOrder[b.safety_score] ?? 1);
                                case 'safety_desc': return (safetyOrder[b.safety_score] ?? 1) - (safetyOrder[a.safety_score] ?? 1);
                                case 'license': return (licenseOrder[a.license_status] ?? 2) - (licenseOrder[b.license_status] ?? 2);
                                case 'entries': return b.entries_processed - a.entries_processed;
                                case 'recent': return new Date(b.license_checked_at || '1970').getTime() - new Date(a.license_checked_at || '1970').getTime();
                                default: return a.name.localeCompare(b.name);
                            }
                        })
                        .map((feed) => (
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
                                            {/* License Status Badge */}
                                            {(() => {
                                                const isBeingChecked = feedsBeingChecked.has(feed.id);
                                                const badge = getLicenseBadge(isBeingChecked ? 'unchecked' : feed.license_status);
                                                const BadgeIcon = badge.icon;
                                                return (
                                                    <div className="relative group/license">
                                                        <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded-full cursor-help ${badge.color} ${isBeingChecked ? 'animate-pulse' : ''}`}>
                                                            <BadgeIcon size={12} className={isBeingChecked ? 'animate-spin' : ''} />
                                                            {isBeingChecked ? 'Checking...' : badge.label}
                                                        </span>
                                                        {feed.license_details && (
                                                            <div className="absolute z-50 left-0 top-full mt-2 w-80 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-xl opacity-0 invisible group-hover/license:opacity-100 group-hover/license:visible transition-all duration-200 whitespace-pre-line">
                                                                <div className="font-semibold mb-1">License Details</div>
                                                                {feed.license_details}
                                                                {feed.license_checked_at && (
                                                                    <div className="mt-2 text-gray-400 text-[10px]">Checked: {formatDate(feed.license_checked_at)}</div>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            })()}
                                            {/* Safety Score Badge with Check Breakdown */}
                                            {(() => {
                                                const safety = feed.safety_score;
                                                const checks = feed.safety_checks || {};
                                                const checkEntries = Object.entries(checks).filter(([, v]) => v && typeof v === 'object');
                                                const passed = checkEntries.filter(([, v]) => v.passed).length;
                                                const total = checkEntries.length;
                                                const safetyConfig: Record<string, { label: string; color: string }> = {
                                                    safe: { label: `✅ ${passed}/${total}`, color: 'bg-emerald-100 text-emerald-700' },
                                                    review: { label: `🟡 ${passed}/${total}`, color: 'bg-amber-100 text-amber-700' },
                                                    unsafe: { label: `🔴 ${passed}/${total}`, color: 'bg-red-100 text-red-700' },
                                                };
                                                const cfg = safetyConfig[safety] || safetyConfig.review;
                                                const checkNames: Record<string, string> = {
                                                    robots_txt: 'Robots.txt',
                                                    press_portal: 'Press Portal',
                                                    tos_analysis: 'Terms of Service',
                                                    image_rights: 'Image Rights',
                                                };
                                                return (
                                                    <div className="relative group/safety">
                                                        <span className={`inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full cursor-help ${cfg.color}`}>
                                                            {total > 0 ? cfg.label : (safety === 'safe' ? '✅ Safe' : safety === 'unsafe' ? '🔴 Unsafe' : '🟡 Review')}
                                                        </span>
                                                        {total > 0 && (
                                                            <div className="absolute z-50 left-0 top-full mt-2 w-72 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-xl opacity-0 invisible group-hover/safety:opacity-100 group-hover/safety:visible transition-all duration-200">
                                                                <div className="font-semibold mb-2">Safety Checks ({passed}/{total} passed)</div>
                                                                {checkEntries.map(([key, val]) => (
                                                                    <div key={key} className="flex items-start gap-2 mb-1.5">
                                                                        <span>{val.passed ? '✅' : '❌'}</span>
                                                                        <div>
                                                                            <div className="font-medium">{checkNames[key] || key}</div>
                                                                            <div className="text-gray-400 text-[10px]">{val.detail}</div>
                                                                        </div>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            })()}
                                            {/* Image Policy Badge */}
                                            <span className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${feed.image_policy === 'original' ? 'bg-blue-100 text-blue-700' :
                                                feed.image_policy === 'pexels_only' ? 'bg-purple-100 text-purple-700' :
                                                    'bg-gray-100 text-gray-600'
                                                }`} title={`Image policy: ${feed.image_policy}`}>
                                                {feed.image_policy === 'original' ? '📷 Original' :
                                                    feed.image_policy === 'pexels_only' ? '🖼️ Pexels' :
                                                        '📷+🖼️ Fallback'}
                                            </span>
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
                                                <span>
                                                    {feedStats[feed.id] ? (
                                                        <>
                                                            {feedStats[feed.id].total_items} items • {feedStats[feed.id].generated_count} articles • {feedStats[feed.id].pending_count_items} pending
                                                        </>
                                                    ) : (
                                                        <>Entries processed: {feed.entries_processed} | Pending: {feed.pending_count}</>
                                                    )}
                                                </span>
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

                                        <button
                                            onClick={() => handleCheckLicense(feed.id)}
                                            disabled={checkingLicense === feed.id}
                                            className="flex items-center gap-2 px-3 py-2 bg-amber-100 text-amber-800 rounded hover:bg-amber-200 disabled:opacity-50 text-sm"
                                        >
                                            <Shield className={checkingLicense === feed.id ? 'animate-pulse' : ''} size={16} />
                                            {checkingLicense === feed.id ? 'Checking...' : 'Check License'}
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
            {/* Toast Notification */}
            {toast && (
                <div className={`fixed bottom-6 right-6 z-50 px-5 py-3 rounded-lg shadow-xl text-white text-sm font-medium flex items-center gap-2 transition-all duration-300 ${toast.type === 'success' ? 'bg-emerald-600' : 'bg-blue-600'
                    }`}>
                    {toast.message}
                    <button onClick={() => setToast(null)} className="ml-2 text-white/70 hover:text-white">
                        <X size={14} />
                    </button>
                </div>
            )}
        </div>
    );
}
