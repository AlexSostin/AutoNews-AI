'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Save, TestTube, CheckCircle, XCircle, AlertCircle, Wand2 } from 'lucide-react';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface Category {
    id: number;
    name: string;
}

interface FeedMeta {
    title: string;
    link: string;
    description: string;
}

interface FeedTestResult {
    success: boolean;
    message: string;
    entries?: Array<{
        title: string;
        link: string;
        published?: string;
    }>;
    feed_meta?: FeedMeta;
}

export default function NewRSSFeedPage() {
    const router = useRouter();
    const [categories, setCategories] = useState<Category[]>([]);
    const [loading, setLoading] = useState(false);
    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState<FeedTestResult | null>(null);
    const [formData, setFormData] = useState({
        name: '',
        feed_url: '',
        website_url: '',
        source_type: 'brand',
        is_enabled: true,
        auto_publish: false,
        default_category: '',
        logo_url: '',
        description: '',
        scan_frequency: 60,
        include_keywords: '',
        exclude_keywords: '',
        auto_publish_min_score: 0,
    });

    useEffect(() => {
        fetchCategories();
    }, []);

    const fetchCategories = async () => {
        try {
            const { data } = await api.get('/categories/');
            setCategories(data);
        } catch (error) {
            console.error('Error fetching categories:', error);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        try {
            await api.post('/rss-feeds/', {
                ...formData,
                default_category: formData.default_category ? parseInt(formData.default_category, 10) : null,
            });
            router.push('/admin/rss-feeds');
        } catch (error: any) {
            console.error('Error creating RSS feed:', error);
            const detail = error.response?.data?.detail || error.response?.data?.feed_url?.[0] || 'Failed to create RSS feed';
            toast.error(detail);
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value, type } = e.target;
        
        let parsedValue: any = value;
        if (type === 'checkbox') {
            parsedValue = (e.target as HTMLInputElement).checked;
        } else if (type === 'number') {
            parsedValue = value === '' ? '' : Number(value);
        }

        setFormData(prev => ({
            ...prev,
            [name]: parsedValue,
        }));
        // Clear test result when URL changes
        if (name === 'feed_url') {
            setTestResult(null);
        }
    };

    const testFeed = async () => {
        if (!formData.feed_url) {
            setTestResult({ success: false, message: 'Please enter a feed URL first' });
            return;
        }

        setTesting(true);
        setTestResult(null);

        try {
            const { data } = await api.post('/rss-feeds/test_feed/', { feed_url: formData.feed_url });

            setTestResult({
                success: true,
                message: `✓ Valid RSS feed! Found ${data.entries_count} entries.`,
                entries: data.entries,
                feed_meta: data.feed_meta,
            });
        } catch (error: any) {
            const msg = error.response?.data?.error || error.message;
            setTestResult({
                success: false,
                message: `✗ Error: ${msg}`,
            });
        } finally {
            setTesting(false);
        }
    };

    const autoFillFromMeta = () => {
        if (!testResult?.feed_meta) return;
        const meta = testResult.feed_meta;
        setFormData(prev => ({
            ...prev,
            name: meta.title || prev.name,
            website_url: meta.link || prev.website_url,
            description: meta.description || prev.description,
        }));
    };

    return (
        <div className="p-6 max-w-3xl mx-auto">
            <div className="mb-6">
                <Link
                    href="/admin/rss-feeds"
                    className="flex items-center gap-2 text-indigo-600 hover:text-indigo-800 mb-4"
                >
                    <ArrowLeft size={20} />
                    Back to RSS Feeds
                </Link>
                <h1 className="text-3xl font-bold text-gray-900">Add New RSS Feed</h1>
                <p className="text-gray-600 mt-1">Configure a new RSS feed for automatic article generation</p>
            </div>

            <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md p-6 space-y-8">
                {/* Basic Information Section */}
                <div className="border-b pb-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">📋 Basic Information</h2>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Feed Name *
                            </label>
                            <input
                                type="text"
                                name="name"
                                value={formData.name}
                                onChange={handleChange}
                                required
                                placeholder="e.g., Mercedes-Benz Press"
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                            />
                            <p className="text-xs text-gray-500 mt-1">Display name for this RSS feed</p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                RSS Feed URL *
                            </label>
                            <div className="flex gap-2">
                                <input
                                    type="url"
                                    name="feed_url"
                                    value={formData.feed_url}
                                    onChange={handleChange}
                                    required
                                    placeholder="https://example.com/rss"
                                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                                />
                                <button
                                    type="button"
                                    onClick={testFeed}
                                    disabled={testing || !formData.feed_url}
                                    className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <TestTube size={18} />
                                    {testing ? 'Testing...' : 'Test Feed'}
                                </button>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">Examples: Mercedes RSS, BMW Press, Tesla Blog</p>

                            {/* Test Result */}
                            {testResult && (
                                <div className={`mt-3 p-3 rounded-lg border ${testResult.success
                                    ? 'bg-green-50 border-green-200'
                                    : 'bg-red-50 border-red-200'
                                    }`}>
                                    <div className="flex items-start gap-2">
                                        {testResult.success ? (
                                            <CheckCircle className="text-green-600 flex-shrink-0" size={20} />
                                        ) : (
                                            <XCircle className="text-red-600 flex-shrink-0" size={20} />
                                        )}
                                        <div className="flex-1">
                                            <p className={`text-sm font-medium ${testResult.success ? 'text-green-800' : 'text-red-800'
                                                }`}>
                                                {testResult.message}
                                            </p>
                                            {testResult.entries && testResult.entries.length > 0 && (
                                                <div className="mt-2 space-y-1">
                                                    <p className="text-xs font-medium text-gray-700">Recent entries:</p>
                                                    {testResult.entries.map((entry, idx) => (
                                                        <div key={idx} className="text-xs text-gray-600 pl-2 border-l-2 border-green-300">
                                                            • {entry.title}
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                            {testResult.success && testResult.feed_meta && (
                                                <div className="mt-3 pt-3 border-t border-green-200">
                                                    <div className="text-xs text-gray-600 space-y-0.5 mb-2">
                                                        {testResult.feed_meta.title && <p><span className="font-medium">Name:</span> {testResult.feed_meta.title}</p>}
                                                        {testResult.feed_meta.link && <p><span className="font-medium">Website:</span> {testResult.feed_meta.link}</p>}
                                                        {testResult.feed_meta.description && <p><span className="font-medium">Description:</span> {testResult.feed_meta.description.substring(0, 100)}{testResult.feed_meta.description.length > 100 ? '...' : ''}</p>}
                                                    </div>
                                                    <button
                                                        type="button"
                                                        onClick={autoFillFromMeta}
                                                        className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white rounded-md hover:bg-green-700 text-xs font-medium transition-colors"
                                                    >
                                                        <Wand2 size={14} />
                                                        Auto-fill fields
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Website URL
                            </label>
                            <input
                                type="url"
                                name="website_url"
                                value={formData.website_url}
                                onChange={handleChange}
                                placeholder="https://example.com"
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                            />
                            <p className="text-xs text-gray-500 mt-1">Main website of the brand/source</p>
                        </div>
                    </div>
                </div>

                {/* Filtering Section */}
                <div className="border-b pb-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">🔍 Filters & Scheduling</h2>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Scan Frequency (minutes)
                            </label>
                            <input
                                type="number"
                                name="scan_frequency"
                                value={formData.scan_frequency}
                                onChange={handleChange}
                                min="10"
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                            />
                            <p className="text-xs text-gray-500 mt-1">How often the server should check for new articles (default 60)</p>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Include Keywords (comma-separated)
                            </label>
                            <input
                                type="text"
                                name="include_keywords"
                                value={formData.include_keywords}
                                onChange={handleChange}
                                placeholder="e.g. EV, electric, hybrid"
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                            />
                            <p className="text-xs text-gray-500 mt-1">Only process articles containing at least one of these keywords (Optional)</p>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Exclude Keywords (comma-separated)
                            </label>
                            <input
                                type="text"
                                name="exclude_keywords"
                                value={formData.exclude_keywords}
                                onChange={handleChange}
                                placeholder="e.g. recall, crash, lawsuit"
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                            />
                            <p className="text-xs text-gray-500 mt-1">Skip articles containing any of these keywords (Optional)</p>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Auto-Publish Minimum AI Score
                            </label>
                            <input
                                type="number"
                                name="auto_publish_min_score"
                                value={formData.auto_publish_min_score}
                                onChange={handleChange}
                                min="0"
                                max="10"
                                placeholder="0"
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                            />
                            <p className="text-xs text-gray-500 mt-1">If set {'>'} 0, overrides the global minimum required AI score for auto-publishing articles from this feed</p>
                        </div>
                    </div>
                </div>

                {/* Settings Section */}
                <div className="border-b pb-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">⚙️ Settings</h2>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Source Type *
                            </label>
                            <select
                                name="source_type"
                                value={formData.source_type}
                                onChange={handleChange}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                            >
                                <option value="brand">Automotive Brand</option>
                                <option value="media">Automotive Media</option>
                                <option value="blog">Industry Blog</option>
                            </select>
                            <p className="text-xs text-gray-500 mt-1">Type of content source</p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Default Category
                            </label>
                            <select
                                name="default_category"
                                value={formData.default_category}
                                onChange={handleChange}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                            >
                                <option value="">No default category</option>
                                {categories.map((cat) => (
                                    <option key={cat.id} value={cat.id}>
                                        {cat.name}
                                    </option>
                                ))}
                            </select>
                            <p className="text-xs text-gray-500 mt-1">Articles from this feed will be assigned to this category</p>
                        </div>
                    </div>
                </div>

                {/* Branding Section */}
                <div className="border-b pb-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">🎨 Branding</h2>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Brand Logo URL (optional)
                            </label>
                            <input
                                type="url"
                                name="logo_url"
                                value={formData.logo_url}
                                onChange={handleChange}
                                placeholder="https://example.com/logo.png"
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                            />
                            {formData.logo_url && (
                                <div className="mt-2">
                                    <img
                                        src={formData.logo_url}
                                        alt="Logo preview"
                                        className="h-12 object-contain"
                                        onError={(e) => e.currentTarget.style.display = 'none'}
                                    />
                                </div>
                            )}
                            <p className="text-xs text-gray-500 mt-1">URL to brand logo (will be displayed with articles)</p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Description
                            </label>
                            <textarea
                                name="description"
                                value={formData.description}
                                onChange={handleChange}
                                rows={3}
                                placeholder="Brief description of this RSS feed"
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                            />
                            <p className="text-xs text-gray-500 mt-1">Internal notes about this feed source</p>
                        </div>
                    </div>
                </div>

                {/* Monitoring Options Section */}
                <div>
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">🔔 Monitoring Options</h2>

                    <div className="space-y-4">
                        <label className="flex items-start gap-3">
                            <input
                                type="checkbox"
                                name="is_enabled"
                                checked={formData.is_enabled}
                                onChange={handleChange}
                                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 mt-1"
                            />
                            <div>
                                <span className="text-sm font-medium text-gray-700">Enable monitoring</span>
                                <p className="text-xs text-gray-500">Automatically check this feed for new articles</p>
                            </div>
                        </label>

                        <label className="flex items-start gap-3">
                            <input
                                type="checkbox"
                                name="auto_publish"
                                checked={formData.auto_publish}
                                onChange={handleChange}
                                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 mt-1"
                            />
                            <div>
                                <span className="text-sm font-medium text-gray-700">Auto-publish (skip review)</span>
                                <div className="flex items-center gap-1 mt-1">
                                    <AlertCircle size={14} className="text-amber-500" />
                                    <p className="text-xs text-amber-600">Warning: Articles will be published immediately without review</p>
                                </div>
                            </div>
                        </label>
                    </div>
                </div>

                <div className="flex gap-4 pt-4">
                    <button
                        type="submit"
                        disabled={loading}
                        className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 font-medium"
                    >
                        <Save size={20} />
                        {loading ? 'Creating...' : 'Create RSS Feed'}
                    </button>
                    <Link
                        href="/admin/rss-feeds"
                        className="px-6 py-3 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 font-medium"
                    >
                        Cancel
                    </Link>
                </div>
            </form>
        </div>
    );
}
