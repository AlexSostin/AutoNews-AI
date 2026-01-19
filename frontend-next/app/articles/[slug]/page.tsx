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
import ArticleRating from '@/components/public/ArticleRating';
import CommentSection from '@/components/public/CommentSection';
import ImageGallery from '@/components/public/ImageGallery';
import Breadcrumbs from '@/components/public/Breadcrumbs';
import { Article } from '@/types';
import { Calendar, User, Eye, Tag, Star } from 'lucide-react';

const getApiUrl = () => {
  return process.env.NEXT_PUBLIC_API_URL_SERVER || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1';
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

  const imageUrl = article.image
    ? (article.image.startsWith('http://') || article.image.startsWith('https://') 
        ? article.image 
        : `${process.env.NEXT_PUBLIC_MEDIA_URL || 'http://localhost:8001/media'}${article.image}`)
    : 'https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=1200';

  const fullUrl = `${process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'}/articles/${article.slug}`;
  
  // Prepare article content HTML
  const articleContentHtml = article.content;
  const hasYoutubeVideo = Boolean(article.youtube_url);
  const youtubeEmbedUrl = article.youtube_url ? article.youtube_url.replace('watch?v=', 'embed/') : '';

  return (
    <>
      <Header />
      
      <main className="flex-1 bg-gray-50">
        {/* Hero Image */}
        <div className="relative h-[300px] sm:h-[400px] md:h-[500px] w-full">
          <Image
            src={imageUrl}
            alt={article.title}
            fill
            className="object-cover"
            priority
            unoptimized
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent"></div>
          
          {/* Article Title Overlay */}
          <div className="absolute bottom-0 left-0 right-0 p-8 text-white">
            <div className="container mx-auto">
              {article.category_name && (
                <Link 
                  href={`/categories/${article.category_slug}`}
                  className="inline-block bg-indigo-600 px-4 py-2 rounded-full text-sm font-bold mb-4 hover:bg-indigo-700 transition-colors"
                >
                  {article.category_name}
                </Link>
              )}
              <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold mb-4 drop-shadow-lg max-w-4xl">
                {article.title}
              </h1>
              <p className="text-base sm:text-lg md:text-xl text-white/90 max-w-3xl">
                {article.summary}
              </p>
            </div>
          </div>
        </div>

        <div className="container mx-auto px-4 py-12">
          {/* Breadcrumbs */}
          <Breadcrumbs 
            items={[
              { label: article.category_name, href: `/categories/${article.category_slug}` },
              { label: article.title }
            ]}
          />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
            {/* Main Content */}
            <div className="lg:col-span-2">
              {/* Article Meta */}
              <div className="bg-white rounded-xl shadow-md p-6 mb-8">
                <div className="flex flex-wrap gap-6 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <Calendar size={18} className="text-indigo-600" />
                    <span>{formatDate(article.created_at)}</span>
                  </div>
                  
                  {article.author && (
                    <div className="flex items-center gap-2">
                      <User size={18} className="text-indigo-600" />
                      <span>{article.author}</span>
                    </div>
                  )}
                  
                  {(article.views && article.views > 0) && (
                    <div className="flex items-center gap-2">
                      <Eye size={18} className="text-indigo-600" />
                      <span>{article.views} views</span>
                    </div>
                  )}
                  
                  <ArticleRating 
                    initialRating={article.average_rating}
                    initialCount={article.rating_count}
                  />
                </div>
              </div>

              {/* Top Article Ad */}
              <div className="mb-8 flex justify-center">
                <AdBanner format="leaderboard" />
              </div>

              {/* Article Content */}
              <div className="bg-white rounded-xl shadow-md p-8 mb-8 prose prose-lg max-w-none">
                <div 
                  id="articleContent"
                  dangerouslySetInnerHTML={{ __html: articleContentHtml }}
                  className="text-gray-800 leading-relaxed"
                />
              </div>

              {/* Mid Article Ad */}
              <div className="mb-8 flex justify-center">
                <AdBanner format="rectangle" />
              </div>

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
                            src={
                              related.image
                                ? (related.image.startsWith('http://') || related.image.startsWith('https://') 
                                    ? related.image 
                                    : `http://127.0.0.1:8001${related.image}`)
                                : 'https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=400'
                            }
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
