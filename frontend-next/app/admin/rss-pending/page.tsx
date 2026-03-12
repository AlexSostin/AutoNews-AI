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
    Brain,
    Combine,
    SkipForward,
    Bookmark,
    ChevronDown,
    ChevronUp,
    Zap,
    BarChart3,
    RefreshCw,
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
    llm_score: number | null;       // gpt-4o-mini score stored in DB
    llm_score_reason: string;       // short reason phrase
    source_count: number;           // how many feeds covered this story
}

// ----------------------------------------------------------------
// Smart RSS Curator types
// ----------------------------------------------------------------
interface CuratorItem {
    id: number;
    title: string;
    excerpt: string;
    source_url: string;
    image_url: string;
    feed_name: string;
    published_at: string | null;
    brand: string | null;
    score: number;
    score_breakdown: Record<string, number>;
    has_specs: boolean;
    duplicate_of: number | null;
    source_count: number;
    llm_score: number | null;
    is_favorite: boolean;
    ai_summary: string;
}

interface CuratorCluster {
    id: string;
    topic: string;
    items: CuratorItem[];
    max_score: number;
    merge_suggested: boolean;
    merge_reason: string;
}

interface CuratorResult {
    success: boolean;
    items_scanned: number;
    clusters: CuratorCluster[];
    stats: {
        total_clusters: number;
        recommended: number;
        skippable: number;
        duplicates_found: number;
    };
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

    // Smart Curator state
    const [curatorResults, setCuratorResults] = useState<CuratorResult | null>(null);
    const [curatorLoading, setCuratorLoading] = useState(false);
    const [curatorOpen, setCuratorOpen] = useState(false);
    const [curatorDeciding, setCuratorDeciding] = useState<string | null>(null); // cluster_id being decided on
    const [merging, setMerging] = useState<string | null>(null);
    const [expandedCluster, setExpandedCluster] = useState<string | null>(null);
    const [statsScanned, setStatsScanned] = useState<number>(0);
    const [generateAllLoading, setGenerateAllLoading] = useState(false);
    const [generateAllProgress, setGenerateAllProgress] = useState('');

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

    // ----------------------------------------------------------------
    // Smart Curator handlers
    // ----------------------------------------------------------------

    const handleCurate = async () => {
        setCuratorLoading(true);
        setCuratorOpen(true);
        try {
            const res = await api.post('/rss-news-items/curate/', {
                days: 7,
                include_ai_summary: true,
                provider: 'gemini',
            });
            setCuratorResults(res.data);
        } catch (error: any) {
            logCaughtError('curator_run', error);
            toast.error(`Curator failed: ${error.response?.data?.error || error.message}`);
        } finally {
            setCuratorLoading(false);
        }
    };

    const handleCuratorDecision = async (
        itemId: number,
        decision: 'generate' | 'skip' | 'save_later',
        clusterId: string,
        score: number,
        brand: string,
    ) => {
        setCuratorDeciding(`${clusterId}_${itemId}_${decision}`);
        try {
            const res = await api.post('/rss-news-items/curator_decision/', {
                item_id: itemId,
                decision,
                cluster_id: clusterId,
                score,
                brand,
            });

            if (decision === 'generate' && res.data.generated_article_id) {
                toast.success(`✅ Article generated! (Pending #${res.data.generated_article_id})`);
            } else if (decision === 'skip') {
                toast.success('⏭️ Skipped — ML will remember this preference');
            } else if (decision === 'save_later') {
                toast.success('📌 Saved for later');
            }

            // Remove item from curator results
            if (curatorResults) {
                const updated = {
                    ...curatorResults,
                    clusters: curatorResults.clusters.map(c => ({
                        ...c,
                        items: c.items.filter(i => i.id !== itemId),
                    })).filter(c => c.items.length > 0),
                };
                setCuratorResults(updated);
            }

            // Refresh main list
            fetchNewsItems();
        } catch (error: any) {
            logCaughtError('curator_decision', error);
            toast.error(`Decision failed: ${error.response?.data?.error || error.message}`);
        } finally {
            setCuratorDeciding(null);
        }
    };

