'use client';

/**
 * InfiniteArticleScroll — orchestrates loading of subsequent articles.
 * - Watches the bottom of the last article with IntersectionObserver sentinel
 * - Shows NextArticlePreview card before loading next article
 * - Switches URL via history.pushState as each article becomes active
 * - Fires GA4 page_view event per article switch
 * - Limits to MAX_ARTICLES to keep DOM manageable
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import ArticleUnit from '@/components/public/ArticleUnit';
import NextArticlePreview from '@/components/public/NextArticlePreview';
import CommentSection from '@/components/public/CommentSection';
import RelatedCarousel from '@/components/public/RelatedCarousel';
import ReadingProgressBar from '@/components/public/ReadingProgressBar';
import FeedbackButton from '@/components/public/FeedbackButton';
import RatingStars from '@/components/public/RatingStars';
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

type Phase = 'reading' | 'preview' | 'loading' | 'done';

export default function InfiniteArticleScroll({ initialArticle }: InfiniteArticleScrollProps) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [articles, setArticles] = useState<any[]>([initialArticle]);
    const [previewArticle, setPreviewArticle] = useState<any | null>(null);
    const [phase, setPhase] = useState<Phase>('reading');
    const [activeSlug, setActiveSlug] = useState(initialArticle.slug);
    const sentinelRef = useRef<HTMLDivElement>(null);
    const loadedSlugsRef = useRef<string[]>([initialArticle.slug]);

    // --- URL + analytics switching ---
    const handleBecameActive = useCallback((slug: string, title: string) => {
        if (slug === activeSlug) return;
        setActiveSlug(slug);
        // pushState: update URL without navigation
        const newUrl = `/articles/${slug}`;
        window.history.pushState({ slug }, '', newUrl);
        document.title = `${title} | Fresh Motors`;
        // GA4 virtual pageview
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

    // --- Fetch next article ---
    const fetchNext = useCallback(async () => {
        if (phase !== 'reading') return;
        if (articles.length >= MAX_ARTICLES) {
            setPhase('done');
            return;
        }

        const currentSlug = articles[articles.length - 1].slug;
        const excludeParam = loadedSlugsRef.current.map(s => `exclude=${encodeURIComponent(s)}`).join('&');
        const url = `${getApiUrl()}/articles/${currentSlug}/next-article/?${excludeParam}`;

        try {
            const res = await fetch(url);
            if (!res.ok) { setPhase('done'); return; }
            const data = await res.json();
            if (!data.article) { setPhase('done'); return; }

            setPreviewArticle(data.article);
            setPhase('preview');
        } catch {
            setPhase('done');
        }
    }, [phase, articles]);

    // --- IntersectionObserver on sentinel ---
    useEffect(() => {
        if (phase !== 'reading') return;
        const el = sentinelRef.current;
        if (!el) return;

        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting) {
                    observer.disconnect();
                    fetchNext();
                }
            },
            { rootMargin: '200px' } // start 200px before the bottom
        );
        observer.observe(el);
        return () => observer.disconnect();
    }, [fetchNext, phase, articles.length]); // re-attach after new article loads

    // --- Load next article after preview approval ---
    const handleLoadNext = useCallback(() => {
        if (!previewArticle) return;
        setPhase('loading');
        loadedSlugsRef.current.push(previewArticle.slug);
        setArticles(prev => [...prev, previewArticle]);
        setPreviewArticle(null);
        setPhase('reading');
    }, [previewArticle]);

    const handleSkip = useCallback(() => {
        setPreviewArticle(null);
        setPhase('done');
    }, []);

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

                        {/* --- Feed of articles --- */}
                        {articles.map((article, index) => (
                            <ArticleUnit
                                key={article.slug}
                                article={article}
                                index={index}
                                onBecameActive={handleBecameActive}
                            />
                        ))}

                        {/* --- Sentinel: triggers fetch when visible --- */}
                        {phase === 'reading' && (
                            <div ref={sentinelRef} className="h-4" aria-hidden="true" />
                        )}

                        {/* --- Loading spinner --- */}
                        {phase === 'loading' && (
                            <div className="flex justify-center py-8">
                                <div className="size-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
                            </div>
                        )}

                        {/* --- Next article preview card --- */}
                        {phase === 'preview' && previewArticle && (
                            <NextArticlePreview
                                article={previewArticle}
                                onLoad={handleLoadNext}
                                onSkip={handleSkip}
                            />
                        )}

                        {/* --- Max reached: manual load more --- */}
                        {phase === 'done' && articles.length >= MAX_ARTICLES && (
                            <div className="text-center py-6">
                                <a
                                    href="/articles"
                                    className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-6 py-3 rounded-full transition shadow"
                                >
                                    Browse All Articles →
                                </a>
                            </div>
                        )}

                        {/* --- Bottom of FIRST article: comments + related (always shown) --- */}
                        <div className="space-y-6 mt-2">
                            <FeedbackButton articleSlug={initialArticle.slug} />
                            <RatingStars
                                articleSlug={initialArticle.slug}
                                initialRating={initialArticle.average_rating}
                                ratingCount={initialArticle.rating_count}
                            />
                            {initialArticle.categories?.[0]?.slug && (
                                <RelatedCarousel
                                    categorySlug={initialArticle.categories[0].slug}
                                    currentArticleSlug={activeSlug}
                                    currentArticleId={initialArticle.id}
                                />
                            )}
                            <CommentSection articleId={initialArticle.id} />
                        </div>

                    </div>
                </div>
            </main>
        </>
    );
}
