import { notFound } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import ArticleCard from '@/components/public/ArticleCard';
import AdBanner from '@/components/public/AdBanner';
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
import { Article } from '@/types';
import {
  Calendar,
  User,
  Eye,
  Tag,
  Star,
  Youtube,
  Handshake,
  ExternalLink,
  AlertTriangle,
  Rss
} from 'lucide-react';
import type { Metadata } from 'next';

export async function generateMetadata(
  { params }: { params: Promise<{ slug: string }> }
): Promise<Metadata> {
  const { slug } = await params;
  const article = await getArticle(slug);

  if (!article) {
    return {
      title: 'Article Not Found',
    };
  }

  return {
    title: `${article.title} - Fresh Motors`,
    description: article.summary,
    alternates: {
      canonical: `https://www.freshmotors.net/articles/${slug}`,
    },
    openGraph: {
      title: article.title,
      description: article.summary,
      url: `https://www.freshmotors.net/articles/${slug}`,
      type: 'article',
      publishedTime: article.created_at,
      modifiedTime: article.updated_at,
      authors: ['Fresh Motors'],
      images: [
        {
          url: article.image || 'https://www.freshmotors.net/logo.png',
          width: 1200,
          height: 630,
          alt: article.title,
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: article.title,
      description: article.summary,
      images: [article.image || 'https://www.freshmotors.net/logo.png'],
    },
  };
}

// Production API URL
const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const LOCAL_API_URL = 'http://localhost:8000/api/v1';

const getApiUrl = () => {
  // Server-side: prefer internal Docker URL
  if (typeof window === 'undefined') {
    if (process.env.API_INTERNAL_URL) {
      return process.env.API_INTERNAL_URL;
    }
    if (process.env.RAILWAY_ENVIRONMENT === 'production') {
      return PRODUCTION_API_URL;
    }
    return process.env.NEXT_PUBLIC_API_URL || LOCAL_API_URL;
  }
  // Client-side: detect by hostname
  const host = window.location.hostname;
  if (host !== 'localhost' && host !== '127.0.0.1') {
    return PRODUCTION_API_URL;
  }
  return LOCAL_API_URL;
};

async function getArticle(slug: string): Promise<Article | null> {
  const { headers } = await import('next/headers');
  const headersList = await headers();
  const cookie = headersList.get('cookie') || '';

  const res = await fetch(`${getApiUrl()}/articles/${slug}/`, {
    cache: 'no-store',
    headers: {
      'Cookie': cookie
    }
  });

  if (!res.ok) {
    return null;
  }

  return res.json();
}

function formatDate(dateString: string) {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
}

export default async function ArticleDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = await getArticle(slug);

  if (!article) {
    notFound();
  }

  // Constants for URLs
  const PROD_MEDIA = 'https://heroic-healing-production-2365.up.railway.app';
  const LOCAL_MEDIA = 'http://localhost:8000';
  const isProduction = process.env.RAILWAY_ENVIRONMENT === 'production';

  // Helper to fix image URLs
  const fixUrl = (url: string | null | undefined): string => {
    if (!url) return 'https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=1200';
    const mediaUrl = isProduction ? PROD_MEDIA : LOCAL_MEDIA;
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url.replace('http://backend:8000', mediaUrl).replace('http://localhost:8000', mediaUrl);
    }
    return `${mediaUrl}${url}`;
  };

  const imageUrl = fixUrl(article.image);

  const fullUrl = `${process.env.NEXT_PUBLIC_SITE_URL || 'https://www.freshmotors.net'}/articles/${article.slug}`;

  // Prepare article content HTML - strip inline iframes (video shown separately below)
  const articleContentHtml = (article.content || '').replace(/<div[^>]*class="video-container"[^>]*>[\s\S]*?<\/div>/g, '').replace(/<iframe[^>]*>[\s\S]*?<\/iframe>/g, '');
  const hasYoutubeVideo = Boolean(article.youtube_url);
  const youtubeEmbedUrl = article.youtube_url
    ? `https://www.youtube.com/embed/${article.youtube_url.match(/(?:watch\?v=|embed\/|youtu\.be\/)([a-zA-Z0-9_-]+)/)?.[1] || ''}`
    : '';

  // Get article images URLs
  const articleImages = [
    article.thumbnail_url || article.image,
    article.image_2_url || article.image_2,
    article.image_3_url || article.image_3
  ].filter((url): url is string => Boolean(url)).map(url => fixUrl(url));

  // Extract YouTube video ID for thumbnail and schema
  const youtubeVideoId = article.youtube_url
    ? article.youtube_url.match(/(?:watch\?v=|embed\/|youtu\.be\/)([\w-]+)/)?.[1] || ''
    : '';

  // JSON-LD data for SEO
  const jsonLdData: Record<string, unknown>[] = [
    {
      "@context": "https://schema.org",
      "@type": "NewsArticle",
      "headline": article.title,
      "description": article.summary,
      "image": articleImages,
      "datePublished": article.created_at,
      "dateModified": article.updated_at || article.created_at,
      "author": {
        "@type": "Person",
        "name": article.author || "Fresh Motors Team"
      },
      "publisher": {
        "@type": "Organization",
        "name": "Fresh Motors",
        "logo": {
          "@type": "ImageObject",
          "url": `${process.env.NEXT_PUBLIC_SITE_URL}/logo.png`
        }
      },
      "mainEntityOfPage": {
        "@type": "WebPage",
        "@id": fullUrl
      },
      ...(hasYoutubeVideo ? {
        "video": {
          "@type": "VideoObject",
          "name": article.title,
          "description": article.summary,
          "thumbnailUrl": `https://img.youtube.com/vi/${youtubeVideoId}/maxresdefault.jpg`,
          "uploadDate": article.created_at,
          "embedUrl": youtubeEmbedUrl,
          "contentUrl": article.youtube_url
        }
      } : {})
    }
  ];

  // Add standalone VideoObject for better video indexing
  if (hasYoutubeVideo) {
    jsonLdData.push({
      "@context": "https://schema.org",
      "@type": "VideoObject",
      "name": article.title,
      "description": article.summary,
      "thumbnailUrl": `https://img.youtube.com/vi/${youtubeVideoId}/maxresdefault.jpg`,
      "uploadDate": article.created_at,
      "embedUrl": youtubeEmbedUrl,
      "contentUrl": article.youtube_url
    });
  }

  return (
    <>
      {/* JSON-LD Microdata */}
      {jsonLdData.map((data, i) => (
        <JsonLd key={i} data={data} />
      ))}

      {/* Track page view */}
      <ViewTracker articleSlug={article.slug} />

      {/* Reading Progress Bar */}
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

                {article.author_name ? (
                  <div className="flex items-center gap-2">
                    <User size={16} className="text-indigo-600" />
                    <span className="font-bold">Source:</span>
                    {article.author_channel_url ? (
                      <a
                        href={article.author_channel_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-indigo-600 hover:text-indigo-800 transition-colors font-bold"
                      >
                        {article.author_name}
                      </a>
                    ) : (
                      <span>{article.author_name}</span>
                    )}
                  </div>
                ) : (article.author && (
                  <div className="flex items-center gap-2">
                    <User size={16} className="text-indigo-600" />
                    <span>{article.author}</span>
                  </div>
                ))}

                {/* RSS Source Attribution */}
                {article.rss_feed && (
                  <div className="flex items-center gap-2">
                    <Rss size={16} className="text-orange-600" />
                    <span className="font-bold">Source:</span>
                    <span>{article.rss_feed.name}</span>
                    {article.source_url && (
                      <a
                        href={article.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-orange-600 hover:text-orange-800 transition-colors flex items-center gap-1"
                      >
                        <ExternalLink size={14} />
                        Original
                      </a>
                    )}
                  </div>
                )}

                {/* Reading Time */}
                <ReadingTime content={article.content} />

                {(article.average_rating > 0 && article.rating_count > 0) && (
                  <ArticleRating
                    initialRating={article.average_rating}
                    initialCount={article.rating_count}
                  />
                )}
              </div>

              {/* View Stats with Trending Badge */}
              {article.views && article.views > 0 && (
                <div className="mt-4">
                  <ViewStats
                    views={article.views}
                    createdAt={article.created_at}
                    isTrending={article.views > 100}
                  />
                </div>
              )}
            </div>

            {/* Title Section */}
            <div className="mb-8">
              {article.categories && article.categories.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {article.categories.map((cat: { id: number; name: string; slug: string }) => (
                    <Link
                      key={cat.id}
                      href={`/categories/${cat.slug}`}
                      className="inline-block bg-indigo-600 text-white px-4 py-2 rounded-full text-sm font-bold hover:bg-indigo-700 transition-colors"
                    >
                      {cat.name}
                    </Link>
                  ))}
                </div>
              )}
              <div className="flex items-start justify-between gap-4 mb-4">
                <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold text-gray-900 flex-1">
                  {article.title}
                </h1>
                <FavoriteButton
                  articleId={article.id}
                  initialIsFavorited={article.is_favorited}
                  size="lg"
                />
              </div>
              <p className="text-base sm:text-lg md:text-xl text-gray-600 max-w-3xl">
                {article.summary}
              </p>

              {/* Price Display with Currency Converter */}
              {article.price_usd && (
                <div className="mt-4">
                  <PriceConverter priceUsd={article.price_usd} />
                </div>
              )}
            </div>
          </div>

          <div className="max-w-4xl mx-auto">
            {/* Main Content */}
            <div className="space-y-8">

              {/* Top Article Ad (Conditional - hidden for now) */}
              <AdBanner format="leaderboard" />

              {/* Article Content */}
              <div className="bg-white rounded-xl shadow-md p-8">
                <ArticleContentWithImages
                  content={articleContentHtml}
                  images={articleImages}
                />
              </div>

              {/* Mid Article Ad (Conditional - hidden for now) */}
              <AdBanner format="rectangle" />

              {/* YouTube Video Section */}
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

              {/* Unified Vehicle Gallery - combines main images + gallery images */}
              {
                (() => {
                  // Build array of all images
                  const allImages: { url: string; alt: string }[] = [];
                  if (article.thumbnail_url) allImages.push({ url: fixUrl(article.thumbnail_url), alt: `${article.title} - View 1` });
                  if (article.image_2_url) allImages.push({ url: fixUrl(article.image_2_url), alt: `${article.title} - View 2` });
                  if (article.image_3_url) allImages.push({ url: fixUrl(article.image_3_url), alt: `${article.title} - View 3` });

                  // Add gallery images
                  if (article.images && article.images.length > 0) {
                    article.images.forEach((img: any, i: number) => {
                      const imgUrl = img.image_url || img.image;
                      if (imgUrl) {
                        allImages.push({ url: fixUrl(imgUrl), alt: img.caption || `${article.title} - View ${allImages.length + 1}` });
                      }
                    });
                  }

                  if (allImages.length === 0) return null;

                  const gridCols = allImages.length === 1 ? 'md:grid-cols-1 max-w-2xl mx-auto'
                    : allImages.length === 2 ? 'md:grid-cols-2'
                      : allImages.length <= 4 ? 'md:grid-cols-3'
                        : 'md:grid-cols-3 lg:grid-cols-4';

                  return (
                    <div className="bg-white rounded-xl shadow-md p-4 sm:p-8">
                      <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-4 sm:mb-6">Vehicle Gallery</h3>

                      {/* Mobile: Horizontal scroll slider */}
                      <div className="md:hidden">
                        <div className="flex gap-3 overflow-x-auto snap-x snap-mandatory scrollbar-hide pb-4 -mx-4 px-4">
                          {allImages.map((img, index) => (
                            <div key={index} className="relative flex-shrink-0 w-[85vw] aspect-video rounded-lg overflow-hidden snap-center">
                              <Image
                                src={img.url}
                                alt={img.alt}
                                fill
                                className="object-cover"
                              />
                              <div className="absolute bottom-2 left-2 bg-black/60 text-white text-xs px-2 py-1 rounded">
                                {index + 1} / {allImages.length}
                              </div>
                            </div>
                          ))}
                        </div>
                        <p className="text-center text-gray-500 text-sm mt-2">← Swipe to see more →</p>
                      </div>

                      {/* Desktop: Grid layout */}
                      <div className={`hidden md:grid gap-4 ${gridCols}`}>
                        {allImages.map((img, index) => (
                          <div key={index} className="relative aspect-video rounded-lg overflow-hidden">
                            <Image
                              src={img.url}
                              alt={img.alt}
                              fill
                              className="object-cover hover:scale-105 transition-transform duration-300"
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()
              }

              {/* Share Buttons */}
              <ShareButtons url={fullUrl} title={article.title} />

              {/* Rating System */}
              <RatingStars
                articleSlug={article.slug}
                initialRating={article.average_rating}
                ratingCount={article.rating_count}
              />

              {/* Tags */}
              {article.tag_names && article.tag_names.length > 0 && (
                <div className="bg-white rounded-xl shadow-md p-6">
                  <div className="flex items-center gap-3 flex-wrap">
                    <Tag size={20} className="text-indigo-600" />
                    {article.tag_names.map((tag: string) => (
                      <Link
                        key={tag}
                        href={`/articles?tag=${tag}`}
                        className="px-4 py-2 bg-indigo-50 text-indigo-700 rounded-full hover:bg-indigo-100 transition-colors font-medium border border-indigo-100"
                      >
                        {tag}
                      </Link>
                    ))}
                  </div>
                </div>
              )}


              {/* Related Articles Carousel */}
              {article.categories?.[0]?.slug && (
                <RelatedCarousel
                  categorySlug={article.categories[0].slug}
                  currentArticleSlug={article.slug}
                />
              )}

              {/* Comments Section */}
              <CommentSection articleId={article.id} />
            </div>
          </div>
        </div>
      </main>

    </>
  );
}
