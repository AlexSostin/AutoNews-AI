'use client';

/**
 * ArticleUnit — renders a single article block for the infinite scroll feed.
 * Accepts a pre-loaded article object (no slug fetch needed).
 * Notifies parent when it enters the viewport via `onBecameActive`.
 */

import { useEffect, useRef } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import AdBanner from '@/components/public/AdBanner';
import ArticleContentWithImages from '@/components/public/ArticleContentWithImages';
import ShareButtons from '@/components/public/ShareButtons';
import ImageLightbox from '@/components/public/ImageLightbox';
import SpecsCardLink from '@/components/public/SpecsCardLink';
import ViewTracker from '@/components/public/ViewTracker';
import FavoriteButton from '@/components/public/FavoriteButton';
import PriceConverter from '@/components/public/PriceConverter';
import ArticleFeedbackCapsules from '@/components/public/ArticleFeedbackCapsules';
import CommentSection from '@/components/public/CommentSection';
import FeedbackButton from '@/components/public/FeedbackButton';
import { Calendar, User, Rss, ExternalLink, Youtube, Tag, Clock } from 'lucide-react';
import AuthorCard from '@/components/public/AuthorCard';
import JsonLd from '@/components/public/JsonLd';
import TableOfContents, { TocHeading } from '@/components/public/TableOfContents';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

function formatDate(dateString: string) {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric', month: 'long', day: 'numeric',
    });
}