    const handleMergeGenerate = async (ids: number[], clusterId: string) => {
        setMerging(clusterId);
        try {
            const res = await api.post('/rss-news-items/merge_generate/', {
                ids,
                provider: 'gemini',
            });
            toast.success(`🔗 Roundup created: ${res.data.title} (${res.data.word_count} words)`);

            // Remove merged items from curator results
            if (curatorResults) {
                const updated = {
                    ...curatorResults,
                    clusters: curatorResults.clusters.filter(c => c.id !== clusterId),
                };
                setCuratorResults(updated);
            }

            fetchNewsItems();
        } catch (error: any) {
            logCaughtError('merge_generate', error);
            toast.error(`Merge failed: ${error.response?.data?.error || error.message}`);
        } finally {
            setMerging(null);
        }
    };

    const getScoreColor = (score: number) => {
        if (score >= 70) return 'bg-emerald-500 text-white';
        if (score >= 50) return 'bg-amber-500 text-white';
        if (score >= 30) return 'bg-orange-400 text-white';
        return 'bg-gray-400 text-white';
    };

    // Generate All Recommended — sequential generation of top items from each cluster
    const handleGenerateAllRecommended = async () => {
        if (!curatorResults) return;
        const recommended = curatorResults.clusters.filter(c => c.max_score >= 50 && !c.items[0]?.duplicate_of);
        if (recommended.length === 0) {
            toast.error('No recommended clusters to generate');
            return;
        }
        setGenerateAllLoading(true);
        let success = 0;
        let failed = 0;
        for (let i = 0; i < recommended.length; i++) {
            const cluster = recommended[i];
            const topItem = cluster.items[0];
            if (!topItem) continue;
            setGenerateAllProgress(`${i + 1}/${recommended.length}: ${topItem.title.slice(0, 40)}...`);
            try {
                await api.post('/rss-news-items/curator_decision/', {
                    item_id: topItem.id,
                    decision: 'generate',
                    cluster_id: cluster.id,
                    score: topItem.score,
                    brand: topItem.brand || '',
                });
                success++;
                // Remove from curator results
                if (curatorResults) {
                    setCuratorResults(prev => prev ? {
                        ...prev,
                        clusters: prev.clusters.filter(c => c.id !== cluster.id),
                    } : null);
                }
            } catch {
                failed++;
            }
        }
        setGenerateAllLoading(false);
        setGenerateAllProgress('');
        fetchNewsItems();
        toast.success(`✅ Generated ${success} articles${failed > 0 ? `, ${failed} failed` : ''}`);
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
            <div className="mb-6 flex items-start justify-between">
                <div>
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
                <div className="flex items-center gap-2">
                    {/* If we already have results, show a Refresh button separately */}
                    {curatorResults && !curatorLoading && (
                        <button
                            onClick={handleCurate}
                            className="flex items-center gap-1.5 px-3 py-2.5 bg-white border border-violet-300 text-violet-600 rounded-xl hover:bg-violet-50 transition-all font-medium text-sm"
                            title="Re-analyze with AI (costs tokens)"
                        >
                            <RefreshCw size={14} />
                            Refresh
                        </button>
                    )}
                    <button
                        onClick={() => {
                            // If results already exist, just toggle panel visibility (free)
                            if (curatorResults && !curatorLoading) {
                                setCuratorOpen(prev => !prev);
                            } else {
                                handleCurate();
                            }
                        }}
                        disabled={curatorLoading}
                        className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-violet-600 to-purple-600 text-white rounded-xl hover:from-violet-700 hover:to-purple-700 disabled:opacity-60 transition-all font-bold shadow-lg hover:shadow-xl text-sm"
                    >
                        {curatorLoading ? (
                            <><Loader2 className="animate-spin" size={18} /> Analyzing...</>
                        ) : curatorResults ? (
                            <><Brain size={18} /> {curatorOpen ? 'Hide Curator' : 'Show Curator'}</>
                        ) : (
                            <><Brain size={18} /> 🤖 Analyze Feed</>
                        )}
                    </button>
                </div>
            </div>

            {/* ═══════ Smart Curator Panel ═══════ */}
            {curatorOpen && (
                <div className="mb-6 bg-gradient-to-br from-violet-50 to-purple-50 rounded-2xl shadow-xl border border-violet-200 overflow-hidden">
                    {/* Curator Header */}
                    <div
                        className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-violet-100/50 transition-colors"
                        onClick={() => setCuratorOpen(prev => !prev)}
                    >
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl shadow-md">
                                <Brain size={20} className="text-white" />
                            </div>
                            <div>
                                <h2 className="text-lg font-bold text-gray-900">Smart Curator</h2>
                                {curatorResults && !curatorLoading && (
                                    <p className="text-sm text-gray-500">
                                        Scanned {curatorResults.items_scanned} items → {curatorResults.stats.total_clusters} clusters → <span className="font-semibold text-emerald-600">{curatorResults.stats.recommended} recommended</span>
                                    </p>
                                )}
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            {curatorResults && (
                                <div className="flex gap-2 text-xs">
                                    <span className="px-2.5 py-1 bg-emerald-100 text-emerald-700 rounded-full font-bold flex items-center gap-1">
                                        <Zap size={12} /> {curatorResults.stats.recommended} rec
                                    </span>
                                    <span className="px-2.5 py-1 bg-gray-100 text-gray-600 rounded-full font-medium">
                                        {curatorResults.stats.skippable} skip
                                    </span>
                                    {curatorResults.stats.duplicates_found > 0 && (
                                        <span className="px-2.5 py-1 bg-red-100 text-red-600 rounded-full font-medium">
                                            {curatorResults.stats.duplicates_found} dup
                                        </span>
                                    )}
                                </div>
                            )}
                            {/* Generate All Recommended button */}
                            {curatorResults && curatorResults.stats.recommended > 0 && (
                                <button
                                    onClick={(e) => { e.stopPropagation(); handleGenerateAllRecommended(); }}
                                    disabled={generateAllLoading}
                                    className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-emerald-500 to-emerald-600 text-white rounded-lg text-xs font-bold hover:from-emerald-600 hover:to-emerald-700 disabled:opacity-60 transition-all shadow-sm"
                                    title="Generate articles from all recommended clusters"
                                >
                                    {generateAllLoading ? (
                                        <><Loader2 className="animate-spin" size={12} /> {generateAllProgress}</>
                                    ) : (
                                        <><Wand2 size={12} /> Generate All ({curatorResults.stats.recommended})</>
                                    )}
                                </button>
                            )}
                            <button
                                onClick={(e) => { e.stopPropagation(); setCuratorOpen(false); }}
                                className="text-gray-400 hover:text-gray-600 transition-colors"
                            >
                                <XCircle size={20} />
                            </button>
                        </div>
                    </div>

                    {/* Loading State */}
                    {curatorLoading && (
                        <div className="px-6 py-12 flex flex-col items-center gap-4">
                            <div className="relative">
                                <div className="w-16 h-16 border-4 border-violet-200 rounded-full animate-spin border-t-violet-600" />
                                <Brain className="text-violet-600 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" size={24} />
                            </div>
                            <p className="text-sm text-gray-500 font-medium">Analyzing RSS items with AI...</p>
                            <p className="text-xs text-gray-400">Clustering → Scoring → Generating summaries</p>
                        </div>
                    )}

                    {/* Curator Clusters */}
                    {curatorResults && !curatorLoading && (
                        <div className="px-6 pb-6 space-y-3 max-h-[600px] overflow-y-auto">
                            {curatorResults.clusters.length === 0 ? (
                                <p className="text-center text-gray-500 py-8">No pending items to analyze.</p>
                            ) : (
                                curatorResults.clusters.map((cluster) => {
                                    const isExpCluster = expandedCluster === cluster.id;
                                    const topItem = cluster.items[0];
                                    return (
                                        <div
                                            key={cluster.id}
                                            className={`bg-white rounded-xl border transition-all ${
                                                cluster.max_score >= 60
                                                    ? 'border-emerald-200 shadow-md'
                                                    : 'border-gray-200 shadow-sm'
                                            }`}
                                        >
                                            {/* Cluster Header */}
                                            <div
                                                className="px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-gray-50/80 transition-colors"
                                                onClick={() => setExpandedCluster(isExpCluster ? null : cluster.id)}
                                            >
                                                {/* Image + Score */}
                                                <div className="flex items-center gap-2">
                                                    {topItem?.image_url && (
                                                        <img
                                                            src={topItem.image_url}
                                                            alt=""
                                                            className="w-10 h-10 rounded-lg object-cover flex-shrink-0"
                                                            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                                                        />
                                                    )}
                                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-black flex-shrink-0 ${getScoreColor(cluster.max_score)}`} title={`Score: ${cluster.max_score}`}>
                                                        {cluster.max_score}
                                                    </div>
                                                </div>

                                                {/* Topic + Info */}
                                                <div className="flex-1 min-w-0">
                                                    <h3 className="font-bold text-gray-900 text-sm truncate">{cluster.topic || topItem?.title || 'Unknown'}</h3>
                                                    <div className="flex items-center gap-2 mt-0.5">
                                                        <span className="text-xs text-gray-500">{cluster.items.length} item{cluster.items.length > 1 ? 's' : ''}</span>
                                                        {topItem?.brand && (
                                                            <span className="text-xs px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded font-semibold">{topItem.brand}</span>
                                                        )}
                                                        {cluster.merge_suggested && cluster.items.length >= 2 && (
                                                            <span className="text-xs px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded font-semibold flex items-center gap-0.5">
                                                                <Combine size={10} /> Merge
                                                            </span>
                                                        )}
                                                        {topItem?.duplicate_of && (
                                                            <span className="text-xs px-1.5 py-0.5 bg-red-100 text-red-600 rounded font-semibold">⚠ Duplicate</span>
                                                        )}
                                                    </div>
                                                </div>

                                                {/* Quick Actions */}
                                                <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                                                    {topItem && !topItem.duplicate_of && (
                                                        <button
                                                            onClick={() => handleCuratorDecision(topItem.id, 'generate', cluster.id, topItem.score, topItem.brand || '')}
                                                            disabled={curatorDeciding === `${cluster.id}_${topItem.id}_generate`}
                                                            className="flex items-center gap-1 px-3 py-1.5 bg-gradient-to-r from-emerald-500 to-emerald-600 text-white rounded-lg text-xs font-bold hover:from-emerald-600 hover:to-emerald-700 disabled:opacity-50 transition-all shadow-sm"
                                                        >
                                                            {curatorDeciding === `${cluster.id}_${topItem.id}_generate` ? (
                                                                <Loader2 className="animate-spin" size={12} />
                                                            ) : (
                                                                <><Wand2 size={12} /> Generate</>
                                                            )}
                                                        </button>
                                                    )}
                                                    {cluster.merge_suggested && cluster.items.length >= 2 && (
                                                        <button
                                                            onClick={() => handleMergeGenerate(cluster.items.map(i => i.id), cluster.id)}
                                                            disabled={merging === cluster.id}
                                                            className="flex items-center gap-1 px-3 py-1.5 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-lg text-xs font-bold hover:from-purple-600 hover:to-purple-700 disabled:opacity-50 transition-all shadow-sm"
                                                        >
                                                            {merging === cluster.id ? <Loader2 className="animate-spin" size={12} /> : <><Combine size={12} /> Merge</>}
                                                        </button>
                                                    )}
                                                    <button
                                                        onClick={() => topItem && handleCuratorDecision(topItem.id, 'skip', cluster.id, topItem.score, topItem.brand || '')}
                                                        disabled={!topItem || curatorDeciding === `${cluster.id}_${topItem?.id}_skip`}
                                                        className="flex items-center gap-1 px-2 py-1.5 text-gray-500 hover:bg-gray-100 rounded-lg text-xs font-medium transition-all"
                                                    >
                                                        <SkipForward size={12} /> Skip
                                                    </button>
                                                </div>

                                                {isExpCluster ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
                                            </div>

                                            {/* AI Summary */}
                                            {topItem?.ai_summary && (
                                                <div className="px-4 pb-2">
                                                    <p className="text-xs text-violet-600 italic pl-[52px]">💡 {topItem.ai_summary}</p>
                                                </div>
                                            )}

                                            {/* Expanded: all items in cluster */}
                                            {isExpCluster && (
                                                <div className="border-t border-gray-100 px-4 py-3 space-y-2 bg-gray-50/50">
                                                    {cluster.items.map((ci) => (
                                                        <div key={ci.id} className="flex items-start gap-3 py-2">
                                                            <div
                                                                className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-black flex-shrink-0 ${getScoreColor(ci.score)}`}
                                                            >
                                                                {ci.score}
                                                            </div>
                                                            <div className="flex-1 min-w-0">
                                                                <p className="text-sm font-semibold text-gray-800 truncate">{ci.title}</p>
                                                                <div className="flex items-center gap-2 mt-0.5">
                                                                    <span className="text-xs text-gray-400">{ci.feed_name}</span>
                                                                    {ci.brand && <span className="text-xs px-1 py-0.5 bg-amber-50 text-amber-600 rounded">{ci.brand}</span>}
                                                                    {ci.duplicate_of && <span className="text-xs text-red-500">⚠ dup of #{ci.duplicate_of}</span>}
                                                                    {Object.entries(ci.score_breakdown).map(([k, v]) => (
                                                                        <span key={k} className={`text-[10px] px-1 py-0.5 rounded ${
                                                                            (v as number) > 0 ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-500'
                                                                        }`}>
                                                                            {k}: {v > 0 ? '+' : ''}{v as number}
                                                                        </span>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                                                                {!ci.duplicate_of && (
                                                                    <button
                                                                        onClick={() => handleCuratorDecision(ci.id, 'generate', cluster.id, ci.score, ci.brand || '')}
                                                                        disabled={curatorDeciding === `${cluster.id}_${ci.id}_generate`}
                                                                        className="px-2 py-1 bg-emerald-100 text-emerald-700 rounded text-xs font-semibold hover:bg-emerald-200 disabled:opacity-50 transition-all"
                                                                    >
                                                                        {curatorDeciding === `${cluster.id}_${ci.id}_generate` ? <Loader2 className="animate-spin" size={10} /> : 'Gen'}
                                                                    </button>
                                                                )}
                                                                <button
                                                                    onClick={() => handleCuratorDecision(ci.id, 'skip', cluster.id, ci.score, ci.brand || '')}
                                                                    className="px-2 py-1 text-gray-400 hover:bg-gray-100 rounded text-xs transition-all"
                                                                >
                                                                    Skip
                                                                </button>
                                                                {ci.source_url && (
                                                                    <a href={ci.source_url} target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-gray-600">
                                                                        <ExternalLink size={12} />
                                                                    </a>
                                                                )}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })
                            )}
                        </div>
                    )}
                </div>
            )}

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
                                                    {/* 🔥 Hot Story badge — shown when 3+ sources cover the same story */}
                                                    {(item.source_count ?? 1) >= 3 && (
                                                        <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-red-50 text-red-600 border border-red-200 flex items-center gap-0.5">
                                                            🔥 Hot · {item.source_count} sources
                                                        </span>
                                                    )}
                                                    {/* LLM score reason pill */}
                                                    {item.llm_score_reason && item.llm_score_reason !== 'keyword-fallback' && (
                                                        <span className="px-2 py-0.5 text-[10px] font-medium rounded-full bg-indigo-50 text-indigo-600 border border-indigo-100 truncate max-w-[140px]" title={item.llm_score_reason}>
                                                            ✦ {item.llm_score_reason}
                                                        </span>
                                                    )}
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

