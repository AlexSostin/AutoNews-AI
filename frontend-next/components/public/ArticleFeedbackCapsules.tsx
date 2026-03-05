'use client';

/**
 * ArticleFeedbackCapsules — unified "Rate this article" widget.
 * Combines:
 *   1. Capsule feedback buttons (10 toggles: 5 positive, 5 negative)
 *   2. Star rating (1-5 stars)
 *
 * Theme-aware: uses indigo-* classes which auto-adapt to
 * Indigo / Emerald / Ocean Blue via CSS variable overrides.
 */

import { useState, useEffect, useCallback } from 'react';
import { Star } from 'lucide-react';
import api from '@/lib/api';

const getApiUrl = () => {
    if (typeof window === 'undefined') return '';
    const h = window.location.hostname;
    return (h === 'localhost' || h === '127.0.0.1')
        ? 'http://localhost:8000/api/v1'
        : 'https://heroic-healing-production-2365.up.railway.app/api/v1';
};

interface CapsuleConfig {
    key: string;
    emoji: string;
    label: string;
    positive: boolean;
}

const POSITIVE_CAPSULES: CapsuleConfig[] = [
    { key: 'accurate_specs', emoji: '📊', label: 'Accurate Specs', positive: true },
    { key: 'well_written', emoji: '✍️', label: 'Well Written', positive: true },
    { key: 'great_photos', emoji: '📸', label: 'Great Photos', positive: true },
    { key: 'fair_review', emoji: '⚖️', label: 'Fair Review', positive: true },
    { key: 'useful_info', emoji: '💡', label: 'Useful Info', positive: true },
];

const NEGATIVE_CAPSULES: CapsuleConfig[] = [
    { key: 'wrong_specs', emoji: '📊', label: 'Wrong Specs', positive: false },
    { key: 'too_long', emoji: '✍️', label: 'Too Long', positive: false },
    { key: 'need_photos', emoji: '📸', label: 'Need Photos', positive: false },
    { key: 'missing_price', emoji: '💰', label: 'Missing Price', positive: false },
    { key: 'inaccurate', emoji: '❌', label: 'Inaccurate', positive: false },
];

interface Props {
    articleSlug: string;
    initialRating?: number;
    ratingCount?: number;
}

