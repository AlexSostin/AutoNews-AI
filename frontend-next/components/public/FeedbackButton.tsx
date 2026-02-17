'use client';

import { useState } from 'react';
import { AlertTriangle, X, Send, CheckCircle } from 'lucide-react';

interface FeedbackButtonProps {
    articleSlug: string;
}

const CATEGORIES = [
    { value: 'factual_error', label: '❌ Factual Error', desc: 'Wrong specs, price, or facts' },
    { value: 'hallucination', label: '🤖 AI Hallucination', desc: 'Made-up features or specs' },
    { value: 'typo', label: '✏️ Typo / Grammar', desc: 'Spelling or language errors' },
    { value: 'outdated', label: '📅 Outdated Info', desc: 'No longer accurate' },
    { value: 'other', label: '💬 Other', desc: 'Something else' },
];

export default function FeedbackButton({ articleSlug }: FeedbackButtonProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [category, setCategory] = useState('');
    const [message, setMessage] = useState('');
    const [status, setStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState('');

    const getApiUrl = () => {
        if (typeof window !== 'undefined') {
            const host = window.location.hostname;
            if (host !== 'localhost' && host !== '127.0.0.1') {
                return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
            }
        }
        return 'http://localhost:8000/api/v1';
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!category || message.length < 5) return;

        setStatus('sending');
        try {
            const res = await fetch(`${getApiUrl()}/articles/${articleSlug}/feedback/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ category, message }),
            });

            const data = await res.json();
            if (res.ok) {
                setStatus('success');
                setTimeout(() => {
                    setIsOpen(false);
                    setStatus('idle');
                    setCategory('');
                    setMessage('');
                }, 2500);
            } else {
                setStatus('error');
                setErrorMessage(data.error || 'Something went wrong');
            }
        } catch {
            setStatus('error');
            setErrorMessage('Network error — please try again');
        }
    };

    return (
        <>
            {/* Trigger Button */}
            <button
                onClick={() => setIsOpen(true)}
                className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-red-600 transition-colors group cursor-pointer"
                aria-label="Report an issue with this article"
            >
                <AlertTriangle size={16} className="group-hover:text-red-600 transition-colors" />
                <span className="underline underline-offset-2 decoration-gray-300 group-hover:decoration-red-400">
                    Found an error?
                </span>
            </button>

            {/* Modal Overlay */}
            {isOpen && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => status !== 'sending' && setIsOpen(false)}>
                    <div
                        className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 relative animate-in fade-in zoom-in-95 duration-200"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Close button */}
                        <button
                            onClick={() => setIsOpen(false)}
                            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer"
                            disabled={status === 'sending'}
                        >
                            <X size={20} />
                        </button>

                        {status === 'success' ? (
                            <div className="text-center py-8">
                                <CheckCircle size={48} className="mx-auto text-green-500 mb-4" />
                                <h3 className="text-xl font-bold text-gray-900 mb-2">Thank you!</h3>
                                <p className="text-gray-600">Your feedback helps us improve article quality.</p>
                            </div>
                        ) : (
                            <>
                                <h3 className="text-xl font-bold text-gray-900 mb-1">Report an Issue</h3>
                                <p className="text-sm text-gray-500 mb-5">Help us improve — describe what&apos;s wrong.</p>

                                <form onSubmit={handleSubmit} className="space-y-4">
                                    {/* Category Selection */}
                                    <div className="grid grid-cols-1 gap-2">
                                        {CATEGORIES.map((cat) => (
                                            <button
                                                key={cat.value}
                                                type="button"
                                                onClick={() => setCategory(cat.value)}
                                                className={`text-left px-4 py-3 rounded-xl border-2 transition-all cursor-pointer ${category === cat.value
                                                        ? 'border-indigo-500 bg-indigo-50'
                                                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                                                    }`}
                                            >
                                                <div className="font-medium text-sm">{cat.label}</div>
                                                <div className="text-xs text-gray-500">{cat.desc}</div>
                                            </button>
                                        ))}
                                    </div>

                                    {/* Message */}
                                    <textarea
                                        value={message}
                                        onChange={(e) => setMessage(e.target.value)}
                                        placeholder="Describe the issue (e.g., 'The horsepower listed is 500hp but the actual spec is 300hp')"
                                        className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-indigo-500 focus:outline-none resize-none text-sm text-gray-800 placeholder:text-gray-400"
                                        rows={3}
                                        maxLength={1000}
                                        required
                                    />

                                    {/* Error */}
                                    {status === 'error' && (
                                        <p className="text-red-500 text-sm">{errorMessage}</p>
                                    )}

                                    {/* Submit */}
                                    <button
                                        type="submit"
                                        disabled={!category || message.length < 5 || status === 'sending'}
                                        className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer"
                                    >
                                        <Send size={16} />
                                        {status === 'sending' ? 'Sending...' : 'Submit Feedback'}
                                    </button>
                                </form>
                            </>
                        )}
                    </div>
                </div>
            )}
        </>
    );
}
