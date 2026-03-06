'use client';

import { useState, useEffect, useMemo } from 'react';
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
    ArrowUpDown,
    Sparkles,
    Tag,
    Heart,
} from 'lucide-react';
import api from '@/lib/api';
import { logCaughtError } from '@/lib/error-logger';
import toast from 'react-hot-toast';
import { sanitizeHtml } from '@/lib/sanitize';

// ----------------------------------------------------------------
// Known automotive brands (mirrors backend KNOWN_BRANDS)
// ----------------------------------------------------------------
const KNOWN_BRANDS: string[] = [
    // Multi-word first so they match before single-word substrings
    'li auto', 'lynk & co', 'land rover', 'range rover', 'alfa romeo',
    'aston martin', 'rolls-royce', 'mercedes-benz', 'im motors', 'rising auto',
    // Chinese
    'byd', 'xiaomi', 'xpeng', 'zeekr', 'geely', 'dongfeng', 'nio', 'changan',
    'gac', 'voyah', 'avatr', 'smart', 'polestar', 'wey', 'tank', 'haval',
    'ora', 'leapmotor', 'neta', 'jidu', 'deepal', 'denza', 'yangwang',
    'fangchengbao', 'hyptec', 'onvo', 'firefly', 'hongqi', 'baic', 'arcfox',
    'gwm', 'chery', 'jetour', 'exeed', 'forthing', 'seres',
    // European
    'bmw', 'mercedes', 'audi', 'porsche', 'volkswagen', 'vw', 'volvo',
    'bentley', 'ferrari', 'lamborghini', 'maserati', 'fiat', 'peugeot',
    'citroen', 'renault', 'skoda', 'seat', 'cupra', 'mini', 'bugatti',
    'mclaren', 'lotus', 'jaguar',
    // Japanese
    'toyota', 'honda', 'nissan', 'mazda', 'subaru', 'mitsubishi', 'suzuki',
    'lexus', 'infiniti', 'acura',
    // Korean
    'hyundai', 'kia', 'genesis',
    // American
    'tesla', 'ford', 'chevrolet', 'gm', 'gmc', 'cadillac', 'chrysler',
    'dodge', 'jeep', 'ram', 'buick', 'lincoln', 'rivian', 'lucid', 'fisker', 'canoo',
    // Others
    'tata', 'mahindra', 'vinfast',
];

const BRAND_DISPLAY: Record<string, string> = {
    'byd': 'BYD', 'bmw': 'BMW', 'gm': 'GM', 'gmc': 'GMC', 'gac': 'GAC',
    'nio': 'NIO', 'vw': 'Volkswagen', 'mercedes-benz': 'Mercedes-Benz',
    'mercedes': 'Mercedes-Benz', 'rolls-royce': 'Rolls-Royce',
    'land rover': 'Land Rover', 'range rover': 'Range Rover',
    'alfa romeo': 'Alfa Romeo', 'aston martin': 'Aston Martin',
    'li auto': 'Li Auto', 'lynk & co': 'Lynk & Co',
    'im motors': 'IM Motors', 'rising auto': 'Rising Auto',
    'zeekr': 'ZEEKR', 'xiaomi': 'XIAOMI', 'xpeng': 'XPENG',
    'voyah': 'VOYAH', 'avatr': 'AVATR', 'baic': 'BAIC',
    'tesla': 'Tesla', 'ford': 'Ford', 'chevrolet': 'Chevrolet',
    'cadillac': 'Cadillac', 'dodge': 'Dodge', 'jeep': 'Jeep',
    'ram': 'RAM', 'buick': 'Buick', 'lincoln': 'Lincoln',
    'rivian': 'Rivian', 'lucid': 'Lucid', 'fisker': 'Fisker',
    'toyota': 'Toyota', 'honda': 'Honda', 'nissan': 'Nissan',
    'mazda': 'Mazda', 'subaru': 'Subaru', 'suzuki': 'Suzuki',
    'lexus': 'Lexus', 'infiniti': 'Infiniti', 'acura': 'Acura',
    'hyundai': 'Hyundai', 'kia': 'Kia', 'genesis': 'Genesis',
    'audi': 'Audi', 'porsche': 'Porsche', 'volkswagen': 'Volkswagen',
    'volvo': 'Volvo', 'bentley': 'Bentley', 'ferrari': 'Ferrari',
    'lamborghini': 'Lamborghini', 'maserati': 'Maserati',
    'peugeot': 'Peugeot', 'renault': 'Renault', 'skoda': 'Škoda',
    'cupra': 'CUPRA', 'mini': 'MINI', 'jaguar': 'Jaguar',
    'tata': 'Tata', 'mahindra': 'Mahindra', 'vinfast': 'VinFast',
    'haval': 'Haval', 'tank': 'Tank', 'leapmotor': 'Leapmotor',
    'chery': 'Chery', 'geely': 'Geely', 'dongfeng': 'Dongfeng',
    'polestar': 'Polestar', 'canoo': 'Canoo',
};

