'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Save } from 'lucide-react';

interface Category {
    id: number;
    name: string;
}

export default function NewRSSFeedPage() {
    const router = useRouter();
    const [categories, setCategories] = useState<Category[]>([]);
    const [loading, setLoading] = useState(false);
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
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/rss-feeds/`, {
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

            <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md p-6 space-y-6">
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
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        RSS Feed URL *
                    </label>
                    <input
                        type="url"
                        name="feed_url"
                        value={formData.feed_url}
                        onChange={handleChange}
                        required
                        placeholder="https://example.com/rss"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                    />
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
                </div>

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
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Logo URL (optional)
                    </label>
                    <input
                        type="url"
                        name="logo_url"
                        value={formData.logo_url}
                        onChange={handleChange}
                        placeholder="https://example.com/logo.png"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                    />
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
                </div>

                <div className="flex items-center gap-6">
                    <label className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            name="is_enabled"
                            checked={formData.is_enabled}
                            onChange={handleChange}
                            className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                        />
                        <span className="text-sm font-medium text-gray-700">Enable monitoring</span>
                    </label>

                    <label className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            name="auto_publish"
                            checked={formData.auto_publish}
                            onChange={handleChange}
                            className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                        />
                        <span className="text-sm font-medium text-gray-700">Auto-publish (skip review)</span>
                    </label>
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
