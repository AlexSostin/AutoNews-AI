import { notFound } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import Header from '@/components/public/Header';
import Footer from '@/components/public/Footer';
import ArticleCard from '@/components/public/ArticleCard';
import AdBanner from '@/components/public/AdBanner';
import StickyBottomAd from '@/components/public/StickyBottomAd';
import ShareButtons from '@/components/public/ShareButtons';
import RatingStars from '@/components/public/RatingStars';
import ArticleContentWithImages from '@/components/public/ArticleContentWithImages';
import ArticleRating from '@/components/public/ArticleRating';
import CommentSection from '@/components/public/CommentSection';
import ImageGallery from '@/components/public/ImageGallery';
import Breadcrumbs from '@/components/public/Breadcrumbs';
import FavoriteButton from '@/components/public/FavoriteButton';
import ReadingProgressBar from '@/components/public/ReadingProgressBar';
import ReadingTime from '@/components/public/ReadingTime';
import ViewStats from '@/components/public/ViewStats';
import ViewTracker from '@/components/public/ViewTracker';
import PriceConverter from '@/components/public/PriceConverter';
import { Article } from '@/types';
import { Calendar, User, Eye, Tag, Star } from 'lucide-react';

// Production API URL
const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const LOCAL_API_URL = 'http://localhost:8001/api/v1';