export default function ArticleFeedbackCapsules({ articleSlug, initialRating = 0, ratingCount = 0 }: Props) {
    // --- Capsule state ---
    const [voted, setVoted] = useState<Set<string>>(new Set());
    const [animating, setAnimating] = useState<string | null>(null);
    const [showThankYou, setShowThankYou] = useState(false);

    // --- Star rating state ---
    const [rating, setRating] = useState(initialRating || 0);
    const [count, setCount] = useState(ratingCount || 0);
    const [hoveredStar, setHoveredStar] = useState(0);
    const [userRating, setUserRating] = useState(0);
    const [isSubmittingStar, setIsSubmittingStar] = useState(false);
    const [starMessage, setStarMessage] = useState('');

    // Load capsule votes
    useEffect(() => {
        const stored = localStorage.getItem(`capsule_fb_${articleSlug}`);
        if (stored) {
            try { setVoted(new Set(JSON.parse(stored))); } catch { /* ignore */ }
        }
        fetch(`${getApiUrl()}/capsule-feedback/${articleSlug}/`)
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data?.voted?.length) {
                    setVoted(new Set(data.voted));
                    localStorage.setItem(`capsule_fb_${articleSlug}`, JSON.stringify(data.voted));
                }
            })
            .catch(() => { /* silent */ });
    }, [articleSlug]);

    // Load user star rating
    useEffect(() => {
        const loadUserRating = async () => {
            try {
                const response = await api.get(`/articles/${articleSlug}/my-rating/`);
                if (response.data.has_rated) {
                    setUserRating(response.data.user_rating);
                }
            } catch (error: any) {
                if (error.response?.status !== 401 && error.response?.status !== 404) {
                    console.error('Failed to load user rating:', error);
                }
            }
        };
        loadUserRating();
    }, [articleSlug]);

    // Capsule toggle
    const handleToggle = useCallback(async (key: string) => {
        setAnimating(key);
        setTimeout(() => setAnimating(null), 300);

        const newVoted = new Set(voted);
        const wasVoted = newVoted.has(key);

        if (wasVoted) {
            newVoted.delete(key);
        } else {
            newVoted.add(key);
        }
        setVoted(newVoted);
        localStorage.setItem(`capsule_fb_${articleSlug}`, JSON.stringify([...newVoted]));

        if (newVoted.size > 0 && !wasVoted) {
            setShowThankYou(true);
            setTimeout(() => setShowThankYou(false), 2000);
        }

        try {
            await fetch(`${getApiUrl()}/capsule-feedback/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ slug: articleSlug, feedback_type: key }),
            });
        } catch { /* silent */ }
    }, [voted, articleSlug]);

    // Star rating submit
    const handleRate = async (stars: number) => {
        setIsSubmittingStar(true);
        try {
            const response = await api.post(`/articles/${articleSlug}/rate/`, { rating: stars });
            setRating(response.data.average_rating);
            setCount(response.data.rating_count);
            setUserRating(stars);

            if (typeof window !== 'undefined' && (window as any).updateArticleRating) {
                (window as any).updateArticleRating(response.data.average_rating, response.data.rating_count);
            }

            setStarMessage('✓ Rating updated!');
            setTimeout(() => setStarMessage(''), 3000);
        } catch (error: any) {
            setStarMessage(error.response?.data?.error || 'Failed to submit rating');
            setTimeout(() => setStarMessage(''), 3000);
        } finally {
            setIsSubmittingStar(false);
        }
    };

    const renderCapsule = (capsule: CapsuleConfig) => {
        const isActive = voted.has(capsule.key);
        const isAnimatingThis = animating === capsule.key;

        return (
            <button
                key={capsule.key}
                onClick={() => handleToggle(capsule.key)}
                className={`
                    inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs sm:text-sm font-medium
                    transition-all duration-200 select-none cursor-pointer border
                    ${isAnimatingThis ? 'scale-110' : 'scale-100'}
                    ${isActive && capsule.positive
                        ? 'bg-indigo-50 border-indigo-400 text-indigo-700 shadow-sm'
                        : isActive && !capsule.positive
                            ? 'bg-rose-50 border-rose-400 text-rose-700 shadow-sm'
                            : 'bg-white border-gray-200 text-gray-600 hover:border-indigo-300 hover:bg-indigo-50/50'
                    }
                `}
                title={isActive ? `Remove: ${capsule.label}` : capsule.label}
            >
                <span className="text-sm">{capsule.emoji}</span>
                <span>{capsule.label}</span>
                {isActive && (
                    <span className="ml-0.5 text-xs opacity-60">✓</span>
                )}
            </button>
        );
    };

    return (
        <div className="bg-white rounded-xl shadow-md p-6 mb-8 border-t-4 border-indigo-500">
            {/* Header */}
            <div className="flex items-center justify-center gap-2 mb-5">
                <span className="text-xl">🎯</span>
                <h3 className="text-lg font-bold text-gray-900">
                    Rate this article
                </h3>
                {showThankYou && (
                    <span className="ml-2 text-xs font-medium text-indigo-600">
                        ✅ Thanks!
                    </span>
                )}
            </div>

            {/* ===== Star Rating Section ===== */}
            <div className="text-center mb-6 pb-6 border-b border-gray-100">
                {userRating > 0 && (
                    <p className="text-sm text-indigo-600 font-medium mb-2">
                        Your rating: {userRating} ★
                    </p>
                )}
                <div className="flex justify-center items-center gap-4 mb-2">
                    <div className="flex gap-1">
                        {[1, 2, 3, 4, 5].map((star) => (
                            <button
                                key={star}
                                onClick={() => handleRate(star)}
                                onMouseEnter={() => setHoveredStar(star)}
                                onMouseLeave={() => setHoveredStar(0)}
                                disabled={isSubmittingStar}
                                className="transition-all transform hover:scale-110 disabled:cursor-not-allowed cursor-pointer"
                            >
                                <Star
                                    size={36}
                                    className={`${star <= (hoveredStar || userRating)
                                        ? 'fill-amber-400 text-amber-400'
                                        : 'text-gray-300'
                                        } transition-colors`}
                                />
                            </button>
                        ))}
                    </div>
                    <div className="text-center">
                        <div className="text-2xl font-bold text-gray-900">
                            {(rating || 0).toFixed(1)}
                        </div>
                        <div className="text-xs text-gray-500">
                            ({count || 0} {count === 1 ? 'vote' : 'votes'})
                        </div>
                    </div>
                </div>
                {starMessage && (
                    <p className={`text-sm font-medium ${starMessage.includes('✓') ? 'text-green-600' : 'text-red-600'}`}>
                        {starMessage}
                    </p>
                )}
                {userRating === 0 && !starMessage && (
                    <p className="text-xs text-gray-400">Click a star to rate</p>
                )}
            </div>

            {/* ===== Capsule Feedback Section ===== */}
            <div className="mb-4 text-center">
                <p className="text-xs text-gray-500 mb-2.5 font-medium uppercase tracking-wide">
                    What was good?
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                    {POSITIVE_CAPSULES.map(renderCapsule)}
                </div>
            </div>

            <div className="text-center">
                <p className="text-xs text-gray-500 mb-2.5 font-medium uppercase tracking-wide">
                    What could improve?
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                    {NEGATIVE_CAPSULES.map(renderCapsule)}
                </div>
            </div>
        </div>
    );
}