/** Inject anchors IDs into H2 tags and extract headings for the ToC. */
function extractAndLabelHeadings(html: string): { html: string; headings: TocHeading[] } {
    const headings: TocHeading[] = [];
    const seenIds = new Map<string, number>();
    const patched = html.replace(/<h2[^>]*>([\s\S]*?)<\/h2>/gi, (_match, inner) => {
        const raw = inner.replace(/<[^>]+>/g, '').trim();
        const text = raw
            .replace(/&amp;/g, '&')
            .replace(/&lt;/g, '<')
            .replace(/&gt;/g, '>')
            .replace(/&quot;/g, '"')
            .replace(/&#39;/g, "'")
            .replace(/&nbsp;/g, ' ');
        const base = text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'section';
        const count = seenIds.get(base) ?? 0;
        seenIds.set(base, count + 1);
        const id = count === 0 ? base : `${base}-${count}`;
        headings.push({ id, text });
        return `<h2 id="${id}">${inner}</h2>`;
    });
    return { html: patched, headings };
}

/** Estimate reading time from HTML content (200 wpm). */
function calcReadingTime(html: string): number {
    const words = html.replace(/<[^>]+>/g, ' ').trim().split(/\s+/).filter(Boolean).length;
    return Math.max(1, Math.ceil(words / 200));
}

function fixUrl(url: string | null | undefined): string {
    if (!url) return 'https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=1200';
    const isProd = typeof window !== 'undefined'
        ? !['localhost', '127.0.0.1'].includes(window.location.hostname)
        : false;
    const mediaUrl = isProd
        ? 'https://heroic-healing-production-2365.up.railway.app'
        : 'http://localhost:8000';
    if (url.startsWith('http://') || url.startsWith('https://')) {
        return url.replace('http://backend:8000', mediaUrl).replace('http://localhost:8000', mediaUrl);
    }
    return `${mediaUrl}${url}`;
}

interface ArticleUnitProps {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    article: any;
    onBecameActive?: (slug: string, title: string) => void;
    /** Index in the feed (0 = original, 1+ = auto-loaded) */
    index?: number;
}

export default function ArticleUnit({ article, onBecameActive, index = 0 }: ArticleUnitProps) {
    const headlineRef = useRef<HTMLDivElement>(null);

    // IntersectionObserver: fire onBecameActive when headline is 40%+ visible
    useEffect(() => {
        if (!onBecameActive) return;
        const el = headlineRef.current;
        if (!el) return;

        const observer = new IntersectionObserver(
            (entries) => {
                const entry = entries[0];
                if (entry.isIntersecting) {
                    onBecameActive(article.slug, article.title);
                }
            },
            { threshold: 0.4 }
        );
        observer.observe(el);
        return () => observer.disconnect();
    }, [article.slug, article.title, onBecameActive]);

    const imageUrl = fixUrl(article.image);
    const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.freshmotors.net';
    const fullUrl = `${siteUrl}/articles/${article.slug}`;

    const articleContentHtml = (article.content || '')
        .replace(/<div[^>]*class="video-container"[^>]*>[\s\S]*?<\/div>/g, '')
        .replace(/<iframe[^>]*>[\s\S]*?<\/iframe>/g, '')
        .replace(/<div[^>]*class="entity-mismatch-warning"[^>]*>[\s\S]*?<\/div>/g, '');

    // Inject IDs into H2 headings so ToC links work
    const { html: labelledContent, headings } = extractAndLabelHeadings(articleContentHtml);

    // Reading time: prefer backend value, fall back to calc from content
    const readingTime: number = article.reading_time ?? calcReadingTime(labelledContent);

    const hasYoutubeVideo = Boolean(article.youtube_url) && article.show_youtube !== false;
    const youtubeVideoId = article.youtube_url
        ? article.youtube_url.match(/(?:watch\?v=|embed\/|youtu\.be\/)([\w-]+)/)?.[1] || ''
        : '';
    const youtubeEmbedUrl = youtubeVideoId ? `https://www.youtube.com/embed/${youtubeVideoId}` : '';

    const articleImages = [
        article.thumbnail_url || article.image,
        article.image_2_url || article.image_2,
        article.image_3_url || article.image_3,
    ].filter((url): url is string => Boolean(url)).map(url => fixUrl(url));

    const allGalleryImages: { url: string; alt: string }[] = [];
    if (article.thumbnail_url) allGalleryImages.push({ url: fixUrl(article.thumbnail_url), alt: `${article.title} - View 1` });
    if (article.image_2_url) allGalleryImages.push({ url: fixUrl(article.image_2_url), alt: `${article.title} - View 2` });
    if (article.image_3_url) allGalleryImages.push({ url: fixUrl(article.image_3_url), alt: `${article.title} - View 3` });
    if (article.images?.length > 0) {
        article.images.forEach((img: any) => {
            const imgUrl = img.image_url || img.image;
            if (imgUrl) allGalleryImages.push({ url: fixUrl(imgUrl), alt: img.caption || `${article.title}` });
        });
    }

    return (
        <article data-article-slug={article.slug} data-article-index={index}>
            <ViewTracker
                articleSlug={article.slug}
                articleId={article.id}
                articleTitle={article.title}
                categoryName={article.categories?.[0]?.name}
            />

            {/* NewsArticle JSON-LD for SEO rich results */}
            <JsonLd data={{
                "@context": "https://schema.org",
                "@type": "NewsArticle",
                "headline": article.title,
                "description": article.summary || '',
                "datePublished": article.created_at,
                "dateModified": article.updated_at || article.created_at,
                "image": fixUrl(article.image),
                "url": fullUrl,
                "author": {
                    "@type": "Person",
                    "name": article.author_name || "Alexander Sostin",
                    "url": "https://www.freshmotors.net"
                },
                "publisher": {
                    "@type": "Organization",
                    "name": "Fresh Motors",
                    "url": "https://www.freshmotors.net",
                    "logo": {
                        "@type": "ImageObject",
                        "url": "https://www.freshmotors.net/logo.png"
                    }
                },
                "mainEntityOfPage": {
                    "@type": "WebPage",
                    "@id": fullUrl
                }
            }} />

            {/* BreadcrumbList JSON-LD for Google breadcrumb display */}
            <JsonLd data={{
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://www.freshmotors.net" },
                    ...(article.categories?.[0] ? [{
                        "@type": "ListItem" as const,
                        "position": 2,
                        "name": article.categories[0].name,
                        "item": `https://www.freshmotors.net/categories/${article.categories[0].slug}`
                    }] : []),
                    {
                        "@type": "ListItem",
                        "position": article.categories?.[0] ? 3 : 2,
                        "name": article.title
                    }
                ]
            }} />

            {/* Divider between articles */}
            {index > 0 && (
                <div className="flex items-center gap-4 my-6">
                    <div className="flex-1 border-t-2 border-dashed border-indigo-200" />
                    <span className="text-xs text-indigo-400 font-semibold tracking-wider uppercase whitespace-nowrap">
                        Next Article
                    </span>
                    <div className="flex-1 border-t-2 border-dashed border-indigo-200" />
                </div>
            )}

            {/* Hero Image — floats above background, no black bars, no pixel artifacts */}
            <div className="relative h-[250px] sm:h-[350px] md:h-[500px] max-h-[600px] w-full rounded-2xl overflow-hidden will-change-transform"
                style={{ boxShadow: '0 8px 32px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.10)' }}>
                <Image
                    src={imageUrl}
                    alt={article.title}
                    fill
                    className="object-cover"
                    priority={index === 0}
                    loading={index === 0 ? 'eager' : 'lazy'}
                    unoptimized
                />
                {article.categories?.[0] && (
                    <div className="absolute top-4 left-4">
                        <Link
                            href={`/categories/${article.categories[0].slug}`}
                            className="bg-indigo-600 text-white px-4 py-1.5 rounded-full text-sm font-bold shadow-lg hover:bg-indigo-700 transition"
                        >
                            {article.categories[0].name}
                        </Link>
                    </div>
                )}
            </div>

            {/* Article header — this is the IntersectionObserver target */}
            <div ref={headlineRef} className="mt-6 mb-4">
                <div className="flex flex-wrap gap-4 text-xs sm:text-sm text-gray-600 items-center mb-4">
                    <div className="flex items-center gap-2">
                        <Clock size={14} className="text-indigo-600" />
                        <span>{readingTime} min read</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Calendar size={14} className="text-indigo-600" />
                        <span>{formatDate(article.created_at)}</span>
                    </div>
                    {(article.show_source !== false) && article.author_name && (
                        <div className="flex items-center gap-2">
                            <User size={14} className="text-indigo-600" />
                            <span className="font-bold">Source:</span>
                            {article.author_channel_url ? (
                                <a href={article.author_channel_url} target="_blank" rel="noopener noreferrer"
                                    className="text-indigo-600 hover:text-indigo-800 font-bold transition-colors">
                                    {article.author_name}
                                </a>
                            ) : <span>{article.author_name}</span>}
                        </div>
                    )}
                    {article.rss_feed && (
                        <div className="flex items-center gap-2">
                            <Rss size={14} className="text-orange-600" />
                            <span>{article.rss_feed.name}</span>
                            {article.source_url && (
                                <a href={article.source_url} target="_blank" rel="noopener noreferrer"
                                    className="text-orange-600 hover:text-orange-800 flex items-center gap-1">
                                    <ExternalLink size={12} /> Original
                                </a>
                            )}
                        </div>
                    )}
                </div>

                <div className="flex items-start justify-between gap-4">
                    <h1 className="text-2xl sm:text-3xl md:text-4xl font-extrabold text-gray-900 flex-1 leading-tight">
                        <Link href={`/articles/${article.slug}`} className="hover:text-indigo-700 transition-colors">
                            {article.title}
                        </Link>
                    </h1>
                    <FavoriteButton articleId={article.id} initialIsFavorited={article.is_favorited} size="lg" />
                </div>

                {article.summary && (
                    <p className="text-base sm:text-lg text-gray-600 mt-3 max-w-3xl">{article.summary}</p>
                )}


            </div>

            {/* Table of contents — parsed from H2 headings */}
            <TableOfContents headings={headings} />

            {/* Content */}
            <div className="space-y-6 mt-6">
                <AdBanner position="header" />

                <div className="bg-white rounded-xl shadow-md p-6 sm:p-8">
                    <ArticleContentWithImages
                        content={labelledContent}
                        images={articleImages}
                        imageSource={article.image_source}
                        authorName={article.author_name}
                        articleId={article.id}
                        apiUrl={API_URL}
                    />
                </div>

                {article.tags?.length > 0 && (
                    <SpecsCardLink
                        articleId={article.id}
                        articleTitle={article.title}
                        tagNames={article.tags.map((t: any) => typeof t === 'string' ? t : t.name)}
                    />
                )}

                <AdBanner position="after_content" />

                {hasYoutubeVideo && (
                    <div className="bg-white rounded-xl shadow-md p-4 sm:p-8">
                        <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-3">
                            <Youtube className="text-red-600" size={24} />
                            Watch Video Review
                        </h3>
                        <div className="relative w-full aspect-video rounded-xl overflow-hidden shadow-lg">
                            <iframe
                                src={youtubeEmbedUrl}
                                title={article.title}
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                                allowFullScreen
                                loading="lazy"
                                className="absolute inset-0 w-full h-full"
                            />
                        </div>
                    </div>
                )}

                {allGalleryImages.length > 0 && (
                    <div className="bg-white rounded-xl shadow-md p-4 sm:p-8">
                        <h3 className="text-xl font-bold text-gray-900 mb-4">Vehicle Gallery</h3>
                        <ImageLightbox images={allGalleryImages} />
                    </div>
                )}

                <ShareButtons url={fullUrl} title={article.title} />

                {/* Author signature */}
                <AuthorCard />


                {article.tag_names?.length > 0 && (
                    <div className="bg-white rounded-xl shadow-md p-6">
                        <div className="flex items-center gap-3 flex-wrap">
                            <Tag size={18} className="text-indigo-600" />
                            {article.tag_names.map((tag: string) => (
                                <Link key={tag} href={`/articles?tag=${tag}`}
                                    className="px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-full hover:bg-indigo-100 transition-colors text-sm font-medium border border-indigo-100">
                                    {tag}
                                </Link>
                            ))}
                        </div>
                    </div>
                )}

                <AdBanner position="sidebar" />
            </div>

            {/* --- Rating + Comments for every article in the feed --- */}
            <div className="space-y-6 mt-6">
                <ArticleFeedbackCapsules
                    articleSlug={article.slug}
                    initialRating={article.average_rating}
                    ratingCount={article.rating_count}
                />
                <FeedbackButton articleSlug={article.slug} />
                <CommentSection articleId={article.id} />
            </div>
        </article>
    );
}
