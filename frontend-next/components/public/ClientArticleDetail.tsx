'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import AdBanner from '@/components/public/AdBanner';
import ABTitle from '@/components/public/ABTitle';
import ABImpressionTracker from '@/components/public/ABImpressionTracker';
import ShareButtons from '@/components/public/ShareButtons';
import RatingStars from '@/components/public/RatingStars';
import ArticleContentWithImages from '@/components/public/ArticleContentWithImages';
import ArticleRating from '@/components/public/ArticleRating';
import CommentSection from '@/components/public/CommentSection';
import Breadcrumbs from '@/components/public/Breadcrumbs';
import FavoriteButton from '@/components/public/FavoriteButton';
import ReadingProgressBar from '@/components/public/ReadingProgressBar';
import ReadingTime from '@/components/public/ReadingTime';
import ViewStats from '@/components/public/ViewStats';
import ViewTracker from '@/components/public/ViewTracker';
import PriceConverter from '@/components/public/PriceConverter';
import JsonLd from '@/components/public/JsonLd';
import RelatedCarousel from '@/components/public/RelatedCarousel';
import FeedbackButton from '@/components/public/FeedbackButton';
import SpecsCardLink from '@/components/public/SpecsCardLink';
import ImageLightbox from '@/components/public/ImageLightbox';
import {
    Calendar, User, Tag, Youtube, ExternalLink, Rss
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

function formatDate(dateString: string) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
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

export default function ClientArticleDetail({ slug }: { slug: string }) {
    const [article, setArticle] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        fetch(`${API_URL}/articles/${slug}/`)
            .then(res => {
                if (!res.ok) throw new Error(`${res.status}`);
                return res.json();
            })
            .then(data => setArticle(data))
            .catch(() => setError(true))
            .finally(() => setLoading(false));
    }, [slug]);

    if (loading) return <ArticleDetailSkeleton />;
    if (error || !article) {
        return (
            <main className="flex-1 bg-gray-50 flex items-center justify-center min-h-screen">
                <div className="text-center py-20">
                    <h1 className="text-4xl font-bold text-gray-900 mb-4">Article Not Found</h1>
                    <p className="text-gray-600 mb-8">The article you're looking for doesn't exist or has been removed.</p>
                    <Link href="/articles" className="bg-indigo-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-indigo-700 transition">
                        Browse Articles
                    </Link>
                </div>
            </main>
        );
    }

    const imageUrl = fixUrl(article.image);
    const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.freshmotors.net';
    const fullUrl = `${siteUrl}/articles/${article.slug}`;
    const categoryName = article.categories?.[0]?.name || 'News';
    const categorySlug = article.categories?.[0]?.slug || 'news';

    const articleContentHtml = (article.content || '')
        .replace(/<div[^>]*class="video-container"[^>]*>[\s\S]*?<\/div>/g, '')
        .replace(/<iframe[^>]*>[\s\S]*?<\/iframe>/g, '')
        .replace(/<div[^>]*class="entity-mismatch-warning"[^>]*>[\s\S]*?<\/div>/g, '');

    const hasYoutubeVideo = Boolean(article.youtube_url) && article.show_youtube !== false;
    const youtubeVideoId = article.youtube_url
        ? article.youtube_url.match(/(?:watch\?v=|embed\/|youtu\.be\/)([\w-]+)/)?.[1] || ''
        : '';
    const youtubeEmbedUrl = youtubeVideoId ? `https://www.youtube.com/embed/${youtubeVideoId}` : '';

    const articleImages = [
        article.thumbnail_url || article.image,
        article.image_2_url || article.image_2,
        article.image_3_url || article.image_3
    ].filter((url): url is string => Boolean(url)).map(url => fixUrl(url));

    // JSON-LD
    const jsonLdData: Record<string, unknown>[] = [
        {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": article.title,
            "description": article.summary || article.seo_description,
            "image": articleImages,
            "datePublished": article.created_at,
            "dateModified": article.updated_at || article.created_at,
            "author": { "@type": "Person", "name": article.author || "Fresh Motors Team" },
            "publisher": { "@type": "Organization", "name": "Fresh Motors", "url": siteUrl },
            "mainEntityOfPage": { "@type": "WebPage", "@id": fullUrl },
            "articleSection": categoryName,
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                { "@type": "ListItem", "position": 1, "name": "Home", "item": siteUrl },
                { "@type": "ListItem", "position": 2, "name": categoryName, "item": `${siteUrl}/articles?category=${categorySlug}` },
                { "@type": "ListItem", "position": 3, "name": article.title }
            ]
        }
    ];

    return (
        <>
            {jsonLdData.map((data, i) => (
                <JsonLd key={i} data={data} />
            ))}

            <ViewTracker
                articleSlug={article.slug}
                articleId={article.id}
                articleTitle={article.title}
                categoryName={article.categories?.[0]?.name}
            />
            <ABImpressionTracker
                variantId={article.ab_variant_id}
                imageVariantId={article.ab_image_variant_id}
            />
            <ReadingProgressBar />

            <main className="flex-1 bg-gray-50">
                {/* Hero Image */}
                <div className="relative h-[250px] sm:h-[350px] md:h-[500px] lg:h-[600px] xl:h-[650px] 2xl:h-[700px] max-h-[700px] w-full">
                    <Image
                        src={imageUrl}
                        alt={article.title}
                        fill
                        className="object-cover"
                        priority
                        loading="eager"
                        unoptimized
                    />
                </div>

                <div className="container mx-auto px-4 py-8">
                    <div className="max-w-4xl mx-auto">
                        {/* Breadcrumbs */}
                        <div className="mb-6">
                            <Breadcrumbs
                                items={[
                                    ...(article.categories?.length > 0 ? [{ label: article.categories[0].name, href: `/categories/${article.categories[0].slug}` }] : []),
                                    { label: article.title }
                                ]}
                            />
                        </div>

                        {/* Article Meta */}
                        <div className="mb-6">
                            <div className="flex flex-wrap gap-4 sm:gap-6 text-xs sm:text-sm text-gray-600 items-center">
                                <div className="flex items-center gap-2">
                                    <Calendar size={16} className="text-indigo-600" />
                                    <span>{formatDate(article.created_at)}</span>
                                </div>

                                {(article.show_source !== false) && article.author_name ? (
                                    <div className="flex items-center gap-2">
                                        <User size={16} className="text-indigo-600" />
                                        <span className="font-bold">Source:</span>
                                        {article.author_channel_url ? (
                                            <a href={article.author_channel_url} target="_blank" rel="noopener noreferrer"
                                                className="text-indigo-600 hover:text-indigo-800 transition-colors font-bold">
                                                {article.author_name}
                                            </a>
                                        ) : (
                                            <span>{article.author_name}</span>
                                        )}
                                    </div>
                                ) : ((article.show_source !== false) && article.author && (
                                    <div className="flex items-center gap-2">
                                        <User size={16} className="text-indigo-600" />
                                        <span>{article.author}</span>
                                    </div>
                                ))}

                                {article.rss_feed && (
                                    <div className="flex items-center gap-2">
                                        <Rss size={16} className="text-orange-600" />
                                        <span className="font-bold">Source:</span>
                                        <span>{article.rss_feed.name}</span>
                                        {article.source_url && (
                                            <a href={article.source_url} target="_blank" rel="noopener noreferrer"
                                                className="text-orange-600 hover:text-orange-800 transition-colors flex items-center gap-1">
                                                <ExternalLink size={14} /> Original
                                            </a>
                                        )}
                                    </div>
                                )}

                                <ReadingTime content={article.content} />

                                {(article.average_rating > 0 && article.rating_count > 0) && (
                                    <ArticleRating
                                        initialRating={article.average_rating}
                                        initialCount={article.rating_count}
                                    />
                                )}
                            </div>

                            {article.views && article.views > 0 && (
                                <div className="mt-4">
                                    <ViewStats views={article.views} createdAt={article.created_at} isTrending={article.views > 100} />
                                </div>
                            )}
                        </div>

                        {/* Title Section */}
                        <div className="mb-8">
                            {article.categories && article.categories.length > 0 && (
                                <div className="flex flex-wrap gap-2 mb-4">
                                    {article.categories.map((cat: any) => (
                                        <Link key={cat.id} href={`/categories/${cat.slug}`}
                                            className="inline-block bg-indigo-600 text-white px-4 py-2 rounded-full text-sm font-bold hover:bg-indigo-700 transition-colors">
                                            {cat.name}
                                        </Link>
                                    ))}
                                </div>
                            )}
                            <div className="flex items-start justify-between gap-4 mb-4">
                                <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold text-gray-900 flex-1">
                                    <ABTitle articleSlug={article.slug} originalTitle={article.title} />
                                </h1>
                                <FavoriteButton articleId={article.id} initialIsFavorited={article.is_favorited} size="lg" />
                            </div>
                            <p className="text-base sm:text-lg md:text-xl text-gray-600 max-w-3xl">
                                {article.summary}
                            </p>

                            {article.price_usd && article.show_price !== false && (
                                <div className="mt-4">
                                    <PriceConverter priceUsd={article.price_usd} />
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="max-w-4xl mx-auto">
                        <div className="space-y-8">
                            <AdBanner position="header" />

                            <div className="bg-white rounded-xl shadow-md p-8">
                                <ArticleContentWithImages
                                    content={articleContentHtml}
                                    images={articleImages}
                                    imageSource={article.image_source}
                                    authorName={article.author_name}
                                    articleId={article.id}
                                    apiUrl={API_URL}
                                />
                            </div>

                            {article.tags && article.tags.length > 0 && (
                                <SpecsCardLink
                                    articleId={article.id}
                                    articleTitle={article.title}
                                    tagNames={article.tags.map((t: any) => typeof t === 'string' ? t : t.name)}
                                />
                            )}

                            <AdBanner position="after_content" />

                            {hasYoutubeVideo && (
                                <div className="bg-white rounded-xl shadow-md p-4 sm:p-8">
                                    <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-4 sm:mb-6 flex items-center gap-3">
                                        <Youtube className="text-red-600" size={28} />
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

                            {/* Vehicle Gallery */}
                            {(() => {
                                const allImages: { url: string; alt: string }[] = [];
                                if (article.thumbnail_url) allImages.push({ url: fixUrl(article.thumbnail_url), alt: `${article.title} - View 1` });
                                if (article.image_2_url) allImages.push({ url: fixUrl(article.image_2_url), alt: `${article.title} - View 2` });
                                if (article.image_3_url) allImages.push({ url: fixUrl(article.image_3_url), alt: `${article.title} - View 3` });
                                if (article.images && article.images.length > 0) {
                                    article.images.forEach((img: any) => {
                                        const imgUrl = img.image_url || img.image;
                                        if (imgUrl) allImages.push({ url: fixUrl(imgUrl), alt: img.caption || `${article.title} - View ${allImages.length + 1}` });
                                    });
                                }
                                if (allImages.length === 0) return null;
                                return (
                                    <div className="bg-white rounded-xl shadow-md p-4 sm:p-8">
                                        <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-4 sm:mb-6">Vehicle Gallery</h3>
                                        <ImageLightbox images={allImages} />
                                    </div>
                                );
                            })()}

                            <ShareButtons url={fullUrl} title={article.title} />
                            <div className="flex justify-center">
                                <FeedbackButton articleSlug={article.slug} />
                            </div>
                            <RatingStars articleSlug={article.slug} initialRating={article.average_rating} ratingCount={article.rating_count} />

                            {article.tag_names && article.tag_names.length > 0 && (
                                <div className="bg-white rounded-xl shadow-md p-6">
                                    <div className="flex items-center gap-3 flex-wrap">
                                        <Tag size={20} className="text-indigo-600" />
                                        {article.tag_names.map((tag: string) => (
                                            <Link key={tag} href={`/articles?tag=${tag}`}
                                                className="px-4 py-2 bg-indigo-50 text-indigo-700 rounded-full hover:bg-indigo-100 transition-colors font-medium border border-indigo-100">
                                                {tag}
                                            </Link>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <AdBanner position="sidebar" />

                            {article.categories?.[0]?.slug && (
                                <RelatedCarousel
                                    categorySlug={article.categories[0].slug}
                                    currentArticleSlug={article.slug}
                                    currentArticleId={article.id}
                                />
                            )}

                            <CommentSection articleId={article.id} />
                        </div>
                    </div>
                </div>
            </main>
        </>
    );
}

function ArticleDetailSkeleton() {
    return (
        <main className="flex-1 bg-gray-50">
            {/* Hero skeleton */}
            <div className="relative h-[250px] sm:h-[350px] md:h-[500px] lg:h-[600px] w-full bg-gray-300 animate-pulse" />
            <div className="container mx-auto px-4 py-8">
                <div className="max-w-4xl mx-auto space-y-6">
                    {/* Breadcrumbs skeleton */}
                    <div className="h-4 bg-gray-200 rounded w-1/3 animate-pulse" />
                    {/* Meta skeleton */}
                    <div className="flex gap-4">
                        <div className="h-4 bg-gray-200 rounded w-32 animate-pulse" />
                        <div className="h-4 bg-gray-200 rounded w-24 animate-pulse" />
                    </div>
                    {/* Title skeleton */}
                    <div className="h-10 bg-gray-200 rounded w-3/4 animate-pulse" />
                    <div className="h-6 bg-gray-200 rounded w-full animate-pulse" />
                    <div className="h-6 bg-gray-200 rounded w-2/3 animate-pulse" />
                    {/* Content skeleton */}
                    <div className="bg-white rounded-xl shadow-md p-8 space-y-4">
                        {[1, 2, 3, 4, 5, 6].map(i => (
                            <div key={i} className="h-4 bg-gray-200 rounded animate-pulse" style={{ width: `${90 - i * 5}%` }} />
                        ))}
                    </div>
                </div>
            </div>
        </main>
    );
}
