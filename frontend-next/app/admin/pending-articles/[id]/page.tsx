'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import { ArrowLeft, CheckCircle, XCircle, Loader2, ExternalLink, Calendar, Tag, Rss } from 'lucide-react';

interface PendingArticle {
    id: number;
    title: string;
    content: string;
    excerpt: string;
    featured_image: string;
    images: string[];
    source_url: string;
    status: string;
    created_at: string;
    rss_feed?: {
        id: number;
        name: string;
        logo_url?: string;
    };
    suggested_category?: {
        id: number;
        name: string;
    };
}

export default function PendingArticlePreviewPage() {
    const params = useParams();
    const router = useRouter();
    const [article, setArticle] = useState<PendingArticle | null>(null);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(false);

    useEffect(() => {
        if (params.id) {
            fetchArticle(params.id as string);
        }
    }, [params.id]);

    const fetchArticle = async (id: string) => {
        try {
            const response = await api.get(`/pending-articles/${id}/`);
            setArticle(response.data);
        } catch (error) {
            console.error('Error fetching pending article:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleApprove = async () => {
        if (!article) return;

        setActionLoading(true);
        try {
            await api.post(`/pending-articles/${article.id}/approve/`);
            router.push('/admin/rss-pending');
        } catch (error) {
            console.error('Error approving article:', error);
            alert('Failed to approve article');
        } finally {
            setActionLoading(false);
        }
    };

    const handleReject = async () => {
        if (!article) return;

        if (!confirm('Are you sure you want to reject this article?')) return;

        setActionLoading(true);
        try {
            await api.post(`/pending-articles/${article.id}/reject/`);
            router.push('/admin/rss-pending');
        } catch (error) {
            console.error('Error rejecting article:', error);
            alert('Failed to reject article');
        } finally {
            setActionLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            </div>
        );
    }

    if (!article) {
        return (
            <div className="max-w-4xl mx-auto p-6">
                <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                    <p className="text-red-800 font-medium">Article not found</p>
                    <Link href="/admin/rss-pending" className="text-indigo-600 hover:text-indigo-800 mt-2 inline-block">
                        ← Back to RSS Pending
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-5xl mx-auto p-6">
            {/* Header */}
            <div className="mb-6">
                <Link
                    href="/admin/rss-pending"
                    className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
                >
                    <ArrowLeft size={20} />
                    Back to RSS Pending
                </Link>

                <div className="flex items-center gap-3 mb-4">
                    <span className="px-4 py-1.5 text-sm font-bold rounded-full bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-md">
                        PENDING REVIEW
                    </span>
                    <span className="px-4 py-1.5 text-sm font-semibold rounded-full bg-purple-100 text-purple-700 border border-purple-200">
                        🤖 AI Generated
                    </span>
                </div>
            </div>

            {/* Article Preview */}
            <div className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-200">
                {/* Featured Image */}
                {article.featured_image && (
                    <div className="w-full h-96 bg-gray-100">
                        <img
                            src={article.featured_image}
                            alt={article.title}
                            className="w-full h-full object-cover"
                        />
                    </div>
                )}

                <div className="p-8">
                    {/* Meta Info */}
                    <div className="flex flex-wrap items-center gap-4 mb-6 text-sm text-gray-600">
                        {article.rss_feed && (
                            <div className="flex items-center gap-2 bg-orange-50 px-3 py-1.5 rounded-lg">
                                <Rss size={16} className="text-orange-600" />
                                <span className="font-medium">{article.rss_feed.name}</span>
                            </div>
                        )}
                        {article.suggested_category && (
                            <div className="flex items-center gap-2 bg-indigo-50 px-3 py-1.5 rounded-lg">
                                <Tag size={16} className="text-indigo-600" />
                                <span className="font-medium">{article.suggested_category.name}</span>
                            </div>
                        )}
                        <div className="flex items-center gap-2">
                            <Calendar size={16} className="text-gray-400" />
                            <span>{new Date(article.created_at).toLocaleDateString('en-US', {
                                month: 'long',
                                day: 'numeric',
                                year: 'numeric'
                            })}</span>
                        </div>
                    </div>

                    {/* Title */}
                    <h1 className="text-4xl font-bold text-gray-900 mb-4">
                        {article.title}
                    </h1>

                    {/* Excerpt */}
                    {article.excerpt && (
                        <p className="text-xl text-gray-600 mb-8 leading-relaxed">
                            {article.excerpt}
                        </p>
                    )}

                    {/* Source Link */}
                    {article.source_url && (
                        <a
                            href={article.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 text-indigo-600 hover:text-indigo-800 font-medium mb-8"
                        >
                            <ExternalLink size={18} />
                            View Original Source
                        </a>
                    )}

                    {/* Content */}
                    <div
                        className="prose prose-lg max-w-none"
                        dangerouslySetInnerHTML={{ __html: article.content }}
                    />

                    {/* Additional Images */}
                    {article.images && article.images.length > 1 && (
                        <div className="mt-8 grid grid-cols-2 gap-4">
                            {article.images.slice(1).map((img, idx) => (
                                <img
                                    key={idx}
                                    src={img}
                                    alt={`Image ${idx + 2}`}
                                    className="rounded-lg shadow-md"
                                />
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Action Buttons */}
            <div className="mt-8 flex gap-4 justify-center">
                <button
                    onClick={handleApprove}
                    disabled={actionLoading}
                    className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-green-600 to-green-700 text-white rounded-lg hover:from-green-700 hover:to-green-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold shadow-lg hover:shadow-xl text-lg"
                >
                    {actionLoading ? (
                        <Loader2 className="animate-spin" size={20} />
                    ) : (
                        <CheckCircle size={20} />
                    )}
                    Approve & Publish
                </button>
                <button
                    onClick={handleReject}
                    disabled={actionLoading}
                    className="flex items-center gap-2 px-8 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold shadow-lg hover:shadow-xl text-lg"
                >
                    <XCircle size={20} />
                    Reject
                </button>
            </div>
        </div>
    );
}
