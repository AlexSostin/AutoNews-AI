'use client';

import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Trash2, MessageSquareWarning, ExternalLink } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';

interface Feedback {
    id: number;
    article_id: number;
    article_title: string;
    article_slug: string;
    category: string;
    category_display: string;
    message: string;
    ip_address: string | null;
    is_resolved: boolean;
    admin_notes: string;
    created_at: string;
}

const CATEGORY_ICONS: Record<string, string> = {
    factual_error: '❌',
    hallucination: '🤖',
    typo: '✏️',
    outdated: '📅',
    other: '💬',
};

export default function FeedbackPage() {
    const [feedback, setFeedback] = useState<Feedback[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<'all' | 'open' | 'resolved'>('open');

    useEffect(() => {
        fetchFeedback();
    }, [filter]);

    const fetchFeedback = async () => {
        try {
            setLoading(true);
            const params: Record<string, string> = {};
            if (filter === 'open') params.resolved = 'false';
            else if (filter === 'resolved') params.resolved = 'true';
            const response = await api.get('/feedback/', { params });
            setFeedback(response.data.results || response.data);
        } catch (error) {
            console.error('Failed to fetch feedback:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleResolve = async (id: number) => {
        try {
            await api.post(`/feedback/${id}/resolve/`);
            setFeedback(feedback.map(f => f.id === id ? { ...f, is_resolved: true } : f));
        } catch (error) {
            console.error('Failed to resolve feedback:', error);
        }
    };

    const handleUnresolve = async (id: number) => {
        try {
            await api.post(`/feedback/${id}/unresolve/`);
            setFeedback(feedback.map(f => f.id === id ? { ...f, is_resolved: false } : f));
        } catch (error) {
            console.error('Failed to unresolve feedback:', error);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Delete this feedback?')) return;
        try {
            await api.delete(`/feedback/${id}/`);
            setFeedback(feedback.filter(f => f.id !== id));
        } catch (error) {
            console.error('Failed to delete feedback:', error);
        }
    };

    const openCount = feedback.filter(f => !f.is_resolved).length;

    return (
        <div>
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-3xl font-black text-gray-950">Article Feedback</h1>
                    {openCount > 0 && (
                        <p className="text-amber-600 font-bold mt-2">
                            {openCount} open issue{openCount !== 1 ? 's' : ''} to review
                        </p>
                    )}
                </div>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-lg shadow-md p-4 mb-6">
                <div className="flex gap-2">
                    <button
                        onClick={() => setFilter('all')}
                        className={`px-4 py-2 rounded-lg font-medium transition-all cursor-pointer ${filter === 'all'
                            ? 'bg-indigo-600 text-white shadow-md'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                    >
                        All
                    </button>
                    <button
                        onClick={() => setFilter('open')}
                        className={`px-4 py-2 rounded-lg font-medium transition-all cursor-pointer ${filter === 'open'
                            ? 'bg-amber-600 text-white shadow-md'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                    >
                        Open {openCount > 0 && `(${openCount})`}
                    </button>
                    <button
                        onClick={() => setFilter('resolved')}
                        className={`px-4 py-2 rounded-lg font-medium transition-all cursor-pointer ${filter === 'resolved'
                            ? 'bg-green-600 text-white shadow-md'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                    >
                        Resolved
                    </button>
                </div>
            </div>

            {/* Feedback List */}
            <div className="space-y-4">
                {loading ? (
                    <div className="bg-white rounded-lg shadow-md p-12 text-center">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
                        <p className="text-gray-600 mt-4 font-medium">Loading feedback...</p>
                    </div>
                ) : feedback.length === 0 ? (
                    <div className="bg-white rounded-lg shadow-md p-12 text-center">
                        <MessageSquareWarning size={48} className="mx-auto text-gray-400 mb-4" />
                        <p className="text-gray-700 font-semibold text-lg">No feedback found</p>
                        <p className="text-gray-600 mt-2">
                            {filter === 'open' ? 'No open issues — all clear! 🎉' : 'No feedback submissions yet'}
                        </p>
                    </div>
                ) : (
                    feedback.map((fb) => (
                        <div
                            key={fb.id}
                            className={`bg-white rounded-lg shadow-md p-6 border-l-4 ${fb.is_resolved
                                ? 'border-green-500'
                                : 'border-amber-500'
                                }`}
                        >
                            <div className="flex items-start justify-between gap-4 mb-3">
                                <div className="flex-1">
                                    <div className="flex items-center gap-3 mb-2 flex-wrap">
                                        <span className="px-3 py-1 rounded-full text-xs font-bold bg-gray-100 text-gray-800">
                                            {CATEGORY_ICONS[fb.category] || '💬'} {fb.category_display}
                                        </span>
                                        {fb.is_resolved ? (
                                            <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold">
                                                ✅ Resolved
                                            </span>
                                        ) : (
                                            <span className="px-3 py-1 bg-amber-100 text-amber-700 rounded-full text-xs font-bold">
                                                ⏳ Open
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-sm text-gray-600 font-medium mb-2">
                                        Article:{' '}
                                        <Link
                                            href={`/articles/${fb.article_slug}`}
                                            target="_blank"
                                            className="text-indigo-600 hover:underline font-bold inline-flex items-center gap-1"
                                        >
                                            {fb.article_title}
                                            <ExternalLink size={12} />
                                        </Link>
                                    </p>
                                    <p className="text-gray-900 font-medium text-base">{fb.message}</p>
                                    <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                                        <span>{new Date(fb.created_at).toLocaleString()}</span>
                                        {fb.ip_address && <span>IP: {fb.ip_address}</span>}
                                    </div>
                                </div>
                            </div>

                            <div className="flex gap-2 pt-4 border-t border-gray-200">
                                {!fb.is_resolved ? (
                                    <button
                                        onClick={() => handleResolve(fb.id)}
                                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2 font-bold shadow-md cursor-pointer"
                                    >
                                        <CheckCircle size={18} />
                                        Resolve
                                    </button>
                                ) : (
                                    <button
                                        onClick={() => handleUnresolve(fb.id)}
                                        className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors flex items-center gap-2 font-bold shadow-md cursor-pointer"
                                    >
                                        <XCircle size={18} />
                                        Reopen
                                    </button>
                                )}
                                <button
                                    onClick={() => handleDelete(fb.id)}
                                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2 font-bold shadow-md cursor-pointer"
                                >
                                    <Trash2 size={18} />
                                    Delete
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
