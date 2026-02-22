'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Calendar, ArrowRight, ChevronLeft, ChevronRight } from 'lucide-react';

interface Article {
    id: number;
    title: string;
    slug: string;
    summary: string;
    categories: { id: number; name: string; slug: string }[];
    image: string;
    created_at: string;
    is_hero: boolean;
    views: number;
}

interface SiteSettings {
    use_classic_hero: boolean;
    hero_title: string;
    hero_subtitle: string;
}

interface HeroProps {
    articles: Article[];
    settings: SiteSettings | null;
}

export default function Hero({ articles, settings }: HeroProps) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [touchStart, setTouchStart] = useState<number | null>(null);
    const [touchEnd, setTouchEnd] = useState<number | null>(null);

    // Minimum distance for a swipe to be registered
    const minSwipeDistance = 50;

    // Hero logic: manually marked articles first, then top by views
    const heroArticles = (() => {
        if (articles.length === 0) return [];

        // 1. Manually marked hero articles always come first
        const manualHeroes = articles.filter(a => a.is_hero);

        if (manualHeroes.length >= 5) return manualHeroes.slice(0, 5);

        // 2. Fill remaining slots with top articles by views (excluding already selected)
        const manualIds = new Set(manualHeroes.map(a => a.id));
        const remaining = articles
            .filter(a => !manualIds.has(a.id) && a.image) // must have image
            .sort((a, b) => (b.views || 0) - (a.views || 0));

        return [...manualHeroes, ...remaining].slice(0, 5);
    })();

    const useClassic = settings?.use_classic_hero || heroArticles.length === 0;

    useEffect(() => {
        if (!useClassic && heroArticles.length > 1) {
            const timer = setInterval(() => {
                setCurrentIndex((prev) => (prev + 1) % heroArticles.length);
            }, 7000);
            return () => clearInterval(timer);
        }
    }, [useClassic, heroArticles.length]);

    const nextSlide = () => {
        setCurrentIndex((prev) => (prev + 1) % heroArticles.length);
    };

    const prevSlide = () => {
        setCurrentIndex((prev) => (prev - 1 + heroArticles.length) % heroArticles.length);
    };

    const onTouchStart = (e: React.TouchEvent) => {
        setTouchEnd(null);
        setTouchStart(e.targetTouches[0].clientX);
    };

    const onTouchMove = (e: React.TouchEvent) => {
        setTouchEnd(e.targetTouches[0].clientX);
    };

    const onTouchEnd = () => {
        if (!touchStart || !touchEnd) return;
        const distance = touchStart - touchEnd;
        const isLeftSwipe = distance > minSwipeDistance;
        const isRightSwipe = distance < -minSwipeDistance;

        if (isLeftSwipe) {
            nextSlide();
        } else if (isRightSwipe) {
            prevSlide();
        }
    };

    // Helper to fix image URLs
    const fixUrl = (url: string | null | undefined): string => {
        if (!url) return 'https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=1200';

        const PROD_MEDIA = 'https://heroic-healing-production-2365.up.railway.app';
        const LOCAL_MEDIA = 'http://localhost:8000';

        // Check if we are in browser (client-side)
        const isProd = typeof window !== 'undefined'
            ? window.location.hostname.includes('railway.app') || window.location.hostname.includes('autonews-ai')
            : process.env.RAILWAY_ENVIRONMENT === 'production';

        const mediaUrl = isProd ? PROD_MEDIA : LOCAL_MEDIA;

        if (url.startsWith('http://') || url.startsWith('https://')) {
            return url.replace('http://backend:8000', mediaUrl).replace('http://localhost:8000', mediaUrl);
        }
        return `${mediaUrl}${url}`;
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    };

    if (useClassic) {
        return (
            <section className="bg-gradient-to-br from-slate-900 via-purple-900 to-gray-900 text-white py-24 relative overflow-hidden min-h-[500px] flex items-center">
                <div className="absolute inset-0 bg-black/10"></div>
                <div className="container mx-auto px-4 text-center relative z-10">
                    <h1 className="text-4xl sm:text-5xl md:text-7xl font-bold mb-6 drop-shadow-lg animate-fade-in">
                        {settings?.hero_title || 'Welcome to Fresh Motors'}
                    </h1>
                    <p className="text-lg sm:text-xl md:text-2xl mb-10 text-white/90 max-w-3xl mx-auto leading-relaxed">
                        {settings?.hero_subtitle || 'Your premier source for automotive news, reviews, and insights'}
                    </p>
                    <Link
                        href="/articles"
                        className="bg-white text-purple-900 px-8 sm:px-12 py-4 sm:py-5 rounded-full font-extrabold hover:bg-purple-50 hover:shadow-2xl transition-all inline-block text-lg sm:text-xl shadow-lg hover:scale-105 transform active:scale-95"
                    >
                        Explore Articles <ArrowRight className="inline-block ml-2 w-5 h-5" />
                    </Link>
                </div>

                {/* Decorative elements */}
                <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-purple-500/20 rounded-full blur-3xl animate-pulse"></div>
                <div className="absolute -top-24 -right-24 w-96 h-96 bg-indigo-500/20 rounded-full blur-3xl animate-pulse delay-1000"></div>

                <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-gray-50 to-transparent z-10"></div>
            </section>
        );
    }

    return (
        <section
            className="relative aspect-video sm:h-[550px] md:h-[700px] w-full overflow-hidden bg-black touch-pan-y"
            onTouchStart={onTouchStart}
            onTouchMove={onTouchMove}
            onTouchEnd={onTouchEnd}
        >
            {heroArticles.map((article, index) => (
                <div
                    key={article.id}
                    className={`absolute inset-0 transition-opacity duration-1000 ease-in-out ${index === currentIndex ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'
                        }`}
                >
                    {/* Main Image Layer */}
                    <div className="absolute inset-0 z-0">
                        <Image
                            src={fixUrl(article.image)}
                            alt={article.title}
                            fill
                            className="object-cover"
                            priority={index === 0}
                            loading={index === 0 ? "eager" : "lazy"}
                            unoptimized
                        />
                        {/* Progressive Gradient Overlay: Ensures text readability while keeping car visible */}
                        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent"></div>
                    </div>

                    {/* Content Overlay */}
                    <div className="relative h-full flex flex-col justify-end px-6 pb-12 sm:pb-16 md:pb-32 z-20">
                        <div className="max-w-4xl animate-slide-up">
                            <div className="flex items-center gap-3 mb-2 md:mb-4">
                                <span className="bg-indigo-600 text-white text-[10px] md:text-sm font-bold px-2 md:px-3 py-0.5 md:py-1 rounded-full uppercase tracking-wider">
                                    {article.categories?.[0]?.name || 'News'}
                                </span>
                                <span className="text-white/70 text-[10px] md:text-sm flex items-center gap-1 font-medium bg-black/40 backdrop-blur-md px-2 md:px-3 py-0.5 md:py-1 rounded-full">
                                    <Calendar size={12} className="md:w-3.5 md:h-3.5" />
                                    {formatDate(article.created_at)}
                                </span>
                            </div>

                            <h1 className="text-lg sm:text-3xl md:text-5xl lg:text-6xl font-black text-white mb-4 md:mb-6 leading-tight drop-shadow-2xl line-clamp-2">
                                {article.title}
                            </h1>

                            <p className="hidden md:block text-lg md:text-xl text-gray-200 mb-8 line-clamp-2 md:line-clamp-3 max-w-2xl leading-relaxed">
                                {article.summary}
                            </p>

                            <div className="flex items-center gap-3 md:gap-4 relative z-30">
                                <Link
                                    href={`/articles/${article.slug}`}
                                    className="bg-indigo-600 text-white px-5 md:px-8 py-2.5 md:py-4 rounded-lg md:rounded-xl font-bold hover:bg-indigo-700 hover:shadow-xl transition-all inline-flex items-center justify-center text-sm md:text-lg shadow-lg hover:scale-105 transform active:scale-95 group"
                                >
                                    Read <ArrowRight className="ml-2 w-4 h-4 md:w-5 md:h-5 group-hover:translate-x-1 transition-transform" />
                                </Link>
                                <Link
                                    href="/articles"
                                    className="bg-white/10 backdrop-blur-md text-white border border-white/20 px-5 md:px-8 py-2.5 md:py-4 rounded-lg md:rounded-xl font-bold hover:bg-white/20 transition-all inline-flex items-center justify-center text-sm md:text-lg hover:scale-105 transform active:scale-95"
                                >
                                    Explore
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            ))}

            {/* Navigation Buttons (Desktop) */}
            {
                heroArticles.length > 1 && (
                    <>
                        <button
                            onClick={prevSlide}
                            className="hidden md:flex absolute left-8 top-1/2 -translate-y-1/2 bg-black/20 hover:bg-black/40 backdrop-blur-md text-white p-4 rounded-full transition-all border border-white/10 hover:scale-110 active:scale-90 z-20 group"
                            aria-label="Previous slide"
                        >
                            <ChevronLeft size={32} />
                        </button>
                        <button
                            onClick={nextSlide}
                            className="hidden md:flex absolute right-8 top-1/2 -translate-y-1/2 bg-black/20 hover:bg-black/40 backdrop-blur-md text-white p-4 rounded-full transition-all border border-white/10 hover:scale-110 active:scale-90 z-20"
                            aria-label="Next slide"
                        >
                            <ChevronRight size={32} />
                        </button>
                    </>
                )
            }

            {/* Dots Navigation */}
            {
                heroArticles.length > 1 && (
                    <div className="absolute bottom-6 md:bottom-10 left-1/2 -translate-x-1/2 flex gap-2 md:gap-3 z-30">
                        {heroArticles.map((_, index) => (
                            <button
                                key={index}
                                onClick={() => setCurrentIndex(index)}
                                className={`transition-all duration-300 rounded-full h-1.5 md:h-2 ${index === currentIndex ? 'w-8 md:w-10 bg-indigo-500 shadow-lg' : 'bg-white/20 md:bg-white/40'
                                    }`}
                                aria-label={`Go to slide ${index + 1}`}
                            />
                        ))}
                    </div>
                )
            }

            {/* Bottom Fade (Desktop only) */}
            <div className="hidden md:block absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-gray-50 to-transparent z-10"></div>
        </section >
    );
}