const getApiUrl = () => {
  // Server-side: use production URL on Railway
  if (typeof window === 'undefined') {
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
  const res = await fetch(`${getApiUrl()}/articles/${slug}/`, {
    cache: 'no-store'
  });
  
  if (!res.ok) {
    return null;
  }
  
  return res.json();
}

async function getRelatedArticles(categorySlug: string, currentSlug: string) {
  const res = await fetch(`${getApiUrl()}/articles/?category=${categorySlug}&page_size=3`, {
    cache: 'no-store'
  });
  
  if (!res.ok) {
    return [];
  }
  
  const data = await res.json();
  return data.results.filter((a: any) => a.slug !== currentSlug).slice(0, 3);
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

  const relatedArticles = article.category_slug 
    ? await getRelatedArticles(article.category_slug, article.slug)
    : [];

  // Constants for URLs
  const PROD_MEDIA = 'https://heroic-healing-production-2365.up.railway.app';
  const LOCAL_MEDIA = 'http://localhost:8001';
  const isProduction = process.env.RAILWAY_ENVIRONMENT === 'production';
  
  // Helper to fix image URLs
  const fixUrl = (url: string | null | undefined): string => {
    if (!url) return 'https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=1200';
    const mediaUrl = isProduction ? PROD_MEDIA : LOCAL_MEDIA;
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url.replace('http://backend:8001', mediaUrl).replace('http://localhost:8001', mediaUrl);
    }
    return `${mediaUrl}${url}`;
  };

  const imageUrl = fixUrl(article.image);

  const fullUrl = `${process.env.NEXT_PUBLIC_SITE_URL || 'https://autonews-ai-production.up.railway.app'}/articles/${article.slug}`;
  
  // Prepare article content HTML with images between paragraphs
  const articleContentHtml = article.content;
  const hasYoutubeVideo = Boolean(article.youtube_url);
  const youtubeEmbedUrl = article.youtube_url ? article.youtube_url.replace('watch?v=', 'embed/') : '';
  
  // Get article images URLs
  const articleImages = [
    article.thumbnail_url || article.image,
    article.image_2_url || article.image_2,
    article.image_3_url || article.image_3
  ].filter((url): url is string => Boolean(url)).map(url => fixUrl(url));

  return (
    <>
      <Header />
      
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
            unoptimized
          />
        </div>

        <div className="container mx-auto px-4 py-8">
          {/* Breadcrumbs */}
          <div className="mb-6">
            <Breadcrumbs 
              items={[
                { label: article.category_name, href: `/categories/${article.category_slug}` },
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
              
              {article.author && (
                <div className="flex items-center gap-2">
                  <User size={16} className="text-indigo-600" />
                  <span>{article.author}</span>
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
            {article.category_name && (
              <Link 
                href={`/categories/${article.category_slug}`}
                className="inline-block bg-indigo-600 text-white px-4 py-2 rounded-full text-sm font-bold mb-4 hover:bg-indigo-700 transition-colors"
              >
                {article.category_name}
              </Link>
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

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
            {/* Main Content */}
            <div className="lg:col-span-2">

              {/* Top Article Ad */}
              <div className="mb-8 flex justify-center">
                <AdBanner format="leaderboard" />
              </div>

              {/* Article Content */}
              <div className="bg-white rounded-xl shadow-md p-8 mb-8">
                <ArticleContentWithImages 
                  content={articleContentHtml}
                  images={articleImages}
                />
              </div>

              {/* Mid Article Ad */}
              <div className="mb-8 flex justify-center">
                <AdBanner format="rectangle" />
              </div>

              {/* Video Screenshots Gallery */}
              {(article.image || article.image_2 || article.image_3) && (
                <div className="bg-white rounded-xl shadow-md p-4 sm:p-8 mb-8">
                  <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-4 sm:mb-6">Vehicle Gallery</h3>
                  
                  {/* Mobile: Horizontal scroll slider */}
                  <div className="md:hidden">
                    <div className="flex gap-3 overflow-x-auto snap-x snap-mandatory scrollbar-hide pb-4 -mx-4 px-4">
                      {article.thumbnail_url && (
                        <div className="relative flex-shrink-0 w-[85vw] aspect-video rounded-lg overflow-hidden snap-center">
                          <Image
                            src={fixUrl(article.thumbnail_url)}
                            alt={`${article.title} - View 1`}
                            fill
                            className="object-cover"
                          />
                          <div className="absolute bottom-2 left-2 bg-black/60 text-white text-xs px-2 py-1 rounded">
                            1 / {[article.thumbnail_url, article.image_2_url, article.image_3_url].filter(Boolean).length}
                          </div>
                        </div>
                      )}
                      {article.image_2_url && (
                        <div className="relative flex-shrink-0 w-[85vw] aspect-video rounded-lg overflow-hidden snap-center">
                          <Image
                            src={fixUrl(article.image_2_url)}
                            alt={`${article.title} - View 2`}
                            fill
                            className="object-cover"
                          />
                          <div className="absolute bottom-2 left-2 bg-black/60 text-white text-xs px-2 py-1 rounded">
                            2 / {[article.thumbnail_url, article.image_2_url, article.image_3_url].filter(Boolean).length}
                          </div>
                        </div>
                      )}
                      {article.image_3_url && (
                        <div className="relative flex-shrink-0 w-[85vw] aspect-video rounded-lg overflow-hidden snap-center">
                          <Image
                            src={fixUrl(article.image_3_url)}
                            alt={`${article.title} - View 3`}
                            fill
                            className="object-cover"
                          />
                          <div className="absolute bottom-2 left-2 bg-black/60 text-white text-xs px-2 py-1 rounded">
                            3 / {[article.thumbnail_url, article.image_2_url, article.image_3_url].filter(Boolean).length}
                          </div>
                        </div>
                      )}
                    </div>
                    <p className="text-center text-gray-500 text-sm mt-2">← Swipe to see more →</p>
                  </div>

                  {/* Desktop: Grid layout */}
                  <div className="hidden md:grid md:grid-cols-3 gap-4">
                    {article.thumbnail_url && (
                      <div className="relative aspect-video rounded-lg overflow-hidden">
                        <Image
                          src={fixUrl(article.thumbnail_url)}
                          alt={`${article.title} - View 1`}
                          fill
                          className="object-cover hover:scale-105 transition-transform duration-300"
                        />
                      </div>
                    )}
                    {article.image_2_url && (
                      <div className="relative aspect-video rounded-lg overflow-hidden">
                        <Image
                          src={fixUrl(article.image_2_url)}
                          alt={`${article.title} - View 2`}
                          fill
                          className="object-cover hover:scale-105 transition-transform duration-300"
                        />
                      </div>
                    )}
                    {article.image_3_url && (
                      <div className="relative aspect-video rounded-lg overflow-hidden">
                        <Image
                          src={fixUrl(article.image_3_url)}
                          alt={`${article.title} - View 3`}
                          fill
                          className="object-cover hover:scale-105 transition-transform duration-300"
                        />
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* YouTube Video */}
              {hasYoutubeVideo && (
                <div className="bg-white rounded-xl shadow-md p-6 mb-8">
                  <h3 className="text-2xl font-bold text-gray-900 mb-4">Watch Video</h3>
                  <div className="relative aspect-video">
                    <iframe
                      src={youtubeEmbedUrl}
                      title={article.title}
                      className="absolute inset-0 w-full h-full rounded-lg"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowFullScreen
                    />
                  </div>
                </div>
              )}

              {/* Car Specifications */}
              {article.specs && (
                <div className="bg-white rounded-xl shadow-md p-8 mb-8">
                  <h3 className="text-2xl font-bold text-gray-900 mb-6">Specifications</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {article.specs.make && (
                      <div className="border-b border-gray-200 pb-3">
                        <span className="text-sm font-semibold text-gray-500 uppercase">Make</span>
                        <p className="text-lg font-bold text-gray-900 mt-1">{article.specs.make}</p>
                      </div>
                    )}
                    {article.specs.model && (
                      <div className="border-b border-gray-200 pb-3">
                        <span className="text-sm font-semibold text-gray-500 uppercase">Model</span>
                        <p className="text-lg font-bold text-gray-900 mt-1">{article.specs.model}</p>
                      </div>
                    )}
                    {article.specs.year && (
                      <div className="border-b border-gray-200 pb-3">
                        <span className="text-sm font-semibold text-gray-500 uppercase">Year</span>
                        <p className="text-lg font-bold text-gray-900 mt-1">{article.specs.year}</p>
                      </div>
                    )}
                    {article.specs.engine && (
                      <div className="border-b border-gray-200 pb-3">
                        <span className="text-sm font-semibold text-gray-500 uppercase">Engine</span>
                        <p className="text-lg font-bold text-gray-900 mt-1">{article.specs.engine}</p>
                      </div>
                    )}
                    {article.specs.horsepower && (
                      <div className="border-b border-gray-200 pb-3">
                        <span className="text-sm font-semibold text-gray-500 uppercase">Horsepower</span>
                        <p className="text-lg font-bold text-gray-900 mt-1">{article.specs.horsepower} HP</p>
                      </div>
                    )}
                    {article.specs.transmission && (
                      <div className="border-b border-gray-200 pb-3">
                        <span className="text-sm font-semibold text-gray-500 uppercase">Transmission</span>
                        <p className="text-lg font-bold text-gray-900 mt-1">{article.specs.transmission}</p>
                      </div>
                    )}
                    {article.specs.fuel_type && (
                      <div className="border-b border-gray-200 pb-3">
                        <span className="text-sm font-semibold text-gray-500 uppercase">Fuel Type</span>
                        <p className="text-lg font-bold text-gray-900 mt-1">{article.specs.fuel_type}</p>
                      </div>
                    )}
                    {article.specs.price && (
                      <div className="border-b border-gray-200 pb-3">
                        <span className="text-sm font-semibold text-gray-500 uppercase">Price</span>
                        <p className="text-lg font-bold text-indigo-600 mt-1">${article.specs.price.toLocaleString()}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Image Gallery */}
              {article.gallery && article.gallery.length > 0 && (
                <ImageGallery images={article.gallery} />
              )}

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
                <div className="bg-white rounded-xl shadow-md p-6 mb-8">
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

              {/* Comments Section */}
              <CommentSection articleId={article.id} />
            </div>

            {/* Sidebar */}
            <div className="lg:col-span-1 space-y-8">
              {/* Sidebar Ad 1 */}
              <div className="bg-white rounded-xl shadow-md p-4 flex justify-center sticky top-8">
                <AdBanner format="rectangle" />
              </div>

              {/* Sidebar Ad 2 */}
              <div className="bg-white rounded-xl shadow-md p-4 flex justify-center">
                <AdBanner format="large-rectangle" />
              </div>

              {/* Related Articles */}
              {relatedArticles.length > 0 && (
                <div className="bg-white rounded-xl shadow-md p-6">
                  <h3 className="text-2xl font-bold text-gray-900 mb-6">Related Articles</h3>
                  <div className="space-y-6">{relatedArticles.map((related: any) => (
                      <Link
                        key={related.id}
                        href={`/articles/${related.slug}`}
                        className="block group"
                      >
                        <div className="relative h-32 mb-3 rounded-lg overflow-hidden">
                          <Image
                            src={fixUrl(related.image)}
                            alt={related.title}
                            fill
                            className="object-cover group-hover:scale-110 transition-transform duration-300"
                            unoptimized
                          />
                        </div>
                        <h4 className="font-bold text-gray-900 group-hover:text-indigo-600 transition-colors line-clamp-2 mb-2">
                          {related.title}
                        </h4>
                        <p className="text-sm text-gray-600 flex items-center gap-1">
                          <Calendar size={14} />
                          {formatDate(related.created_at)}
                        </p>
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
      
      <Footer />
    </>
  );
}
