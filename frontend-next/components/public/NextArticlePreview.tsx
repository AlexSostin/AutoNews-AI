'use client';

import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import { ArrowRight, X, ChevronRight } from 'lucide-react';
import { fixImageUrl } from '@/lib/config';

interface NextArticlePreviewProps {
    article: {
        slug: string;
        title: string;
        summary?: string;
        thumbnail_url?: string;
        image?: string;
        categories?: { name: string }[];
    };
    onLoad: () => void;
    onSkip: () => void;
    autoLoadDelay?: number; // ms, default 4000
}

export default function NextArticlePreview({
    article,
    onLoad,
    onSkip,
    autoLoadDelay = 4000,
}: NextArticlePreviewProps) {
    const [countdown, setCountdown] = useState(Math.ceil(autoLoadDelay / 1000));
    const [paused, setPaused] = useState(false);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const remainingRef = useRef(autoLoadDelay);
    const startTimeRef = useRef<number>(Date.now());

    useEffect(() => {
        if (paused) {
            if (intervalRef.current) clearInterval(intervalRef.current);
            remainingRef.current -= Date.now() - startTimeRef.current;
            return;
        }

        startTimeRef.current = Date.now();
        intervalRef.current = setInterval(() => {
            const elapsed = Date.now() - startTimeRef.current;
            const remaining = remainingRef.current - elapsed;
            setCountdown(Math.max(0, Math.ceil(remaining / 1000)));

            if (remaining <= 0) {
                clearInterval(intervalRef.current!);
                onLoad();
            }
        }, 250);

        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
        };
    }, [paused, onLoad]);

    const imageUrl = fixImageUrl(article.thumbnail_url || article.image || '');
    const category = article.categories?.[0]?.name;

    return (
        <div
            className="my-8 rounded-2xl overflow-hidden shadow-lg border border-indigo-100 bg-gradient-to-r from-indigo-50 to-white"
            onMouseEnter={() => setPaused(true)}
            onMouseLeave={() => setPaused(false)}
        >
            {/* Header strip */}
            <div className="bg-indigo-600 px-6 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2 text-white text-sm font-semibold">
                    <ChevronRight size={16} className="animate-pulse" />
                    Up Next
                </div>
                <button
                    onClick={onSkip}
                    className="text-indigo-200 hover:text-white transition-colors"
                    aria-label="Skip to top"
                    title="Skip"
                >
                    <X size={18} />
                </button>
            </div>

            {/* Body */}
            <div className="flex gap-4 p-4 sm:p-6">
                {/* Thumbnail */}
                {imageUrl && (
                    <div className="relative flex-shrink-0 w-24 h-20 sm:w-36 sm:h-28 rounded-xl overflow-hidden shadow">
                        <Image
                            src={imageUrl}
                            alt={article.title}
                            fill
                            className="object-cover"
                            sizes="(max-width: 640px) 96px, 144px"
                        />
                        {category && (
                            <span className="absolute top-1 left-1 bg-indigo-600 text-white text-[10px] px-1.5 py-0.5 rounded font-bold">
                                {category}
                            </span>
                        )}
                    </div>
                )}

                {/* Text + actions */}
                <div className="flex-1 min-w-0 flex flex-col justify-between">
                    <h3 className="font-bold text-gray-900 text-sm sm:text-base line-clamp-3 leading-snug">
                        {article.title}
                    </h3>

                    <div className="flex items-center gap-3 mt-3 flex-wrap">
                        <button
                            onClick={onLoad}
                            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-4 py-2 rounded-full transition-colors shadow"
                        >
                            Continue Reading
                            <ArrowRight size={14} />
                        </button>

                        {/* Countdown ring */}
                        <div className="relative flex items-center justify-center size-9 flex-shrink-0">
                            <svg className="absolute inset-0 -rotate-90" viewBox="0 0 36 36">
                                <circle
                                    cx="18" cy="18" r="15"
                                    fill="none" stroke="#e0e7ff" strokeWidth="3"
                                />
                                <circle
                                    cx="18" cy="18" r="15"
                                    fill="none" stroke="#4f46e5" strokeWidth="3"
                                    strokeDasharray={`${(countdown / Math.ceil(autoLoadDelay / 1000)) * 94.25} 94.25`}
                                    strokeLinecap="round"
                                    className="transition-all duration-250"
                                />
                            </svg>
                            <span className="text-xs font-bold text-indigo-700 relative z-10">{countdown}</span>
                        </div>

                        <button
                            onClick={onSkip}
                            className="text-gray-400 hover:text-gray-600 text-xs underline transition-colors"
                        >
                            No thanks
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
