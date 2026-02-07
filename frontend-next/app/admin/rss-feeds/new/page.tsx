'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Save, TestTube, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface Category {
    id: number;
    name: string;
}

interface FeedTestResult {
    success: boolean;
    message: string;
    entries?: Array<{
        title: string;
        link: string;
        published?: string;
    }>;
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
    });

    useEffect(() => {
        fetchCategories();
    }, []);

    const fetchCategories = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/categories/`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (response.ok) {
                const data = await response.json();
                setCategories(data);
            }
        } catch (error) {
            console.error('Error fetching categories:', error);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/rss-feeds/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ...formData,
                    default_category: formData.default_category || null,
                }),
            });

            if (response.ok) {
                router.push('/admin/rss-feeds');
            } else {
                const error = await response.json();
                alert(`Error: ${JSON.stringify(error)}`);
            }
        } catch (error) {
            console.error('Error creating RSS feed:', error);
            alert('Failed to create RSS feed');
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value, type } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
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
            const response = await fetch(formData.feed_url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/rss+xml, application/xml, text/xml',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const text = await response.text();

            if (!text.includes('<rss') && !text.includes('<feed')) {
                throw new Error('Not a valid RSS/Atom feed');
            }

            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(text, 'text/xml');

            const parseError = xmlDoc.querySelector('parsererror');
            if (parseError) {
                throw new Error('Invalid XML format');
            }

            const items = xmlDoc.querySelectorAll('item, entry');
            const entries = Array.from(items).slice(0, 3).map(item => ({
                title: item.querySelector('title')?.textContent || 'No title',
                link: item.querySelector('link')?.textContent || item.querySelector('link')?.getAttribute('href') || '',
                published: item.querySelector('pubDate, published')?.textContent || '',
            }));

            setTestResult({
                success: true,
                message: `✓ Valid RSS feed! Found ${items.length} entries.`,
                entries,
            });
        } catch (error: any) {
            setTestResult({
                success: false,
                message: `✗ Error: ${error.message}`,
            });
        } finally {
            setTesting(false);
        }
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
