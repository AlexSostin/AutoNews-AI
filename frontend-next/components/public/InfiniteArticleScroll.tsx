'use client';

/**
 * InfiniteArticleScroll — auto-loads subsequent articles as user scrolls.
 * - Sentinel at the bottom triggers fetch when user approaches
 * - New articles append BELOW each article's own rating+comments section
 * - Seamless continuous feed — no preview cards or countdowns
 * - Switches URL via history.pushState as each article becomes active
 * - Fires GA4 page_view event per article switch
 * - Limits to MAX_ARTICLES to keep DOM manageable
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import ArticleUnit from '@/components/public/ArticleUnit';
import ReadingProgressBar from '@/components/public/ReadingProgressBar';
import ABImpressionTracker from '@/components/public/ABImpressionTracker';
import JsonLd from '@/components/public/JsonLd';

const MAX_ARTICLES = 5;

const getApiUrl = () => {
    if (typeof window === 'undefined') return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') return 'http://localhost:8000/api/v1';
    return 'https://heroic-healing-production-2365.up.railway.app/api/v1';
};

interface InfiniteArticleScrollProps {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    initialArticle: any;
}

type Phase = 'idle' | 'fetching' | 'done';

export default function InfiniteArticleScroll({ initialArticle }: InfiniteArticleScrollProps) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [articles, setArticles] = useState<any[]>([initialArticle]);
    const [phase, setPhase] = useState<Phase>('idle');
    const [activeSlug, setActiveSlug] = useState(initialArticle.slug);
    const [infiniteScrollEnabled, setInfiniteScrollEnabled] = useState(true);

    const sentinelRef = useRef<HTMLDivElement>(null);
    const loadedSlugsRef = useRef<string[]>([initialArticle.slug]);
    // Cooldown: prevent rapid re-triggering after an article loads
    const cooldownUntilRef = useRef<number>(0);

    // --- URL + analytics switching ---
    const handleBecameActive = useCallback((slug: string, title: string) => {
        if (slug === activeSlug) return;
        setActiveSlug(slug);
        const newUrl = `/articles/${slug}`;
        window.history.pushState({ slug }, '', newUrl);
        document.title = `${title} | Fresh Motors`;
        window.dispatchEvent(new CustomEvent('article-active-slug', { detail: slug }));
        try {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const w = window as any;
            if (typeof w.gtag === 'function') {
                w.gtag('event', 'page_view', {
                    page_location: window.location.href,
                    page_title: title,
                });
            }
        } catch { /* silent */ }
    }, [activeSlug]);

    // --- Fetch and auto-load next article ---
    const fetchAndLoad = useCallback(async () => {
        if (phase !== 'idle') return;
        // Use ref for length check to avoid stale closure
        if (loadedSlugsRef.current.length >= MAX_ARTICLES) {
            setPhase('done');
            return;
        }

        setPhase('fetching');

        const currentSlug = articles[articles.length - 1].slug;
        const excludeParam = loadedSlugsRef.current.map(s => `exclude=${encodeURIComponent(s)}`).join('&');
        const url = `${getApiUrl()}/articles/${currentSlug}/next-article/?${excludeParam}`;

        try {
            const res = await fetch(url);
            if (!res.ok) { setPhase('done'); return; }
            const data = await res.json();
            if (!data.article) { setPhase('done'); return; }

            // Directly add to the list — article renders AFTER previous article's comments
            loadedSlugsRef.current.push(data.article.slug);
            setArticles(prev => [...prev, data.article]);
            // Cooldown and phase delay must be equal to prevent dead zone
            // where sentinel is visible but cooldown blocks triggering
            cooldownUntilRef.current = Date.now() + 3000;
            setTimeout(() => setPhase('idle'), 3000);
        } catch {
            setPhase('done');
        }
    }, [phase, articles]);

    // --- Fetch infinite scroll setting ---
    useEffect(() => {
        const apiUrl = getApiUrl();
        fetch(`${apiUrl}/settings/1/`)
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data && typeof data.infinite_scroll_enabled === 'boolean') {
                    setInfiniteScrollEnabled(data.infinite_scroll_enabled);
                }
            })
            .catch(() => { /* silent */ });
    }, []);

    // --- IntersectionObserver on sentinel ---
    useEffect(() => {
        if (!infiniteScrollEnabled) return;
        if (phase !== 'idle') return;
        const el = sentinelRef.current;
        if (!el) return;

        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting) {
                    if (Date.now() < cooldownUntilRef.current) return;
                    observer.disconnect();
                    fetchAndLoad();
                }
            },
            { rootMargin: '0px 0px 800px 0px' }  // prefetch when user is ~800px away
        );
        observer.observe(el);
        return () => observer.disconnect();
    }, [fetchAndLoad, phase, articles.length, infiniteScrollEnabled]);

    // JSON-LD for initial article
    const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.freshmotors.net';
    const jsonLdData = [
        {
            '@context': 'https://schema.org',
            '@type': 'NewsArticle',
            headline: initialArticle.title,
            description: initialArticle.summary || initialArticle.seo_description,
            datePublished: initialArticle.created_at,
            dateModified: initialArticle.updated_at || initialArticle.created_at,
            author: { '@type': 'Person', name: initialArticle.author || 'Fresh Motors Team' },
            publisher: { '@type': 'Organization', name: 'Fresh Motors', url: siteUrl },
            mainEntityOfPage: { '@type': 'WebPage', '@id': `${siteUrl}/articles/${initialArticle.slug}` },
        },
    ];

    return (
        <>
            {jsonLdData.map((d, i) => <JsonLd key={i} data={d} />)}
            <ABImpressionTracker
                variantId={initialArticle.ab_variant_id}
                imageVariantId={initialArticle.ab_image_variant_id}
            />
            <ReadingProgressBar />

            <main className="flex-1 bg-gray-50">
                <div className="container mx-auto px-4 py-8">
                    <div className="max-w-4xl mx-auto space-y-12">

                        {/* --- Articles feed (rating + comments inside each ArticleUnit) --- */}
                        {articles.map((article, index) => (
                            <ArticleUnit
                                key={article.id ?? article.slug}
                                article={article}
                                index={index}
                                onBecameActive={handleBecameActive}
                            />
                        ))}

                        {/* --- Sentinel: triggers fetch when user approaches --- */}
                        {infiniteScrollEnabled && phase === 'idle' && (
                            <div ref={sentinelRef} className="h-4" aria-hidden="true" />
                        )}

                        {/* --- Loading spinner --- */}
                        {infiniteScrollEnabled && phase === 'fetching' && (
                            <div className="flex justify-center py-8">
                                <div className="size-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
                            </div>
                        )}

                        {/* --- Max reached: browse button --- */}
                        {phase === 'done' && (
                            <div className="text-center py-6">
                                <a
                                    href="/articles"
                                    className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-6 py-3 rounded-full transition shadow"
                                >
                                    Browse All Articles →
                                </a>
                            </div>
                        )}

                    </div>
                </div>
            </main>
        </>
    );
}
