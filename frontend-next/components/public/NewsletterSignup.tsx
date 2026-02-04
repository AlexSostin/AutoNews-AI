'use client';
import { useState } from 'react';
import api from '@/lib/api';
import { trackNewsletterSignup } from '@/lib/analytics';
import { Mail, CheckCircle, AlertCircle } from 'lucide-react';

export default function NewsletterSignup() {
    const [email, setEmail] = useState('');
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
    const [message, setMessage] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setStatus('loading');
        setMessage('');

        try {
            await api.post('/newsletter/subscribe/', { email });
            setStatus('success');
            setMessage('Successfully subscribed! Check your email for confirmation.');
            setEmail('');
            trackNewsletterSignup('footer_form');

            // Reset success message after 5 seconds
            setTimeout(() => {
                setStatus('idle');
                setMessage('');
            }, 5000);
        } catch (error: any) {
            setStatus('error');
            setMessage(error.response?.data?.error || 'Failed to subscribe. Please try again.');

            // Reset error message after 5 seconds
            setTimeout(() => {
                setStatus('idle');
                setMessage('');
            }, 5000);
        }
    };

    return (
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl p-6 md:p-8 text-white shadow-xl">
            <div className="flex items-center gap-3 mb-3">
                <Mail className="w-6 h-6" />
                <h3 className="text-xl md:text-2xl font-bold">Subscribe to Newsletter</h3>
            </div>
            <p className="text-indigo-100 mb-6 text-sm md:text-base">
                Get the latest automotive news, reviews, and exclusive content delivered straight to your inbox!
            </p>

            <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
                <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    required
                    disabled={status === 'loading' || status === 'success'}
                    className="flex-1 px-4 py-3 rounded-lg text-gray-900 outline-none focus:ring-2 focus:ring-white disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <button
                    type="submit"
                    disabled={status === 'loading' || status === 'success'}
                    className="px-6 py-3 bg-white text-indigo-600 font-bold rounded-lg hover:bg-indigo-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                >
                    {status === 'loading' ? 'Subscribing...' : status === 'success' ? 'Subscribed!' : 'Subscribe'}
                </button>
            </form>

            {message && (
                <div className={`mt-4 flex items-center gap-2 text-sm ${status === 'success' ? 'text-green-200' : 'text-red-200'
                    }`}>
                    {status === 'success' ? (
                        <CheckCircle className="w-4 h-4" />
                    ) : (
                        <AlertCircle className="w-4 h-4" />
                    )}
                    <p>{message}</p>
                </div>
            )}

            <p className="mt-4 text-xs text-indigo-200">
                We respect your privacy. Unsubscribe at any time.
            </p>
        </div>
    );
}
