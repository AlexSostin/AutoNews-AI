'use client';

import { useState, useEffect, useCallback } from 'react';
import { authenticatedFetch } from '@/lib/authenticatedFetch';
import toast from 'react-hot-toast';
import {
    FlaskConical,
    Trophy,
    BarChart3,
    MousePointerClick,
    Eye,
    ExternalLink,
    Loader2,
    RefreshCw,
    Crown,
    TrendingUp,
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface TitleVariant {
    id: number;
    variant: string;
    title: string;
    impressions: number;
    clicks: number;
    ctr: number;
    is_winner: boolean;
}

interface ABTestData {
    article_id: number;
    article_slug: string;
    original_title: string;
    variants: TitleVariant[];
    total_impressions: number;
    total_clicks: number;
}

interface Article {
    id: number;
    slug: string;
    title: string;
    is_published: boolean;
    created_at: string;
    views: number;
}

export default function ABTestingPage() {
    const [articles, setArticles] = useState<Article[]>([]);
    const [abTests, setAbTests] = useState<Record<string, ABTestData>>({});
    const [loading, setLoading] = useState(true);
    const [expandedSlug, setExpandedSlug] = useState<string | null>(null);
    const [pickingWinner, setPickingWinner] = useState<string | null>(null);

    const fetchArticlesWithAB = useCallback(async () => {
        setLoading(true);
        try {
            // Fetch published articles
            const res = await authenticatedFetch(
                `${API_BASE}/articles/?page_size=100&ordering=-created_at`
            );
            const data = await res.json();
            const allArticles: Article[] = data.results || [];

            // Check each article for A/B test data
            const tests: Record<string, ABTestData> = {};
            await Promise.all(
                allArticles.map(async (article) => {
                    try {
                        const abRes = await authenticatedFetch(
                            `${API_BASE}/articles/${article.slug}/ab-stats/`
                        );
                        if (abRes.ok) {
                            const abData: ABTestData = await abRes.json();
                            if (abData.variants && abData.variants.length > 0) {
                                tests[article.slug] = abData;
                            }
                        }
                    } catch {
                        // No A/B test for this article
                    }
                })
            );

            setArticles(allArticles.filter((a) => tests[a.slug]));
            setAbTests(tests);
        } catch (err) {
            console.error('Failed to fetch A/B data:', err);
            toast.error('Failed to load A/B test data');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchArticlesWithAB();
    }, [fetchArticlesWithAB]);

    const pickWinner = async (slug: string, variant: string) => {
        setPickingWinner(`${slug}-${variant}`);
        try {
            const res = await authenticatedFetch(
                `${API_BASE}/articles/${slug}/ab-pick-winner/`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ variant }),
                }
            );
            const data = await res.json();
            if (res.ok) {
                toast.success(`🏆 Winner picked: Variant ${variant}!`);
                fetchArticlesWithAB(); // Refresh
            } else {
                toast.error(data.error || 'Failed to pick winner');
            }
        } catch {
            toast.error('Network error');
        } finally {
            setPickingWinner(null);
        }
    };

    const getVariantColor = (variant: string) => {
        switch (variant) {
            case 'A': return 'bg-blue-100 text-blue-800 border-blue-300';
            case 'B': return 'bg-emerald-100 text-emerald-800 border-emerald-300';
            case 'C': return 'bg-purple-100 text-purple-800 border-purple-300';
            default: return 'bg-gray-100 text-gray-800 border-gray-300';
        }
    };

    const getBestVariant = (variants: TitleVariant[]) => {
        const withImpressions = variants.filter((v) => v.impressions >= 10);
        if (withImpressions.length === 0) return null;
        return withImpressions.reduce((best, v) => (v.ctr > best.ctr ? v : best));
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
                <span className="ml-3 text-gray-500">Loading A/B tests...</span>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <FlaskConical className="w-7 h-7 text-indigo-600" />
                        A/B Title Testing
                    </h1>
                    <p className="text-gray-500 mt-1">
                        {articles.length} article{articles.length !== 1 ? 's' : ''} with active tests
                    </p>
                </div>
                <button
                    onClick={fetchArticlesWithAB}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-700 text-white border border-gray-600 rounded-lg hover:bg-gray-600 transition-colors"
                >
                    <RefreshCw className="w-4 h-4" />
                    Refresh
                </button>
            </div>

            {articles.length === 0 ? (
                <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                    <FlaskConical className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900">No A/B Tests Yet</h3>
                    <p className="text-gray-500 mt-2">
                        A/B title variants are automatically created when articles are generated.
                        <br />
                        Generate a new article to start testing!
                    </p>
                </div>
            ) : (
                <div className="space-y-4">
                    {articles.map((article) => {
                        const test = abTests[article.slug];
                        if (!test) return null;
                        const isExpanded = expandedSlug === article.slug;
                        const bestVariant = getBestVariant(test.variants);
                        const hasWinner = test.variants.some((v) => v.is_winner);

                        return (
                            <div
                                key={article.slug}
                                className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
                            >
                                {/* Article Header */}
                                <button
                                    onClick={() => setExpandedSlug(isExpanded ? null : article.slug)}
                                    className="w-full text-left p-5 flex items-center justify-between hover:bg-gray-50 transition-colors"
                                >
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            {hasWinner && (
                                                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-100 text-amber-800 text-xs font-medium rounded-full">
                                                    <Crown className="w-3 h-3" /> Winner Selected
                                                </span>
                                            )}
                                            {bestVariant && !hasWinner && test.total_impressions >= 30 && (
                                                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-800 text-xs font-medium rounded-full">
                                                    <TrendingUp className="w-3 h-3" /> Leading: {bestVariant.variant}
                                                </span>
                                            )}
                                        </div>
                                        <h3 className="font-semibold text-gray-900 truncate">
                                            {article.title}
                                        </h3>
                                        <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                                            <span className="flex items-center gap-1">
                                                <Eye className="w-3.5 h-3.5" />
                                                {test.total_impressions.toLocaleString()} impressions
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <MousePointerClick className="w-3.5 h-3.5" />
                                                {test.total_clicks.toLocaleString()} clicks
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <BarChart3 className="w-3.5 h-3.5" />
                                                {test.variants.length} variants
                                            </span>
                                        </div>
                                    </div>
                                    <svg
                                        className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        stroke="currentColor"
                                    >
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                </button>

                                {/* Expanded Details */}
                                {isExpanded && (
                                    <div className="border-t border-gray-200 p-5 bg-gray-50">
                                        <div className="space-y-3">
                                            {test.variants.map((v) => {
                                                const isLeading = bestVariant?.variant === v.variant && !hasWinner && test.total_impressions >= 30;

                                                return (
                                                    <div
                                                        key={v.id}
                                                        className={`flex items-start gap-4 p-4 rounded-lg border ${v.is_winner
                                                            ? 'bg-amber-50 border-amber-300 ring-2 ring-amber-200'
                                                            : isLeading
                                                                ? 'bg-green-50 border-green-200'
                                                                : 'bg-white border-gray-200'
                                                            }`}
                                                    >
                                                        {/* Variant Badge */}
                                                        <span
                                                            className={`inline-flex items-center justify-center w-8 h-8 rounded-full font-bold text-sm border ${getVariantColor(v.variant)}`}
                                                        >
                                                            {v.variant}
                                                        </span>

                                                        {/* Title & Stats */}
                                                        <div className="flex-1 min-w-0">
                                                            <div className="flex items-center gap-2">
                                                                <p className="font-medium text-gray-900">
                                                                    {v.title}
                                                                </p>
                                                                {v.is_winner && (
                                                                    <Trophy className="w-4 h-4 text-amber-500 flex-shrink-0" />
                                                                )}
                                                            </div>
                                                            <div className="flex items-center gap-4 mt-1.5 text-sm text-gray-500">
                                                                <span>{v.impressions.toLocaleString()} views</span>
                                                                <span>{v.clicks.toLocaleString()} clicks</span>
                                                                <span className={`font-semibold ${v.ctr > 0 ? 'text-indigo-600' : ''}`}>
                                                                    {v.ctr}% CTR
                                                                </span>
                                                                {v.variant === 'A' && (
                                                                    <span className="text-xs text-gray-400">(original)</span>
                                                                )}
                                                            </div>
                                                        </div>

                                                        {/* Actions */}
                                                        {!hasWinner && (
                                                            <button
                                                                onClick={() => pickWinner(article.slug, v.variant)}
                                                                disabled={pickingWinner === `${article.slug}-${v.variant}`}
                                                                className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors flex-shrink-0"
                                                            >
                                                                {pickingWinner === `${article.slug}-${v.variant}` ? (
                                                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                                ) : (
                                                                    <Trophy className="w-3.5 h-3.5" />
                                                                )}
                                                                Pick Winner
                                                            </button>
                                                        )}
                                                    </div>
                                                );
                                            })}
                                        </div>

                                        {/* CTR Bar Chart */}
                                        {test.total_impressions > 0 && (
                                            <div className="mt-4 pt-4 border-t border-gray-200">
                                                <h4 className="text-sm font-medium text-gray-700 mb-2">CTR Comparison</h4>
                                                <div className="space-y-2">
                                                    {test.variants.map((v) => {
                                                        const maxCtr = Math.max(...test.variants.map((x) => x.ctr), 1);
                                                        const width = maxCtr > 0 ? (v.ctr / maxCtr) * 100 : 0;
                                                        return (
                                                            <div key={v.id} className="flex items-center gap-2">
                                                                <span className="w-6 text-sm font-medium text-gray-500">{v.variant}</span>
                                                                <div className="flex-1 bg-gray-200 rounded-full h-5 overflow-hidden">
                                                                    <div
                                                                        className={`h-full rounded-full transition-all duration-500 ${v.variant === 'A'
                                                                            ? 'bg-blue-500'
                                                                            : v.variant === 'B'
                                                                                ? 'bg-emerald-500'
                                                                                : 'bg-purple-500'
                                                                            }`}
                                                                        style={{ width: `${Math.max(width, 2)}%` }}
                                                                    />
                                                                </div>
                                                                <span className="w-16 text-sm text-gray-600 text-right">{v.ctr}%</span>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </div>
                                        )}

                                        {/* Min data warning */}
                                        {test.total_impressions < 30 && (
                                            <p className="mt-3 text-xs text-amber-600 bg-amber-50 p-2 rounded-lg">
                                                ⚠️ Need at least 30 total impressions for reliable CTR data.
                                                Currently: {test.total_impressions}
                                            </p>
                                        )}

                                        {/* Link to article */}
                                        <a
                                            href={`/articles/${article.slug}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="inline-flex items-center gap-1 mt-3 text-sm text-indigo-600 hover:text-indigo-800"
                                        >
                                            <ExternalLink className="w-3.5 h-3.5" />
                                            View Article
                                        </a>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
