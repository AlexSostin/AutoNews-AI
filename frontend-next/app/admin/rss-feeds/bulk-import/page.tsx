'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Upload, CheckCircle, XCircle, AlertCircle, Loader2, RefreshCw } from 'lucide-react';
import api from '@/lib/api';

type FeedStatus = 'pending' | 'testing' | 'importing' | 'success' | 'duplicate' | 'error';

interface FeedRow {
    url: string;
    status: FeedStatus;
    name?: string;
    website_url?: string;
    description?: string;
    entries_count?: number;
    error?: string;
}

export default function BulkImportPage() {
    const [rawUrls, setRawUrls] = useState('');
    const [feeds, setFeeds] = useState<FeedRow[]>([]);
    const [running, setRunning] = useState(false);
    const [sourceType, setSourceType] = useState('media');
    const [done, setDone] = useState(false);

    const parseUrls = (text: string): string[] => {
        return text
            .split('\n')
            .map(l => l.trim())
            .filter(l => l.length > 0 && (l.startsWith('http://') || l.startsWith('https://')));
    };

    const updateRow = (idx: number, patch: Partial<FeedRow>) => {
        setFeeds(prev => prev.map((f, i) => i === idx ? { ...f, ...patch } : f));
    };

    const handleImport = async () => {
        const urls = parseUrls(rawUrls);
        if (urls.length === 0) {
            alert('No valid URLs found. Make sure each URL is on its own line and starts with http:// or https://');
            return;
        }

        const rows: FeedRow[] = urls.map(url => ({ url, status: 'pending' }));
        setFeeds(rows);
        setRunning(true);
        setDone(false);

        for (let i = 0; i < rows.length; i++) {
            // --- Step 1: Test feed ---
            updateRow(i, { status: 'testing' });
            let feedMeta: { title?: string; link?: string; description?: string } = {};
            let entries_count = 0;

            try {
                const testRes = await api.post('/rss-feeds/test_feed/', { feed_url: rows[i].url });
                feedMeta = testRes.data.feed_meta || {};
                entries_count = testRes.data.entries_count || 0;
            } catch {
                updateRow(i, { status: 'error', error: 'Feed unreachable or invalid' });
                continue;
            }

            const name = feedMeta.title || new URL(rows[i].url).hostname.replace('www.', '');

            // --- Step 2: Create feed ---
            updateRow(i, { status: 'importing', name, website_url: feedMeta.link, description: feedMeta.description, entries_count });

            try {
                await api.post('/rss-feeds/', {
                    feed_url: rows[i].url,
                    name,
                    website_url: feedMeta.link || '',
                    description: feedMeta.description || '',
                    source_type: sourceType,
                    is_enabled: true,
                    auto_publish: false,
                    default_category: null,
                });
                updateRow(i, { status: 'success' });
            } catch (err: any) {
                const msg = err?.response?.data?.feed_url?.[0] || err?.response?.data?.detail || '';
                if (msg.toLowerCase().includes('already') || msg.toLowerCase().includes('unique') || err?.response?.status === 400) {
                    updateRow(i, { status: 'duplicate', name, error: 'Already in database' });
                } else {
                    updateRow(i, { status: 'error', name, error: msg || 'Failed to save' });
                }
            }

            // Small delay so we don't hammer the server
            await new Promise(r => setTimeout(r, 200));
        }

        setRunning(false);
        setDone(true);
    };

    const stats = {
        total: feeds.length,
        success: feeds.filter(f => f.status === 'success').length,
        duplicate: feeds.filter(f => f.status === 'duplicate').length,
        error: feeds.filter(f => f.status === 'error').length,
        pending: feeds.filter(f => ['pending', 'testing', 'importing'].includes(f.status)).length,
    };

    const statusIcon = (status: FeedStatus) => {
        switch (status) {
            case 'success': return <CheckCircle className="text-green-500 flex-shrink-0" size={18} />;
            case 'duplicate': return <AlertCircle className="text-yellow-500 flex-shrink-0" size={18} />;
            case 'error': return <XCircle className="text-red-500 flex-shrink-0" size={18} />;
            case 'testing':
            case 'importing': return <Loader2 className="text-blue-500 animate-spin flex-shrink-0" size={18} />;
            default: return <div className="w-4 h-4 rounded-full border-2 border-gray-300 flex-shrink-0" />;
        }
    };

    const statusLabel = (f: FeedRow) => {
        switch (f.status) {
            case 'success': return <span className="text-green-700 text-xs font-medium">✓ Imported{f.entries_count ? ` (${f.entries_count} entries)` : ''}</span>;
            case 'duplicate': return <span className="text-yellow-700 text-xs">Already exists</span>;
            case 'error': return <span className="text-red-600 text-xs">{f.error || 'Error'}</span>;
            case 'testing': return <span className="text-blue-600 text-xs">Testing…</span>;
            case 'importing': return <span className="text-blue-600 text-xs">Saving…</span>;
            default: return <span className="text-gray-400 text-xs">Waiting</span>;
        }
    };

    return (
        <div className="p-6 max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-6">
                <Link href="/admin/rss-feeds" className="flex items-center gap-2 text-indigo-600 hover:text-indigo-800 mb-4">
                    <ArrowLeft size={20} />
                    Back to RSS Feeds
                </Link>
                <h1 className="text-3xl font-bold text-gray-900">Bulk Import RSS Feeds</h1>
                <p className="text-gray-600 mt-1">Paste a list of RSS feed URLs (one per line) — each will be tested and imported automatically.</p>
            </div>

            {/* Input form */}
            {!running && !done && (
                <div className="bg-white rounded-lg shadow-md p-6 space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            RSS Feed URLs <span className="text-gray-400 font-normal">(one per line)</span>
                        </label>
                        <textarea
                            value={rawUrls}
                            onChange={e => setRawUrls(e.target.value)}
                            rows={14}
                            placeholder={`https://www.autoblog.com/rss.xml\nhttps://feeds.feedburner.com/electrek/feed\nhttps://www.motortrend.com/feed/`}
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 font-mono text-sm text-gray-900 resize-y"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            {parseUrls(rawUrls).length} valid URL{parseUrls(rawUrls).length !== 1 ? 's' : ''} detected
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Default Source Type</label>
                        <select
                            value={sourceType}
                            onChange={e => setSourceType(e.target.value)}
                            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 text-gray-900"
                        >
                            <option value="media">Automotive Media</option>
                            <option value="brand">Automotive Brand</option>
                            <option value="blog">Industry Blog</option>
                        </select>
                    </div>

                    <button
                        onClick={handleImport}
                        disabled={parseUrls(rawUrls).length === 0}
                        className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                    >
                        <Upload size={20} />
                        Import {parseUrls(rawUrls).length > 0 ? `${parseUrls(rawUrls).length} Feeds` : 'Feeds'}
                    </button>
                </div>
            )}

            {/* Progress / Results */}
            {feeds.length > 0 && (
                <div className="bg-white rounded-lg shadow-md mt-6 overflow-hidden">
                    {/* Summary bar */}
                    {done && (
                        <div className="p-4 bg-gray-50 border-b flex items-center gap-6 flex-wrap">
                            <span className="font-semibold text-gray-700">Results: {stats.total} total</span>
                            {stats.success > 0 && <span className="text-green-700 font-medium">✓ {stats.success} imported</span>}
                            {stats.duplicate > 0 && <span className="text-yellow-700 font-medium">⚠ {stats.duplicate} already existed</span>}
                            {stats.error > 0 && <span className="text-red-700 font-medium">✗ {stats.error} failed</span>}
                            <div className="ml-auto flex gap-2">
                                <button
                                    onClick={() => { setFeeds([]); setDone(false); setRunning(false); }}
                                    className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700"
                                >
                                    <RefreshCw size={14} /> Import More
                                </button>
                                <Link href="/admin/rss-feeds" className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-200 text-gray-700 rounded-lg text-sm hover:bg-gray-300">
                                    View Feeds →
                                </Link>
                            </div>
                        </div>
                    )}

                    {running && (
                        <div className="p-4 bg-blue-50 border-b flex items-center gap-3">
                            <Loader2 className="animate-spin text-blue-600" size={20} />
                            <span className="text-blue-700 font-medium">
                                Processing… {stats.success + stats.duplicate + stats.error} / {stats.total}
                            </span>
                        </div>
                    )}

                    {/* Feed list */}
                    <div className="divide-y divide-gray-100 max-h-[60vh] overflow-y-auto">
                        {feeds.map((f, i) => (
                            <div key={i} className={`flex items-center gap-3 px-4 py-3 ${f.status === 'testing' || f.status === 'importing' ? 'bg-blue-50' : ''}`}>
                                {statusIcon(f.status)}
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-gray-900 truncate">{f.name || f.url}</p>
                                    <p className="text-xs text-gray-400 truncate">{f.url}</p>
                                </div>
                                <div className="text-right flex-shrink-0">
                                    {statusLabel(f)}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