function extractBrandFromTitle(title: string): string | null {
    const lower = title.toLowerCase();
    for (const brand of KNOWN_BRANDS) {
        const escaped = brand.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        if (new RegExp(`\\b${escaped}\\b`, 'i').test(lower)) {
            return BRAND_DISPLAY[brand] ?? brand.charAt(0).toUpperCase() + brand.slice(1);
        }
    }
    return null;
}

// Returns JSX with brand names wrapped in highlight spans
function HighlightedTitle({ title, activeBrand }: { title: string; activeBrand: string | null }) {
    const parts: React.ReactNode[] = [];
    let remaining = title;
    let key = 0;

    for (const brand of KNOWN_BRANDS) {
        const escaped = brand.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(\\b${escaped}\\b)`, 'gi');
        const displayName = BRAND_DISPLAY[brand] ?? brand.charAt(0).toUpperCase() + brand.slice(1);
        const isActive = activeBrand === displayName;

        if (regex.test(remaining)) {
            const splitResult = remaining.split(new RegExp(`(\\b${escaped}\\b)`, 'gi'));
            remaining = '';
            for (const part of splitResult) {
                if (new RegExp(`^${escaped}$`, 'i').test(part)) {
                    parts.push(
                        <mark
                            key={key++}
                            className={`px-0.5 rounded font-semibold not-italic ${isActive
                                ? 'bg-indigo-200 text-indigo-900'
                                : 'bg-amber-100 text-amber-800'
                                }`}
                        >
                            {part}
                        </mark>
                    );
                } else {
                    parts.push(<span key={key++}>{part}</span>);
                }
            }
            break;
        }
    }

    if (parts.length === 0) return <>{title}</>;
    return <>{parts}</>;
}

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
    is_favorite: boolean;
    pending_article: number | null;
    created_at: string;
    relevance_score: number;
    relevance_label: 'high' | 'medium' | 'low';
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
    new: { label: 'New', color: 'from-blue-500 to-blue-600', icon: '🆕' },
    read: { label: 'Read', color: 'from-gray-400 to-gray-500', icon: '👁️' },
    generating: { label: 'Generating...', color: 'from-yellow-500 to-yellow-600', icon: '⚡' },
    generated: { label: 'Article Created', color: 'from-green-500 to-green-600', icon: '✅' },
    dismissed: { label: 'Dismissed', color: 'from-red-400 to-red-500', icon: '❌' },
};

const RELEVANCE_COLORS = {
    high: { stripe: 'bg-emerald-500', badge: 'bg-emerald-100 text-emerald-700 border-emerald-200', text: 'High', dot: 'bg-emerald-500' },
    medium: { stripe: 'bg-orange-500', badge: 'bg-orange-100 text-orange-700 border-orange-300', text: 'Medium', dot: 'bg-orange-500' },
    low: { stripe: 'bg-rose-400', badge: 'bg-rose-100 text-rose-600 border-rose-300', text: 'Low', dot: 'bg-rose-400' },
};

export default function RSSNewsPage() {
    const [feeds, setFeeds] = useState<RSSFeed[]>([]);
    const [newsItems, setNewsItems] = useState<RSSNewsItem[]>([]);
    const [selectedFeed, setSelectedFeed] = useState<number | null>(null);
    const [statusFilter, setStatusFilter] = useState<string>('new');
    const [sortBy, setSortBy] = useState<'relevance' | 'date'>('relevance');
    const [brandFilter, setBrandFilter] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [generatingId, setGeneratingId] = useState<number | null>(null);
    const [selectedItems, setSelectedItems] = useState<Set<number>>(new Set());
    const [bulkDismissing, setBulkDismissing] = useState(false);
    const [bulkGenerating, setBulkGenerating] = useState(false);
    const [bulkProgress, setBulkProgress] = useState('');
    const [expandedItem, setExpandedItem] = useState<number | null>(null);
    const [nextPage, setNextPage] = useState<string | null>(null);
    const [totalCount, setTotalCount] = useState<number>(0);

    // Global brand stats — fetched from API (all items in DB, last 30 days)
    const [globalBrandStats, setGlobalBrandStats] = useState<[string, number][]>([]);
    const [loadingStats, setLoadingStats] = useState(false);
    const [statsScanned, setStatsScanned] = useState<number>(0);

    const fetchGlobalBrandStats = async () => {
        setLoadingStats(true);
        try {
            const res = await api.get('/rss-news-items/trending_brands/', { params: { days: 30, min: 1 } });
            const brands: Array<{ brand: string; display_name?: string; count: number }> = res.data.brands || [];
            // Use display_name (e.g. 'Toyota') not raw key ('toyota')
            setGlobalBrandStats(brands.map(b => [b.display_name ?? b.brand, b.count]));
            setStatsScanned(brands.reduce((s, b) => s + b.count, 0));
        } catch (e) {
            logCaughtError('rss_trending_brands', e);
        } finally {
            setLoadingStats(false);
        }
    };

    // Local brand counts from loaded page — for filter matching
    const localBrandCounts = useMemo(() => {
        const counts: Record<string, number> = {};
        for (const item of newsItems) {
            const brand = extractBrandFromTitle(item.title);
            if (brand) counts[brand] = (counts[brand] ?? 0) + 1;
        }
        return counts;
    }, [newsItems]);

    // Priority: global API stats > local page counts
    const brandCounts: [string, number][] = globalBrandStats.length > 0
        ? globalBrandStats
        : Object.entries(localBrandCounts).sort((a, b) => b[1] - a[1]);


    useEffect(() => {
        fetchFeeds();
        fetchGlobalBrandStats(); // Scan all DB items, not just loaded page
    }, []);

    useEffect(() => {
        // brandFilter/statusFilter/sortBy change triggers a new server-side fetch
        fetchNewsItems();
    }, [selectedFeed, statusFilter, brandFilter, sortBy]);


    const fetchFeeds = async () => {
        try {
            const response = await api.get('/rss-feeds/');
            const feedsData = Array.isArray(response.data) ? response.data : (response.data.results || []);
            setFeeds(feedsData);
        } catch (error) {
            logCaughtError('rss_pending_fetch_feeds', error);
        }
    };

    const fetchNewsItems = async (loadMore = false, brandOverride?: string | null) => {
        if (loadMore) {
            setLoadingMore(true);
        } else {
            setLoading(true);
        }
        // Use brandOverride if provided, else current brandFilter state
        const activeBrand = brandOverride !== undefined ? brandOverride : brandFilter;
        try {
            let response;
            if (loadMore && nextPage) {
                response = await api.get(nextPage.replace(/^.*\/api\/v1/, ''));
            } else {
                const params: any = {};
                if (selectedFeed) params.feed = selectedFeed;
                if (statusFilter) params.status = statusFilter;
                if (statusFilter === 'dismissed') params.show_dismissed = 'true';
                if (activeBrand) params.brand = activeBrand;
                // Server-side ordering so sort works across all pages
                params.ordering = sortBy === 'relevance' ? '-is_favorite,-created_at' : '-published_at,-created_at';
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
            logCaughtError('rss_pending_fetch_items', error);
        } finally {
            setLoading(false);
            setLoadingMore(false);
        }
    };

    const handleGenerate = async (itemId: number) => {
        setGeneratingId(itemId);
        try {
            const response = await api.post(`/rss-news-items/${itemId}/generate/`);
            if (response.data.pending_article) {
                setNewsItems(prev => prev.map(item =>
                    item.id === itemId
                        ? { ...item, status: 'generated', pending_article: response.data.pending_article.id }
                        : item
                ));
                toast.success('Article generated successfully!');
            }
        } catch (error: any) {
            logCaughtError('rss_pending_generate', error, { itemId });
            const detail = error.response?.data?.error || error.message;
            toast.error(`Generation failed: ${detail}`);
        } finally {
            setGeneratingId(null);
        }
    };

    const handleDismiss = async (itemId: number) => {
        try {
            await api.post(`/rss-news-items/${itemId}/dismiss/`);
            setNewsItems(prev => prev.filter(item => item.id !== itemId));
        } catch (error) {
            logCaughtError('rss_pending_dismiss', error, { itemId });
        }
    };

    const handleToggleFavorite = async (itemId: number) => {
        try {
            const response = await api.post(`/rss-news-items/${itemId}/toggle_favorite/`);
            const { is_favorite } = response.data;
            setNewsItems(prev => prev.map(item =>
                item.id === itemId ? { ...item, is_favorite } : item
            ));
            toast.success(is_favorite ? '❤️ Saved — kept 60 days as ML signal' : 'Removed from favorites');
        } catch (error) {
            logCaughtError('rss_pending_toggle_favorite', error, { itemId });
            toast.error('Could not update favorite');
        }
    };

    const handleBulkDismiss = async () => {
        if (selectedItems.size === 0) return;
        setBulkDismissing(true);
        try {
            await api.post('/rss-news-items/bulk_dismiss/', {
                item_ids: Array.from(selectedItems)
            });
            setNewsItems(prev => prev.filter(item => !selectedItems.has(item.id)));
            setSelectedItems(new Set());
            toast.success(`Dismissed ${selectedItems.size} items`);
        } catch (error) {
            logCaughtError('rss_pending_bulk_dismiss', error);
            toast.error('Bulk dismiss failed');
        } finally {
            setBulkDismissing(false);
        }
    };

    const handleBulkGenerate = async () => {
        if (selectedItems.size === 0) return;
        setBulkGenerating(true);
        setBulkProgress('Starting...');
        try {
            const response = await api.post('/rss-news-items/bulk_generate/', {
                item_ids: Array.from(selectedItems)
            });

            const results = response.data.results || [];
            let successCount = 0;
            let failCount = 0;

            for (const r of results) {
                if (r.status === 'success' || r.status === 'generated') {
                    successCount++;
                    setNewsItems(prev => prev.map(item =>
                        item.id === r.item_id
                            ? { ...item, status: 'generated', pending_article: r.pending_article_id }
                            : item
                    ));
                } else {
                    failCount++;
                }
            }

            setSelectedItems(new Set());
            setBulkProgress('');
            const msg = failCount > 0
                ? `${successCount} generated, ${failCount} failed`
                : `${successCount} articles generated!`;
            toast.success(msg);
        } catch (error) {
            logCaughtError('rss_pending_bulk_generate', error);
            toast.error('Bulk generation failed');
        } finally {
            setBulkGenerating(false);
            setBulkProgress('');
        }
    };

    const toggleItemSelection = (itemId: number) => {
        setSelectedItems(prev => {
            const next = new Set(prev);
            if (next.has(itemId)) {
                next.delete(itemId);
            } else {
                next.add(itemId);
            }
            return next;
        });
    };

    const toggleSelectAll = () => {
        if (selectedItems.size === newsItems.length) {
            setSelectedItems(new Set());
        } else {
            setSelectedItems(new Set(newsItems.map(item => item.id)));
        }
    };

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return 'Unknown';
        const d = new Date(dateStr);
        const now = new Date();
        const diffHours = Math.floor((now.getTime() - d.getTime()) / 3600000);
        if (diffHours < 1) return 'Just now';
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffHours < 48) return 'Yesterday';
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };

    // Sort only — brand filtering is now server-side via ?brand= query param
    const sortedItems = useMemo(() => {
        return [...newsItems].sort((a, b) => {
            if (sortBy === 'relevance') return (b.relevance_score || 0) - (a.relevance_score || 0);
            const dateA = new Date(a.published_at || a.created_at).getTime();
            const dateB = new Date(b.published_at || b.created_at).getTime();
            return dateB - dateA;
        });
    }, [newsItems, sortBy]);


    // Stats (based on full list, not filtered)
    const highCount = newsItems.filter(i => i.relevance_label === 'high').length;
    const medCount = newsItems.filter(i => i.relevance_label === 'medium').length;
    const lowCount = newsItems.filter(i => i.relevance_label === 'low').length;

    return (
        <div className="p-4 sm:p-6 max-w-[1440px] mx-auto min-h-screen bg-gray-50">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-2xl sm:text-3xl font-black text-gray-950 flex items-center gap-3">
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

                        <div className="border-t border-gray-200 pt-3 mt-3 space-y-2 max-h-[300px] overflow-y-auto">
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

                        {/* Relevance Stats */}
                        {newsItems.length > 0 && (
                            <div className="border-t border-gray-200 pt-4 mt-4">
                                <div className="flex items-center gap-2 mb-3">
                                    <Sparkles size={16} className="text-yellow-500" />
                                    <span className="text-sm font-semibold text-gray-700">Relevance</span>
                                </div>
                                <div className="space-y-1.5">
                                    <div className="flex items-center justify-between text-sm">
                                        <span className="flex items-center gap-2 text-gray-800 font-medium"><span className="w-3 h-3 rounded-full bg-emerald-500"></span> High</span>
                                        <span className="font-bold text-emerald-600">{highCount}</span>
                                    </div>
                                    <div className="flex items-center justify-between text-sm">
                                        <span className="flex items-center gap-2 text-gray-800 font-medium"><span className="w-3 h-3 rounded-full bg-orange-500"></span> Medium</span>
                                        <span className="font-bold text-orange-600">{medCount}</span>
                                    </div>
                                    <div className="flex items-center justify-between text-sm">
                                        <span className="flex items-center gap-2 text-gray-800 font-medium"><span className="w-3 h-3 rounded-full bg-rose-400"></span> Low</span>
                                        <span className="font-bold text-rose-500">{lowCount}</span>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Main Content - News Cards */}
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
                            {/* Brand Filter Pills — powered by global stats from API */}
                            <div className="bg-white rounded-xl shadow-md p-4 mb-4 border border-gray-200">
                                <div className="flex items-center gap-2 mb-3">
                                    <Tag size={15} className="text-indigo-500" />
                                    <span className="text-sm font-semibold text-gray-700">Filter by Brand</span>
                                    {statsScanned > 0 && (
                                        <span className="text-xs text-gray-400 ml-1">
                                            — {statsScanned.toLocaleString()} mentions across all feeds
                                        </span>
                                    )}
                                    <div className="ml-auto flex items-center gap-2">
                                        {brandFilter && (
                                            <button
                                                onClick={() => setBrandFilter(null)}
                                                className="text-xs text-gray-400 hover:text-gray-700 transition-colors flex items-center gap-1"
                                            >
                                                <XCircle size={13} /> Clear
                                            </button>
                                        )}
                                        <button
                                            onClick={fetchGlobalBrandStats}
                                            disabled={loadingStats}
                                            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg transition-all disabled:opacity-60"
                                            title="Refresh stats from all items in DB"
                                        >
                                            {loadingStats
                                                ? <Loader2 size={12} className="animate-spin" />
                                                : <ArrowUpDown size={12} />
                                            }
                                            {loadingStats ? 'Scanning...' : 'Refresh Stats'}
                                        </button>
                                    </div>
                                </div>
                                {loadingStats && brandCounts.length === 0 ? (
                                    <div className="flex items-center gap-2 text-sm text-gray-400 py-2">
                                        <Loader2 size={14} className="animate-spin" />
                                        Scanning all items for brand mentions...
                                    </div>
                                ) : (
                                    <div className="flex flex-wrap gap-2">
                                        {brandCounts.map(([brand, count]) => (
                                            <button
                                                key={brand}
                                                onClick={() => setBrandFilter(brandFilter === brand ? null : brand)}
                                                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all duration-150 border ${brandFilter === brand
                                                    ? 'bg-indigo-600 text-white border-indigo-700 shadow-md scale-105'
                                                    : 'bg-white text-gray-700 border-gray-200 hover:border-indigo-400 hover:bg-indigo-50'
                                                    }`}
                                            >
                                                <span className={`w-1.5 h-1.5 rounded-full ${brandFilter === brand ? 'bg-indigo-200' : 'bg-amber-400'}`} />
                                                {brand}
                                                <span className={`ml-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-bold ${brandFilter === brand
                                                    ? 'bg-indigo-500 text-indigo-100'
                                                    : 'bg-gray-100 text-gray-500'
                                                    }`}>{count}</span>
                                            </button>
                                        ))}
                                    </div>
                                )}
                                {brandFilter && (
                                    <p className="mt-2 text-xs text-gray-500">
                                        Showing {sortedItems.length} of {newsItems.length} loaded items for <strong>{brandFilter}</strong>
                                        {globalBrandStats.length > 0 && (
                                            <span className="text-gray-400"> · {(brandCounts.find(([b]) => b === brandFilter)?.[1] ?? 0).toLocaleString()} total in DB</span>
                                        )}
                                    </p>
                                )}
                            </div>


                            {/* Toolbar: Bulk Actions + Sort */}
                            <div className="bg-white rounded-xl shadow-md p-4 mb-4 flex items-center justify-between border border-gray-200">
                                <div className="flex items-center gap-3">
                                    <input
                                        type="checkbox"
                                        checked={selectedItems.size === sortedItems.length && sortedItems.length > 0}
                                        onChange={toggleSelectAll}
                                        className="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 cursor-pointer"
                                    />
                                    <span className="text-sm font-medium text-gray-700">
                                        {selectedItems.size > 0
                                            ? `${selectedItems.size} selected`
                                            : `${sortedItems.length}${brandFilter ? ` (${newsItems.length} total)` : ''} items`}
                                    </span>
                                </div>
                                <div className="flex items-center gap-3">
                                    {/* Sort toggle */}
                                    <button
                                        onClick={() => setSortBy(sortBy === 'relevance' ? 'date' : 'relevance')}
                                        className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition-all"
                                    >
                                        <ArrowUpDown size={14} />
                                        {sortBy === 'relevance' ? '🎯 By Relevance' : '🕐 By Date'}
                                    </button>

                                    {selectedItems.size > 0 && (
                                        <>
                                            <button
                                                onClick={handleBulkGenerate}
                                                disabled={bulkGenerating || selectedItems.size > 10}
                                                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 transition-all font-medium shadow-sm text-sm"
                                            >
                                                {bulkGenerating ? (
                                                    <><Loader2 className="animate-spin" size={16} /> {bulkProgress || 'Generating...'}</>
                                                ) : (
                                                    <><Wand2 size={16} /> Generate ({selectedItems.size})</>
                                                )}
                                            </button>
                                            <button
                                                onClick={handleBulkDismiss}
                                                disabled={bulkDismissing}
                                                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-all font-medium shadow-sm text-sm"
                                            >
                                                {bulkDismissing ? (
                                                    <><Loader2 className="animate-spin" size={16} /> Dismissing...</>
                                                ) : (
                                                    <><XCircle size={16} /> Dismiss</>
                                                )}
                                            </button>
                                        </>
                                    )}
                                </div>
                            </div>

                            {/* 3-Column Card Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                                {sortedItems.map((item) => {
                                    const statusCfg = STATUS_CONFIG[item.status] || STATUS_CONFIG.new;
                                    const relevance = RELEVANCE_COLORS[item.relevance_label] || RELEVANCE_COLORS.low;
                                    const isExpanded = expandedItem === item.id;

                                    return (
                                        <div
                                            key={item.id}
                                            className={`bg-white rounded-xl shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden border border-gray-100 flex flex-col ${selectedItems.has(item.id) ? 'ring-2 ring-indigo-400 border-indigo-200' : ''
                                                }`}
                                        >
                                            {/* Relevance Color Stripe */}
                                            <div className={`h-1.5 ${relevance.stripe}`} />

                                            {/* Image */}
                                            {item.image_url && (
                                                <div className="relative">
                                                    <img
                                                        src={item.image_url}
                                                        alt={item.title}
                                                        className="w-full h-36 object-cover"
                                                        onError={(e) => {
                                                            e.currentTarget.style.display = 'none';
                                                        }}
                                                    />
                                                    {/* Checkbox overlay */}
                                                    <div className="absolute top-2 left-2">
                                                        <input
                                                            type="checkbox"
                                                            checked={selectedItems.has(item.id)}
                                                            onChange={() => toggleItemSelection(item.id)}
                                                            className="w-5 h-5 text-indigo-600 border-2 border-white rounded focus:ring-indigo-500 cursor-pointer shadow-md"
                                                        />
                                                    </div>
                                                    {/* Score badge overlay */}
                                                    <div className="absolute top-2 right-2">
                                                        <span className={`px-2 py-0.5 text-xs font-bold rounded-full border shadow-sm ${relevance.badge}`}>
                                                            {item.relevance_score}
                                                        </span>
                                                    </div>
                                                </div>
                                            )}

                                            <div className="p-4 flex-1 flex flex-col">
                                                {/* No image — show checkbox + badges inline */}
                                                {!item.image_url && (
                                                    <div className="flex items-center justify-between mb-2">
                                                        <input
                                                            type="checkbox"
                                                            checked={selectedItems.has(item.id)}
                                                            onChange={() => toggleItemSelection(item.id)}
                                                            className="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 cursor-pointer"
                                                        />
                                                        <span className={`px-2 py-0.5 text-xs font-bold rounded-full border ${relevance.badge}`}>
                                                            Score: {item.relevance_score}
                                                        </span>
                                                    </div>
                                                )}

                                                {/* Status + Source badges */}
                                                <div className="flex items-center gap-1.5 mb-2 flex-wrap">
                                                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full bg-gradient-to-r ${statusCfg.color} text-white`}>
                                                        {statusCfg.icon} {statusCfg.label}
                                                    </span>
                                                    <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-orange-50 text-orange-600 border border-orange-200 truncate max-w-[120px]">
                                                        {item.feed_name}
                                                    </span>
                                                </div>

                                                {/* Title with brand highlight */}
                                                <h3
                                                    className="text-sm font-bold text-gray-900 mb-1.5 cursor-pointer hover:text-indigo-600 transition-colors line-clamp-2 leading-tight"
                                                    onClick={() => setExpandedItem(isExpanded ? null : item.id)}
                                                >
                                                    <HighlightedTitle title={item.title} activeBrand={brandFilter} />
                                                </h3>

                                                {/* Excerpt */}
                                                <p className="text-xs text-gray-500 leading-relaxed line-clamp-2 mb-3 flex-1">
                                                    {item.excerpt || 'No preview available'}
                                                </p>

                                                {/* Meta row */}
                                                <div className="flex items-center justify-between text-[11px] text-gray-400 mb-3">
                                                    <div className="flex items-center gap-1">
                                                        <Clock size={12} />
                                                        {formatDate(item.published_at || item.created_at)}
                                                    </div>
                                                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${relevance.badge}`}>
                                                        {relevance.text}
                                                    </span>
                                                </div>

                                                {/* Actions */}
                                                <div className="flex gap-1.5 mt-auto">
                                                    {item.status !== 'generated' && item.status !== 'generating' && (
                                                        <button
                                                            onClick={() => handleGenerate(item.id)}
                                                            disabled={generatingId === item.id}
                                                            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 transition-all text-xs font-medium shadow-sm"
                                                        >
                                                            {generatingId === item.id ? (
                                                                <Loader2 className="animate-spin" size={14} />
                                                            ) : (
                                                                <><Wand2 size={14} /> Generate</>
                                                            )}
                                                        </button>
                                                    )}

                                                    {item.status === 'generated' && (
                                                        <span className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-green-100 text-green-700 rounded-lg text-xs font-medium">
                                                            <CheckCircle2 size={14} /> Created
                                                        </span>
                                                    )}

                                                    {item.source_url && (
                                                        <a
                                                            href={item.source_url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="flex items-center justify-center p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-all"
                                                            title="Open Original"
                                                        >
                                                            <ExternalLink size={14} />
                                                        </a>
                                                    )}

                                                    {/* Heart / Favorite button */}
                                                    <button
                                                        onClick={() => handleToggleFavorite(item.id)}
                                                        className={`flex items-center justify-center p-2 rounded-lg transition-all ${item.is_favorite
                                                            ? 'bg-red-50 text-red-500 hover:bg-red-100'
                                                            : 'text-gray-300 hover:bg-red-50 hover:text-red-400'
                                                            }`}
                                                        title={item.is_favorite ? 'Remove from favorites (saved 60 days)' : 'Save as interesting — kept 60 days for ML'}
                                                    >
                                                        <Heart
                                                            size={14}
                                                            className={item.is_favorite ? 'fill-current' : ''}
                                                        />
                                                    </button>

                                                    {item.status !== 'dismissed' && item.status !== 'generated' && (
                                                        <button
                                                            onClick={() => handleDismiss(item.id)}
                                                            className="flex items-center justify-center p-2 text-red-500 hover:bg-red-50 rounded-lg transition-all"
                                                            title="Dismiss"
                                                        >
                                                            <XCircle size={14} />
                                                        </button>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Expanded Content */}
                                            {isExpanded && (
                                                <div className="border-t border-gray-100 p-4 bg-gray-50">
                                                    <div className="flex items-center gap-2 mb-2">
                                                        <Eye size={14} className="text-indigo-600" />
                                                        <span className="text-xs font-semibold text-gray-600">Full Content</span>
                                                    </div>
                                                    <div
                                                        className="prose prose-sm max-w-none text-gray-700 text-xs max-h-[200px] overflow-y-auto"
                                                        dangerouslySetInnerHTML={{ __html: sanitizeHtml(item.content || '<p>No content available</p>') }}
                                                    />
                                                </div>
                                            )}
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

